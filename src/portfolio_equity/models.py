"""Sourced Black-Litterman formulas and three explicit covariance estimators."""
from dataclasses import dataclass
import numpy as np
from numpy.typing import ArrayLike
from .math import covariance, positive, vector, weights


@dataclass(frozen=True)
class CovarianceEstimate:
    matrix: tuple[tuple[float, ...], ...]
    estimator: str
    observations: int
    shrinkage: float | None
    periods_per_year: int


def estimate_covariance(returns: ArrayLike, method: str = "ledoit_wolf",
                        periods_per_year: int = 252, decay: float = .94) -> CovarianceEstimate:
    """Aligned daily arithmetic excess returns, oldest first, no missing values.

    Sample: centered n-1. EWMA: RiskMetrics zero-mean recursion initialized
    with first outer product, no future seed. LW: centered ML covariance
    shrunk toward trace(S)/p I (2004 well-conditioned estimator), NOT the
    constant-correlation target from 'Honey'. Annualization multiplies by A.
    """
    x = np.asarray(returns, dtype=float)
    if x.ndim != 2 or x.shape[0] < 2 or x.shape[1] < 1 or not np.isfinite(x).all():
        raise ValueError("At least two complete finite return rows required")
    if type(periods_per_year) is not int or periods_per_year < 1:
        raise ValueError("Invalid annualization")
    n, p = x.shape
    centered = x - x.mean(axis=0)
    shrinkage = None
    if method == "sample":
        result = centered.T @ centered / (n - 1)
    elif method == "ewma":
        if not np.isfinite(decay) or not 0 < decay < 1:
            raise ValueError("EWMA decay must be in (0,1)")
        result = np.outer(x[0], x[0])
        for row in x[1:]:
            result = decay * result + (1 - decay) * np.outer(row, row)
    elif method == "ledoit_wolf":
        sample = centered.T @ centered / n
        target = np.eye(p) * np.trace(sample) / p
        distance = float(np.sum((sample - target) ** 2))
        # Estimated squared sampling error of the ML covariance, divided by n.
        beta = max(0.0, (float(np.mean(np.sum(centered**2, axis=1)**2)) - float(np.sum(sample**2))) / n)
        shrinkage = 0.0 if distance == 0 else min(1.0, beta / distance)
        result = (1 - shrinkage) * sample + shrinkage * target
    else:
        raise ValueError("Unknown covariance estimator")
    result = covariance(result * periods_per_year, positive=False)
    return CovarianceEstimate(tuple(map(tuple, result)), method, n, shrinkage, periods_per_year)


def equilibrium(risk: ArrayLike, benchmark: ArrayLike, risk_aversion: float) -> np.ndarray:
    """Pi=delta*Sigma*w_reference, annual arithmetic excess returns."""
    sigma = covariance(risk)
    positive(risk_aversion)
    return risk_aversion * sigma @ weights(benchmark, len(sigma))


@dataclass(frozen=True)
class Posterior:
    mean: tuple[float, ...]
    mean_covariance: tuple[tuple[float, ...], ...]
    predictive_covariance: tuple[tuple[float, ...], ...]


def posterior(risk: ArrayLike, prior: ArrayLike, tau: float,
              picks: ArrayLike, opinions: ArrayLike, omega: ArrayLike) -> Posterior:
    """Gaussian conditioning equivalent to Idzorek (2004), equation 3.

    M is uncertainty in the mean; Sigma+M is predictive return covariance.
    The baseline optimizer deliberately uses Sigma, following that paper's
    example. Empty views return the prior exactly. No explicit matrix inverses.
    Singular contradictory/dependent hard views fail closed.
    """
    sigma = covariance(risk)
    pi = vector(prior, len(sigma)); positive(tau)
    p = np.asarray(picks, dtype=float)
    q = np.asarray(opinions, dtype=float)
    om = np.asarray(omega, dtype=float)
    if q.ndim != 1 or p.shape != (len(q), len(pi)) or om.shape != (len(q), len(q)):
        raise ValueError("Invalid P/Q/Omega dimensions")
    if not np.isfinite(p).all() or not np.isfinite(q).all():
        raise ValueError("Nonfinite view")
    m = tau * sigma
    if len(q):
        om = covariance(om, positive=False)
        if (np.linalg.norm(p, axis=1) == 0).any():
            raise ValueError("Empty view portfolio")
        cross = m @ p.T
        system = covariance(p @ cross + om)
        mean = pi + cross @ np.linalg.solve(system, q - p @ pi)
        m = m - cross @ np.linalg.solve(system, cross.T)
        m = (m + m.T) / 2
    else:
        mean = pi
    covariance(m, positive=False)
    return Posterior(tuple(mean), tuple(map(tuple, m)), tuple(map(tuple, sigma + m)))


def confidence_variance(risk: ArrayLike, pick: ArrayLike, tau: float, confidence: float) -> float:
    """Single-view interpolation convention: omega=((1-c)/c)*tau*p'Sigma*p.

    c=.5 gives the He-Litterman scaled-variance baseline described by Idzorek.
    With one view, p*posterior=(1-c)*p*prior+c*q. For multiple views this is NOT
    a guarantee of independent tilt percentages or Idzorek's numerical method.
    Zero-confidence views must be omitted; c=1 is a hard equality view.
    """
    sigma = covariance(risk); p = vector(pick, len(sigma)); positive(tau)
    if not np.isfinite(confidence) or not 0 < confidence <= 1 or not np.any(p):
        raise ValueError("Confidence must be in (0,1] and pick nonzero")
    return float((1 - confidence) / confidence * tau * p @ sigma @ p)
