"""Causal price-derived features from an explicitly selected vintage snapshot."""
from dataclasses import dataclass
from datetime import datetime
from .config import DataConfig
from .contracts import Datum, DataQualityError, ensure_fresh, validate_series
from portfolio_lab.rules import realized_volatility


@dataclass(frozen=True)
class Feature:
    instrument_id: str
    observation_time: datetime
    available_to_model_time: datetime
    currency: str
    basis: str
    unit: str
    return_1d: float
    realized_volatility: float | None
    window_observations: int


def make_features(rows: list[Datum], decision_time: datetime, config: DataConfig) -> list[Feature]:
    """r_t=P_t/P_previous-1; trailing sample std*sqrt(A), no cross-series join.

    These returns are in the instrument's quote currency. No EUR portfolio
    conversion or multi-sleeve allocation is implied. Availability is the max
    across every price dependency, including the first price of each return.
    A result computed from a downloaded revised history is available now, never
    assigned a fictitious historical publication timestamp.
    """
    ordered = validate_series(rows,config.max_gap_days)
    ensure_fresh(ordered,decision_time,config.max_age_days)
    returns, dependencies, result = [], [], []
    for previous,current in zip(ordered,ordered[1:]):
        returns.append(current.value/previous.value-1)
        dependencies.append(max(previous.available_to_model_time,current.available_to_model_time))
        available = max(dependencies[-config.volatility_window:])
        if available > decision_time:
            raise DataQualityError("Future dependency in feature")
        volatility = realized_volatility(returns,config.volatility_window,
                                         config.volatility_min_observations,config.periods_per_year)
        result.append(Feature(current.instrument_id,current.observation_time,available,
                              current.currency,current.basis,current.unit,returns[-1],volatility,
                              min(len(returns),config.volatility_window)))
    return result
