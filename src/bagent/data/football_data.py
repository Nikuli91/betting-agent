"""football-data.co.uk: tulokset, aikaiset ja sulkeutuvat kertoimet, (2026/27 alkaen) xG.

Sarakenimet on todennettu lähteen notes.txt:stä ja ladatuista CSV-otsikoista 2026-11-07,
ks. docs/data_sources.md. Tuntemattomia sarakkeita ei jäsennetä.

Aikaleimat:
- Kellonajat ovat Lontoon aikaa (todennettu Bundesliigan aloitusajoista).
- "Pre-closing"-kertoimet kerätään pe-iltapäivänä (viikonloppu) tai ti-iltapäivänä (viikko).
  Tarkkaa hetkeä ei ole, joten available_at arvioidaan varovaisesti myöhäiseksi.
"""
from __future__ import annotations

import io
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import pandas as pd

from bagent.config import RAW_DIR, season_code, settings
from bagent.data.team_names import to_canonical

BASE_URL = "https://www.football-data.co.uk/mmz4281/{code}/{div}.csv"

# Dokumentoidut välittäjäprefiksit 1X2-markkinalle (notes.txt). Avain = sarakeprefiksi,
# arvo = projektin välittäjätunnus. Sulkeutuva = prefiksi + "C" (esim. PSCH).
H2H_PREFIXES: dict[str, str] = {
    "PS": "pinnacle",
    "B365": "bet365",
    "BW": "betandwin",
    "BF": "betfair_sportsbook",
    "BFE": "betfair_exchange",
    "BFD": "betfred",
    "BV": "betvictor",
    "WH": "william_hill",
    "1XB": "1xbet",
    "PP": "paddy_power",
    "Max": "market_max",
    "Avg": "market_avg",
}
# Yli/alle 2,5: early-sarake -> closing-sarake. Pinnaclella prefiksi on "P" ja closing "PC".
OU_PREFIXES: dict[str, tuple[str, str]] = {
    "pinnacle": ("P", "PC"),
    "bet365": ("B365", "B365C"),
    "betfair_exchange": ("BFE", "BFEC"),
    "market_max": ("Max", "MaxC"),
    "market_avg": ("Avg", "AvgC"),
}

LONDON = ZoneInfo("Europe/London")


@dataclass(frozen=True)
class FDFile:
    div: str
    season: int  # aloitusvuosi

    @property
    def url(self) -> str:
        return BASE_URL.format(code=season_code(self.season), div=self.div)

    @property
    def path(self) -> Path:
        return RAW_DIR / "football_data" / season_code(self.season) / f"{self.div}.csv"


def download(f: FDFile, *, force: bool = False, client: httpx.Client | None = None) -> Path:
    """Lataa CSV välimuistiin. Päättyneet kaudet ladataan vain kerran."""
    cfg = settings()
    is_current = f.season >= cfg["current_season"]
    if f.path.exists() and not force:
        age_h = (time.time() - f.path.stat().st_mtime) / 3600
        if not is_current or age_h < cfg["http"]["current_season_max_age_hours"]:
            return f.path
    own = client is None
    client = client or httpx.Client(
        follow_redirects=True, timeout=60, headers={"User-Agent": cfg["http"]["user_agent"]}
    )
    try:
        r = client.get(f.url)
        r.raise_for_status()
        f.path.parent.mkdir(parents=True, exist_ok=True)
        f.path.write_bytes(r.content)
        time.sleep(cfg["http"]["delay_seconds"])
    finally:
        if own:
            client.close()
    return f.path


def read_raw(path: Path) -> pd.DataFrame:
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig", errors="replace")
    df = pd.read_csv(io.StringIO(text), dtype=str)
    df = df.dropna(how="all")
    df = df[df["HomeTeam"].notna() & df["AwayTeam"].notna()]
    df.columns = [c.strip() for c in df.columns]
    return df.reset_index(drop=True)


def kickoff_utc(date_str: str, time_str: str | None) -> datetime:
    """'16/08/2024' + '20:00' (Lontoo) -> UTC. Vanhoissa tiedostoissa vuosi voi olla 2-numeroinen."""
    fmt = "%d/%m/%Y" if len(date_str.split("/")[-1]) == 4 else "%d/%m/%y"
    d = datetime.strptime(date_str, fmt)
    if time_str and isinstance(time_str, str) and ":" in time_str:
        hh, mm = (int(x) for x in time_str.split(":")[:2])
    else:  # aika puuttuu: oletetaan klo 12 paikallista, mikä on varovainen tuloksille, ei kertoimille
        hh, mm = 12, 0
    return d.replace(hour=hh, minute=mm, tzinfo=LONDON).astimezone(timezone.utc)


def early_odds_available_at(ko_utc: datetime) -> datetime:
    """Arvio pre-closing-kertoimien keruuhetkelle.

    pe/la/su/ma-ottelut -> edeltävä (tai sama) perjantai; ti/ke/to -> edeltävä (tai sama) tiistai.
    Kellonaika asetuksista (oletus 18:00 Lontoo). Rajataan viimeistään N min ennen aloitusta.
    """
    cfg = settings()["availability"]
    local = ko_utc.astimezone(LONDON)
    wd = local.weekday()  # ma=0 ... su=6
    anchor = 4 if wd in (4, 5, 6, 0) else 1  # perjantai tai tiistai
    back = (wd - anchor) % 7
    day = (local - timedelta(days=back)).date()
    hh, mm = (int(x) for x in cfg["early_odds_collection_local_time"].split(":"))
    est = datetime(day.year, day.month, day.day, hh, mm, tzinfo=LONDON).astimezone(timezone.utc)
    latest = ko_utc - timedelta(minutes=cfg["early_odds_min_minutes_before_kickoff"])
    return min(est, latest)


def _price(row: pd.Series, col: str) -> float | None:
    v = row.get(col)
    if v is None or (isinstance(v, float) and pd.isna(v)) or v == "":
        return None
    try:
        x = float(v)
    except ValueError:
        return None
    return x if x > 1.0 else None


def match_id(league: str, ko_utc: datetime, home_id: str, away_id: str) -> str:
    return f"{league}_{ko_utc:%Y%m%d}_{home_id}_{away_id}"


def parse(df: pd.DataFrame, league: str, season: int, div: str) -> dict[str, pd.DataFrame]:
    """Muuntaa raaka-CSV:n normalisoiduiksi tauluiksi: matches, results, odds, xg."""
    cfg = settings()["availability"]
    res_delay = timedelta(minutes=cfg["result_minutes_after_kickoff"])
    xg_delay = timedelta(minutes=cfg["xg_minutes_after_kickoff"])
    matches, results, odds, xg = [], [], [], []
    for _, r in df.iterrows():
        ko = kickoff_utc(r["Date"], r.get("Time"))
        h = to_canonical("football_data", r["HomeTeam"])
        a = to_canonical("football_data", r["AwayTeam"])
        mid = match_id(league, ko, h, a)
        matches.append(dict(match_id=mid, league=league, division=div, season=season,
                            kickoff_utc=ko, home_id=h, away_id=a,
                            source_home=r["HomeTeam"], source_away=r["AwayTeam"],
                            kickoff_time_known=bool(isinstance(r.get("Time"), str))))
        if isinstance(r.get("FTHG"), str) and r["FTHG"] != "":
            results.append(dict(match_id=mid, home_goals=int(float(r["FTHG"])),
                                away_goals=int(float(r["FTAG"])), ftr=r["FTR"],
                                available_at=ko + res_delay, source="football_data"))
        if "HxG" in df.columns and isinstance(r.get("HxG"), str) and r["HxG"] != "":
            xg.append(dict(match_id=mid, source="football_data", home_xg=float(r["HxG"]),
                           away_xg=float(r["AxG"]), available_at=ko + xg_delay))
        early_at = early_odds_available_at(ko)
        for pre, book in H2H_PREFIXES.items():
            for phase, p2, at in (("early", pre, early_at), ("closing", pre + "C", ko)):
                prices = {s: _price(r, f"{p2}{s}") for s in "HDA"}
                if all(prices.values()):
                    for s, p in prices.items():
                        odds.append(dict(match_id=mid, source="football_data", bookmaker=book,
                                         market="1x2", phase=phase, selection=s, price=p,
                                         available_at=at, available_at_estimated=phase == "early"))
        for book, (e, c) in OU_PREFIXES.items():
            for phase, p2, at in (("early", e, early_at), ("closing", c, ko)):
                o, u = _price(r, f"{p2}>2.5"), _price(r, f"{p2}<2.5")
                if o and u:
                    for s, p in (("O", o), ("U", u)):
                        odds.append(dict(match_id=mid, source="football_data", bookmaker=book,
                                         market="ou25", phase=phase, selection=s, price=p,
                                         available_at=at, available_at_estimated=phase == "early"))
    return {
        "matches": pd.DataFrame(matches),
        "results": pd.DataFrame(results),
        "odds": pd.DataFrame(odds),
        "xg": pd.DataFrame(xg),
    }


def all_files() -> list[tuple[str, FDFile]]:
    """Pääsarjat ja syöttösarjat Elo-esilämmityksen alusta nykyiseen kauteen.

    Syöttösarjojen (E1, D2) ottelut tallennetaan liigatunnuksella '<LIIGA>_FEEDER'; niitä käytetään
    vain Elon laskentaan.
    """
    cfg = settings()
    out = []
    for league, lc in cfg["leagues"].items():
        for s in range(cfg["elo_warmup_first_season"], cfg["current_season"] + 1):
            out.append((league, FDFile(lc["football_data"], s)))
            if lc.get("feeder"):
                out.append((f"{league}_FEEDER", FDFile(lc["feeder"], s)))
    return out
