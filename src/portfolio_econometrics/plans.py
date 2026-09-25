"""Translate research forecasts into proposals subject to independent risk sizing."""
from dataclasses import asdict
from datetime import datetime
from portfolio_fx.contracts import Candle,Rate,FXConfig,ExecutionConfig
from portfolio_fx.data import NotReady,candles_asof
from portfolio_data.contracts import utc
from portfolio_fx_risk.contracts import Capacity,RiskConfig,VolatilityConfig
from portfolio_fx_risk.volatility import forecast as volatility_forecast
from portfolio_fx_risk.sizing import size,stop_distance
from .forecast import forecast
from .contracts import EconometricConfig
from .audit import digest,source_hash


def direction(mean: float,execution: ExecutionConfig,risk: RiskConfig,config: EconometricConfig) -> tuple[int,float]:
    """First-order log-return cost hurdle, a policy rather than guaranteed alpha.

    Adverse carry reserve uses the full configured maximum holding period.
    Actual execution P&L still charges spread, slippage, fees and realized carry.
    """
    side=1 if mean>0 else -1
    carry=execution.long_carry_annual_rate if side>0 else execution.short_carry_annual_rate
    threshold=2*execution.cost_rate+config.signal_buffer+max(0.,-carry)*risk.maximum_holding_hours/(365*24)
    return (side if abs(mean)>threshold else 0),threshold


def propose(rows: tuple[Candle,...],rates: tuple[Rate,...],time: datetime|str,model: str,capacity: Capacity,
            risk: RiskConfig=RiskConfig(),volatility: VolatilityConfig=VolatilityConfig(),
            features: FXConfig=FXConfig(),execution: ExecutionConfig=ExecutionConfig(),
            econometrics: EconometricConfig=EconometricConfig()) -> dict:
    prediction=forecast(rows,rates,time,model,econometrics); value=prediction['payload']; side=0; threshold=None; vol=None
    result=dict(state='NO_TRADE',reason=value['reason'])
    if value['status']=='READY':
        side,threshold=direction(value['mean'],execution,risk,econometrics)
        result=dict(state='NO_TRADE',reason='below_configured_cost_hurdle')
        if side:
            try:
                known=candles_asof(rows,time)
                if not known or (utc(time)-known[-1].end).total_seconds()>features.max_30m_age_minutes*60:
                    raise NotReady('stale_entry_reference')
                vol=volatility_forecast(rows,time,volatility,features.max_4h_age_minutes,features.max_history_gap_hours)
                entry=known[-1].close; distance=stop_distance(entry,vol['sigma'],risk)
                result=size(entry,side,distance,capacity,risk,execution)
            except NotReady as error: result=dict(state='NO_TRADE',reason=str(error))
    body=dict(decision_time=value['decision_time'],forecast=prediction,volatility=vol,sizing=result,
              requested_direction=side,cost_hurdle=threshold,risk_config=asdict(risk),volatility_config=asdict(volatility),
              execution_config=asdict(execution),capacity=asdict(capacity),model_version='econometric_risk_v1',
              source_hash=source_hash(),executable=False,execution_scope='research_only_no_broker')
    return dict(plan_id=digest(body),payload=body)
