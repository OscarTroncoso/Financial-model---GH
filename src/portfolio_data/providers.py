"""Free-source adapters. No subscription, credential, scraper or trading calls."""
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone
import csv
import io
import json
import math
from pathlib import Path
from urllib.parse import urlencode
from curl_cffi import requests
from zoneinfo import ZoneInfo

from .contracts import Datum, DataQualityError, Instrument, utc


@dataclass(frozen=True)
class Capture:
    instrument: Instrument
    start: date
    end: date
    ingested_at: datetime
    payload: bytes
    media_type: str
    source_url: str
    adapter_version: str


def period_end(day: str, zone: str) -> datetime:
    """Conservative next local midnight, NOT a claim of exchange closing time."""
    next_day = date.fromisoformat(day) + timedelta(days=1)
    return datetime.combine(next_day,time.min,ZoneInfo(zone)).astimezone(timezone.utc)


def fetch(instrument: Instrument, start: date, end: date, cache: Path) -> Capture:
    """Dates are [start,end), daily only. Network failures never synthesize data."""
    if start >= end:
        raise DataQualityError("Start must precede exclusive end")
    if instrument.provider == "yfinance":
        import yfinance as yf
        yf.set_tz_cache_location(str(cache))
        ticker = yf.Ticker(instrument.symbol)
        frame = ticker.history(start=start.isoformat(),end=end.isoformat(),interval="1d",
             actions=True,auto_adjust=False,back_adjust=False,repair=False,keepna=True,
             rounding=False,timeout=20,raise_errors=True)
        if frame.empty:
            raise DataQualityError("Yahoo returned no daily data")
        meta = ticker.get_history_metadata()
        currency = meta.get("currency")
        zone = meta.get("exchangeTimezoneName")
        if currency != instrument.currency or zone != instrument.timezone:
            raise DataQualityError(f"Provider metadata mismatch: currency={currency}, timezone={zone}")
        rows = []
        for index,row in frame.iterrows():
            values = {str(key):None if not math.isfinite(float(value)) else float(value) for key,value in row.items()}
            values["date"] = index.date().isoformat()
            rows.append(values)
        # Bronze preserves the library output, not falsely labelled raw HTTP.
        payload = json.dumps({"currency":currency,"timezone":zone,"rows":rows},
                             sort_keys=True,allow_nan=False).encode()
        return Capture(instrument,start,end,datetime.now(timezone.utc),payload,"application/json",
                       "https://finance.yahoo.com/quote/"+instrument.symbol,"yfinance-"+yf.__version__)
    url = "https://data-api.ecb.europa.eu/service/data/EXR/"+instrument.symbol+"?"+urlencode({
        "startPeriod":start.isoformat(),"endPeriod":(end-timedelta(days=1)).isoformat(),"format":"csvdata"})
    response = requests.get(url,headers={"Accept":"text/csv","User-Agent":"PortfolioResearchLab/0.4"},
                            timeout=30,verify=True)
    response.raise_for_status()
    payload = response.content
    if len(payload)>20_000_000:
        raise DataQualityError("Response exceeds daily research size limit")
    return Capture(instrument,start,end,datetime.now(timezone.utc),payload,"text/csv",url,"ecb-sdmx-v1")


def normalize(capture: Capture) -> list[Datum]:
    """Validate values, corporate-action fields, date range and currency/unit.

    Adj Close ratios already incorporate vendor adjustments; do not add dividends
    or splits again. Original OHLC/action fields stay in the immutable payload.
    ECB rates are reference observations, never executable FX bid/ask quotes.
    """
    inst = capture.instrument
    stamp = utc(capture.ingested_at)
    if inst.provider == "yfinance":
        document = json.loads(capture.payload)
        if document.get("currency") != inst.currency or document.get("timezone") != inst.timezone:
            raise DataQualityError("Yahoo currency/timezone mismatch")
        data = document["rows"]
    else:
        data = list(csv.DictReader(io.StringIO(capture.payload.decode("utf-8-sig"))))
    rows = []
    for row in data:
        if inst.provider == "yfinance":
            day = row["date"]
            for key in ("Open","High","Low","Close"):
                if row.get(key) is None or not math.isfinite(row[key]) or row[key] <= 0:
                    raise DataQualityError("Missing/nonpositive OHLC")
            if not row["Low"] <= min(row["Open"],row["Close"]) <= max(row["Open"],row["Close"]) <= row["High"]:
                raise DataQualityError("Inconsistent OHLC")
            for key in ("Volume","Dividends","Stock Splits"):
                value = row.get(key)
                if value is None or not math.isfinite(value) or value < 0:
                    raise DataQualityError("Missing/invalid volume or corporate action")
            value = row.get("Adj Close" if inst.basis == "adjusted_close" else "Close")
            if value is None:
                raise DataQualityError("Requested price basis is missing; no silent fallback")
        else:
            if row.get("CURRENCY") != "USD" or row.get("CURRENCY_DENOM") != "EUR" or row.get("FREQ") != "D":
                raise DataQualityError("ECB series identity mismatch")
            if row.get("OBS_STATUS") not in ("A",):
                raise DataQualityError("Non-normal/missing ECB observation status")
            day = row["TIME_PERIOD"]
            try:
                value = float(row["OBS_VALUE"])
            except (KeyError,ValueError) as error:
                raise DataQualityError("Missing ECB observation value") from error
        if not capture.start <= date.fromisoformat(day) < capture.end:
            raise DataQualityError("Observation outside requested range")
        observed = period_end(day,inst.timezone)
        rows.append(Datum(inst.instrument_id,observed,value,inst.currency,inst.basis,
                          inst.unit,stamp,max(stamp,observed)))
    return rows
