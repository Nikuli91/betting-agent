"""Understatin xG Kaggle-aineistosta (codytipton/understat-data, tiedosto game_stats.csv).

Rakenne todennettu 2026-11-07: yksi rivi per joukkue per ottelu, sarakkeet mm.
league, season, club_name, home_away ('h'/'a'), xG, xGA, scored, missed, date.
Vastustajaa ei ole, joten koti- ja vierasrivi parittuvat: sama liiga ja päivämäärä,
kotirivin xG = vierasrivin xGA ja päinvastoin. Ottelu liitetään football-datan otteluun
koti- ja vierasjoukkueen sekä päivämäärän (±1 vrk) perusteella, ja maalit tarkistetaan.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import duckdb
import pandas as pd

from bagent.config import RAW_DIR, settings
from bagent.data.team_names import to_canonical

RAW_PATH = RAW_DIR / "understat_kaggle" / "game_stats.csv"
LEAGUE_MAP = {"EPL": "EPL", "Bundesliga": "BUNDESLIGA"}
SOURCE = "understat_kaggle"


def pair_matches(g: pd.DataFrame) -> pd.DataFrame:
    first = settings()["elo_warmup_first_season"]  # vain kaudet, joiden ottelut ovat kannassa
    g = g[g["league"].isin(LEAGUE_MAP) & (g["season"] >= first)].copy()
    g["league"] = g["league"].map(LEAGUE_MAP)
    g["team_id"] = [to_canonical("understat", n) for n in g["club_name"]]
    g["day"] = pd.to_datetime(g["date"]).dt.date
    h = g[g["home_away"] == "h"]
    a = g[g["home_away"] == "a"]
    m = h.merge(a, on=["league", "season", "day"], suffixes=("_h", "_a"))
    m = m[(abs(m["xG_h"] - m["xGA_a"]) < 1e-6) & (abs(m["xGA_h"] - m["xG_a"]) < 1e-6)
          & (m["scored_h"] == m["missed_a"]) & (m["missed_h"] == m["scored_a"])]
    return m[["league", "season", "day", "team_id_h", "team_id_a", "xG_h", "xG_a",
              "scored_h", "scored_a"]].rename(columns={
        "team_id_h": "home_id", "team_id_a": "away_id", "xG_h": "home_xg", "xG_a": "away_xg",
        "scored_h": "home_goals", "scored_a": "away_goals"})


def import_xg(con: duckdb.DuckDBPyConnection, path: Path = RAW_PATH) -> dict[str, int]:
    pairs = pair_matches(pd.read_csv(path))
    fx = con.execute("""SELECT m.match_id, m.league, m.home_id, m.away_id, m.kickoff_utc,
                               r.home_goals AS fd_hg, r.away_goals AS fd_ag
                        FROM matches m JOIN results r USING (match_id)
                        WHERE m.league IN ('EPL','BUNDESLIGA')""").df()
    fx["day"] = fx["kickoff_utc"].dt.tz_convert("Europe/London").dt.date
    j = pairs.merge(fx, on=["league", "home_id", "away_id"])
    j = j[(pd.to_datetime(j["day_x"]) - pd.to_datetime(j["day_y"])).abs() <= pd.Timedelta(days=1)]
    goals_ok = (j["home_goals"] == j["fd_hg"]) & (j["away_goals"] == j["fd_ag"])
    bad = j[~goals_ok]
    good = j[goals_ok]
    delay = timedelta(minutes=settings()["availability"]["xg_minutes_after_kickoff"])
    out = pd.DataFrame(dict(match_id=good["match_id"], source=SOURCE, home_xg=good["home_xg"],
                            away_xg=good["away_xg"], available_at=good["kickoff_utc"] + delay))
    out = out.drop_duplicates("match_id")
    con.execute("DELETE FROM xg WHERE source = ?", [SOURCE])
    from bagent.data.store import upsert
    upsert(con, "xg", out)
    return {"understat_pairs": len(pairs), "matched": len(out), "goal_mismatch": len(bad),
            "unmatched": len(pairs) - len(j)}
