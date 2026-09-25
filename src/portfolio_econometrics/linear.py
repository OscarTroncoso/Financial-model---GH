"""OLS AR(1), ARX(1) and bivariate VAR(1), using only lagged predictors."""
import numpy as np
from .contracts import EconometricConfig,Rejected


def least_squares(x: np.ndarray,y: np.ndarray,max_condition: float) -> tuple[np.ndarray,np.ndarray,float]:
    """Full-rank OLS; residual covariance uses n-k degrees of freedom."""
    x=np.asarray(x,dtype=float); y=np.asarray(y,dtype=float)
    if x.ndim!=2 or y.ndim!=2 or len(x)!=len(y) or len(x)<=x.shape[1] or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('Invalid regression dimensions/data')
    beta,_,rank,singular=np.linalg.lstsq(x,y,rcond=None)
    condition=float(singular[0]/singular[-1]) if singular[-1]>0 else float('inf')
    if rank<x.shape[1] or condition>max_condition: raise Rejected('rank_deficient_or_ill_conditioned')
    residual=y-x@beta; covariance=residual.T@residual/(len(x)-x.shape[1])
    return beta,covariance,condition


def stable(matrix: np.ndarray, maximum_root: float) -> float:
    """Companion spectral radius; lag one here. Equality to bound rejects."""
    matrix=np.asarray(matrix,dtype=float)
    if matrix.ndim!=2 or matrix.shape[0]!=matrix.shape[1] or not np.isfinite(matrix).all(): raise ValueError('Invalid dynamics matrix')
    radius=float(max(abs(np.linalg.eigvals(matrix))))
    if radius>=maximum_root: raise Rejected('unstable_autoregressive_root')
    return radius


def estimate(returns: list[float], macro_changes: list[float]|None, model: str, config: EconometricConfig) -> dict:
    """Fit one lag, intercept; ARIMAX here is ARX/ARIMA(1,0,0)+lagged X.

    Standardization uses only this training window. VAR second endogenous
    variable is change in the as-of policy-rate differential, not FX levels.
    """
    if model not in ('ar','arimax','var'): raise ValueError('Unsupported linear model')
    r=np.asarray(returns,dtype=float)
    values=r[:,None] if model=='ar' else np.column_stack((r,np.asarray(macro_changes,dtype=float)))
    if len(values)!=config.window or not np.isfinite(values).all(): raise ValueError('Invalid training window')
    center=values.mean(axis=0); scale=values.std(axis=0)
    if (scale<=config.minimum_scale).any(): raise Rejected('degenerate_training_feature')
    z=(values-center)/scale
    x=np.column_stack((np.ones(len(z)-1),z[:-1])); y=z[1:] if model=='var' else z[1:,:1]
    beta,cov,condition=least_squares(x,y,config.max_condition)
    if abs(beta).max()>config.maximum_standardized_coefficient: raise Rejected('excessive_standardized_coefficient')
    radius=stable(beta[1:].T if model=='var' else beta[1:2],config.maximum_root)
    prediction=np.r_[1.,z[-1]]@beta
    return dict(mean=float(center[0]+scale[0]*prediction[0]),variance=float(cov[0,0]*scale[0]**2),
                parameters=dict(coefficients=beta.tolist(),residual_covariance=cov.tolist(),center=center.tolist(),scale=scale.tolist()),
                diagnostics=dict(condition=condition,spectral_radius=radius,order=[1,0,0],residual_degrees_freedom=len(x)-x.shape[1]),
                variance_kind='innovation_only_excludes_parameter_uncertainty')
