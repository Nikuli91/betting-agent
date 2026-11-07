"""Understat: historiallinen xG otteluittain (2020/21–2025/26).

TILA 2026-11-07: understat.com palautti huoltosivun ("We will come back soon") kaikkiin
liigasivuihin, joten vastausten rakennetta ei ole voitu todentaa. PLAN 2.6:n mukaisesti
jäsennintä ei kirjoiteta arvaamalla: tämä moduuli hakee ja tallentaa raakavastaukset
välimuistiin (kohteliaasti, viiveellä), ja parse() toteutetaan, kun rakenne on nähty.
"""
from __future__ import annotations

import time
from pathlib import Path

import httpx

from bagent.config import RAW_DIR, settings

LEAGUE_SLUG = {"EPL": "EPL", "BUNDESLIGA": "Bundesliga"}
MAINTENANCE_MARKER = "We will come back soon"


class SourceUnavailableError(RuntimeError):
    pass


def raw_path(league: str, season: int) -> Path:
    return RAW_DIR / "understat" / f"{LEAGUE_SLUG[league]}_{season}.html"


def fetch_league_page(league: str, season: int, *, force: bool = False) -> Path:
    p = raw_path(league, season)
    if p.exists() and not force and MAINTENANCE_MARKER not in p.read_text(errors="ignore"):
        return p
    cfg = settings()["http"]
    url = f"https://understat.com/league/{LEAGUE_SLUG[league]}/{season}"
    with httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": cfg["user_agent"]}) as c:
        r = c.get(url)
    time.sleep(cfg["delay_seconds"])
    if r.status_code != 200 or MAINTENANCE_MARKER in r.text:
        raise SourceUnavailableError(f"Understat ei vastaa ({r.status_code}): {url}")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(r.text, encoding="utf-8")
    return p


def parse(path: Path):  # pragma: no cover - toteutetaan, kun rakenne on todennettu
    raise NotImplementedError("Understatin vastausrakennetta ei ole vielä todennettu (ks. docs/data_sources.md)")
