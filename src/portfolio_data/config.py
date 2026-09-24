"""Configuration for free daily data sources and conservative validation."""
from dataclasses import dataclass, fields
import json
from pathlib import Path
from .contracts import DataQualityError, Instrument


@dataclass(frozen=True)
class DataConfig:
    instruments: tuple[Instrument, ...]
    max_gap_days: int = 7
    max_age_days: int = 7
    volatility_window: int = 20
    volatility_min_observations: int = 5
    periods_per_year: int = 252

    def __post_init__(self) -> None:
        if not self.instruments or len({i.instrument_id for i in self.instruments}) != len(self.instruments):
            raise DataQualityError("Unique, nonempty instrument universe required")
        for name in ("max_gap_days","max_age_days","volatility_window","volatility_min_observations","periods_per_year"):
            if type(getattr(self,name)) is not int or getattr(self,name) < 1:
                raise DataQualityError(f"{name} must be a positive integer")
        if not 2 <= self.volatility_min_observations <= self.volatility_window:
            raise DataQualityError("Invalid volatility window")


def load_data_config(path: str | Path) -> DataConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data,dict) or data.keys()-{f.name for f in fields(DataConfig)}:
        raise DataQualityError("Unknown/malformed data configuration")
    try:
        data["instruments"] = tuple(Instrument(**item) for item in data["instruments"])
        return DataConfig(**data)
    except (TypeError,KeyError) as error:
        raise DataQualityError("Malformed instruments") from error
