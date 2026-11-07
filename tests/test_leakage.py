"""Vuototesti (PLAN 2.2): ennuste hetkellä t näkee vain rivit, joiden available_at < t."""
from datetime import timedelta

import pandas as pd
import pytest

from bagent.data.store import TIMED_TABLES, PointInTime, upsert
from bagent.models.elo import compute_pre_match
from tests.conftest import utc


def _seed(con):
    ko = [utc(2024, 8, 17, 14), utc(2024, 8, 24, 14), utc(2024, 8, 31, 14)]
    m = pd.DataFrame(dict(match_id=["m1", "m2", "m3"], league="EPL", division="E0", season=2024,
                          kickoff_utc=ko, home_id=["a", "b", "a"], away_id=["b", "a", "b"],
                          source_home="x", source_away="y", kickoff_time_known=True))
    r = pd.DataFrame(dict(match_id=["m1", "m2", "m3"], home_goals=[2, 0, 1], away_goals=[0, 0, 3], ftr=["H", "D", "A"],
                          available_at=[k + timedelta(minutes=150) for k in ko], source="t"))
    upsert(con, "matches", m)
    upsert(con, "results", r)
    return m, r


def test_point_in_time_filters_strictly(mem_con):
    m, r = _seed(mem_con)
    t = r.available_at[1]  # tasan m2:n tuloksen hetki -> m2 ei näy (ehto on <)
    got = PointInTime(mem_con, t).table("results")
    assert set(got.match_id) == {"m1"}
    assert (got.available_at < t).all()


def test_point_in_time_rejects_untimed_and_naive(mem_con):
    _seed(mem_con)
    with pytest.raises(ValueError):
        PointInTime(mem_con, utc(2024, 9, 1)).table("matches")
    with pytest.raises(ValueError):
        from datetime import datetime
        PointInTime(mem_con, datetime(2024, 9, 1))


def test_future_rows_do_not_change_past_view(mem_con):
    _seed(mem_con)
    t = utc(2024, 8, 25)
    before = PointInTime(mem_con, t).table("results")
    upsert(mem_con, "results", pd.DataFrame(dict(match_id=["m3"], home_goals=[9], away_goals=[9], ftr=["D"],
                                                 available_at=[utc(2024, 8, 31, 16, 30)], source="t")))
    after = PointInTime(mem_con, t).table("results")
    pd.testing.assert_frame_equal(before, after)


def test_elo_uses_only_past_results():
    m = pd.DataFrame(dict(match_id=["m1", "m2", "m3"], league="EPL", division="E0", season=2024,
                          kickoff_utc=[utc(2024, 8, 17, 14), utc(2024, 8, 24, 14), utc(2024, 8, 31, 14)],
                          home_id=["a", "b", "a"], away_id=["b", "a", "b"]))
    r = pd.DataFrame(dict(match_id=["m1", "m2", "m3"], home_goals=[2, 0, 1], away_goals=[0, 0, 3],
                          available_at=[k + timedelta(minutes=150) for k in m.kickoff_utc]))
    base = compute_pre_match(m, r).set_index("match_id")
    r2 = r.copy()
    r2.loc[2, ["home_goals", "away_goals"]] = [7, 0]  # muutetaan vain viimeisen ottelun tulosta
    r2.loc[1, ["home_goals", "away_goals"]] = [5, 0]  # ja toiseksi viimeisen
    alt = compute_pre_match(m, r2).set_index("match_id")
    # m1 ja m2 ennen muutettuja tuloksia -> identtiset; m3 riippuu m2:sta -> muuttuu
    assert base.loc["m1", "home_elo"] == alt.loc["m1", "home_elo"]
    assert base.loc["m2", "home_elo"] == alt.loc["m2", "home_elo"]
    assert base.loc["m3", "home_elo"] != alt.loc["m3", "home_elo"]
    assert (base["available_at"] < m.set_index("match_id")["kickoff_utc"]).all()


def test_result_not_available_until_after_kickoff_even_if_late_published():
    """Jos tulos julkaistaan vasta seuraavan ottelun jälkeen, Elo ei saa käyttää sitä."""
    m = pd.DataFrame(dict(match_id=["m1", "m2"], league="EPL", division="E0", season=2024,
                          kickoff_utc=[utc(2024, 8, 17, 14), utc(2024, 8, 17, 18)],
                          home_id=["a", "a"], away_id=["b", "c"]))
    r = pd.DataFrame(dict(match_id=["m1"], home_goals=[3], away_goals=[0],
                          available_at=[utc(2024, 8, 17, 18, 30)]))  # vasta m2:n aloituksen jälkeen
    e = compute_pre_match(m, r).set_index("match_id")
    assert e.loc["m2", "home_elo"] == e.loc["m1", "home_elo"]


# --- oikea tietokanta -------------------------------------------------------------
@pytest.mark.parametrize("table", [t for t in TIMED_TABLES if t != "results"])
def test_real_db_pre_match_rows_precede_kickoff(real_con, table):
    """Ennen ottelua käytettävät rivit: kertoimet (paitsi closing = aloitushetki) ja Elo < aloitus."""
    if table == "xg":
        sql = """SELECT count(*) FROM xg JOIN matches USING (match_id) WHERE xg.available_at <= matches.kickoff_utc"""
    elif table == "odds":
        sql = """SELECT count(*) FROM odds JOIN matches USING (match_id)
                 WHERE (phase <> 'closing' AND odds.available_at >= matches.kickoff_utc)
                    OR (phase = 'closing' AND odds.available_at > matches.kickoff_utc)"""
    else:
        sql = f"""SELECT count(*) FROM {table} JOIN matches USING (match_id)
                  WHERE {table}.available_at >= matches.kickoff_utc"""
    assert real_con.execute(sql).fetchone()[0] == 0


def test_real_db_results_after_kickoff(real_con):
    n = real_con.execute("""SELECT count(*) FROM results JOIN matches USING (match_id)
                            WHERE results.available_at <= matches.kickoff_utc""").fetchone()[0]
    assert n == 0


def test_real_db_point_in_time_snapshot(real_con):
    t = utc(2024, 1, 1)
    pit = PointInTime(real_con, t)
    for name in TIMED_TABLES:
        df = pit.table(name)
        assert df.empty or (df["available_at"] < t).all()
