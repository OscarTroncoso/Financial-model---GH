"""Phase 5: explicit vintages and cross-sectional factor normalization."""
from dataclasses import asdict,dataclass
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import portfolio_lab
import portfolio_data
import portfolio_equity
from portfolio_data.contracts import utc
from portfolio_equity.contracts import Universe


def encoded(value) -> bytes:
    return json.dumps(value,sort_keys=True,indent=2,allow_nan=False,
                      default=lambda x:x.isoformat()).encode('utf-8')


def digest(value) -> str:
    return hashlib.sha256(encoded(value)).hexdigest()


def source_hash() -> str:
    roots=(Path(__file__).parent,Path(portfolio_data.__file__).parent,Path(portfolio_equity.__file__).parent,Path(portfolio_lab.__file__).parent)
    return digest({root.name+'/'+p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                   for root in roots for p in sorted(root.glob('*.py'))})


@dataclass(frozen=True)
class Feature:
    """One raw descriptor vintage, before any normalization.

    Observation is the economic period end; published is its release; ingestion
    is our first capture of this vintage. Availability cannot precede any of
    them. A new revision is a new immutable record, not an overwrite.
    """
    asset_id: str
    factor_id: str
    value: float
    unit: str
    observation_time: datetime
    published_at: datetime
    ingested_at: datetime
    available_at: datetime
    source_id: str
    revision_id: str

    def __post_init__(self) -> None:
        for name in ('observation_time','published_at','ingested_at','available_at'):
            object.__setattr__(self,name,utc(getattr(self,name)))
        for name in ('asset_id','factor_id','unit','source_id','revision_id'):
            if not isinstance(getattr(self,name),str) or not getattr(self,name).strip():
                raise ValueError('Feature identity, units and provenance are required')
        if isinstance(self.value,bool) or not isinstance(self.value,(int,float)) or not math.isfinite(self.value):
            raise ValueError('Finite numeric feature required; missing values are not zero')
        object.__setattr__(self,'value',float(self.value))
        if not self.observation_time <= self.published_at <= self.ingested_at <= self.available_at:
            raise ValueError('Invalid observation/publication/ingestion/availability order')


@dataclass(frozen=True)
class FactorSpec:
    factor_id: str
    unit: str
    direction: int
    weight: float
    max_age_days: float

    def __post_init__(self) -> None:
        if not isinstance(self.factor_id,str) or not isinstance(self.unit,str) or not self.factor_id or not self.unit or type(self.direction) is not int or self.direction not in (-1,1):
            raise ValueError('Factor identity/unit and direction +/-1 required')
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in (self.weight,self.max_age_days)):
            raise ValueError('Positive factor weight and age required')


@dataclass(frozen=True)
class FactorConfig:
    factors: tuple[FactorSpec,...]
    clip_z: float = 3.0
    minimum_assets: int = 2

    def __post_init__(self) -> None:
        object.__setattr__(self,'factors',tuple(self.factors))
        if not self.factors or any(not isinstance(f,FactorSpec) for f in self.factors):
            raise ValueError('Explicit factor specifications required')
        if len({f.factor_id for f in self.factors})!=len(self.factors):
            raise ValueError('Duplicate factor definitions')
        if not math.isclose(sum(f.weight for f in self.factors),1,rel_tol=0,abs_tol=1e-12):
            raise ValueError('Factor weights must sum to one; no silent renormalization')
        if isinstance(self.clip_z,bool) or not math.isfinite(self.clip_z) or self.clip_z<=0:
            raise ValueError('Positive finite z-score cap required')
        if type(self.minimum_assets) is not int or self.minimum_assets<2:
            raise ValueError('At least two assets required')


def config_from_dict(value: dict) -> FactorConfig:
    if set(value)!={'factors','clip_z','minimum_assets'}:
        raise ValueError('Unknown or missing factor configuration fields')
    return FactorConfig(tuple(FactorSpec(**f) for f in value['factors']),value['clip_z'],value['minimum_assets'])


def normalize(values: tuple[float,...],direction: int,clip_z: float) -> dict:
    """Population z-scores, then orientation and clipping, not raw winsorization.

    This is a declared project transformation, not an MSCI index replication or
    a return forecast. Constant cross-sections receive neutral zero scores.
    Clipped scores need not retain mean zero or variance one.
    """
    x=np.asarray(values,dtype=float)
    if x.ndim!=1 or len(x)<2 or not np.isfinite(x).all():
        raise ValueError('Complete finite cross-section required')
    if type(direction) is not int or direction not in (-1,1) or isinstance(clip_z,bool) or not math.isfinite(clip_z) or clip_z<=0:
        raise ValueError('Invalid normalization settings')
    with np.errstate(over='ignore',invalid='ignore',under='ignore'):
        mean=float(x.mean()); deviation=float(x.std(ddof=0))
    if not math.isfinite(mean) or not math.isfinite(deviation):
        raise ValueError('Normalization overflow; no score produced')
    if deviation==0:
        if not np.all(x==x[0]): raise ValueError('Normalization underflow')
        raw=np.zeros(len(x)); status='constant'
    else:
        raw=direction*(x-mean)/deviation; status='ready'
    score=np.clip(raw,-clip_z,clip_z)
    if not np.isfinite(score).all(): raise ValueError('Nonfinite normalized score')
    return {'mean':mean,'population_std':deviation,'unclipped_scores':raw.tolist(),
            'scores':score.tolist(),'status':status,'clipped':[bool(v) for v in (raw!=score)]}


def snapshot(universe: Universe,features: tuple[Feature,...],decision_time: datetime,
             config: FactorConfig) -> dict:
    """Select vintages before normalizing; never fill absent observations.

    For each asset/factor, choose the latest economic observation known at t,
    then the latest availability for that observation. A late revision of an
    older period cannot displace a newer period. Ambiguous ties are rejected.
    The same eligible input set is invariant to unavailable future suffixes.
    """
    time=utc(decision_time)
    if universe.available_at>time: raise ValueError('Universe unavailable')
    if len(universe.asset_ids)<config.minimum_assets: raise ValueError('Universe too small')
    selected=[]; factor_audits=[]
    composite=np.zeros(len(universe.asset_ids))
    for spec in config.factors:
        cross=[]; inputs=[]
        for asset in universe.asset_ids:
            eligible=[f for f in features if f.asset_id==asset and f.factor_id==spec.factor_id and f.available_at<=time]
            if not eligible: raise ValueError(f'Missing available feature: {asset}/{spec.factor_id}')
            observation=max(f.observation_time for f in eligible)
            period=[f for f in eligible if f.observation_time==observation]
            available=max(f.available_at for f in period)
            latest=[f for f in period if f.available_at==available]
            unique={digest(asdict(f)):f for f in latest}
            if len(unique)!=1: raise ValueError(f'Conflicting same-time vintages: {asset}/{spec.factor_id}')
            feature=next(iter(unique.values()))
            if feature.unit!=spec.unit: raise ValueError('Feature unit mismatch; no implicit conversion')
            if (time-feature.observation_time).total_seconds()>spec.max_age_days*86400:
                raise ValueError(f'Stale feature: {asset}/{spec.factor_id}')
            record=asdict(feature); record['input_id']=digest(record)
            selected.append(record); inputs.append(record['input_id']); cross.append(feature.value)
        stats=normalize(tuple(cross),spec.direction,config.clip_z)
        composite+=spec.weight*np.asarray(stats['scores'])
        factor_audits.append({'factor':asdict(spec),'input_ids':inputs,'raw_values':cross,**stats})
    payload={'schema':1,'model_version':'factor_snapshot_v1','source_hash':source_hash(),
             'decision_time':time.isoformat(),'universe':asdict(universe),'config':asdict(config),
             'selected_inputs':selected,'factors':factor_audits,
             'composite_scores':dict(zip(universe.asset_ids,composite.tolist())),
             'available_to_model_time':max([universe.available_at]+[f['available_at'] for f in selected]).isoformat(),
             'contains_bl_views':False,'interpretation':'dimensionless descriptive scores, not expected returns'}
    payload=json.loads(encoded(payload))
    return {'snapshot_id':digest(payload),'payload':payload}
