"""Post-run scoring and predeclared research rejection; never trade inputs."""
from collections import Counter
from dataclasses import asdict
import math
import numpy as np
from portfolio_data.contracts import utc
from portfolio_fx.data import aggregate
from portfolio_regimes.engine import rule
from portfolio_regimes.contracts import RegimeConfig
from portfolio_regimes.performance import attribute
from .contracts import EconometricConfig
from .audit import digest


def error_metrics(observations: list[dict]) -> dict:
    """Continuous-return diagnostics, with a paired zero-return comparator."""
    if not observations: return dict(n=0,mae=None,rmse=None,directional_accuracy=None,information_coefficient=None,paired_no_change_mse=None,mse_skill_vs_no_change=None)
    actual=np.array([r['actual'] for r in observations]); predicted=np.array([r['predicted'] for r in observations]); error=predicted-actual
    mse=float(np.mean(error**2)); baseline=float(np.mean(actual**2))
    correlation=float(np.corrcoef(actual,predicted)[0,1]) if len(actual)>1 and np.std(actual)>0 and np.std(predicted)>0 else None
    return dict(n=len(actual),mae=float(np.mean(abs(error))),rmse=math.sqrt(mse),
                directional_accuracy=float(np.mean(np.sign(actual)==np.sign(predicted))),information_coefficient=correlation,
                paired_no_change_mse=baseline,mse_skill_vs_no_change=1-mse/baseline if baseline>0 else None)


def evaluate(result: dict, rows: tuple, metrics: dict,config: EconometricConfig,regimes: RegimeConfig) -> dict:
    """Attach later labels only after all trading decisions have been produced."""
    bars=aggregate(rows,240); next_bar={a['end']:(a,b) for a,b in zip(bars,bars[1:])}
    records=[]; observations=[]; statuses=Counter(); reasons=Counter()
    for plan in result['signals']:
        prediction=plan['payload']['forecast']['payload']; time=prediction['decision_time']
        statuses[prediction['status']]+=1; reasons[prediction['reason']]+=1
        returns=prediction['inputs'].get('returns',[])
        regime=rule(returns[-regimes.rule_window:],regimes) if len(returns)>=regimes.rule_window else dict(state='UNKNOWN',probabilities={'UNKNOWN':1.},probability_kind='abstention_marker')
        body=dict(decision_time=time,rule=regime,version='rule_regime_attribution_v1',config=asdict(regimes),inputs=prediction['inputs'])
        records.append(dict(regime_id=digest(body),payload=body))
        pair=next_bar.get(time)
        if prediction['status']=='READY' and pair and utc(pair[1]['end'])<=utc(result['end']):
            observations.append(dict(decision_time=time,label_end=pair[1]['end'],actual=math.log(pair[1]['close']/pair[0]['close']),
                                     predicted=prediction['mean'],regime=regime['state']))
    coverage=statuses['READY']/len(result['signals']) if result['signals'] else 0.
    rejected=[]
    if coverage<config.minimum_forecast_coverage: rejected.append('insufficient_forecast_coverage')
    if metrics['maximum_drawdown']>config.maximum_drawdown: rejected.append('drawdown_research_limit')
    return dict(forecast_metrics=error_metrics(observations),observations=observations,
                errors_by_regime={state:error_metrics([r for r in observations if r['regime']==state]) for state in sorted({r['regime'] for r in observations})},
                regimes=records,performance_by_regime=attribute(result,records,'rule'),forecast_status_counts=dict(statuses),
                forecast_reason_counts=dict(reasons),coverage=coverage,
                research_status='REJECTED' if rejected else 'ELIGIBLE_FOR_FURTHER_RESEARCH',rejection_reasons=rejected,
                economic_promotion=False,hyperparameter_selection_uses_holdout=False,research_screen_uses_completed_holdout=True)
