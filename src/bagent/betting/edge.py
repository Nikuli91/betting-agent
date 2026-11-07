"""EV ja vihjeiden valinta (PLAN 8).

EV = p · k − 1, missä k on paras kerroin käyttäjän välittäjillä. Terävän markkinan kerrointa käytetään
vain todennäköisyyteen. Jos mallin ja terävän markkinan ero on yli varoitusrajan, kohde merkitään
tarkistettavaksi eikä sitä pelata (useimmiten datavirhe).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def ev(p, k):
    return np.asarray(p, float) * np.asarray(k, float) - 1.0


def select_bets(p: np.ndarray, k: np.ndarray, p_sharp: np.ndarray, threshold: float,
                divergence_pp: float) -> pd.DataFrame:
    """Rivi per ottelu: paras valinta, jos sen EV ≥ kynnys. Enintään yksi veto per ottelu ja markkina.

    p, k, p_sharp: (n × K). k:ssa NaN = kerrointa ei ole. Palauttaa sarakkeet
    sel (indeksi tai −1), ev, bet (bool), flagged (bool).
    """
    e = ev(p, k)
    e = np.where(np.isnan(e), -np.inf, e)
    sel = e.argmax(axis=1)
    best = e[np.arange(len(e)), sel]
    div = np.abs(p - p_sharp)[np.arange(len(e)), sel] * 100
    passes = best >= threshold
    flagged = passes & (div > divergence_pp)
    return pd.DataFrame({"sel": np.where(passes, sel, -1), "ev": best, "bet": passes & ~flagged,
                         "flagged": flagged})
