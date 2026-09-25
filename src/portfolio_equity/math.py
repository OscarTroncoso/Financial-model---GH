"""Validated linear algebra and long-only constrained mean-variance allocation."""
from dataclasses import dataclass
import math
import numpy as np
from numpy.typing import ArrayLike, NDArray


def vector(value: ArrayLike, size: int | None = None) -> NDArray[np.float64]:
    result = np.asarray(value, dtype=float)
    if result.ndim != 1 or not len(result) or not np.isfinite(result).all() or (size is not None and len(result) != size):
        raise ValueError("Invalid finite vector or asset dimension")
    return result.copy()


def covariance(value: ArrayLike, positive: bool = True) -> NDArray[np.float64]:
    result = np.asarray(value, dtype=float)
    if result.ndim != 2 or not len(result) or result.shape[0] != result.shape[1] or not np.isfinite(result).all():
        raise ValueError("Invalid square covariance")
    if not np.allclose(result, result.T, rtol=1e-12, atol=1e-14):
        raise ValueError("Asymmetric covariance")
    eigen = np.linalg.eigvalsh(result)
    if eigen[0] < -1e-12 or (positive and (eigen[0] <= 0 or eigen[-1] / eigen[0] > 1e12)):
        raise ValueError("Covariance is nonpositive or ill-conditioned; no silent repair")
    return result.copy()


def positive(value: float) -> None:
    if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
        raise ValueError("Positive finite scalar required")


def weights(value: ArrayLike, size: int | None = None) -> NDArray[np.float64]:
    result = vector(value, size)
    if (result < 0).any() or not np.isclose(result.sum(), 1, atol=1e-10, rtol=0):
        raise ValueError("Long-only weights must sum to one")
    return result


def project_capped_simplex(value: ArrayLike, caps: ArrayLike) -> NDArray[np.float64]:
    """Euclidean projection onto sum(w)=1, 0<=w_i<=cap_i via a dual scalar."""
    v = vector(value)
    upper = vector(caps, len(v))
    if (upper < 0).any() or (upper > 1).any() or upper.sum() < 1:
        raise ValueError("Infeasible allocation caps")
    low, high = float(np.min(v - upper)), float(np.max(v))
    for _ in range(100):
        middle = (low + high) / 2
        projected = np.clip(v - middle, 0, upper)
        if projected.sum() > 1:
            low = middle
        else:
            high = middle
    return np.clip(v - (low + high) / 2, 0, upper)


@dataclass(frozen=True)
class Optimum:
    weights: tuple[float, ...]
    utility: float
    optimality_gap: float
    iterations: int


def optimize(mean: ArrayLike, risk: ArrayLike, risk_aversion: float,
             caps: ArrayLike, tolerance: float = 1e-10, max_iterations: int = 20000) -> Optimum:
    """Maximize mu'w-delta*w'Sigma*w/2 on a capped long-only simplex.

    Projected gradient has a Lipschitz step. A linear minimization over the
    feasible set gives a convex objective-gap certificate; failure is explicit.
    Tolerance is in utility units, not a bound on individual weight error.
    No costs are hidden in utility: monetary execution costs are handled by the
    rebalance ledger. Units: annual excess mean and annualized return covariance.
    """
    sigma = covariance(risk)
    mu, upper = vector(mean, len(sigma)), vector(caps, len(sigma))
    positive(risk_aversion); positive(tolerance)
    if type(max_iterations) is not int or max_iterations < 1:
        raise ValueError("Invalid iteration budget")
    current = project_capped_simplex(np.ones(len(mu)) / len(mu), upper)
    lipschitz = risk_aversion * np.linalg.eigvalsh(sigma)[-1]
    for iteration in range(1, max_iterations + 1):
        gradient = risk_aversion * sigma @ current - mu
        vertex, remaining = np.zeros(len(mu)), 1.0
        for index in np.argsort(gradient, kind="stable"):
            vertex[index] = min(upper[index], remaining)
            remaining -= vertex[index]
        gap = float(gradient @ (current - vertex))
        if gap <= tolerance:
            return Optimum(tuple(current), float(mu @ current - risk_aversion * current @ sigma @ current / 2), max(0.0, gap), iteration)
        current = project_capped_simplex(current - gradient / lipschitz, upper)
    raise ValueError("Optimizer did not converge; allocation disabled")
