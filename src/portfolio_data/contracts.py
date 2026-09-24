"""Strict data contracts. Availability is evidence, never guessed vintage history."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import math
import re
from zoneinfo import ZoneInfo


class DataQualityError(ValueError):
    """Data must not enter model inputs until this failure is resolved."""


def utc(value: datetime | str) -> datetime:
    """Normalize aware instants; naive dates/times are ambiguous and rejected."""
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise DataQualityError("Timezone-aware timestamp required")
    return stamp.astimezone(timezone.utc)


def iso(value: datetime | str) -> str:
    return utc(value).isoformat()


@dataclass(frozen=True)
class Instrument:
    instrument_id: str
    provider: str
    symbol: str
    currency: str
    timezone: str
    basis: str
    unit: str

    def __post_init__(self) -> None:
        if not all(isinstance(v, str) and v for v in asdict(self).values()):
            raise DataQualityError("Instrument fields must be nonempty text")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", self.instrument_id):
            raise DataQualityError("Invalid instrument ID")
        if self.provider not in {"yfinance", "ecb"}:
            raise DataQualityError("Unknown provider")
        if self.basis not in {"adjusted_close", "close", "reference_rate"}:
            raise DataQualityError("Unknown price basis")
        if not re.fullmatch(r"[A-Z]{3}", self.currency):
            raise DataQualityError("ISO currency required")
        ZoneInfo(self.timezone)
        if self.provider == "ecb" and (self.basis != "reference_rate" or self.symbol != "D.USD.EUR.SP00.A"
            or self.currency != "USD" or self.unit != "USD_per_EUR" or self.timezone != "Europe/Brussels"):
            raise DataQualityError("ECB adapter currently supports only daily USD per EUR reference rates")
        if self.provider == "yfinance" and self.basis == "reference_rate":
            raise DataQualityError("Yahoo series is not an ECB reference rate")


@dataclass(frozen=True)
class Datum:
    """One positive price/rate vintage; raw corporate-action fields remain in bronze.

    observation_time is the conservative end of a completed daily period.
    Source publication/revision instants are optional evidence, not date labels.
    available_to_model_time >= all known instants AND ingestion time. A current
    provider download never creates an earlier verified historical vintage.
    """
    instrument_id: str
    observation_time: datetime
    value: float
    currency: str
    basis: str
    unit: str
    ingested_at: datetime
    available_to_model_time: datetime
    published_at: datetime | None = None
    revision_at: datetime | None = None
    availability_basis: str = "observed_at_ingestion"

    def __post_init__(self) -> None:
        for field in ("observation_time", "ingested_at", "available_to_model_time", "published_at", "revision_at"):
            value = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, utc(value))
        if type(self.value) not in (int,float) or not math.isfinite(self.value) or self.value <= 0:
            raise DataQualityError("Price/reference rate must be finite and strictly positive")
        object.__setattr__(self,"value",float(self.value))
        if self.observation_time > self.ingested_at:
            raise DataQualityError("Future/incomplete observation")
        times = [self.observation_time,self.ingested_at]
        times += [t for t in (self.published_at,self.revision_at) if t is not None]
        if self.available_to_model_time < max(times):
            raise DataQualityError("Availability precedes evidence")
        if self.availability_basis != "observed_at_ingestion":
            raise DataQualityError("Unsupported availability claim")

    def to_dict(self) -> dict:
        return {key:iso(value) if isinstance(value,datetime) else value for key,value in asdict(self).items()}


def validate_series(rows: list[Datum], max_gap_days: int = 7) -> list[Datum]:
    """Reject conflicting/duplicate dates and material gaps, never forward-fill.

    Calendar-day tolerance is configurable, not a complete exchange calendar.
    One series only, at least two completed observations to derive a return.
    """
    if type(max_gap_days) is not int or max_gap_days < 1:
        raise DataQualityError("Positive integer gap tolerance required")
    if len(rows) < 2:
        raise DataQualityError("Need at least two observations")
    ordered = sorted(rows,key=lambda r:r.observation_time)
    identity = {(r.instrument_id,r.currency,r.basis,r.unit) for r in ordered}
    if len(identity) != 1:
        raise DataQualityError("Mixed instruments, units or price bases")
    for a,b in zip(ordered,ordered[1:]):
        elapsed = (b.observation_time-a.observation_time).total_seconds()/86400
        if elapsed < .5:
            raise DataQualityError("Duplicate/subdaily observations in daily series")
        if elapsed > max_gap_days + 1/24:
            raise DataQualityError("Missing observations: excessive daily gap")
    return ordered


def ensure_fresh(rows: list[Datum], decision_time: datetime, max_age_days: int) -> None:
    """A fresh download of old data is still stale. Check observation age."""
    decision_time = utc(decision_time)
    if type(max_age_days) is not int or max_age_days < 1:
        raise DataQualityError("Positive integer age tolerance required")
    if not rows:
        raise DataQualityError("No data available at decision time")
    if any(r.available_to_model_time > decision_time or r.observation_time > decision_time for r in rows):
        raise DataQualityError("Future release/observation cannot enter model inputs")
    if (decision_time-max(r.observation_time for r in rows)).total_seconds() > max_age_days*86400:
        raise DataQualityError("Stale series at decision time")
