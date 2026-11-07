"""Panostus: murto-Kelly ja rajat (PLAN 8, settings.core)."""
from __future__ import annotations

import numpy as np


def kelly(p: float, k: float) -> float:
    """Täysi Kelly-osuus kassasta yksittäiselle vedolle: (p·k − 1)/(k − 1), negatiivinen -> 0."""
    if k <= 1:
        return 0.0
    return max(0.0, (p * k - 1.0) / (k - 1.0))


def stakes(p: np.ndarray, k: np.ndarray, fraction: float, max_per_bet: float, max_per_round: float) -> np.ndarray:
    """Kierroksen vetojen osuudet kassasta: fraction · Kelly, katto per veto ja kierroksen summalle
    (summa skaalataan suhteessa alas). Ei koskaan kasvata panoksia rajojen yli."""
    s = np.array([min(fraction * kelly(pi, ki), max_per_bet) for pi, ki in zip(p, k)], float)
    tot = s.sum()
    if tot > max_per_round:
        s *= max_per_round / tot
    return s
