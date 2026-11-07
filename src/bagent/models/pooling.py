"""Log-lineaarinen pooli p ∝ p_A^w · p_B^(1−w) ja painon w sovitus (PLAN 6).

w sovitetaan minimoimalla ristientropia kohdetta vastaan:
- kohde = lopputulos (one-hot) -> tavallinen log loss
- kohde = katteeton sulkeutumistodennäköisyys (pehmeä jakauma) -> ennustetaanko markkinan liike
w on rajattu välille [0, 1]; reunalla oleva arvo on sellaisenaan tulos (esim. w = 0: malli A ei lisää mitään).
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize_scalar

EPS = 1e-12


def pool(pa: np.ndarray, pb: np.ndarray, w: float) -> np.ndarray:
    la = np.log(np.clip(pa, EPS, 1))
    lb = np.log(np.clip(pb, EPS, 1))
    z = w * la + (1 - w) * lb
    z -= z.max(axis=-1, keepdims=True)
    p = np.exp(z)
    return p / p.sum(axis=-1, keepdims=True)


def cross_entropy(p: np.ndarray, target: np.ndarray) -> float:
    return float(-np.mean(np.sum(target * np.log(np.clip(p, EPS, 1)), axis=-1)))


def one_hot(y: np.ndarray, k: int) -> np.ndarray:
    o = np.zeros((len(y), k))
    o[np.arange(len(y)), y] = 1
    return o


def fit_w(pa: np.ndarray, pb: np.ndarray, target: np.ndarray, bounds=(0.0, 1.0)) -> float:
    r = minimize_scalar(lambda w: cross_entropy(pool(pa, pb, w), target), bounds=bounds, method="bounded",
                        options={"xatol": 1e-5})
    return float(r.x)


def bootstrap_w(pa, pb, target, n_boot: int = 500, seed: int = 20261107, groups: np.ndarray | None = None):
    """Bootstrap-väli w:lle. groups = kierrostunnus -> klusteroitu otanta (saman kierroksen ottelut korreloivat)."""
    rng = np.random.default_rng(seed)
    if groups is None:
        groups = np.arange(len(pa))
    ug, inv = np.unique(groups, return_inverse=True)
    members = [np.flatnonzero(inv == g) for g in range(len(ug))]
    ws = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(ug), len(ug))
        ix = np.concatenate([members[g] for g in pick])
        ws.append(fit_w(pa[ix], pb[ix], target[ix]))
    ws = np.array(ws)
    return float(np.quantile(ws, 0.025)), float(np.quantile(ws, 0.975)), ws
