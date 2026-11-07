from datetime import timedelta

import pandas as pd

from bagent.models.elo import EloParams, compute_pre_match, expected_home
from tests.conftest import utc


def test_expected_symmetry():
    assert abs(expected_home(1500, 1500, 0) - 0.5) < 1e-12
    assert expected_home(1600, 1500, 0) + expected_home(1500, 1600, 0) == 1.0


def test_winner_gains_and_zero_sum():
    ko = [utc(2024, 8, 17, 14), utc(2024, 8, 24, 14)]
    m = pd.DataFrame(dict(match_id=["m1", "m2"], league="EPL", division="E0", season=2024,
                          kickoff_utc=ko, home_id=["a", "c"], away_id=["b", "a"]))
    r = pd.DataFrame(dict(match_id=["m1"], home_goals=[1], away_goals=[0],
                          available_at=[ko[0] + timedelta(hours=3)]))
    e = compute_pre_match(m, r, EloParams()).set_index("match_id")
    a_after = e.loc["m2", "away_elo"]
    assert a_after > 1500
    gain = a_after - 1500
    assert abs(gain - 20 * (1 - expected_home(1500, 1500, 60))) < 1e-9


def test_feeder_init_and_promotion_carries_rating():
    ko = [utc(2023, 8, 5, 14), utc(2024, 8, 17, 14)]
    m = pd.DataFrame(dict(match_id=["f1", "m1"], league=["EPL_FEEDER", "EPL"], division=["E1", "E0"],
                          season=[2023, 2024], kickoff_utc=ko, home_id=["p", "p"], away_id=["q", "a"]))
    r = pd.DataFrame(dict(match_id=["f1"], home_goals=[3], away_goals=[0], available_at=[ko[0] + timedelta(hours=3)]))
    e = compute_pre_match(m, r, EloParams(season_regress=0.0)).set_index("match_id")
    assert e.loc["f1", "home_elo"] == 1350
    assert e.loc["m1", "home_elo"] > 1350 and e.loc["m1", "home_games"] == 1
    assert e.loc["m1", "away_elo"] == 1500
