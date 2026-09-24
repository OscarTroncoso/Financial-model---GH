"""Daily input contract; no vendor connectivity or phase-2 storage pipeline."""

from dataclasses import dataclass
from datetime import datetime
import math


@dataclass(frozen=True)
class Observation:
    """One completed market period, timezone-aware timestamps, decimal returns.

    available_to_model_time covers both supplied returns. None safe_return uses
    the configured ACT/365 net rate. First observation is a zero-return inception.
    """
    timestamp: datetime
    available_to_model_time: datetime
    risky_return: float
    safe_return: float | None = None

    def __post_init__(self) -> None:
        for stamp in (self.timestamp, self.available_to_model_time):
            if stamp.tzinfo is None or stamp.utcoffset() is None:
                raise ValueError("Timezone-aware timestamps required")
        if self.available_to_model_time > self.timestamp:
            raise ValueError("Observation unavailable at decision timestamp")
        for value in (self.risky_return, self.safe_return):
            if value is not None and (not math.isfinite(value) or value < -1):
                raise ValueError("Return must be finite and >= -100%")


def validate_path(observations: tuple[Observation, ...]) -> None:
    """Fail before returning any allocation if the full supplied path is invalid."""
    if len(observations) < 2:
        raise ValueError("Need inception and at least one market observation")
    first = observations[0]
    if first.risky_return != 0 or first.safe_return not in (None, 0):
        raise ValueError("First observation must be zero-return inception")
    for prior, current in zip(observations, observations[1:]):
        if current.timestamp <= prior.timestamp or current.timestamp.date() <= prior.timestamp.date():
            raise ValueError("Strictly increasing daily observations required")
        if (current.timestamp.date() - prior.timestamp.date()).days > 7:
            raise ValueError("Missing daily data: gap exceeds seven calendar days")
