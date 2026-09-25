"""Risk proposals preserve the directional signal and causal volatility evidence."""
from dataclasses import asdict
from portfolio_fx.contracts import Candle,Rate,FXConfig,ExecutionConfig
from portfolio_fx.signals import signal
from portfolio_fx.data import NotReady
from .contracts import RiskConfig,VolatilityConfig,Capacity
from .volatility import forecast
from .sizing import size,stop_distance
from .audit import digest,source_hash


def propose(rows: tuple[Candle,...],rates: tuple[Rate,...],time,model: str,capacity: Capacity,
            risk: RiskConfig=RiskConfig(),volatility: VolatilityConfig=VolatilityConfig(),
            features: FXConfig=FXConfig(),execution: ExecutionConfig=ExecutionConfig()) -> dict:
    candidate=signal(rows,rates,time,model,features); directional=candidate['payload']
    result=dict(state='NO_TRADE',reason=directional['reason']); vol=None
    if directional['direction']:
        try:
            vol=forecast(rows,time,volatility,features.max_4h_age_minutes,features.max_history_gap_hours)
            distance=stop_distance(directional['entry_reference'],vol['sigma'],risk)
            result=size(directional['entry_reference'],directional['direction'],distance,capacity,risk,execution)
        except NotReady as error: result=dict(state='NO_TRADE',reason=str(error))
    body=dict(decision_time=directional['decision_time'],directional_signal=candidate,volatility=vol,
              sizing=result,risk_config=asdict(risk),volatility_config=asdict(volatility),execution_config=asdict(execution),
              capacity=asdict(capacity),model_version='fx_risk_v1',source_hash=source_hash(),
              executable=False,execution_scope='research_only_no_broker')
    return dict(plan_id=digest(body),payload=body)
