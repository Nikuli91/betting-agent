"""DuckDB-skeema, kirjoitus ja ajankohtaan sidottu luku.

Vuotosuoja (PLAN 2.2): jokaisella ennusteessa käytettävällä rivillä on available_at.
Ennustekoodi lukee dataa vain PointInTime-näkymän kautta, joka palauttaa rivit, joille
available_at < t. Ottelurunko (matches) on aikataulutietoa ja aina luettavissa, mutta
lopputulos on omassa taulussaan (results) eikä sitä ole matches-taulussa.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

from bagent.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS matches (
    match_id VARCHAR PRIMARY KEY,
    league VARCHAR NOT NULL,
    division VARCHAR NOT NULL,
    season INTEGER NOT NULL,
    kickoff_utc TIMESTAMPTZ NOT NULL,
    home_id VARCHAR NOT NULL,
    away_id VARCHAR NOT NULL,
    source_home VARCHAR,
    source_away VARCHAR,
    kickoff_time_known BOOLEAN
);
CREATE TABLE IF NOT EXISTS results (
    match_id VARCHAR PRIMARY KEY,
    home_goals INTEGER NOT NULL,
    away_goals INTEGER NOT NULL,
    ftr VARCHAR NOT NULL,
    available_at TIMESTAMPTZ NOT NULL,
    source VARCHAR NOT NULL
);
CREATE TABLE IF NOT EXISTS xg (
    match_id VARCHAR NOT NULL,
    source VARCHAR NOT NULL,
    home_xg DOUBLE NOT NULL,
    away_xg DOUBLE NOT NULL,
    available_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (match_id, source)
);
CREATE TABLE IF NOT EXISTS odds (
    match_id VARCHAR NOT NULL,
    source VARCHAR NOT NULL,
    bookmaker VARCHAR NOT NULL,
    market VARCHAR NOT NULL,          -- '1x2' | 'ou25'
    phase VARCHAR NOT NULL,           -- 'early' | 'closing' | 'snapshot'
    selection VARCHAR NOT NULL,       -- H/D/A | O/U
    price DOUBLE NOT NULL,
    available_at TIMESTAMPTZ NOT NULL,
    available_at_estimated BOOLEAN NOT NULL,
    PRIMARY KEY (match_id, source, bookmaker, market, phase, selection, available_at)
);
CREATE TABLE IF NOT EXISTS elo_pre (
    match_id VARCHAR PRIMARY KEY,
    home_elo DOUBLE NOT NULL,
    away_elo DOUBLE NOT NULL,
    home_games INTEGER NOT NULL,      -- ottelut, joista luku on laskettu
    away_games INTEGER NOT NULL,
    available_at TIMESTAMPTZ NOT NULL -- viimeisimmän käytetyn tuloksen available_at
);
CREATE TABLE IF NOT EXISTS model_registry (
    version VARCHAR PRIMARY KEY,
    git_commit VARCHAR NOT NULL,
    train_window VARCHAR,
    validation_metrics JSON,
    deployed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL
);
"""

TIMED_TABLES = ("results", "xg", "odds", "elo_pre")


def connect(path: Path | str | None = None) -> duckdb.DuckDBPyConnection:
    p = Path(path) if path is not None else DB_PATH
    if str(p) != ":memory:":
        p.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(p))
    con.execute("SET TimeZone='UTC'")
    con.execute(SCHEMA)
    return con


def upsert(con: duckdb.DuckDBPyConnection, table: str, df: pd.DataFrame) -> int:
    """Korvaa samat pääavaimet. Lähdedata (ei ennusteloki) saa päivittyä, esim. korjatut tulokset."""
    if df is None or df.empty:
        return 0
    cols = list(df.columns)
    con.register("_incoming", df)
    try:
        con.execute(f"INSERT OR REPLACE INTO {table} ({', '.join(cols)}) "
                    f"SELECT {', '.join(cols)} FROM _incoming")
    finally:
        con.unregister("_incoming")
    return len(df)


def _as_utc(t: datetime) -> datetime:
    if t.tzinfo is None:
        raise ValueError("Ajankohdalla pitää olla aikavyöhyke")
    return t.astimezone(timezone.utc)


@dataclass(frozen=True)
class PointInTime:
    """Datanäkymä hetkellä t: vain rivit, joiden available_at < t."""

    con: duckdb.DuckDBPyConnection
    t: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "t", _as_utc(self.t))

    def table(self, name: str, where: str = "", params: list | None = None) -> pd.DataFrame:
        if name not in TIMED_TABLES:
            raise ValueError(f"{name} ei ole aikaleimattu taulu; käytä fixtures()-metodia")
        sql = f"SELECT * FROM {name} WHERE available_at < ?"
        if where:
            sql += f" AND ({where})"
        return self.con.execute(sql, [self.t, *(params or [])]).df()

    def fixtures(self, where: str = "", params: list | None = None) -> pd.DataFrame:
        """Otteluohjelma (ei tuloksia). Aikataulu on julkinen etukäteen, joten sitä ei rajata."""
        sql = "SELECT * FROM matches"
        if where:
            sql += f" WHERE {where}"
        return self.con.execute(sql, params or []).df()
