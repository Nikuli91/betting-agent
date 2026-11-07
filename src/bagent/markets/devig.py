"""Katteenpoisto: multiplicative, power ja Shin (PLAN 6, malli B).

Kaikki funktiot ottavat desimaalikertoimet (yhden markkinan kaikki lopputulokset) ja
palauttavat todennäköisyydet, joiden summa on 1. Vektoroidut versiot ottavat
(n_ottelua × n_lopputulosta)-matriisin.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import brentq

METHODS = ("multiplicative", "power", "shin")


def _implied(odds) -> np.ndarray:
    o = np.asarray(odds, dtype=float)
    if np.any(~np.isfinite(o)) or np.any(o <= 1.0):
        raise ValueError(f"Kertoimien pitää olla > 1: {o}")
    return 1.0 / o


def multiplicative(odds) -> np.ndarray:
    q = _implied(odds)
    return q / q.sum()


def power(odds) -> np.ndarray:
    """p_i = q_i^k, k valitaan niin, että Σp = 1. Pienentää pitkien kertoimien todennäköisyyttä enemmän."""
    q = _implied(odds)
    s = q.sum()
    if abs(s - 1.0) < 1e-12:
        return q.copy()
    f = lambda k: np.sum(q ** k) - 1.0  # noqa: E731
    # q_i < 1, joten Σq^k on laskeva k:n suhteen. s > 1 -> k > 1; s < 1 -> k < 1.
    lo, hi = (1.0, 2.0) if s > 1 else (0.5, 1.0)
    while f(lo) * f(hi) > 0:
        lo, hi = (lo, hi * 2) if s > 1 else (lo / 2, hi)
    k = brentq(f, lo, hi, xtol=1e-14)
    p = q ** k
    return p / p.sum()


def shin_z(odds) -> float:
    """Shinin sisäpiirikaupan osuus z ≥ 0. Jos Σq ≤ 1 (ei katetta), z = 0."""
    q = _implied(odds)
    s = q.sum()
    if s <= 1.0 + 1e-12:
        return 0.0

    def total(z: float) -> float:
        return float(np.sum(_shin_p(q, s, z)) - 1.0)

    return float(brentq(total, 0.0, 0.999, xtol=1e-14))


def _shin_p(q: np.ndarray, s: float, z: float) -> np.ndarray:
    return (np.sqrt(z * z + 4.0 * (1.0 - z) * q * q / s) - z) / (2.0 * (1.0 - z))


def shin(odds) -> np.ndarray:
    q = _implied(odds)
    s = q.sum()
    z = shin_z(odds)
    if z == 0.0:
        return q / s
    p = _shin_p(q, s, z)
    return p / p.sum()  # poistaa numeerisen jäännöksen


_FUNCS = {"multiplicative": multiplicative, "power": power, "shin": shin}


def devig(odds, method: str = "power") -> np.ndarray:
    try:
        return _FUNCS[method](odds)
    except KeyError:
        raise ValueError(f"Tuntematon menetelmä {method!r}; vaihtoehdot {METHODS}") from None


def devig_matrix(odds: np.ndarray, method: str = "power") -> np.ndarray:
    """Rivi kerrallaan; multiplicative vektoroitu."""
    odds = np.asarray(odds, dtype=float)
    if method == "multiplicative":
        q = 1.0 / odds
        return q / q.sum(axis=1, keepdims=True)
    return np.vstack([devig(row, method) for row in odds])


def overround(odds) -> float:
    return float(_implied(odds).sum() - 1.0)
