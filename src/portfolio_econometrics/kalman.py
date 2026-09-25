"""Time-varying AR coefficients with a linear Gaussian Kalman filter."""
import numpy as np
from .contracts import EconometricConfig,Rejected
from .linear import stable


def update(state: np.ndarray,covariance: np.ndarray,h: np.ndarray,observation: float,q: float,r: float) -> tuple[np.ndarray,np.ndarray,float]:
    """Random-walk prediction then scalar observation update (Joseph covariance)."""
    state=np.asarray(state,dtype=float); covariance=np.asarray(covariance,dtype=float); h=np.asarray(h,dtype=float)
    if state.ndim!=1 or covariance.shape!=(len(state),len(state)) or h.shape!=state.shape or not np.isfinite(state).all() or not np.isfinite(covariance).all() or not np.isfinite(h).all() or not np.isfinite([observation,q,r]).all() or q<0 or r<=0:
        raise ValueError('Invalid Kalman inputs')
    if not np.allclose(covariance,covariance.T) or np.linalg.eigvalsh(covariance).min()<-1e-12: raise ValueError('Invalid state covariance')
    prior=covariance+np.eye(len(state))*q; innovation_variance=float(h@prior@h+r)
    gain=prior@h/innovation_variance; posterior=state+gain*(observation-h@state)
    residual=np.eye(len(state))-np.outer(gain,h)
    covariance=residual@prior@residual.T+np.outer(gain,gain)*r
    return posterior,(covariance+covariance.T)/2,innovation_variance


def estimate(returns: list[float],config: EconometricConfig) -> dict:
    """Reset prior on each rolling window; Q/R preconfigured, never OOS tuned."""
    raw=np.asarray(returns,dtype=float)
    if raw.shape!=(config.window,) or not np.isfinite(raw).all(): raise ValueError('Invalid Kalman window')
    center=float(raw.mean()); scale=float(raw.std())
    if scale<=config.minimum_scale: raise Rejected('degenerate_training_feature')
    z=(raw-center)/scale; state=np.zeros(2); covariance=np.eye(2)*config.kalman_initial_variance; path=[]
    for previous,current in zip(z,z[1:]):
        state,covariance,s=update(state,covariance,np.array([1.,previous]),float(current),config.kalman_process_variance,config.kalman_observation_variance)
        path.append(dict(coefficients=state.tolist(),innovation_variance=s))
    radius=stable(state[1:].reshape(1,1),config.maximum_root)
    if abs(state).max()>config.maximum_standardized_coefficient or np.trace(covariance)>config.maximum_state_covariance:
        raise Rejected('excessive_kalman_state_or_covariance')
    h=np.array([1.,z[-1]]); prior=covariance+np.eye(2)*config.kalman_process_variance
    return dict(mean=float(center+scale*(h@state)),variance=float(scale**2*(h@prior@h+config.kalman_observation_variance)),
                parameters=dict(coefficients=state.tolist(),covariance=covariance.tolist(),center=center,scale=scale,path=path),
                diagnostics=dict(spectral_radius=radius,process_variance=config.kalman_process_variance,observation_variance=config.kalman_observation_variance),
                variance_kind='conditional_state_and_observation_uncertainty_fixed_Q_R')
