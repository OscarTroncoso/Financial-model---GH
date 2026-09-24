from dataclasses import asdict, replace
from datetime import date, datetime, timedelta, timezone
import json
import math
from pathlib import Path
import tempfile
import unittest
import duckdb

from portfolio_data.config import DataConfig, load_data_config
from portfolio_data.contracts import Datum, DataQualityError, Instrument, ensure_fresh, utc, validate_series
from portfolio_data.features import make_features
from portfolio_data.providers import Capture, fetch, normalize, period_end
from portfolio_data.storage import DataLake, digest, encode, parquet_rows

UTC=timezone.utc
STAMP=datetime(2026,1,8,12,tzinfo=UTC)
INST=Instrument('example','yfinance','EXAMPLE','EUR','Europe/Berlin','adjusted_close','EUR_per_share')
CFG=DataConfig((INST,),volatility_window=2,volatility_min_observations=2,periods_per_year=4)


def capture(values=(100,110,99), stamp=STAMP, days=('2026-01-02','2026-01-05','2026-01-06'), **changes):
    rows=[{'date':day,'Open':v,'High':v,'Low':v,'Close':v,'Adj Close':v,
           'Volume':100,'Dividends':0,'Stock Splits':0} for day,v in zip(days,values)]
    document={'currency':'EUR','timezone':'Europe/Berlin','rows':rows}
    document.update(changes)
    return Capture(INST,date(2026,1,1),date(2026,1,8),stamp,encode(document),
                   'application/json','fixture://synthetic','fixture-v1')


class ContractTests(unittest.TestCase):
    def test_timezone_normalization_and_naive_rejection(self):
        self.assertEqual(utc('2026-01-08T13:00:00+01:00'),STAMP)
        with self.assertRaises(DataQualityError): utc('2026-01-08T12:00:00')

    def test_dst_period_boundaries(self):
        self.assertEqual(period_end('2026-03-28','Europe/Berlin').hour,23)
        self.assertEqual(period_end('2026-03-29','Europe/Berlin').hour,22)
        self.assertEqual(period_end('2026-10-25','Europe/Berlin').hour,23)

    def test_future_incomplete_price_rejected(self):
        with self.assertRaisesRegex(DataQualityError,'Future'):
            normalize(capture(stamp=datetime(2026,1,2,12,tzinfo=UTC)))

    def test_availability_cannot_predate_ingestion_or_release(self):
        row=normalize(capture())[0]
        with self.assertRaises(DataQualityError):replace(row,available_to_model_time=STAMP-timedelta(seconds=1))
        with self.assertRaises(DataQualityError):replace(row,published_at=STAMP+timedelta(days=1))
        with self.assertRaises(DataQualityError):replace(row,revision_at=STAMP+timedelta(days=1))

    def test_invalid_positive_price_domain(self):
        row=normalize(capture())[0]
        for value in (0,-1,float('nan'),float('inf'),True):
            with self.subTest(value=value),self.assertRaises(DataQualityError):replace(row,value=value)

    def test_duplicate_and_gap_detection(self):
        rows=normalize(capture())
        with self.assertRaises(DataQualityError):validate_series(rows+[rows[0]])
        with self.assertRaises(DataQualityError):validate_series(rows,1)
        with self.assertRaises(DataQualityError):validate_series(rows[:1])

    def test_mixed_units_or_basis_rejected(self):
        rows=normalize(capture())
        for field,value in (('currency','USD'),('basis','close'),('unit','USD_per_share')):
            with self.assertRaises(DataQualityError):validate_series([rows[0],replace(rows[1],**{field:value})])

    def test_download_date_does_not_hide_staleness(self):
        rows=normalize(capture(stamp=STAMP+timedelta(days=30)))
        with self.assertRaisesRegex(DataQualityError,'Stale'):ensure_fresh(rows,STAMP+timedelta(days=30),7)

    def test_future_release_never_enters_features(self):
        rows=normalize(capture())
        future=STAMP+timedelta(days=1)
        rows[1]=replace(rows[1],published_at=future,available_to_model_time=future)
        with self.assertRaisesRegex(DataQualityError,'Future'):make_features(rows,STAMP,CFG)

    def test_strict_configuration(self):
        self.assertEqual(len(load_data_config('config/data.json').instruments),3)
        for changes in ({'max_gap_days':True},{'max_age_days':0},{'volatility_window':1}):
            with self.assertRaises(DataQualityError):replace(CFG,**changes)
        with self.assertRaises(DataQualityError):replace(INST,instrument_id='../escape')
        with self.assertRaises(DataQualityError):replace(INST,provider='tradingview_scraper')


class AdapterTests(unittest.TestCase):
    def test_payload_retains_corporate_actions_no_double_adjustment(self):
        c=capture();doc=json.loads(c.payload)
        doc['rows'][1]['Dividends']=10
        doc['rows'][1]['Stock Splits']=2
        values=normalize(replace(c,payload=encode(doc)))
        # Adj Close ratio already supplies .1, not .2 with dividend added again.
        self.assertAlmostEqual(make_features(values,STAMP,CFG)[0].return_1d,.1)

    def test_missing_basis_never_falls_back_to_close(self):
        c=capture();doc=json.loads(c.payload);del doc['rows'][1]['Adj Close']
        with self.assertRaisesRegex(DataQualityError,'basis'):normalize(replace(c,payload=encode(doc)))

    def test_bad_ohlc_volume_actions_currency(self):
        for key,value in (('Low',200),('Volume',-1),('Stock Splits',None),('Close',0)):
            c=capture();doc=json.loads(c.payload);doc['rows'][1][key]=value
            with self.assertRaises(DataQualityError):normalize(replace(c,payload=encode(doc)))
        with self.assertRaises(DataQualityError):normalize(capture(currency='USD'))

    def test_requested_date_range_enforced(self):
        with self.assertRaises(DataQualityError):normalize(replace(capture(),end=date(2026,1,5)))

    def test_ecb_daily_reference_identity_and_units(self):
        inst=Instrument('fx','ecb','D.USD.EUR.SP00.A','USD','Europe/Brussels','reference_rate','USD_per_EUR')
        payload=b'TIME_PERIOD,OBS_VALUE,FREQ,CURRENCY,CURRENCY_DENOM,OBS_STATUS\n2026-01-02,1.1,D,USD,EUR,A\n2026-01-05,1.21,D,USD,EUR,A\n'
        c=replace(capture(),instrument=inst,payload=payload,media_type='text/csv')
        rows=normalize(c)
        self.assertEqual(rows[0].value,1.1)
        self.assertEqual(rows[0].unit,'USD_per_EUR')
        for old,new in ((b'1.1',b'NaN'),(b',A',b',E'),(b',USD,',b',GBP,')):
            with self.assertRaises((DataQualityError,ValueError)):normalize(replace(c,payload=payload.replace(old,new)))

    def test_yahoo_fetch_explicit_adjustment_flags_and_metadata(self):
        import pandas as pd
        from unittest.mock import Mock, patch
        document=json.loads(capture().payload)
        frame=pd.DataFrame(document['rows']).drop(columns=['date'])
        frame.index=pd.DatetimeIndex([r['date'] for r in document['rows']],tz='Europe/Berlin')
        ticker=Mock()
        ticker.history.return_value=frame
        ticker.get_history_metadata.return_value={'currency':'EUR','exchangeTimezoneName':'Europe/Berlin'}
        with patch('yfinance.Ticker',return_value=ticker),patch('yfinance.set_tz_cache_location'):
            result=fetch(INST,date(2026,1,1),date(2026,1,8),Path('unused-cache'))
        kwargs=ticker.history.call_args.kwargs
        self.assertFalse(kwargs['auto_adjust'])
        self.assertFalse(kwargs['back_adjust'])
        self.assertFalse(kwargs['repair'])
        self.assertTrue(kwargs['keepna'])
        self.assertTrue(kwargs['raise_errors'])
        self.assertEqual(len(normalize(result)),3)
        ticker.get_history_metadata.return_value['currency']='USD'
        with patch('yfinance.Ticker',return_value=ticker),patch('yfinance.set_tz_cache_location'):
            with self.assertRaisesRegex(DataQualityError,'metadata mismatch'):
                fetch(INST,date(2026,1,1),date(2026,1,8),Path('unused-cache'))

    def test_ecb_fetch_verifies_tls_and_propagates_http_failure(self):
        from unittest.mock import Mock, patch
        inst=Instrument('fx','ecb','D.USD.EUR.SP00.A','USD','Europe/Brussels','reference_rate','USD_per_EUR')
        response=Mock()
        response.raise_for_status.side_effect=RuntimeError('HTTP failure')
        with patch('portfolio_data.providers.requests.get',return_value=response) as request:
            with self.assertRaisesRegex(RuntimeError,'HTTP failure'):
                fetch(inst,date(2026,1,1),date(2026,1,8),Path('unused-cache'))
        self.assertTrue(request.call_args.kwargs['verify'])
        self.assertIn('endPeriod=2026-01-07',request.call_args.args[0])


class FeatureTests(unittest.TestCase):
    def test_returns_and_volatility_by_hand(self):
        rows=make_features(normalize(capture()),STAMP,CFG)
        self.assertAlmostEqual(rows[0].return_1d,.1)
        self.assertIsNone(rows[0].realized_volatility)
        self.assertAlmostEqual(rows[1].return_1d,-.1)
        self.assertAlmostEqual(rows[1].realized_volatility,math.sqrt(.08))
        self.assertEqual(rows[1].available_to_model_time,STAMP)

    def test_dependency_includes_prior_price_release(self):
        rows=normalize(capture())
        later=STAMP+timedelta(hours=1)
        rows[0]=replace(rows[0],revision_at=later,available_to_model_time=later)
        result=make_features(rows,later,CFG)
        self.assertEqual(result[0].available_to_model_time,later)
        self.assertEqual(result[1].available_to_model_time,later)

    def test_future_suffix_cannot_change_existing_features(self):
        a=make_features(normalize(capture((100,110,99))),STAMP,CFG)
        b=make_features(normalize(capture((100,110,121))),STAMP,CFG)
        self.assertEqual(a[0],b[0])


class LakeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.lake=DataLake(Path(self.temp.name))

    def test_immutable_roundtrip_and_idempotent_ingestion(self):
        c=capture();sid=self.lake.ingest(c)
        self.assertEqual(self.lake.read_capture(sid),c)
        self.assertEqual(self.lake.read_rows(sid),normalize(c))
        path=self.lake.root/'clean'/sid/'observations.parquet'
        before=path.read_bytes();stamp=path.stat().st_mtime_ns
        self.assertEqual(self.lake.ingest(c),sid)
        self.assertEqual(path.read_bytes(),before)
        self.assertEqual(path.stat().st_mtime_ns,stamp)
        with duckdb.connect(str(self.lake.catalog),read_only=True) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM snapshots').fetchone()[0],1)

    def test_same_snapshot_features_are_identical(self):
        sid=self.lake.ingest(capture())
        fid=self.lake.build_features([sid],STAMP,CFG)
        path=self.lake.root/'features'/fid/'features.parquet'
        content=path.read_bytes()
        self.assertEqual(self.lake.build_features([sid],STAMP,CFG),fid)
        self.assertEqual(path.read_bytes(),content)
        self.lake.verify_features(fid)

    def test_revision_is_selected_only_after_its_availability(self):
        a=self.lake.ingest(capture())
        later=STAMP+timedelta(days=1)
        b=self.lake.ingest(capture((100,110,121),stamp=later))
        self.assertNotEqual(a,b)
        self.assertEqual(self.lake.as_of([a,b],STAMP)[-1].value,99)
        self.assertEqual(self.lake.as_of([a,b],later)[-1].value,121)
        self.assertEqual(self.lake.as_of([a],later)[-1].value,99)
        self.assertEqual(self.lake.as_of([a,b],STAMP-timedelta(seconds=1)),[])

    def test_conflicting_same_time_vintage_rejected(self):
        a=self.lake.ingest(capture())
        b=self.lake.ingest(capture((100,110,121)))
        with self.assertRaisesRegex(DataQualityError,'Conflicting'):self.lake.as_of([a,b],STAMP)

    def test_corrupt_raw_is_rejected(self):
        sid=self.lake.ingest(capture())
        (self.lake.root/'raw'/sid/'payload.dat').write_bytes(b'changed')
        with self.assertRaises(DataQualityError):self.lake.read_rows(sid)

    def test_corrupt_parquet_is_rejected(self):
        sid=self.lake.ingest(capture())
        (self.lake.root/'clean'/sid/'observations.parquet').write_bytes(b'changed')
        with self.assertRaises(DataQualityError):self.lake.as_of([sid],STAMP)

    def test_corrupt_feature_is_rejected(self):
        sid=self.lake.ingest(capture());fid=self.lake.build_features([sid],STAMP,CFG)
        (self.lake.root/'features'/fid/'features.parquet').write_bytes(b'changed')
        with self.assertRaises(DataQualityError):self.lake.verify_features(fid)

    def test_bad_input_preserved_raw_but_not_published(self):
        with self.assertRaises(DataQualityError):self.lake.ingest(capture((0,110,99)))
        self.assertEqual(len(list((self.lake.root/'raw').glob('*/payload.dat'))),1)
        self.assertEqual(list((self.lake.root/'clean').glob('*/manifest.json')),[])
        with duckdb.connect(str(self.lake.catalog),read_only=True) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM snapshots').fetchone()[0],0)

    def test_missing_future_and_stale_inputs_fail_closed(self):
        sid=self.lake.ingest(capture())
        for stamp in (STAMP-timedelta(seconds=1),STAMP+timedelta(days=30)):
            with self.assertRaises(DataQualityError):self.lake.build_features([sid],stamp,CFG)
        self.assertEqual(list((self.lake.root/'features').glob('*/manifest.json')),[])

    def test_no_path_traversal_or_duplicate_snapshot_input(self):
        sid=self.lake.ingest(capture())
        with self.assertRaises(DataQualityError):self.lake.read_rows('../escape')
        with self.assertRaises(DataQualityError):self.lake.as_of([sid,sid],STAMP)

    def test_wrong_feature_currency_rejected(self):
        sid=self.lake.ingest(capture())
        cfg=replace(CFG,instruments=(replace(INST,currency='USD'),))
        with self.assertRaises(DataQualityError):self.lake.build_features([sid],STAMP,cfg)
