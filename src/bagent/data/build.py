"""Datan rakennus: raaka-CSV:t -> DuckDB, Elo, ja vaiheen 1 portin kattavuusraportti."""
from __future__ import annotations

import duckdb
import pandas as pd

from bagent.config import settings
from bagent.data import football_data as fd
from bagent.data.store import upsert
from bagent.models.elo import compute_pre_match


def build_football_data(con: duckdb.DuckDBPyConnection, download: bool = True) -> dict[str, int]:
    counts = {"matches": 0, "results": 0, "odds": 0, "xg": 0}
    for league, f in fd.all_files():
        if download:
            fd.download(f)
        elif not f.path.exists():
            continue
        parsed = fd.parse(fd.read_raw(f.path), league, f.season, f.div)
        replace_source_rows(con, parsed["matches"]["match_id"], "football_data")
        for table, df in parsed.items():
            counts[table] += upsert(con, table, df)
    return counts


def replace_source_rows(con: duckdb.DuckDBPyConnection, match_ids: pd.Series, source: str) -> None:
    """Poistaa lähteen aiemmat rivit näille otteluille, jotta uudelleenrakennus on idempotentti
    myös silloin, kun available_at-sääntö (osa pääavainta) muuttuu."""
    if match_ids.empty:
        return
    con.register("_ids", pd.DataFrame({"match_id": match_ids.unique()}))
    try:
        for table in ("odds", "xg", "results"):
            con.execute(f"DELETE FROM {table} WHERE source = ? AND match_id IN (SELECT match_id FROM _ids)", [source])
    finally:
        con.unregister("_ids")


def build_elo(con: duckdb.DuckDBPyConnection) -> int:
    m = con.execute("SELECT match_id, league, division, season, kickoff_utc, home_id, away_id FROM matches").df()
    r = con.execute("SELECT match_id, home_goals, away_goals, available_at FROM results").df()
    elo = compute_pre_match(m, r)
    con.execute("DELETE FROM elo_pre")
    return upsert(con, "elo_pre", elo)


def coverage(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Vaiheen 1 portti: kattavuus pääsarjoille historiakausilta ja nykykaudelta."""
    cfg = settings()
    first = cfg["first_history_season"]
    sharp = cfg["sharp_reference"]["historical"]
    sharp_sql = ", ".join(f"'{b}'" for b in sharp)
    fb = cfg["sharp_reference"]["fallback"]
    return con.execute(f"""
        WITH o AS (
          SELECT match_id,
            bool_or(market='1x2' AND phase='early') AS early_1x2,
            bool_or(market='1x2' AND phase='closing') AS close_1x2,
            bool_or(market='ou25' AND phase='early') AS early_ou,
            bool_or(market='ou25' AND phase='closing') AS close_ou,
            bool_or(market='1x2' AND phase='closing' AND bookmaker IN ({sharp_sql})) AS sharp_close_1x2,
            bool_or(market='ou25' AND phase='closing' AND bookmaker IN ({sharp_sql})) AS sharp_close_ou,
            bool_or(market='1x2' AND phase='closing' AND bookmaker IN ({sharp_sql}, '{fb}')) AS ref_close_1x2,
            bool_or(market='ou25' AND phase='closing' AND bookmaker IN ({sharp_sql}, '{fb}')) AS ref_close_ou,
            bool_or(market='1x2' AND phase='closing' AND bookmaker='pinnacle') AS pin_close_1x2,
            bool_or(market='1x2' AND phase='closing' AND bookmaker='betfair_exchange') AS bfe_close_1x2
          FROM odds GROUP BY match_id)
        SELECT m.league, m.season, count(*) AS matches,
          count(r.match_id) AS result,
          count(e.match_id) FILTER (WHERE e.home_games > 0 AND e.away_games > 0) AS elo,
          count(*) FILTER (WHERE o.early_1x2) AS early_1x2,
          count(*) FILTER (WHERE o.close_1x2) AS close_1x2,
          count(*) FILTER (WHERE o.early_ou) AS early_ou,
          count(*) FILTER (WHERE o.close_ou) AS close_ou,
          count(*) FILTER (WHERE o.sharp_close_1x2) AS sharp_close_1x2,
          count(*) FILTER (WHERE o.sharp_close_ou) AS sharp_close_ou,
          count(*) FILTER (WHERE o.ref_close_1x2) AS ref_close_1x2,
          count(*) FILTER (WHERE o.ref_close_ou) AS ref_close_ou,
          count(*) FILTER (WHERE o.pin_close_1x2) AS pinnacle_close,
          count(*) FILTER (WHERE o.bfe_close_1x2) AS bfe_close,
          count(x.match_id) AS xg
        FROM matches m
        LEFT JOIN results r USING (match_id)
        LEFT JOIN elo_pre e USING (match_id)
        LEFT JOIN o USING (match_id)
        LEFT JOIN (SELECT DISTINCT match_id FROM xg) x USING (match_id)
        WHERE m.league NOT LIKE '%_FEEDER' AND m.season >= {first}
        GROUP BY ALL ORDER BY m.league, m.season
    """).df()


def gate_ok(cov: pd.DataFrame) -> tuple[bool, list[str]]:
    """Portti historiakausille (pois lukien nykyinen, kesken oleva kausi)."""
    cur = settings()["current_season"]
    hist = cov[cov["season"] < cur]
    need = ["result", "elo", "early_1x2", "close_1x2", "early_ou", "close_ou", "ref_close_1x2", "ref_close_ou"]
    problems = []
    for _, row in hist.iterrows():
        for c in need:
            if row[c] < row["matches"]:
                problems.append(f"{row['league']} {row['season']}: {c} {row[c]}/{row['matches']}")
    fb_1x2 = int((hist["ref_close_1x2"] - hist["sharp_close_1x2"]).sum())
    fb_ou = int((hist["ref_close_ou"] - hist["sharp_close_ou"]).sum())
    notes = [f"HUOM: vertailukerroin varavaihtoehdosta (market_avg): 1X2 {fb_1x2}, yli/alle {fb_ou} ottelua"]
    return (not problems), problems + notes
