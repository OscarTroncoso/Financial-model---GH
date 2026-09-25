"""Entry-decision regime attribution, retaining the existing risk ledger."""
from math import isclose
from portfolio_data.contracts import utc


def attribute(result, records, method):
    """Group realized trade net P&L by the regime at its actual entry signal.

    Safe collateral income stays separate. No invented subgroup Sharpe: groups
    are conditional completed-trade samples, not self-financing portfolios.
    """
    if method not in ('rule','hmm'): raise ValueError('Unknown regime method')
    by_time={r['payload']['decision_time']:r for r in records}
    if len(by_time)!=len(records): raise ValueError('Duplicate regime timestamps')
    signals={s['plan_id']:s['payload']['decision_time'] for s in result['signals']}
    entry_fills={}; units=0.
    for fill in result['fills']:
        before=units; units+=fill['quantity_eur']
        if abs(before)<1e-9 and abs(units)>1e-9:
            if fill['time'] in entry_fills: raise ValueError('Multiple entries at same timestamp')
            entry_fills[fill['time']]=fill
    groups={}; assignments=[]
    for trade in result['trades']:
        fill=entry_fills.get(trade['entry_time'])
        if fill is None or fill['quantity_eur']*trade['direction']<=0 or not isclose(abs(fill['quantity_eur']),trade['units_eur']):
            raise ValueError('Invalid entry fill lineage')
        decision=signals.get(fill['signal_id']); record=by_time.get(decision)
        if decision is None or utc(decision)>=utc(trade['entry_time']): raise ValueError('Entry must follow its decision')
        if record is None: raise ValueError('Missing entry-decision regime')
        regime=record['payload'][method]; state=regime['state']
        group=groups.setdefault(state,dict(trades=0,net_pnl_usd=0.,gross_pnl_usd=0.,carry_usd=0.,costs_usd=0.,wins=0,holding_hours=0.))
        group['trades']+=1; group['wins']+=int(trade['net_pnl']>0)
        for output,key in (('net_pnl_usd','net_pnl'),('gross_pnl_usd','gross_pnl'),('carry_usd','carry'),('costs_usd','costs'),('holding_hours','holding_hours')):
            group[output]+=trade[key]
        assignments.append(dict(entry_time=trade['entry_time'],decision_time=decision,regime_id=record['regime_id'],state=state,
                                probabilities=regime['probabilities'],net_pnl_usd=trade['net_pnl']))
    for group in groups.values():
        group['expectancy_usd']=group['net_pnl_usd']/group['trades']; group['hit_rate']=group['wins']/group['trades']
        group['average_holding_hours']=group['holding_hours']/group['trades']
    net=sum(g['net_pnl_usd'] for g in groups.values()); safe=result['totals']['safe_income']
    if not isclose(net+safe,result['final_nav']-result['initial_nav'],abs_tol=1e-7): raise ArithmeticError('Regime P&L does not reconcile')
    return dict(groups=groups,assignments=assignments,trade_net_pnl_usd=net,unallocated_safe_income_usd=safe,
                total_nav_change_usd=net+safe,attribution='entry_decision_hard_state',risk_limits_unchanged=True)
