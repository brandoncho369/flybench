"""Graded scores, ceilings, and seed statistics.

Pass/fail with a threshold has a cliff: 5.1 Hz passes, 4.9 Hz fails, and two models on either side
look categorically different. Every check therefore also gets a *graded* score in [0, 1]:

- **against a recording** (`observed: {mean, sd, n, source}` on the check): z = (value − mean) / sd
  and graded = 1 / (1 + exp(2·(|z| − k))), k = 2 by default (SciUnit/NeuronUnit Z-score scoring).
  |z| = 0 → 0.98, |z| = k → 0.5, |z| = 2k → 0.02. `pass` is |z| < k. If sd is missing or 0 the
  check declares `sd: unknown` and falls back to the threshold rule below.
- **against a threshold** (every existing check): graded = 1 / (1 + 10^(−2·margin)), where margin
  is the signed log10 distance from the line (bench.margin_of). 3.2× on the passing side → 0.91,
  on the line → 0.5, 3.2× on the failing side → 0.09. `pass` is the op, unchanged.

A check may carry a `ceiling` in (0, 1]: the score a perfect model of the real fly would get,
because the fly itself is not deterministic (e.g. 95 % of flies take off to a loom, Card &
Dickinson 2008). The reported score is graded / ceiling, capped at 1 and flagged when it caps —
a model that escapes 100 % of the time is not a better fly. "A benchmark without a ceiling is
not interpretable" (Brain-Score).

Seed statistics (rliable, NeurIPS 2021; Colas et al. 2018): the interquartile mean of per-seed
graded scores, a stratified bootstrap 95 % CI (resample seeds within each task), and a performance
profile (fraction of checks whose margin is ≥ τ, over a grid of τ) so the whole curve is visible
rather than one cut. Two runs are compared by paired per-check differences (`flybench diff`).
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np

DEFAULT_K = 2.0
PROFILE_TAUS = (-1.0, -0.5, -0.25, 0.0, 0.25, 0.5, 1.0)


def graded_from_margin(margin: float) -> float:
    """Threshold checks: logistic in decades of margin. NaN margin → 0 (no measurement)."""
    if margin is None or not np.isfinite(margin):
        return 0.0
    m = max(-10.0, min(10.0, float(margin)))
    return float(1.0 / (1.0 + 10.0 ** (-2.0 * m)))


def z_score(value: float, mean: float, sd: float) -> float:
    if sd is None or not np.isfinite(sd) or sd <= 0 or not np.isfinite(value):
        return float("nan")
    return float((value - mean) / sd)


def graded_from_z(z: float, k: float = DEFAULT_K) -> float:
    if not np.isfinite(z):
        return 0.0
    return float(1.0 / (1.0 + math.exp(min(60.0, 2.0 * (abs(z) - k)))))


def observed_sd(observed: dict | None) -> float | None:
    """The sd a check's `observed` block provides, or None when it is absent/'unknown'/0."""
    if not observed:
        return None
    sd = observed.get("sd")
    if sd in (None, "unknown"):
        return None
    try:
        sd = float(sd)
    except (TypeError, ValueError):
        return None
    return sd if np.isfinite(sd) and sd > 0 else None


def grade_check(value: float, margin: float, observed: dict | None = None, ceiling: float | None = None,
                k: float = DEFAULT_K) -> tuple[float, float, bool, float | None, bool]:
    """Return (graded, z, pass_by_z, ceiling_applied, capped).

    pass_by_z is only meaningful when z is finite (a recording-match check); callers keep the
    threshold pass otherwise. graded is already divided by the ceiling when one is given."""
    sd = observed_sd(observed)
    if sd is not None:
        z = z_score(value, float(observed["mean"]), sd)
        g = graded_from_z(z, k)
        pz = bool(np.isfinite(z) and abs(z) < k)
    else:
        z, g, pz = float("nan"), graded_from_margin(margin), False
    capped = False
    if ceiling is not None and 0 < ceiling <= 1:
        g = g / ceiling
        if g > 1.0:
            g, capped = 1.0, True
    return float(g), z, pz, ceiling, capped


# ---------------------------------------------------------------- seed statistics

def iqm(values: Sequence[float]) -> float:
    """Interquartile mean: mean of the middle 50 % (robust to a single bad seed, needs fewer runs than a median)."""
    v = np.asarray([x for x in values if np.isfinite(x)], dtype=float)
    if v.size == 0:
        return float("nan")
    if v.size < 4:
        return float(v.mean())
    lo, hi = np.percentile(v, [25, 75])
    mid = v[(v >= lo) & (v <= hi)]
    return float(mid.mean()) if mid.size else float(v.mean())


def stratified_bootstrap_ci(per_task_seeds: Sequence[Sequence[float]], n_boot: int = 1000, seed: int = 0,
                            stat=iqm, level: float = 0.95) -> tuple[float, float] | None:
    """CI on stat(mean over tasks of the per-task score), resampling seeds *within* each task.
    Returns None when no task has more than one seed (there is nothing to resample)."""
    rows = [np.asarray([x for x in r if np.isfinite(x)], dtype=float) for r in per_task_seeds]
    rows = [r for r in rows if r.size]
    if not rows or all(r.size < 2 for r in rows):
        return None
    rng = np.random.default_rng(seed)
    out = np.empty(n_boot)
    for b in range(n_boot):
        out[b] = float(np.mean([stat(rng.choice(r, size=r.size, replace=True)) for r in rows]))
    a = (1 - level) / 2
    lo, hi = np.percentile(out, [100 * a, 100 * (1 - a)])
    return float(lo), float(hi)


def performance_profile(margins: Sequence[float], taus: Sequence[float] = PROFILE_TAUS) -> dict[str, float]:
    """Fraction of checks whose margin is at least τ, for each τ (in decades). τ = 0 is the pass rate."""
    m = np.asarray([x for x in margins if np.isfinite(x)], dtype=float)
    if m.size == 0:
        return {f"{t:g}": float("nan") for t in taus}
    return {f"{t:g}": float((m >= t).mean()) for t in taus}


def paired_difference(a: Sequence[float], b: Sequence[float]) -> dict[str, float]:
    """Per-item paired differences a − b (same checks, two models): mean, its SE, and the fraction
    of items on which a is better (probability of improvement, ties count half)."""
    x = np.asarray(a, dtype=float); y = np.asarray(b, dtype=float)
    ok = np.isfinite(x) & np.isfinite(y)
    d = x[ok] - y[ok]
    if d.size == 0:
        return {"n": 0, "mean": float("nan"), "se": float("nan"), "p_improve": float("nan")}
    se = float(d.std(ddof=1) / math.sqrt(d.size)) if d.size > 1 else float("nan")
    p = float(((d > 0).sum() + 0.5 * (d == 0).sum()) / d.size)
    return {"n": int(d.size), "mean": float(d.mean()), "se": se, "p_improve": p}
