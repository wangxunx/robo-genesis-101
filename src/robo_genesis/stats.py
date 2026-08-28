"""Binomial-proportion confidence intervals shared across the eval + analysis tools.

Centralizes the Wilson score interval (a single success rate) and the Newcombe method-10
interval (difference of two independent rates) so every tool reports identical numbers.
Several tools used to carry their own slightly-different copies; import from here instead.

Only the standard library is used (no scipy/statsmodels dependency).

Conventions
-----------
* ``wilson(k, n)``       -> (lo, hi)            two-sided interval, always inside [0, 1].
* ``wilson_rate(k, n)``  -> (p_hat, lo, hi)     the same, plus the point estimate.
* ``wilson_err(k, n)``   -> (p_hat, lo_err, hi_err)  asymmetric half-widths for matplotlib yerr.
* ``newcombe_diff(k1, n1, k2, n2)`` -> (diff, lo, hi)  CI for ``p2 - p1`` (second minus first).

The Wilson interval is preferred over the Wald (normal-approx) interval because it stays inside
[0, 1] and keeps good coverage at small ``n`` or when ``p`` is near 0/1 -- exactly the regime of
these evals (tens-to-hundreds of episodes, rates often 80-100%).
"""

from __future__ import annotations

import math

DEFAULT_Z = 1.96  # ~95% two-sided


def wilson(k: int, n: int, z: float = DEFAULT_Z) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion. Returns (lo, hi) in [0, 1]."""
    if n <= 0:
        return (0.0, 0.0)
    p = k / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    return (max(0.0, center - half), min(1.0, center + half))


def wilson_rate(k: int, n: int, z: float = DEFAULT_Z) -> tuple[float, float, float]:
    """Wilson interval plus the point estimate. Returns (p_hat, lo, hi); NaNs if n == 0."""
    if n <= 0:
        return (float("nan"), float("nan"), float("nan"))
    lo, hi = wilson(k, n, z)
    return (k / n, lo, hi)


def wilson_err(k: int, n: int, z: float = DEFAULT_Z) -> tuple[float, float, float]:
    """Point estimate + asymmetric half-widths (clamped >= 0), handy for matplotlib ``yerr``.

    Returns (p_hat, lo_err, hi_err). At p_hat == 0 or 1 one half-width is ~0, which is correct
    (a bar at 100% has no upper whisker); the clamp guards against tiny negative round-off.
    """
    p, lo, hi = wilson_rate(k, n, z)
    if math.isnan(p):
        return (float("nan"), 0.0, 0.0)
    return (p, max(0.0, p - lo), max(0.0, hi - p))


def newcombe_diff(k1: int, n1: int, k2: int, n2: int, z: float = DEFAULT_Z) -> tuple[float, float, float]:
    """Newcombe (1998) method-10 CI for ``p2 - p1`` of two independent proportions.

    Builds the difference interval from the two Wilson intervals ("square-and-add"); more reliable
    than a Wald difference when either rate is near 0/1. Returns (diff, lo, hi) with diff = p2 - p1.
    """
    p1, l1, u1 = wilson_rate(k1, n1, z)
    p2, l2, u2 = wilson_rate(k2, n2, z)
    diff = p2 - p1
    lo = diff - math.sqrt((p2 - l2) ** 2 + (u1 - p1) ** 2)
    hi = diff + math.sqrt((u2 - p2) ** 2 + (p1 - l1) ** 2)
    return (diff, lo, hi)
