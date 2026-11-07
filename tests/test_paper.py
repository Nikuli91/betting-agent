"""Paperiajo: pörssin palkkio ja ottelukohtaiset syötteet."""
import numpy as np
import pandas as pd
import pytest

from bagent.agent import run as agent


def test_effective_odds_commission():
    assert agent.effective_odds(3.0, "betfair_ex_eu") == pytest.approx(1 + 2 * 0.95)
    assert agent.effective_odds(3.0, "coolbet") == 3.0


def test_match_inputs_best_user_price_and_sharp():
    rows = []
    for book, pr in (("pinnacle", (2.0, 3.6, 4.0)), ("coolbet", (2.1, 3.4, 3.9)),
                     ("betfair_ex_eu", (2.2, 3.7, 4.2)), ("williamhill", (1.9, 3.3, 4.5))):
        for s, p in zip("HDA", pr):
            rows.append(dict(bookmaker=book, market="h2h", selection=s, price=p))
    g = pd.DataFrame(rows)
    inp = agent.match_inputs(g, "1x2", np.array([0.45, 0.28, 0.27]))
    assert inp["sharp_book"] == "pinnacle"
    assert inp["p_sharp"].sum() == pytest.approx(1)
    # H: betfair 2.2 -> 1 + 1.2·0.95 = 2.14 > coolbet 2.1; A: williamhill ei ole käyttäjän välittäjä
    assert inp["user"]["H"] == (pytest.approx(2.14), "betfair_ex_eu")
    assert inp["user"]["A"][1] == "betfair_ex_eu"
    assert inp["X"].shape == (3, 4) and np.all(inp["X"][:, 2] == 0)
