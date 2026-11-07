"""CLV (PLAN 7): mitataan aina katteettomaan terävään sulkeutumiseen.

CLV = k_veto · p_sulkeutuminen − 1, missä p_sulkeutuminen on terävän vertailukertoimen katteeton
todennäköisyys (sama menetelmä kuin devig-oletus). Lisäksi kerroinpohjainen k_veto/k_sulkeutuminen − 1
saman välittäjän sisällä raportoidaan, mutta sitä ei käytetä porttina.
"""
from __future__ import annotations

import numpy as np


def clv(k_bet, p_close):
    return np.asarray(k_bet, float) * np.asarray(p_close, float) - 1.0


def price_clv(k_bet, k_close_same_book):
    return np.asarray(k_bet, float) / np.asarray(k_close_same_book, float) - 1.0


def cluster_bootstrap_mean(x: np.ndarray, groups: np.ndarray, n_boot: int = 2000, seed: int = 20261107,
                           alpha: float = 0.05) -> tuple[float, float]:
    """Klusteroitu bootstrap (saman kierroksen vedot korreloivat sulkeutumisliikkeen kautta)."""
    x = np.asarray(x, float)
    if len(x) == 0:
        return (np.nan, np.nan)
    ug, inv = np.unique(groups, return_inverse=True)
    sums = np.bincount(inv, x, len(ug))
    cnts = np.bincount(inv, minlength=len(ug)).astype(float)
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, len(ug), (n_boot, len(ug)))
    means = sums[pick].sum(axis=1) / cnts[pick].sum(axis=1)
    return float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2))
