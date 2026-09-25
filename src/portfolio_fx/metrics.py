"""Trading diagnostics; undefined ratios stay null, never infinite success."""
import math
from statistics import mean, stdev
from datetime import datetime, timedelta


def summarize(result: dict) -> dict:
    events=result['events']; trades=result['trades']; initial=result['initial_nav']
    navs=[initial]+[r['nav'] for r in events]; peak=initial; drawdown=0.
    for nav in navs: peak=max(peak,nav); drawdown=max(drawdown,1-nav/peak)
    pnl=[t['net_pnl'] for t in trades]; wins=[x for x in pnl if x>0]; losses=[x for x in pnl if x<0]
    # Daily close equity, including terminal partial day. Annual ratios require
    # >=2 daily returns, and treat observed UTC sessions as 252 per year.
    daily={}
    for event in events: daily[(datetime.fromisoformat(event['time'])-timedelta(microseconds=1)).date()]=event['nav']
    previous=initial; returns=[]
    for value in daily.values(): returns.append(value/previous-1); previous=value
    deviation=stdev(returns) if len(returns)>1 else 0.
    downside=math.sqrt(mean(min(r,0)**2 for r in returns))
    years=result['elapsed_seconds']/(365*86400)
    cagr=math.expm1(math.log(result['final_nav']/initial)/years)
    # Ratios are descriptive over short fixtures, with zero MAR for Sortino.
    return dict(net_return=result['final_nav']/initial-1,maximum_drawdown=drawdown,
        sharpe_zero_rate=mean(returns)/deviation*math.sqrt(252) if deviation else None,
        sortino_zero_mar=mean(returns)/downside*math.sqrt(252) if downside else None,
        cagr=cagr,calmar=cagr/drawdown if drawdown else None,
        profit_factor=sum(wins)/-sum(losses) if losses else None,
        expectancy_usd=mean(pnl) if pnl else None,hit_rate=len(wins)/len(pnl) if pnl else None,
        average_win_usd=mean(wins) if wins else None,average_loss_usd=mean(losses) if losses else None,
        win_loss_ratio=mean(wins)/-mean(losses) if wins and losses else None,
        exposure_time=result['exposed_seconds']/result['elapsed_seconds'],
        turnover_initial_nav=result['totals']['turnover_usd']/initial,
        average_holding_hours=mean(t['holding_hours'] for t in trades) if trades else None,
        worst_trade_usd=min(pnl) if pnl else None,cost_burden_initial_nav=result['totals']['costs']/initial,
        slippage_usd=result['totals']['slippage'],completed_trades=len(trades),
        daily_observations=len(returns),**result['totals'])
