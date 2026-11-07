from datetime import timedelta

import pandas as pd
import pytest

from bagent.data.store import PointInTime, upsert
from bagent.eval import backtest as bt
from tests.conftest import utc


def _seed(con):
    ko = [utc(2023, 8, 12, 14), utc(2023, 8, 13, 14), utc(2023, 8, 19, 14), utc(2023, 8, 22, 18)]
    m = pd.DataFrame(dict(match_id=["a", "b", "c", "d"], league="EPL", division="E0", season=2023, kickoff_utc=ko,
                          home_id=["x", "y", "x", "z"], away_id=["y", "z", "z", "x"], source_home="", source_away="",
                          kickoff_time_known=True))
    r = pd.DataFrame(dict(match_id=m.match_id, home_goals=[1, 0, 3, 1], away_goals=[0, 0, 1, 2], ftr=list("HDHA"),
                          available_at=[k + timedelta(minutes=150) for k in ko], source="t"))
    rows = []
    for mid, k in zip(m.match_id, ko):
        for phase, at, pr in (("early", k - timedelta(hours=20), (2.0, 3.4, 3.8)),
                              ("late", k - timedelta(minutes=30), (1.5, 4.0, 6.0)),  # lukituksen jälkeen
                              ("closing", k, (1.8, 3.6, 4.4))):
            for s, p in zip("HDA", pr):
                rows.append(dict(match_id=mid, source="t", bookmaker="pinnacle", market="1x2",
                                 phase="early" if phase == "late" else phase, selection=s, price=p,
                                 available_at=at, available_at_estimated=False))
    upsert(con, "matches", m)
    upsert(con, "results", r)
    upsert(con, "odds", pd.DataFrame(rows))
    return m


@pytest.fixture
def seeded(mem_con, monkeypatch):
    _seed(mem_con)
    return mem_con


def test_test_period_locked(seeded):
    with pytest.raises(bt.TestPeriodLockedError):
        bt.load_frame(seeded, [2024])


def test_asof_odds_excludes_after_lock(seeded):
    f = bt.load_frame(seeded, [2023])
    o = bt.asof_odds(seeded, f, phase="early", market="1x2")
    assert (o.merge(f[["match_id", "t"]])["available_at"] < o.merge(f[["match_id", "t"]])["t"]).all()
    # 30 min ennen aloitusta tullut kerroin (1.5) ei saa näkyä lukitushetkellä (60 min ennen)
    assert 1.5 not in set(o.price)
    w = bt.book_matrix(o, "pinnacle", "1x2")
    assert set(w["H"]) == {2.0}


def test_closing_only_inclusive(seeded):
    f = bt.load_frame(seeded, [2023])
    assert bt.asof_odds(seeded, f, phase="closing", market="1x2", time_col="kickoff_utc").empty
    assert len(bt.asof_odds(seeded, f, phase="closing", market="1x2", time_col="kickoff_utc", inclusive=True)) == 12


def test_rounds_and_walk_forward_sees_only_past(seeded):
    f = bt.load_frame(seeded, [2023])
    assert f["round"].nunique() == 3  # 12.–13.8., 19.8., 22.8.
    seen = []

    def fp(con, t_fit, matches):
        res = PointInTime(con, t_fit).table("results")
        assert (res["available_at"] < t_fit).all()
        assert not set(res.match_id) & set(matches.match_id)
        seen.append(len(res))
        return pd.DataFrame(index=matches.match_id)

    bt.walk_forward(seeded, f, fp)
    assert seen == [0, 2, 3]


def test_base_rate_uses_only_past(seeded):
    f = bt.load_frame(seeded, [2023])
    br = bt.base_rate(seeded, f[f.match_id.isin(["c", "d"])], "1x2")
    # c (19.8.): aiemmat tulokset H, D -> [0.5, 0.5, 0]; d: H, D, H -> [2/3, 1/3, 0]
    assert br.loc["c"].tolist() == [0.5, 0.5, 0.0]
    assert br.loc["d"].tolist() == pytest.approx([2 / 3, 1 / 3, 0.0])
