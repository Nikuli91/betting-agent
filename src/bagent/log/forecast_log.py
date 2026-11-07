"""Lukittu, append-only ennusteloki (PLAN 2.3).

- Rivi kirjoitetaan ennen aloitusta; myöhästynyt kirjoitus hylätään.
- Jokainen rivi sisältää malliversion, git-commitin, sisällön hashin ja edellisen rivin hashin
  (hash-ketju). Lukittua riviä ei voi muuttaa rajapinnan kautta; korjaus on uusi rivi, joka
  viittaa korjattavaan (supersedes).
- DuckDB:ssä ei ole triggereitä, joten suora SQL-muokkaus estetään havaitsemalla se:
  verify() tarkistaa ketjun, ja append() kieltäytyy kirjoittamasta rikkinäisen ketjun perään.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import duckdb

from bagent.config import ROOT

LOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS forecast_log (
    seq BIGINT PRIMARY KEY,
    forecast_id VARCHAR NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL,
    match_id VARCHAR NOT NULL,
    kickoff_utc TIMESTAMPTZ NOT NULL,
    model_version VARCHAR NOT NULL,
    git_commit VARCHAR NOT NULL,
    payload JSON NOT NULL,
    supersedes VARCHAR,
    prev_hash VARCHAR NOT NULL,
    content_hash VARCHAR NOT NULL
);
"""
GENESIS = "0" * 64


class LockedRowError(RuntimeError):
    """Lukitun rivin muokkausyritys."""


class TamperedLogError(RuntimeError):
    """Hash-ketju ei täsmää: lokia on muokattu ohi rajapinnan."""


class ForecastTooLateError(RuntimeError):
    """Ennuste yritettiin kirjata aloituksen jälkeen."""


def git_commit() -> str:
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                             text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
                               capture_output=True, text=True, check=True).stdout.strip()
        return sha + ("-dirty" if dirty else "")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "nogit"


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _hash(fields: dict[str, Any], prev_hash: str) -> str:
    return hashlib.sha256((prev_hash + _canonical_json(fields)).encode("utf-8")).hexdigest()


def _ts(t: datetime) -> str:
    return t.astimezone(timezone.utc).isoformat(timespec="microseconds")


@dataclass
class ForecastLog:
    con: duckdb.DuckDBPyConnection

    def __post_init__(self) -> None:
        self.con.execute(LOG_SCHEMA)

    # --- kirjoitus -----------------------------------------------------------------
    def append(self, *, match_id: str, kickoff_utc: datetime, model_version: str,
               payload: dict[str, Any], now: datetime | None = None,
               supersedes: str | None = None, commit: str | None = None) -> str:
        now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        if kickoff_utc.tzinfo is None:
            raise ValueError("kickoff_utc tarvitsee aikavyöhykkeen")
        if now >= kickoff_utc:
            raise ForecastTooLateError(f"{match_id}: {now:%Y-%m-%d %H:%M} >= aloitus {kickoff_utc:%Y-%m-%d %H:%M}")
        self.verify()
        if supersedes is not None and not self._exists(supersedes):
            raise KeyError(f"Korjattavaa ennustetta ei ole: {supersedes}")
        last = self.con.execute("SELECT seq, content_hash FROM forecast_log ORDER BY seq DESC LIMIT 1").fetchone()
        seq, prev = (last[0] + 1, last[1]) if last else (1, GENESIS)
        fid = str(uuid.uuid4())
        fields = dict(seq=seq, forecast_id=fid, created_at=_ts(now), match_id=match_id,
                      kickoff_utc=_ts(kickoff_utc), model_version=model_version,
                      git_commit=commit or git_commit(), payload=payload, supersedes=supersedes)
        h = _hash(fields, prev)
        self.con.execute(
            "INSERT INTO forecast_log VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [seq, fid, now, match_id, kickoff_utc, model_version, fields["git_commit"],
             _canonical_json(payload), supersedes, prev, h],
        )
        return fid

    def correct(self, forecast_id: str, **kwargs: Any) -> str:
        """Korjaus = uusi rivi, joka viittaa alkuperäiseen. Alkuperäinen säilyy."""
        return self.append(supersedes=forecast_id, **kwargs)

    def update(self, *_: Any, **__: Any) -> None:
        raise LockedRowError("Ennustelokin rivit ovat lukittuja. Käytä correct()-metodia.")

    delete = update

    # --- luku ja tarkistus ---------------------------------------------------------
    def _exists(self, fid: str) -> bool:
        return self.con.execute("SELECT 1 FROM forecast_log WHERE forecast_id = ?", [fid]).fetchone() is not None

    def rows(self) -> list[dict[str, Any]]:
        cur = self.con.execute("SELECT * FROM forecast_log ORDER BY seq")
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def verify(self) -> None:
        prev = GENESIS
        for i, r in enumerate(self.rows(), start=1):
            if r["seq"] != i:
                raise TamperedLogError(f"seq-aukko tai poisto kohdassa {i}")
            if r["prev_hash"] != prev:
                raise TamperedLogError(f"seq {r['seq']}: prev_hash ei täsmää")
            fields = dict(seq=r["seq"], forecast_id=r["forecast_id"], created_at=_ts(r["created_at"]),
                          match_id=r["match_id"], kickoff_utc=_ts(r["kickoff_utc"]),
                          model_version=r["model_version"], git_commit=r["git_commit"],
                          payload=json.loads(r["payload"]), supersedes=r["supersedes"])
            if _hash(fields, prev) != r["content_hash"]:
                raise TamperedLogError(f"seq {r['seq']}: sisältö muuttunut lukituksen jälkeen")
            if r["created_at"] >= r["kickoff_utc"]:
                raise TamperedLogError(f"seq {r['seq']}: created_at aloituksen jälkeen")
            prev = r["content_hash"]
