"""Malli A:n walk-forward (PLAN 9, vaihe 3).

Data luetaan kerran muistiin, mutta jokaisella kierroksella käytetään vain rivejä, joiden
available_at < t_fit (kierroksen ensimmäinen ennustehetki). Saman kierroksen myöhemmät ottelut
ennustetaan samalla sovituksella, mikä on varovaista (ei tuoreempaa tietoa kuin tuotannossa).
"""
from __future__ import annotations

from dataclasses import dataclass

import duckdb
import numpy as np
import pandas as pd

from bagent.models import dixon_coles as dc
from bagent.models import scoreline as sl


@dataclass
class History:
    results: pd.DataFrame   # match_id, league, season, kickoff_utc, home_id, away_id, home_goals, away_goals, available_at
    xg: pd.DataFrame        # match_id, home_xg, away_xg, available_at (yksi lähde per ottelu)
    elo: pd.DataFrame       # league(pooli), kickoff_utc, team_id, elo, available_at


def load_history(con: duckdb.DuckDBPyConnection, xg_sources: tuple[str, ...] = ("understat_kaggle", "football_data")) -> History:
    res = con.execute("""
        SELECT m.match_id, m.league, m.season, m.kickoff_utc, m.home_id, m.away_id,
               r.home_goals, r.away_goals, r.available_at
        FROM matches m JOIN results r USING (match_id)
        WHERE m.league IN ('EPL','BUNDESLIGA')""").df()
    src = ", ".join(f"'{s}'" for s in xg_sources)
    order = " ".join(f"WHEN '{s}' THEN {i}" for i, s in enumerate(xg_sources))
    xg = con.execute(f"""
        SELECT match_id, home_xg, away_xg, available_at FROM (
          SELECT *, row_number() OVER (PARTITION BY match_id ORDER BY CASE source {order} END) rn
          FROM xg WHERE source IN ({src})) WHERE rn = 1""").df()
    elo = con.execute("""
        SELECT replace(m.league, '_FEEDER', '') AS league, m.kickoff_utc, m.home_id AS team_id,
               e.home_elo AS elo, e.available_at FROM elo_pre e JOIN matches m USING (match_id)
        UNION ALL
        SELECT replace(m.league, '_FEEDER', ''), m.kickoff_utc, m.away_id, e.away_elo, e.available_at
        FROM elo_pre e JOIN matches m USING (match_id)""").df()
    return History(res, xg, elo)


def training_set(h: History, league: str, t_fit: pd.Timestamp, params: dc.DCParams) -> pd.DataFrame:
    r = h.results
    r = r[(r["league"] == league) & (r["available_at"] < t_fit)
          & (r["kickoff_utc"] >= t_fit - pd.Timedelta(days=params.window_days))]
    if params.variant == "goals":
        return r.assign(y_home=r["home_goals"], y_away=r["away_goals"])
    x = h.xg[h.xg["available_at"] < t_fit]
    r = r.merge(x[["match_id", "home_xg", "away_xg"]], on="match_id")
    return r.assign(y_home=r["home_xg"], y_away=r["away_xg"])


def elo_at(h: History, league: str, t_fit: pd.Timestamp) -> dict[str, float]:
    """Joukkueen viimeisin Elo-luku, jonka available_at < t_fit (pooli sisältää syöttösarjan)."""
    e = h.elo[(h.elo["league"] == league) & (h.elo["available_at"] < t_fit)]
    e = e.sort_values("kickoff_utc").groupby("team_id").tail(1)
    return dict(zip(e["team_id"], e["elo"]))


def predict_round(h: History, t_fit: pd.Timestamp, rnd: pd.DataFrame, params: dc.DCParams) -> pd.DataFrame:
    league = rnd["league"].iloc[0]
    season = int(rnd["season"].iloc[0])
    train = training_set(h, league, t_fit, params)
    cur = train[train["season"] == season]
    games = pd.concat([cur["home_id"], cur["away_id"]]).value_counts().to_dict()
    fit = dc.fit(train, t_fit, params, elo=elo_at(h, league, t_fit), season_games=games)
    lh, la = fit.lambdas(list(rnd["home_id"]), list(rnd["away_id"]))
    m = sl.score_matrix(lh, la, fit.rho)
    p1 = sl.probs_1x2(m)
    po = sl.probs_ou(m)
    return pd.DataFrame({"p_H": p1[:, 0], "p_D": p1[:, 1], "p_A": p1[:, 2], "p_O": po[:, 0], "p_U": po[:, 1],
                         "lambda_h": lh, "lambda_a": la, "rho": fit.rho, "converged": fit.converged},
                        index=rnd["match_id"].to_numpy())


def walk_forward(h: History, frame: pd.DataFrame, params: dc.DCParams) -> pd.DataFrame:
    out = []
    for rid, g in frame.groupby("round", sort=False):
        out.append(predict_round(h, g["t"].min(), g, params))
    return pd.concat(out)
