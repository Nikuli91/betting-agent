"""The Odds API (v4): ajantasaiset kertoimet snapshotteina.

Todennettu 2026-11-07 oikeilla kutsuilla (dokumentaatiosivua ei saatu auki, ks. docs/data_sources.md):
- GET /v4/sports?apiKey=... -> lista {key, group, title, description, active, has_outrights};
  ei kuluta krediittejä (x-requests-last: 0).
- GET /v4/sports/{sport}/odds?apiKey=&regions=eu&markets=h2h,totals&oddsFormat=decimal&dateFormat=iso
  -> lista otteluita {id, sport_key, sport_title, commence_time, home_team, away_team, bookmakers[]};
  bookmakers[] = {key, title, last_update, markets[]}; markets[] = {key, last_update, outcomes[]};
  outcomes[] = {name, price} (h2h: joukkueen nimi tai "Draw"), totals: lisäksi point (2.5, 2.75, 3, ...).
  Kulutus x-requests-last = alueet × markkinat (eu × 2 = 2).
- Vastausotsakkeet: x-requests-remaining, x-requests-used, x-requests-last.

Periaatteet:
- Avain välitetään vain kyselyparametrina. Sitä ei tulosteta; virheviesteistä se peitetään.
- Jokainen vastaus tallennetaan raakana (gzip) hakuhetken aikaleimalla hakemistoon, joka on
  versionhallinnassa (snapshots/odds_api/), koska pilvikontti on lyhytikäinen ja kerroinliikettä
  ei voi kerätä jälkikäteen. Kanta rakennetaan raakatiedostoista uudelleen (`load_all`).
- odds_snapshots-tauluun menee kaikki sellaisenaan. odds-tauluun (phase='snapshot') menee vain
  h2h ja totals-linja 2.5, ja haamukertoimet suodatetaan: alkanut ottelu tai markkinan
  last_update yli `stale_minutes` vanhempi kuin hakuhetki.
- available_at = hakuhetki (silloin kerroin oli meidän tiedossamme).
"""
from __future__ import annotations

import gzip
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import duckdb
import httpx
import pandas as pd

from bagent.config import ROOT, secret, settings
from bagent.data.football_data import match_id
from bagent.data.store import upsert
from bagent.data.team_names import UnknownTeamError, to_canonical

BASE = "https://api.the-odds-api.com/v4"
SOURCE = "odds_api"

SNAPSHOT_SCHEMA = """
CREATE TABLE IF NOT EXISTS odds_api_events (
    event_id VARCHAR PRIMARY KEY,
    match_id VARCHAR NOT NULL,
    league VARCHAR NOT NULL,
    commence_time TIMESTAMPTZ NOT NULL,
    home_id VARCHAR NOT NULL,
    away_id VARCHAR NOT NULL,
    first_seen TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS odds_snapshots (
    fetched_at TIMESTAMPTZ NOT NULL,
    event_id VARCHAR NOT NULL,
    match_id VARCHAR NOT NULL,
    bookmaker VARCHAR NOT NULL,
    market VARCHAR NOT NULL,          -- API:n avain: h2h | totals
    selection VARCHAR NOT NULL,       -- H/D/A | O/U
    point DOUBLE,                     -- totals-linja, h2h: NULL
    price DOUBLE NOT NULL,
    book_last_update TIMESTAMPTZ,
    market_last_update TIMESTAMPTZ
);
"""


class OddsApiError(RuntimeError):
    pass


def cfg() -> dict[str, Any]:
    return settings()["odds_api"]


def snapshot_dir() -> Path:
    return ROOT / cfg()["snapshot_dir"]


def ensure_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(SNAPSHOT_SCHEMA)


def _mask(text: str, key: str | None) -> str:
    return text.replace(key, "***") if key else text


def _get(client: httpx.Client, path: str, params: dict[str, str]) -> tuple[Any, dict[str, str]]:
    key = secret("ODDS_API_KEY")
    if not key:
        raise OddsApiError("ODDS_API_KEY puuttuu (ympäristömuuttuja tai .env)")
    try:
        r = client.get(f"{BASE}{path}", params={"apiKey": key, **params})
    except httpx.HTTPError as e:  # verkkovirheen viesti voi sisältää URL:n
        raise OddsApiError(_mask(f"{type(e).__name__}: {e}", key)) from None
    usage = {k: r.headers.get(k, "") for k in ("x-requests-remaining", "x-requests-used", "x-requests-last")}
    if r.status_code != 200:
        raise OddsApiError(_mask(f"HTTP {r.status_code} {path}: {r.text[:300]}", key))
    return r.json(), usage


def _client() -> httpx.Client:
    return httpx.Client(timeout=30, headers={"User-Agent": settings()["http"]["user_agent"]})


def usage() -> dict[str, str]:
    """Krediittitilanne ilmaisella /sports-kutsulla."""
    with _client() as c:
        _, u = _get(c, "/sports", {})
    return u


def fetch_league(league: str, client: httpx.Client, now: datetime | None = None) -> tuple[Path, dict[str, str]]:
    """Hakee yhden sarjan kertoimet ja tallentaa raakavastauksen. Palauttaa polun ja kulutuksen."""
    c = cfg()
    sport = settings()["leagues"][league]["odds_api"]
    params = {"regions": ",".join(c["regions"]), "markets": ",".join(c["markets"]),
              "oddsFormat": "decimal", "dateFormat": "iso"}
    data, u = _get(client, f"/sports/{sport}/odds", params)
    fetched = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    rec = {"fetched_at": fetched.isoformat(), "league": league, "sport": sport,
           "params": params, "usage": u, "data": data}
    p = snapshot_dir() / f"{fetched:%Y/%m/%d}" / f"{league}_{fetched:%Y%m%dT%H%M%SZ}.json.gz"
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, separators=(",", ":"))
    return p, u


def _ts(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def parse_snapshot(rec: dict[str, Any]) -> dict[str, pd.DataFrame]:
    """Raakavastaus -> odds_api_events, odds_snapshots ja odds (suodatettu, phase='snapshot')."""
    league = rec["league"]
    fetched = _ts(rec["fetched_at"])
    stale = timedelta(minutes=cfg()["stale_minutes"])
    events, snaps, odds = [], [], []
    unknown: set[str] = set()
    for ev in rec["data"]:
        try:
            h = to_canonical(SOURCE, ev["home_team"])
            a = to_canonical(SOURCE, ev["away_team"])
        except UnknownTeamError:
            unknown.update(n for n in (ev["home_team"], ev["away_team"])
                           if n not in _known())
            continue
        ko = _ts(ev["commence_time"])
        mid = match_id(league, ko, h, a)
        events.append(dict(event_id=ev["id"], match_id=mid, league=league, commence_time=ko,
                           home_id=h, away_id=a, first_seen=fetched))
        sel_h2h = {ev["home_team"]: "H", ev["away_team"]: "A", "Draw": "D"}
        for b in ev.get("bookmakers", []):
            for m in b.get("markets", []):
                mlu = _ts(m.get("last_update"))
                rows = []
                for o in m.get("outcomes", []):
                    if m["key"] == "h2h":
                        sel, point = sel_h2h.get(o["name"]), None
                    elif m["key"] == "totals":
                        sel, point = {"Over": "O", "Under": "U"}.get(o["name"]), o.get("point")
                    else:
                        continue
                    if sel is None:
                        raise ValueError(f"Tuntematon outcome {o['name']!r} markkinassa {m['key']}")
                    rows.append(dict(fetched_at=fetched, event_id=ev["id"], match_id=mid,
                                     bookmaker=b["key"], market=m["key"], selection=sel, point=point,
                                     price=float(o["price"]), book_last_update=_ts(b.get("last_update")),
                                     market_last_update=mlu))
                snaps += rows
                # Haamukerroinsuodatus vain odds-tauluun; odds_snapshots säilyttää kaiken.
                if ko <= fetched or (mlu is not None and fetched - mlu > stale):
                    continue
                if m["key"] == "h2h" and len(rows) == 3:
                    market = "1x2"
                    keep = rows
                elif m["key"] == "totals":
                    market = "ou25"
                    keep = [r for r in rows if r["point"] == 2.5]
                    if len(keep) != 2:
                        continue
                else:
                    continue
                odds += [dict(match_id=mid, source=SOURCE, bookmaker=r["bookmaker"], market=market,
                              phase="snapshot", selection=r["selection"], price=r["price"],
                              available_at=fetched, available_at_estimated=False) for r in keep]
    # Tuntematon joukkue ohittaa vain oman ottelunsa; nimet palautetaan, jotta ajo voidaan merkitä virheeksi.
    return {"odds_api_events": pd.DataFrame(events), "odds_snapshots": pd.DataFrame(snaps),
            "odds": pd.DataFrame(odds), "unknown": sorted(unknown)}


def _known() -> set[str]:
    from bagent.data.team_names import known_names
    return known_names(SOURCE)


def read_snapshot(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def load_file(con: duckdb.DuckDBPyConnection, path: Path) -> dict[str, int]:
    ensure_schema(con)
    parsed = parse_snapshot(read_snapshot(path))
    ev = parsed["odds_api_events"]
    if not ev.empty:  # first_seen säilyy ensimmäisenä havaintona
        con.register("_ev", ev)
        try:
            con.execute("INSERT INTO odds_api_events SELECT * FROM _ev "
                        "WHERE event_id NOT IN (SELECT event_id FROM odds_api_events)")
        finally:
            con.unregister("_ev")
    sn = parsed["odds_snapshots"]
    if not sn.empty:  # sama tiedosto uudelleen -> ei kaksoisrivejä
        con.register("_sn", sn[["fetched_at", "event_id"]].drop_duplicates())
        try:
            con.execute("DELETE FROM odds_snapshots WHERE (fetched_at, event_id) IN "
                        "(SELECT (fetched_at, event_id) FROM _sn)")
        finally:
            con.unregister("_sn")
        con.register("_sn", sn)
        try:
            con.execute(f"INSERT INTO odds_snapshots ({', '.join(sn.columns)}) SELECT * FROM _sn")
        finally:
            con.unregister("_sn")
    return {"events": len(ev), "snapshot_rows": len(sn), "unknown": parsed["unknown"],
            "odds_rows": upsert(con, "odds", parsed["odds"])}


def load_all(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Rakentaa snapshot-taulut uudelleen kaikista tallennetuista raakatiedostoista."""
    ensure_schema(con)
    con.execute("DELETE FROM odds_snapshots")
    con.execute("DELETE FROM odds_api_events")
    con.execute("DELETE FROM odds WHERE source = ?", [SOURCE])
    tot = {"files": 0, "events": 0, "snapshot_rows": 0, "odds_rows": 0}
    unknown: set[str] = set()
    for p in sorted(snapshot_dir().rglob("*.json.gz")):
        n = load_file(con, p)
        tot["files"] += 1
        unknown.update(n.pop("unknown"))
        for k, v in n.items():
            tot[k] += v
    if unknown:
        tot["unknown_teams"] = sorted(unknown)
    tot["events"] = con.execute("SELECT count(*) FROM odds_api_events").fetchone()[0]
    return tot


def snapshot(con: duckdb.DuckDBPyConnection, leagues: list[str] | None = None) -> list[dict[str, Any]]:
    """Hakee kaikki sarjat, tallentaa raakana ja kirjoittaa kantaan. Pysähtyy krediittivaran kohdalla."""
    leagues = leagues or list(settings()["leagues"])
    reserve = cfg()["min_credits_reserve"]
    cost = len(cfg()["regions"]) * len(cfg()["markets"])
    out = []
    with _client() as c:
        _, u = _get(c, "/sports", {})
        remaining = int(u["x-requests-remaining"] or 0)
        for lg in leagues:
            if remaining - cost < reserve:
                out.append({"league": lg, "skipped": f"krediittejä {remaining}, varaus {reserve}"})
                continue
            path, u = fetch_league(lg, c)
            remaining = int(u["x-requests-remaining"] or 0)
            res = {"league": lg, "file": str(path.relative_to(ROOT)), **u}
            n = load_file(con, path)  # raakadata on jo tallessa; ohitetut ottelut latautuvat mappauksen jälkeen
            unknown = n.pop("unknown")
            res.update(n)
            if unknown:
                res["error"] = (f"tuntemattomat joukkueet {unknown}; lisää team_registry.csv:n "
                                "odds_api-sarakkeeseen (muut ottelut tallennettiin)")
            out.append(res)
    return out
