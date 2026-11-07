"""Ennustemittarit (PLAN 7). Pienempi on parempi kaikissa paitsi kalibrointitaulussa.

p: (n × K) todennäköisyysmatriisi, y: (n,) oikean luokan indeksi 0..K-1.
1X2:n luokkajärjestys on H, D, A (järjestetty RPS:ää varten).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

EPS = 1e-15


def _check(p, y):
    p = np.asarray(p, dtype=float)
    y = np.asarray(y, dtype=int)
    if p.ndim != 2 or len(p) != len(y):
        raise ValueError("p:n pitää olla (n × K) ja y:n pituus n")
    if not np.allclose(p.sum(axis=1), 1.0, atol=1e-6):
        raise ValueError("Rivien summa ei ole 1")
    return p, y


def log_loss(p, y) -> float:
    p, y = _check(p, y)
    return float(-np.mean(np.log(np.clip(p[np.arange(len(y)), y], EPS, 1.0))))


def brier(p, y) -> float:
    """Monen luokan Brier: Σ_k (p_k − o_k)², keskiarvo otteluittain."""
    p, y = _check(p, y)
    o = np.zeros_like(p)
    o[np.arange(len(y)), y] = 1.0
    return float(np.mean(np.sum((p - o) ** 2, axis=1)))


def rps(p, y) -> float:
    """Ranked probability score järjestetyille luokille: 1/(K−1) Σ (F_k − O_k)²."""
    p, y = _check(p, y)
    k = p.shape[1]
    o = np.zeros_like(p)
    o[np.arange(len(y)), y] = 1.0
    cf, co = np.cumsum(p, axis=1)[:, :-1], np.cumsum(o, axis=1)[:, :-1]
    return float(np.mean(np.sum((cf - co) ** 2, axis=1) / (k - 1)))


def calibration_table(p, y, bins: int = 10) -> pd.DataFrame:
    """Kaikki (ottelu, lopputulos) -parit 10 %:n väleihin: ennuste vs. toteutunut osuus."""
    p, y = _check(p, y)
    o = np.zeros_like(p)
    o[np.arange(len(y)), y] = 1.0
    pf, of = p.ravel(), o.ravel()
    idx = np.minimum((pf * bins).astype(int), bins - 1)
    rows = []
    for b in range(bins):
        m = idx == b
        if m.any():
            rows.append(dict(bin=f"{b / bins:.1f}–{(b + 1) / bins:.1f}", n=int(m.sum()),
                             predicted=float(pf[m].mean()), observed=float(of[m].mean())))
    df = pd.DataFrame(rows)
    df["gap_pp"] = 100 * (df["observed"] - df["predicted"])
    return df


def all_metrics(p, y, ordered: bool = True) -> dict[str, float]:
    out = {"n": int(len(y)), "log_loss": log_loss(p, y), "brier": brier(p, y)}
    if ordered and np.asarray(p).shape[1] > 2:
        out["rps"] = rps(p, y)
    return out
