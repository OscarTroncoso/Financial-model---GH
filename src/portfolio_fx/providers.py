"""Free Yahoo 30m and FRED policy-proxy capture; availability is ingestion."""
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
import csv
import io
import json
import math
from urllib.request import Request, urlopen
from .contracts import Candle, Rate
from .audit import encoded,digest


def normalize_yahoo(document: dict) -> tuple[Candle,...]:
    from portfolio_data.contracts import utc
    stamp=utc(document['ingested_at'])
    if document['symbol']!='EURUSD=X' or document['currency']!='USD': raise ValueError('Yahoo EURUSD metadata mismatch')
    result=[]
    for row in document['rows']:
        start=utc(row['start']); end=start+timedelta(minutes=30)
        if end>stamp: continue  # unfinished current candle retained only in bronze
        if all(row[key] is None for key in ('Open','High','Low','Close')): continue  # missing quote, never filled
        result.append(Candle(start,end,row['Open'],row['High'],row['Low'],row['Close'],stamp,stamp,'Yahoo EURUSD=X '+document['adapter']))
    if not result: raise ValueError('No completed Yahoo candles')
    return tuple(result)


def normalize_fred(payload: str,series: str,currency: str,stamp: datetime) -> tuple[Rate,...]:
    if (series,currency) not in (('DFEDTARU','USD'),('ECBDFR','EUR')): raise ValueError('Unsupported policy proxy')
    rows=[]
    for row in csv.DictReader(io.StringIO(payload)):
        day=row.get('observation_date',row.get('DATE'))
        value=row.get(series)
        if not day or value in (None,'.',''): continue
        # Conservative next UTC midnight for the dated observation; actual
        # release history unknown, so available_at never precedes capture.
        observed=datetime.fromisoformat(day).replace(tzinfo=timezone.utc)+timedelta(days=1)
        if observed>stamp: continue
        rows.append(Rate(currency,float(value)/100,observed,stamp,stamp,'FRED '+series))
    if not rows: raise ValueError('No valid FRED observations')
    return tuple(rows)


def fetch_fred_csv(series: str, start_date: str) -> str:
    """Public CSV via Python HTTPS transport; no API key or curl dependency.

    A bounded response is validated by normalize_fred before model use. HTTP
    failures remain explicit rather than substituting stale or invented rates.
    """
    from datetime import date
    if series not in ('DFEDTARU','ECBDFR'): raise ValueError('Unsupported policy proxy')
    date.fromisoformat(start_date)
    url='https://fred.stlouisfed.org/graph/fredgraph.csv?id='+series+'&cosd='+start_date
    # Explicit Accept: text/csv timed out in live endpoint checks; let the
    # CSV URL determine its representation. Keep TLS verification enabled.
    request=Request(url,headers={'User-Agent':'PortfolioResearchLab/0.8.1'})
    with urlopen(request,timeout=30) as response:
        raw=response.read(2_000_001)
    if len(raw)>2_000_000: raise ValueError('FRED response exceeds research size limit')
    return raw.decode('utf-8-sig')


def capture(output: Path,days: int=30) -> dict:
    """New immutable local capture directory, no secrets or paid subscription.

    Free intraday history is limited. A failed rate source is explicitly
    recorded; its absence leads to NO_TRADE for the rate baseline.
    """
    if type(days) is not int or not 1<=days<=59: raise ValueError('Capture horizon must be 1..59 days')
    output.mkdir(parents=True,exist_ok=False)
    import yfinance as yf
    yf.set_tz_cache_location(str(output/'cache'))
    now=datetime.now(timezone.utc); ticker=yf.Ticker('EURUSD=X')
    frame=ticker.history(start=now-timedelta(days=days),end=now,interval='30m',
        auto_adjust=False,back_adjust=False,repair=False,actions=False,keepna=True,raise_errors=True,timeout=30)
    meta=ticker.get_history_metadata()
    stamp=datetime.now(timezone.utc)
    rows=[{'start':index.to_pydatetime().astimezone(timezone.utc).isoformat(),
           **{key:float(row[key]) if math.isfinite(float(row[key])) else None for key in ('Open','High','Low','Close')}} for index,row in frame.iterrows()]
    document=dict(symbol='EURUSD=X',currency=meta.get('currency'),adapter='yfinance-'+yf.__version__,ingested_at=stamp.isoformat(),rows=rows)
    (output/'yahoo-library-output.json').write_bytes(encoded(document))
    candles=normalize_yahoo(document); rates=[]; errors={}
    for series,currency in (('DFEDTARU','USD'),('ECBDFR','EUR')):
        try:
            raw=fetch_fred_csv(series,(now-timedelta(days=days+14)).date().isoformat())
            (output/(series+'.csv')).write_text(raw,encoding='utf-8')
            captured=datetime.now(timezone.utc)
            rates.extend(normalize_fred(raw,series,currency,captured))
        except Exception as error:
            errors[series]=type(error).__name__+': '+str(error)
    result=dict(candles=[asdict(r) for r in candles],rates=[asdict(r) for r in rates],
                captured_at=datetime.now(timezone.utc),source_errors=errors,historical_vintages=False)
    body=json.loads(encoded(result)); bundle={'checksum':digest(body),'payload':body}
    (output/'normalized.json').write_bytes(encoded(bundle))
    return dict(candles=len(candles),missing_quote_rows=sum(all(r[k] is None for k in ('Open','High','Low','Close')) for r in rows),rates=len(rates),source_errors=errors,checksum=bundle['checksum'],
                historical_backtest_eligible=False,path=str(output/'normalized.json'))
