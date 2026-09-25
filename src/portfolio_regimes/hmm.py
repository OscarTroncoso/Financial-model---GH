"""Univariate Gaussian HMM: log-domain forward filtering and training-only EM.

Rabiner (1989), equations 18-21, 37-40 and 49-54 (one Gaussian/state).
Variance floor, deterministic initialization and state ordering are policies.
Inputs are dimensionless returns. Scaling is fitted on training data only.
"""
import numpy as np
from portfolio_fx.data import NotReady
from .contracts import RegimeConfig


def _log(prob):
    with np.errstate(divide='ignore'): return np.log(prob)


def forward(log_emissions, transition, initial):
    """Return normalized log filtered probabilities and log likelihood.

    Initial describes the state of the FIRST observation (no extra transition).
    Zero probabilities are supported; impossible observations are rejected.
    """
    e=np.asarray(log_emissions,dtype=float); a=np.asarray(transition,dtype=float); pi=np.asarray(initial,dtype=float)
    if e.ndim!=2 or not len(e) or a.shape!=(e.shape[1],e.shape[1]) or pi.shape!=(e.shape[1],):
        raise ValueError('HMM dimensions')
    if not np.isfinite(e).all() or not np.isfinite(a).all() or not np.isfinite(pi).all() or (a<0).any() or (pi<0).any() or not np.allclose(a.sum(axis=1),1,atol=1e-12,rtol=0) or not np.isclose(pi.sum(),1,atol=1e-12,rtol=0):
        raise ValueError('Invalid HMM probabilities/emissions')
    la=_log(a); filtered=np.empty_like(e); likelihood=0.
    for t in range(len(e)):
        prediction=_log(pi) if t==0 else np.logaddexp.reduce(filtered[t-1,:,None]+la,axis=0)
        joint=prediction+e[t]; scale=np.logaddexp.reduce(joint)
        if not np.isfinite(scale): raise NotReady('impossible_hmm_observation')
        filtered[t]=joint-scale; likelihood+=float(scale)
    return filtered,likelihood


def emissions(x, means, variances):
    """Log N(x;mu,v), scalar observations and one variance per state."""
    x=np.asarray(x,dtype=float); means=np.asarray(means,dtype=float); variances=np.asarray(variances,dtype=float)
    if x.ndim!=1 or means.ndim!=1 or variances.shape!=means.shape or not len(means) or not np.isfinite(x).all() or not np.isfinite(means).all() or not np.isfinite(variances).all() or (variances<=0).any():
        raise ValueError('Invalid Gaussian parameters')
    result=-.5*(np.log(2*np.pi*variances)+(x[:,None]-means)**2/variances)
    if not np.isfinite(result).all(): raise NotReady('nonfinite_hmm_emission')
    return result


def expectation(e, a, pi):
    """Smoothed weights ONLY for a completed training sequence; never labels."""
    f,ll=forward(e,a,pi); la=_log(a); backward=np.zeros_like(e)
    for t in range(len(e)-2,-1,-1):
        b=np.logaddexp.reduce(la+e[t+1]+backward[t+1],axis=1)
        backward[t]=b-np.logaddexp.reduce(b)
    g=f+backward; g-=np.logaddexp.reduce(g,axis=1)[:,None]; gamma=np.exp(g)
    counts=np.zeros_like(a)
    for t in range(len(e)-1):
        xi=f[t,:,None]+la+e[t+1]+backward[t+1]
        counts+=np.exp(xi-np.logaddexp.reduce(xi.ravel()))
    return gamma,counts,ll,f


def fit(returns, config=RegimeConfig()):
    """Deterministic constrained Baum-Welch; fail closed if not converged.

    Variances have a floor in training-standardized return units squared.
    State ranks are sorted by fitted variance, then mean; not economic labels.
    """
    raw=np.asarray(returns,dtype=float)
    if raw.ndim!=1 or len(raw)!=config.training_window or not np.isfinite(raw).all(): raise ValueError('Invalid training sample')
    center=float(raw.mean()); scale=float(raw.std(ddof=0))
    if scale<=1e-12: raise NotReady('degenerate_hmm_training')
    x=(raw-center)/scale; k=config.states
    means=np.quantile(x,np.linspace(.15,.85,k)); variances=np.ones(k)
    a=np.full((k,k),.1/(k-1)); np.fill_diagonal(a,.9); pi=np.full(k,1/k)
    history=[]; converged=False
    for iteration in range(config.max_iterations):
        e=emissions(x,means,variances); gamma,counts,ll,f=expectation(e,a,pi); history.append(ll)
        if len(history)>1:
            change=history[-1]-history[-2]
            if change < -1e-7*max(1,abs(history[-2])): raise NotReady('hmm_likelihood_decreased')
            if abs(change)<=config.tolerance*max(1,abs(history[-2])): converged=True; break
        if iteration==config.max_iterations-1: break
        weights=gamma.sum(axis=0)
        if (weights<=1e-10).any() or (counts.sum(axis=1)<=1e-10).any(): raise NotReady('empty_hmm_state')
        means=(gamma*x[:,None]).sum(axis=0)/weights
        variances=np.maximum((gamma*(x[:,None]-means)**2).sum(axis=0)/weights,config.variance_floor)
        pi=gamma[0]; a=counts/counts.sum(axis=1)[:,None]
    if not converged: raise NotReady('hmm_not_converged')
    order=np.lexsort((means,variances))
    return dict(means=means[order].tolist(),variances=variances[order].tolist(),
                transition=a[np.ix_(order,order)].tolist(),initial=pi[order].tolist(),
                last_filtered=np.exp(f[-1,order]).tolist(),center=center,scale=scale,
                return_means=(center+scale*means[order]).tolist(),return_variances=(scale**2*variances[order]).tolist(),
                log_likelihood_history=history,converged=True,iterations=len(history),
                state_order='ascending_training_variance_then_mean')


def filter_returns(returns, model):
    """Frozen-parameter out-of-sample filtering, starting AFTER training."""
    x=(np.asarray(returns,dtype=float)-model['center'])/model['scale']
    a=np.asarray(model['transition']); prior=np.asarray(model['last_filtered'])@a
    f,ll=forward(emissions(x,model['means'],model['variances']),a,prior)
    return np.exp(f).tolist(),ll-len(x)*float(np.log(model['scale']))
