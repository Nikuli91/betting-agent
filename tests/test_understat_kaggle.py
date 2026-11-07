import pandas as pd

from bagent.data.understat_kaggle import pair_matches

ROWS = [  # sarakkeet kuten game_stats.csv:ssä (todennettu 2026-11-07)
    dict(league="EPL", season=2023, club_name="Arsenal", home_away="h", xG=2.1, xGA=0.4, scored=2, missed=0, date="2023-08-12 12:30:00"),
    dict(league="EPL", season=2023, club_name="Nottingham Forest", home_away="a", xG=0.4, xGA=2.1, scored=0, missed=2, date="2023-08-12 12:30:00"),
    dict(league="EPL", season=2023, club_name="Burnley", home_away="h", xG=0.3, xGA=2.0, scored=0, missed=3, date="2023-08-11 19:00:00"),
    dict(league="EPL", season=2023, club_name="Manchester City", home_away="a", xG=2.0, xGA=0.3, scored=3, missed=0, date="2023-08-11 19:00:00"),
    dict(league="La liga", season=2023, club_name="Real Madrid", home_away="h", xG=1, xGA=1, scored=1, missed=1, date="2023-08-12 19:00:00"),
]


def test_pairs_home_and_away_rows():
    p = pair_matches(pd.DataFrame(ROWS)).sort_values("home_id").reset_index(drop=True)
    assert list(p.home_id) == ["eng_arsenal", "eng_burnley"]
    assert list(p.away_id) == ["eng_nott_m_forest", "eng_man_city"]
    assert p.loc[0, "home_xg"] == 2.1 and p.loc[0, "away_xg"] == 0.4


def test_real_db_understat_goals_match_results(real_con):
    """Tuonti hyväksyy vain ottelut, joiden maalit täsmäävät; kattavuus 2020–2023 täydellinen."""
    n = real_con.execute("""SELECT count(*) FROM matches m WHERE m.league IN ('EPL','BUNDESLIGA')
        AND m.season BETWEEN 2020 AND 2023
        AND NOT EXISTS (SELECT 1 FROM xg WHERE xg.match_id = m.match_id)""").fetchone()[0]
    assert n == 0
