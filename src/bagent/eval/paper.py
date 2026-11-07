"""Paperikauden arviointi (PLAN 9.6): lukittujen signaalien CLV terävään sulkeutumiseen.

Sulkeutuva kerroin tulee football-datasta (Pinnacle → Betfair Exchange → markkinakeskiarvo), kun ottelu
on päivittynyt sinne. CLV = k_veto · p_sulkeutuva − 1 (PLAN 7). Portti: ≥ 300 paperivetoa, keskimääräinen
CLV > 0 ja bootstrapin 95 %:n alaraja > 0.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from bagent.config import ROOT, settings
from bagent.eval import clv as cl
from bagent.log import forecast_log as fl
from bagent.markets.devig import devig

CLOSE_BOOKS = ["pinnacle", "betfair_exchange", "market_avg"]
SEL = {"1x2": ["H", "D", "A"], "ou25": ["O", "U"]}


def closing_probs(con: duckdb.DuckDBPyConnection, match_ids: list[str]) -> dict[tuple[str, str], tuple[np.ndarray, str]]:
    if not match_ids:
        return {}
    con.register("_ids", pd.DataFrame({"match_id": match_ids}))
    try:
        o = con.execute("""SELECT match_id, bookmaker, market, selection, price FROM odds
                           WHERE phase = 'closing' AND source = 'football_data'
                             AND match_id IN (SELECT match_id FROM _ids)""").df()
    finally:
        con.unregister("_ids")
    out = {}
    for (mid, market), g in o.groupby(["match_id", "market"]):
        for b in CLOSE_BOOKS:
            w = g[g["bookmaker"] == b].set_index("selection")["price"].reindex(SEL[market])
            if w.notna().all():
                out[(mid, market)] = (devig(w.to_numpy(float), settings()["devig_method"]), b)
                break
    return out


def signals_frame(con: duckdb.DuckDBPyConnection, log_path: Path | None = None) -> pd.DataFrame:
    log = fl.load_jsonl(duckdb.connect(":memory:"), log_path or ROOT / settings()["paper"]["log_path"])
    rows = []
    for r in log.rows():
        import json
        p = json.loads(r["payload"])
        for s in p["signals"]:
            rows.append({"match_id": r["match_id"], "kickoff_utc": r["kickoff_utc"], "created_at": r["created_at"],
                         **s})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    close = closing_probs(con, sorted(df["match_id"].unique()))
    pc, cb = [], []
    for _, s in df.iterrows():
        c = close.get((s["match_id"], s["market"]))
        if c is None:
            pc.append(np.nan)
            cb.append(None)
        else:
            pc.append(float(c[0][SEL[s["market"]].index(s["selection"])]))
            cb.append(c[1])
    df["p_close"], df["close_book"] = pc, cb
    df["clv"] = cl.clv(df["odds"], df["p_close"])
    df["day"] = pd.to_datetime(df["kickoff_utc"]).dt.date.astype(str)
    return df


def summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    done = df[df["clv"].notna()]
    for (strategy, market), g in done.groupby(["strategy", "market"]):
        for label, h in (("veto (EV ≥ kynnys)", g[g["bet"]]), ("signaali (EV ≥ 0)", g)):
            if h.empty:
                continue
            lo, hi = cl.cluster_bootstrap_mean(h["clv"].to_numpy(), h["day"].to_numpy())
            rows.append({"strategia": strategy, "markkina": market, "joukko": label, "n": len(h),
                         "CLV ka.": f"{100 * h['clv'].mean():+.2f} %", "95 % LV": f"[{100 * lo:+.2f}, {100 * hi:+.2f}]",
                         "ka. kerroin": round(h["odds"].mean(), 2),
                         "välittäjät": ", ".join(f"{k} {v}" for k, v in h["book"].value_counts().items())})
    return pd.DataFrame(rows)


def write(con: duckdb.DuckDBPyConnection) -> Path:
    df = signals_frame(con)
    path = ROOT / settings()["paper"]["report_dir"] / "clv.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    if df.empty:
        path.write_text("# Paperikauden CLV\n\nEi lukittuja signaaleja vielä.\n", encoding="utf-8")
        return path
    n_bets = int((df["bet"] & df["clv"].notna()).sum())
    pending = int(df["clv"].isna().sum())
    s = summary(df)
    path.write_text(f"""# Paperikauden CLV

CLV = paras kerroin käyttäjän välittäjillä (pörsseissä palkkio vähennetty) · terävä katteeton sulkeutuminen − 1.
Sulkeutuminen football-datasta (Pinnacle → Betfair Exchange → markkinakeskiarvo). LV = bootstrap ottelupäivittäin.
Signaaleja {len(df)}, joista {pending} odottaa sulkeutumiskerrointa. Arvioituja paperivetoja {n_bets} (portti: ≥ 300,
keskimääräinen CLV > 0 ja 95 %:n alaraja > 0).

{s.to_markdown(index=False) if not s.empty else "Ei vielä arvioitavia signaaleja (sulkeutumiskertoimet päivittyvät football-dataan viiveellä)."}
""", encoding="utf-8")
    return path
