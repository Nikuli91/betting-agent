"""Paperikauden päivittäinen ajo (PLAN 9.5–9.6). Agentti ei aseta vetoja.

1. Uusin kerroinsnapshot per sarja (odds_snapshots). Haamukertoimet ohitetaan (alkanut ottelu tai
   vanhentunut markkina).
2. Jokaiselle ottelulle, joka alkaa seuraavan `window_hours` aikana ja jota ei vielä ole lokissa:
   - terävä p (Pinnacle, varalla Betfair Exchange; power-katteenpoisto), konsensus (kaikkien välittäjien
     keskiarvokerroin), maksimi, malli A (Dixon–Coles maaleilla)
   - strategiat: markkina, Kaunitz, kerroinliikemalli (opetettu historiassa)
   - paras kerroin käyttäjän välittäjillä; pörsseille palkkio vähennettynä
   - signaali, jos EV ≥ 0; veto (paperilla), jos EV ≥ kynnys eikä varoitusta
3. Rivi lukitaan ennustelokiin (hash-ketju) ja loki tallennetaan versionhallintaan (JSONL).
4. Päiväraportti paper/reports/YYYY-MM-DD.md.

Huom: historiassa piirteet tulevat football-datasta (keskiarvo, maksimi, bet365), livenä The Odds API:n
eu-alueesta. Välittäjäjoukko on eri, ja bet365 puuttuu (piirre = 0). Ero raportoidaan, ja kerroinliikemallin
toimivuus arvioidaan paperikaudella.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from bagent.betting import edge, staking
from bagent.config import ROOT, main_leagues, settings
from bagent.data.store import connect
from bagent.eval import model_a as ma
from bagent.eval import phase4 as p4
from bagent.log import forecast_log as fl
from bagent.markets.devig import devig
from bagent.models import movement as mvm
from bagent.models import scoreline as sl
from bagent.models.dixon_coles import DCParams

MODEL_VERSION = "paper-v1"
SEL = {"1x2": ["H", "D", "A"], "ou25": ["O", "U"]}
STRATEGIES = ("markkina", "Kaunitz", "kerroinliikemalli")


def effective_odds(k: float, book: str) -> float:
    c = settings()["bookmakers"].get("commission", {}).get(book, 0.0)
    return 1 + (k - 1) * (1 - c)


def latest_snapshot(con: duckdb.DuckDBPyConnection, now: datetime) -> pd.DataFrame:
    """Uusin snapshot per sarja, vain pelattavat kertoimet (ei alkaneita, ei vanhentuneita markkinoita)."""
    stale = settings()["odds_api"]["stale_minutes"]
    return con.execute(f"""
        WITH last AS (
          SELECT e.league, max(s.fetched_at) AS fetched_at FROM odds_snapshots s
          JOIN odds_api_events e USING (event_id) WHERE s.fetched_at <= ? GROUP BY e.league)
        SELECT s.*, e.league, e.commence_time, e.home_id, e.away_id
        FROM odds_snapshots s JOIN odds_api_events e USING (event_id)
        JOIN last ON last.league = e.league AND last.fetched_at = s.fetched_at
        WHERE e.commence_time > s.fetched_at
          AND (s.market_last_update IS NULL OR s.fetched_at - s.market_last_update <= INTERVAL {int(stale)} MINUTE)
          AND (s.market = 'h2h' OR s.point = 2.5)""", [now]).df()


def _book_prices(g: pd.DataFrame, market: str) -> dict[str, np.ndarray]:
    sel = SEL[market]
    api = "h2h" if market == "1x2" else "totals"
    w = g[g["market"] == api].pivot_table(index="bookmaker", columns="selection", values="price", aggfunc="last")
    w = w.reindex(columns=sel).dropna()
    return {b: w.loc[b].to_numpy(float) for b in w.index}


def match_inputs(g: pd.DataFrame, market: str, pa: np.ndarray) -> dict[str, Any] | None:
    cfg = settings()
    books = _book_prices(g, market)
    sharp = next((b for b in cfg["paper"]["sharp_live"] if b in books), None)
    if sharp is None:
        return None
    method = cfg["devig_method"]
    ps = devig(books[sharp], method)
    allk = np.array(list(books.values()))
    pavg = devig(allk.mean(axis=0), method)
    q = 1 / allk.max(axis=0)
    pmax = q / q.sum()
    user = {}
    for i, s in enumerate(SEL[market]):
        cands = [(effective_odds(books[b][i], b), b) for b in cfg["bookmakers"]["user"] if b in books]
        user[s] = max(cands) if cands else (np.nan, None)
    lps = np.log(ps)
    X = np.stack([np.log(pavg) - lps, np.log(pmax) - lps, np.zeros_like(lps), np.log(pa) - lps], axis=-1)
    return {"sharp_book": sharp, "p_sharp": ps, "p_avg": pavg, "p_max": pmax, "p_A": pa, "X": X,
            "user": user, "n_books": len(books)}


def movement_models(con: duckdb.DuckDBPyConnection) -> dict[str, mvm.MovementModel]:
    """Kerroinliikemalli opetettuna kaikilla historiakausilla (testijakso on jo käytetty, PLAN 7)."""
    d = p4.build(con, settings()["paper"]["movement_train_seasons"], allow_test=True, leagues=main_leagues())
    return {m: mvm.fit(p4._mat(d[m], "ps", m), p4.movement_features(d[m], m), p4._mat(d[m], "pc", m),
                       p4.MOVE_FEATURES) for m in SEL}


def model_a_probs(con, h: ma.History, matches: pd.DataFrame, now: datetime) -> pd.DataFrame:
    c = settings()["phase4"]["model_a"]
    params = DCParams(xi=c["xi"], tau_early=c["tau_early"])
    out = []
    t = pd.Timestamp(now)
    for (league, season), g in matches.groupby(["league", "season"]):
        rnd = g.assign(t=t)
        out.append(ma.predict_round(h, t, rnd, params))
    return pd.concat(out)


def _season(ts: pd.Timestamp) -> int:
    return ts.year if ts.month >= 7 else ts.year - 1


def run(con: duckdb.DuckDBPyConnection | None = None, now: datetime | None = None) -> dict[str, Any]:
    cfg = settings()
    pc = cfg["paper"]
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    con = con or connect()
    log = fl.load_jsonl(duckdb.connect(":memory:"), ROOT / pc["log_path"])
    logged = {r["match_id"] for r in log.rows()}
    snap = latest_snapshot(con, now)
    max_age = timedelta(hours=pc["max_snapshot_age_hours"])
    snap = snap[pd.to_datetime(snap["fetched_at"], utc=True) >= now - max_age]  # ei vanhoilla kertoimilla
    lo = now + timedelta(minutes=pc["min_minutes_before_kickoff"])
    hi = now + timedelta(hours=pc["window_hours"])
    snap = snap[(snap["commence_time"] > lo) & (snap["commence_time"] <= hi) & ~snap["match_id"].isin(logged)]
    if snap.empty:
        return {"logged": 0, "signals": 0, "report": None}
    matches = snap.drop_duplicates("match_id")[["match_id", "league", "commence_time", "home_id", "away_id"]]
    matches = matches.assign(season=matches["commence_time"].map(_season)).set_index("match_id", drop=False)
    pa = model_a_probs(con, ma.load_history(con), matches, now)
    mv = movement_models(con)
    thr = {"1x2": cfg["core"]["ev_threshold"]["h2h"], "ou25": cfg["core"]["ev_threshold"]["totals"]}
    div = cfg["core"]["divergence_warning_pp"]
    commit = fl.git_commit()
    rows = []
    for mid, g in snap.groupby("match_id"):
        m = matches.loc[mid]
        payload: dict[str, Any] = {"league": m["league"], "home_id": m["home_id"], "away_id": m["away_id"],
                                   "snapshot_at": str(g["fetched_at"].iloc[0]), "markets": {}, "signals": []}
        for market, sel in SEL.items():
            cols = [f"p_{s}" for s in sel]
            inp = match_inputs(g, market, pa.loc[mid, cols].to_numpy(float))
            if inp is None:
                continue
            probs = {"markkina": inp["p_sharp"], "Kaunitz": inp["p_avg"],
                     "kerroinliikemalli": mv[market].predict(inp["p_sharp"][None], inp["X"][None])[0]}
            k = np.array([inp["user"][s][0] for s in sel], float)
            payload["markets"][market] = {
                "sharp_book": inp["sharp_book"], "n_books": inp["n_books"],
                "p": {n: [round(float(x), 6) for x in v] for n, v in {**probs, "malli A": inp["p_A"],
                                                                     "maksimi": inp["p_max"]}.items()},
                "user_best": {s: [None if np.isnan(inp["user"][s][0]) else round(float(inp["user"][s][0]), 4),
                                  inp["user"][s][1]] for s in sel}}
            for name, p in probs.items():
                b = edge.select_bets(p[None], k[None], inp["p_sharp"][None], 0.0, div).iloc[0]
                if b["sel"] < 0:
                    continue
                i = int(b["sel"])
                bet = bool(b["ev"] >= thr[market] and not b["flagged"])
                stake = staking.stakes(np.array([p[i]]), np.array([k[i]]), cfg["core"]["kelly_fraction"],
                                       cfg["core"]["max_stake_per_bet"], 1.0)[0] if bet else 0.0
                payload["signals"].append({
                    "strategy": name, "market": market, "selection": sel[i], "p": round(float(p[i]), 6),
                    "p_sharp": round(float(inp["p_sharp"][i]), 6), "odds": round(float(k[i]), 4),
                    "book": inp["user"][sel[i]][1], "ev": round(float(b["ev"]), 6), "bet": bet,
                    "flagged": bool(b["flagged"]), "stake_frac": round(float(stake), 6)})
        if not payload["markets"]:
            continue
        log.append(match_id=mid, kickoff_utc=m["commence_time"].to_pydatetime(), model_version=MODEL_VERSION,
                   payload=payload, now=now, commit=commit)
        rows.append((m, payload))
    fl.export_jsonl(log, ROOT / pc["log_path"])
    report = write_report(rows, now) if rows else None
    return {"logged": len(rows), "signals": sum(len(p["signals"]) for _, p in rows), "report": report}


def write_report(rows: list, now: datetime) -> Path:
    from bagent.data.team_names import display_name
    d = ROOT / settings()["paper"]["report_dir"]
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{now:%Y-%m-%d}.md"
    sig = []
    for m, p in rows:
        for s in p["signals"]:
            sig.append({"aloitus (UTC)": f"{m['commence_time']:%a %d.%m. %H:%M}",
                        "ottelu": f"{display_name(m['home_id'])} – {display_name(m['away_id'])}",
                        "strategia": s["strategy"], "markkina": s["market"], "valinta": s["selection"],
                        "p": f"{s['p']:.3f}", "p terävä": f"{s['p_sharp']:.3f}", "reilu kerroin": f"{1 / s['p']:.2f}",
                        "paras kerroin": f"{s['odds']:.2f} ({s['book']})", "EV": f"{100 * s['ev']:+.1f} %",
                        "veto": "VETO" if s["bet"] else ("tarkista" if s["flagged"] else ""),
                        "panos % kassasta": f"{100 * s['stake_frac']:.2f}" if s["bet"] else ""})
    df = pd.DataFrame(sig)
    bets = df[df["veto"] == "VETO"] if not df.empty else df
    text = [f"# Paperiraportti {now:%Y-%m-%d}", "",
            f"Ajo {now:%Y-%m-%d %H:%M} UTC, malli `{MODEL_VERSION}`, commit `{fl.git_commit()[:12]}`. "
            "**Paperikausi: vihjeet on lukittu ennustelokiin, rahaa ei laiteta.**",
            f"Lukittuja otteluita {len(rows)}. Kertoimet = paras käyttäjän välittäjillä "
            f"({', '.join(settings()['bookmakers']['user'])}); pörsseistä palkkio vähennetty.", "",
            "## Vedot (EV ≥ kynnys, ei varoitusta)", "",
            bets.to_markdown(index=False) if not bets.empty else "Ei vetoja tällä kierroksella.", "",
            "## Kaikki signaalit (EV ≥ 0)", "",
            df.to_markdown(index=False) if not df.empty else "Ei signaaleja.", ""]
    if path.exists():  # saman päivän toinen ajo lisätään perään, aiempaa ei korvata
        text[0] = f"\n---\n\n# Lisäajo {now:%H:%M} UTC"
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n".join(text))
    else:
        path.write_text("\n".join(text), encoding="utf-8")
    return path
