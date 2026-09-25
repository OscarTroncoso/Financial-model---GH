"""Risk-sized signed FX with resting brackets, gap priority and timed exits."""
from dataclasses import asdict
from datetime import datetime,timedelta
from portfolio_fx.contracts import Candle, Rate, FXConfig, ExecutionConfig,finite
from portfolio_fx.signals import MODELS
from .plans import propose
from .contracts import Capacity,RiskConfig,VolatilityConfig
from .sizing import size
from portfolio_data.contracts import utc


def run(rows: tuple[Candle,...], rates: tuple[Rate,...], model: str, start, end,
        config: FXConfig=FXConfig(), execution: ExecutionConfig=ExecutionConfig(),
        risk: RiskConfig=RiskConfig(), volatility: VolatilityConfig=VolatilityConfig(),
        fx_capital_fraction: float=.10) -> dict:
    """Phase-6 USD ledger extended with audited risk sizing and protective exits.

    At open: gap barriers/time/capacity exits take priority over pending entries.
    At close: resting stop precedes TP if both touch; intrabar fill time is
    conservatively the close, including carry. Stops can gap; TP gets no gap
    improvement. No re-entry in the same bar as a protective exit.
    """
    if not finite(fx_capital_fraction) or not 0<fx_capital_fraction<=1: raise ValueError('Invalid FX capital fraction')
    start,end=utc(start),utc(end)
    if model not in MODELS or start>=end: raise ValueError('Invalid model/evaluation interval')
    if not rows: raise ValueError('Empty candle history')
    for i,row in enumerate(rows):
        if row.available_at!=row.end: raise ValueError('Historical replay requires certified close-time vintages; downloads cannot be backdated')
        if i and (row.start<rows[i-1].end or (row.start-rows[i-1].end).total_seconds()>execution.max_data_gap_hours*3600):
            raise ValueError('Unordered, duplicate, overlapping or excessive data gap')
    if len({r.quote_basis for r in rows})!=1: raise ValueError('Mixed execution quote bases')
    test=[r for r in rows if start<=r.start<end and r.end<=end]
    if not test: raise ValueError('Empty holdout')
    nav=execution.initial_usd; units=0.; mark=test[0].open; clock=test[0].start
    pending=None; position=None; fills=[]; completed=[]; events=[]; signals=[]
    totals=dict(price_pnl=0.,safe_income=0.,carry=0.,costs=0.,commission=0.,spread=0.,slippage=0.,turnover_usd=0.)
    exposed_seconds=0.

    def accrue(price, time):
        nonlocal nav,mark,clock,exposed_seconds
        seconds=(time-clock).total_seconds()
        if seconds<0: raise ValueError('Clock reversal')
        fraction=seconds/(365*86400)
        safe=nav*execution.safe_annual_rate*fraction
        carry=abs(units)*mark*(execution.long_carry_annual_rate if units>0 else execution.short_carry_annual_rate)*fraction
        pnl=units*(price-mark)
        nav+=safe+carry+pnl
        totals['price_pnl']+=pnl; totals['safe_income']+=safe; totals['carry']+=carry
        if position is not None: position['carry']+=carry
        if units: exposed_seconds+=seconds
        mark=price; clock=time
        if nav<=0: raise ValueError('Research ledger insolvent; leveraged-loss assumptions exceeded')

    def fill(quantity, price, time, reason, signal_id):
        nonlocal nav
        notional=abs(quantity)*price
        commission=notional*execution.commission_bps/10000
        spread=notional*execution.half_spread_bps/10000
        slippage=notional*execution.slippage_bps/10000
        cost=commission+spread+slippage; nav-=cost
        if nav<=0: raise ValueError("Execution costs exhaust research collateral")
        totals['costs']+=cost; totals['commission']+=commission; totals['spread']+=spread
        totals['slippage']+=slippage; totals['turnover_usd']+=notional
        fills.append(dict(time=time.isoformat(),quantity_eur=quantity,reference_price=price,
            execution_price=price+(1 if quantity>0 else -1)*price*(execution.half_spread_bps+execution.slippage_bps)/10000,
            commission=commission,spread=spread,slippage=slippage,cost=cost,reason=reason,signal_id=signal_id))
        return cost

    def target(direction, price, time, reason, signal_id, proposal=None):
        nonlocal units,position
        old_direction=1 if units>0 else -1 if units<0 else 0
        if old_direction==direction: return
        if units:
            cost=fill(-units,price,time,reason,signal_id)
            gross=units*(price-position['price'])
            completed.append(dict(entry_time=position['time'].isoformat(),exit_time=time.isoformat(),
                direction=old_direction,units_eur=abs(units),gross_pnl=gross,
                carry=position['carry'],costs=position['cost']+cost,
                net_pnl=gross+position['carry']-position['cost']-cost,
                holding_hours=(time-position['time']).total_seconds()/3600,exit_reason=reason,
                modeled_stop_loss_usd=position['modeled_stop_loss_usd'],risk_budget_usd=position['risk_budget_usd'],
                budget_exceeded=-(gross+position['carry']-position['cost']-cost)>position['risk_budget_usd']+1e-8))
            units=0.; position=None
        if direction:
            if proposal is None: raise ValueError('Risk proposal required for entry')
            intended=proposal['payload']['sizing']
            if abs(price/intended['entry_reference']-1)>risk.maximum_entry_drift_fraction: return
            sized=size(price,direction,intended['stop_distance'],Capacity(nav,nav*fx_capital_fraction),risk,execution)
            if sized['state']!='READY': return
            quantity=min(sized['units_eur'],intended['units_eur'])
            units=direction*quantity
            cost=fill(units,price,time,reason,signal_id)
            position=dict(time=time,price=price,cost=cost,carry=0.,stop=sized['stop'],take_profit=sized['take_profit'],
                modeled_stop_loss_usd=sized['modeled_stop_loss_usd']*quantity/sized['units_eur'],
                risk_budget_usd=sized['risk_budget_usd'],deadline=time+timedelta(hours=risk.maximum_holding_hours))
            if abs(units)*price>nav*risk.maximum_portfolio_notional+1e-8: raise ArithmeticError('Post-cost notional limit violated')

    def protected_exit(price,time,reason):
        nonlocal pending
        accrue(price,time)
        target(0,price,time,reason,None)
        pending=None

    for row in test:
        prior=nav; accrue(row.open,row.start)
        exited=False
        if position:
            hit=barrier(position,1 if units>0 else -1,row,opening_only=True)
            if hit:
                protected_exit(hit[0],row.start,hit[1]); exited=True
            elif row.start>=position['deadline']:
                protected_exit(row.open,row.start,'time_stop'); exited=True
            elif risk.kill_switch or abs(units)*row.open>min(nav*risk.maximum_portfolio_notional,risk.maximum_notional_usd):
                protected_exit(row.open,row.start,'hard_risk_limit'); exited=True
        if not exited and pending and utc(pending['payload']['decision_time'])<row.start:
            age=(row.start-utc(pending['payload']['decision_time'])).total_seconds()/3600
            sized=pending['payload']['sizing']
            direction=sized['direction'] if sized['state']=='READY' and age<=execution.max_execution_delay_hours else 0
            target(direction,row.open,row.start,'signal' if age<=execution.max_execution_delay_hours else 'expired_signal',pending['plan_id'],pending)
            pending=None
        if position:
            hit=barrier(position,1 if units>0 else -1,row,opening_only=False)
            if hit:
                protected_exit(hit[0],row.end,hit[1]); exited=True
            elif row.end>=position['deadline']:
                protected_exit(row.close,row.end,'time_stop'); exited=True
        accrue(row.close,row.end)
        if row.end.hour%4==0 and row.end.minute==0:
            pending=propose(rows,rates,row.end,model,Capacity(nav,nav*fx_capital_fraction),risk,volatility,config,execution)
            signals.append(pending)
        events.append(dict(time=row.end.isoformat(),nav=nav,units_eur=units,period_return=nav/prior-1))
    target(0,test[-1].close,test[-1].end,'precommitted_terminal_liquidation',None)
    # Attribute the terminal exit cost to the last recorded period.
    prior=execution.initial_usd if len(events)==1 else events[-2]['nav']
    events[-1].update(nav=nav,units_eur=0.,period_return=nav/prior-1)
    expected=execution.initial_usd+totals['price_pnl']+totals['safe_income']+totals['carry']-totals['costs']
    if abs(nav-expected)>1e-7: raise ArithmeticError('FX ledger does not reconcile')
    if abs(sum(t['net_pnl'] for t in completed)+totals['safe_income']-(nav-execution.initial_usd))>1e-7:
        raise ArithmeticError('Trade P&L does not reconcile with collateral income')
    return dict(model=model,start=start.isoformat(),end=end.isoformat(),config=asdict(config),execution=asdict(execution),
                events=events,fills=fills,trades=completed,signals=signals,totals=totals,
                final_nav=nav,initial_nav=execution.initial_usd,exposed_seconds=exposed_seconds,
                risk_config=asdict(risk),volatility_config=asdict(volatility),fx_capital_fraction=fx_capital_fraction,
                elapsed_seconds=(test[-1].end-test[0].start).total_seconds(),
                pending_terminal_signal=pending is not None,account_currency='USD',execution_contract='risk_sized_collateralized_linear_fx_research')


def barrier(position: dict, direction: int, row: Candle, opening_only: bool) -> tuple[float,str]|None:
    """Resting reference-price barriers; adverse gap stop, conservative gap TP."""
    stop=position['stop']; target=position['take_profit']
    if opening_only:
        if (direction>0 and row.open<=stop) or (direction<0 and row.open>=stop): return row.open,'gap_stop'
        if (direction>0 and row.open>=target) or (direction<0 and row.open<=target): return target,'gap_take_profit'
    else:
        if (direction>0 and row.low<=stop) or (direction<0 and row.high>=stop): return stop,'stop'
        if (direction>0 and row.high>=target) or (direction<0 and row.low<=target): return target,'take_profit'
    return None
