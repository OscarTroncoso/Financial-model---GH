"""EUR/USD data clocks, model parameters and research execution assumptions."""
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import math
from portfolio_data.contracts import utc


def finite(value: float) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


@dataclass(frozen=True)
class Candle:
    """30-minute UTC OHLC, USD per EUR; complete-bar availability is explicit.

    Indicative mid/proxy quotes are not executable bid/ask. Revisions are new
    records. Source and ingestion are required, including synthetic fixtures.
    """
    start: datetime
    end: datetime
    open: float
    high: float
    low: float
    close: float
    ingested_at: datetime
    available_at: datetime
    source: str
    pair: str = 'EURUSD'
    quote_basis: str = 'indicative'

    def __post_init__(self):
        for key in ('start', 'end', 'ingested_at', 'available_at'):
            object.__setattr__(self, key, utc(getattr(self, key)))
        if self.end-self.start != timedelta(minutes=30) or self.start.minute not in (0,30) or self.start.second or self.start.microsecond:
            raise ValueError('UTC 30-minute aligned candles required')
        if not self.end <= self.ingested_at <= self.available_at:
            raise ValueError('Completed candle must precede ingestion/availability')
        if any(not finite(v) or v<=0 for v in (self.open,self.high,self.low,self.close)):
            raise ValueError('Positive finite FX prices required')
        if not self.low<=min(self.open,self.close)<=max(self.open,self.close)<=self.high:
            raise ValueError('Invalid OHLC range')
        if self.pair!='EURUSD' or self.quote_basis not in ('mid','indicative') or not isinstance(self.source,str) or not self.source:
            raise ValueError('EURUSD identity and quote provenance required')


@dataclass(frozen=True)
class Rate:
    """Annual decimal policy-rate proxy, not a broker swap or matched bond yield."""
    currency: str
    value: float
    observation_time: datetime
    ingested_at: datetime
    available_at: datetime
    source: str
    kind: str = 'policy_proxy'

    def __post_init__(self):
        for key in ('observation_time','ingested_at','available_at'):
            object.__setattr__(self,key,utc(getattr(self,key)))
        if self.currency not in ('EUR','USD') or self.kind!='policy_proxy' or not isinstance(self.source,str) or not self.source:
            raise ValueError('Explicit EUR/USD policy proxy provenance required')
        if not finite(self.value) or not -1<self.value<1:
            raise ValueError('Rates must be annual decimals, not percentage points')
        if not self.observation_time<=self.ingested_at<=self.available_at:
            raise ValueError('Invalid rate availability')


@dataclass(frozen=True)
class FXConfig:
    fast_window: int = 6
    slow_window: int = 24
    mean_window: int = 20
    trend_threshold: float = .0005
    reversion_z: float = 1.5
    rate_threshold: float = .0025
    max_rate_age_days: float = 10
    max_30m_age_minutes: float = 60
    max_1h_age_minutes: float = 120
    max_4h_age_minutes: float = 300
    max_daily_age_minutes: float = 5760
    max_history_gap_hours: float = 76

    def __post_init__(self):
        for key in ('fast_window','slow_window','mean_window'):
            if type(getattr(self,key)) is not int or getattr(self,key)<2:
                raise ValueError('Integer windows >=2 required')
        if self.fast_window>=self.slow_window: raise ValueError('Fast window must be shorter')
        for key,value in asdict(self).items():
            if key.endswith('window'): continue
            if not finite(value) or value<=0: raise ValueError('Positive finite model settings required')


@dataclass(frozen=True)
class ExecutionConfig:
    """Fully collateralized USD linear FX research ledger; annual ACT/365 accrual.

    Carry is a signed net return on absolute USD notional, separately supplied
    for longs/shorts. Policy rate features never stand in for actual swap fees.
    Exposure fraction is a research normalization, not stop-based risk sizing.
    """
    initial_usd: float = 10000
    exposure_fraction: float = .10
    commission_bps: float = .5
    half_spread_bps: float = .5
    slippage_bps: float = .5
    safe_annual_rate: float = .02
    long_carry_annual_rate: float = -.025
    short_carry_annual_rate: float = .005
    max_execution_delay_hours: float = 2
    max_data_gap_hours: float = 76

    def __post_init__(self):
        if any(not finite(v) for v in asdict(self).values()): raise ValueError('Finite execution settings required')
        if self.initial_usd<=0 or not 0<self.exposure_fraction<=1: raise ValueError('Invalid research capital/exposure')
        if any(v<0 for v in (self.commission_bps,self.half_spread_bps,self.slippage_bps)) or self.cost_rate>=1:
            raise ValueError('Invalid costs')
        if any(not -1<v<1 for v in (self.safe_annual_rate,self.long_carry_annual_rate,self.short_carry_annual_rate)):
            raise ValueError('Annual decimal accrual rates required')
        if min(self.max_execution_delay_hours,self.max_data_gap_hours)<=0: raise ValueError('Positive clock bounds required')

    @property
    def cost_rate(self):
        return (self.commission_bps+self.half_spread_bps+self.slippage_bps)/10000
