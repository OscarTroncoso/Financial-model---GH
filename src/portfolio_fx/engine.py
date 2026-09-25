"""Delayed signed FX exposure in a fully collateralized USD research ledger."""
from dataclasses import asdict
from datetime import datetime
from .contracts import Candle, Rate, FXConfig, ExecutionConfig
from .signals import signal, MODELS
from portfolio_data.contracts import utc


def run(rows: tuple[Candle,...], rates: tuple[Rate,...], model: str, start, end,
        config: FXConfig=FXConfig(), execution: ExecutionConfig=ExecutionConfig()) -> dict:
    """Evaluate a fixed rule on [start,end); earlier rows are warm-up only.

    USD NAV changes by signed EUR units times USD/EUR price change. All
    collateral earns the configured safe rate; signed net carry is separate.
    Orders cannot fill at the open coincident with a signal's completed close.
    Terminal liquidation is precommitted at the final evaluation close.
    No stops, margin borrowing, EUR-account conversion or portfolio integration.
    """
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

    def target(direction, price, time, reason, signal_id):
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
                holding_hours=(time-position['time']).total_seconds()/3600))
            units=0.; position=None
        if direction:
            notional=nav*execution.exposure_fraction/(1+execution.cost_rate*execution.exposure_fraction)
            units=direction*notional/price
            cost=fill(units,price,time,reason,signal_id)
            position=dict(time=time,price=price,cost=cost,carry=0.)
            if abs(units)*price>nav+1e-8: raise ArithmeticError('Entry exceeds collateral')

    for row in test:
        prior=nav; accrue(row.open,row.start)
        if abs(units)*row.open>nav:
            target(0,row.open,row.start,'collateral_limit',None)
            pending=None
        if pending and utc(pending['payload']['decision_time'])<row.start:
            age=(row.start-utc(pending['payload']['decision_time'])).total_seconds()/3600
            direction=pending['payload']['direction'] if age<=execution.max_execution_delay_hours else 0
            target(direction,row.open,row.start,'signal' if age<=execution.max_execution_delay_hours else 'expired_signal',pending['signal_id'])
            pending=None
        accrue(row.close,row.end)
        # Fixed 4H decision schedule; 30m execution and all four context clocks.
        if row.end.hour%4==0 and row.end.minute==0:
            pending=signal(rows,rates,row.end,model,config); signals.append(pending)
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
                elapsed_seconds=(test[-1].end-test[0].start).total_seconds(),
                pending_terminal_signal=pending is not None,account_currency='USD',execution_contract='collateralized_linear_fx_research')
