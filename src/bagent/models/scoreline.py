"""Tulosmatriisi 0–0 … 10–10 maaliodotuksista ja markkinatodennäköisyydet siitä (PLAN 6).

Dixon–Coles-korjaus τ matalille tuloksille (0–0, 1–0, 0–1, 1–1) parametrilla ρ.
Matriisi normalisoidaan summaan 1 (katkaisu 10 maalissa ja τ-korjaus muuttavat summaa hieman).
"""
from __future__ import annotations

import numpy as np
from scipy.stats import poisson

MAX_GOALS = 10


def dc_tau(lh, la, rho):
    """τ(0,0), τ(0,1), τ(1,0), τ(1,1) vektoreina (Dixon & Coles 1997)."""
    lh, la = np.asarray(lh, float), np.asarray(la, float)
    return 1 - lh * la * rho, 1 + lh * rho, 1 + la * rho, 1 - rho


def score_matrix(lh, la, rho: float = 0.0, max_goals: int = MAX_GOALS) -> np.ndarray:
    """(n × G × G) tai (G × G): P(koti = i, vieras = j)."""
    scalar = np.ndim(lh) == 0
    lh, la = np.atleast_1d(np.asarray(lh, float)), np.atleast_1d(np.asarray(la, float))
    g = np.arange(max_goals + 1)
    ph = poisson.pmf(g[None, :], lh[:, None])
    pa = poisson.pmf(g[None, :], la[:, None])
    m = ph[:, :, None] * pa[:, None, :]
    t00, t01, t10, t11 = dc_tau(lh, la, rho)
    m[:, 0, 0] *= t00
    m[:, 0, 1] *= t01
    m[:, 1, 0] *= t10
    m[:, 1, 1] *= t11
    m = np.clip(m, 0, None)
    m /= m.sum(axis=(1, 2), keepdims=True)
    return m[0] if scalar else m


def probs_1x2(m: np.ndarray) -> np.ndarray:
    """(…, G, G) -> (…, 3) järjestyksessä H, D, A."""
    h = np.tril(np.ones(m.shape[-2:]), -1)  # i > j
    a = np.triu(np.ones(m.shape[-2:]), 1)
    return np.stack([(m * h).sum(axis=(-2, -1)), np.trace(m, axis1=-2, axis2=-1), (m * a).sum(axis=(-2, -1))], -1)


def probs_ou(m: np.ndarray, line: float = 2.5) -> np.ndarray:
    """(…, G, G) -> (…, 2) järjestyksessä yli, alle."""
    g = np.arange(m.shape[-1])
    over = (g[:, None] + g[None, :]) > line
    po = (m * over).sum(axis=(-2, -1))
    return np.stack([po, 1 - po], -1)
