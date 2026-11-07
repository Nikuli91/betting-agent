"""Walk-forward-backtest (PLAN 7).

- Ennustehetki t = aloitus − lukitus (oletus 60 min), kuten tuotannossa.
- Kaikki data liitetään ajankohtaan sidottuna: rivi kelpaa vain, jos available_at < t.
- Kierros = liigan peräkkäiset ottelupäivät; uusi kierros alkaa, kun ottelupäivien väli on > 2 vrk.
  Malli sovitetaan kierroksen alussa datalla, jonka available_at < kierroksen ensimmäinen t.
- Testijakso (settings.splits.test) ajetaan vain kerran eikä mitään viritetä sen perusteella.
  Funktiot kieltäytyvät käyttämästä testikausia, ellei allow_test=True.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

import duckdb
import numpy as np
import pandas as pd

from bagent.config import settings
from bagent.markets.devig import devig_matrix

H2H = ["H", "D", "A"]
OU = ["O", "U"]
SELECTIONS = {"1x2": H2H, "ou25": OU}


class TestPeriodLockedError(RuntimeError):
    pass


def split_of(season: int) -> str:
    s = settings()["splits"]
    for name in ("train", "validation", "test"):
        if season in s[name]:
            return name
    return "other"


def load_frame(con: duckdb.DuckDBPyConnection, seasons: list[int], *, allow_test: bool = False) -> pd.DataFrame:
    test = set(settings()["splits"]["test"])
    if not allow_test and test & set(seasons):
        raise TestPeriodLockedError(f"Testikaudet {sorted(test & set(seasons))} ovat lukittuja (PLAN 7)")
    lock = timedelta(minutes=settings()["schedule"]["lock_minutes_before_kickoff"])
    seasons_sql = ", ".join(str(int(s)) for s in seasons)
    df = con.execute(f"""
        SELECT m.match_id, m.league, m.season, m.kickoff_utc, m.home_id, m.away_id,
               r.home_goals, r.away_goals, r.ftr
        FROM matches m JOIN results r USING (match_id)
        WHERE m.league IN ('EPL', 'BUNDESLIGA') AND m.season IN ({seasons_sql})
        ORDER BY m.kickoff_utc, m.match_id""").df()
    df["t"] = df["kickoff_utc"] - lock
    df["y_1x2"] = df["ftr"].map({"H": 0, "D": 1, "A": 2}).astype(int)
    df["y_ou25"] = np.where(df["home_goals"] + df["away_goals"] > 2.5, 0, 1)
    df["split"] = df["season"].map(split_of)
    df["round"] = assign_rounds(df)
    return df


def assign_rounds(df: pd.DataFrame, gap_days: float = 2.0) -> pd.Series:
    out = pd.Series(index=df.index, dtype=object)
    for lg, g in df.groupby("league"):
        g = g.sort_values("kickoff_utc")
        new = g["kickoff_utc"].diff() > pd.Timedelta(days=gap_days)
        rid = new.cumsum()
        out.loc[g.index] = [f"{lg}_{int(r):04d}" for r in rid]
    return out


# ---------------------------------------------------------------------------------
def asof_odds(con: duckdb.DuckDBPyConnection, frame: pd.DataFrame, *, phase: str, market: str,
              time_col: str = "t", inclusive: bool = False) -> pd.DataFrame:
    """Kertoimet, joiden available_at < frame[time_col] (tai ≤, jos inclusive – vain vertailutasoille)."""
    con.register("_f", frame[["match_id", time_col]].rename(columns={time_col: "t_cut"}))
    op = "<=" if inclusive else "<"
    try:
        df = con.execute(f"""
            SELECT o.match_id, o.bookmaker, o.selection, o.price, o.available_at
            FROM odds o JOIN _f USING (match_id)
            WHERE o.phase = ? AND o.market = ? AND o.available_at {op} _f.t_cut""",
                         [phase, market]).df()
    finally:
        con.unregister("_f")
    return df


def book_matrix(odds: pd.DataFrame, bookmaker: str, market: str) -> pd.DataFrame:
    """Leveä taulu: match_id × valinnat (viimeisin saatavilla oleva kerroin)."""
    sel = SELECTIONS[market]
    o = odds[odds["bookmaker"] == bookmaker].sort_values("available_at")
    w = o.pivot_table(index="match_id", columns="selection", values="price", aggfunc="last")
    return w.reindex(columns=sel).dropna()


def market_probs(odds: pd.DataFrame, market: str, books: list[str], method: str) -> pd.DataFrame:
    """Ensimmäinen saatavilla oleva välittäjä listasta; palauttaa p_* ja käytetyn välittäjän."""
    sel = SELECTIONS[market]
    parts, done = [], set()
    for b in books:
        w = book_matrix(odds, b, market)
        w = w[~w.index.isin(done)]
        if w.empty:
            continue
        p = devig_matrix(w.to_numpy(), method)
        parts.append(pd.DataFrame(p, index=w.index, columns=[f"p_{s}" for s in sel]).assign(source_book=b))
        done |= set(w.index)
    if not parts:
        return pd.DataFrame(columns=[f"p_{s}" for s in sel] + ["source_book"])
    return pd.concat(parts)


# ---------------------------------------------------------------------------------
def _ns(s: pd.Series) -> np.ndarray:
    """Aikavyöhykkeellinen aikaleimasarja -> UTC-nanosekunnit (int64)."""
    return pd.to_datetime(s, utc=True).dt.tz_convert("UTC").dt.tz_localize(None).astype("datetime64[ns]").astype("int64").to_numpy()


def base_rate(con: duckdb.DuckDBPyConnection, frame: pd.DataFrame, market: str,
              window_days: int = 3 * 365) -> pd.DataFrame:
    """Liigan keskiarvojakauma: lopputulosten osuudet ikkunassa, vain tulokset available_at < t."""
    res = con.execute("""SELECT m.league, r.available_at, r.ftr, r.home_goals + r.away_goals AS goals
                         FROM results r JOIN matches m USING (match_id)
                         WHERE m.league IN ('EPL','BUNDESLIGA')""").df()
    sel = SELECTIONS[market]
    if market == "1x2":
        for i, s in enumerate(sel):
            res[s] = (res["ftr"] == s).astype(float)
    else:
        res["O"] = (res["goals"] > 2.5).astype(float)
        res["U"] = 1.0 - res["O"]
    out = []
    for lg, g in frame.groupby("league"):
        r = res[res["league"] == lg].sort_values("available_at").reset_index(drop=True)
        times = _ns(r["available_at"])
        cums = np.vstack([np.zeros(len(sel)), np.cumsum(r[sel].to_numpy(), axis=0)])
        t = _ns(g["t"])
        hi = np.searchsorted(times, t, side="left")  # rivit, joiden available_at < t
        lo = np.searchsorted(times, t - window_days * 86_400 * 10**9, side="left")
        counts = cums[hi] - cums[lo]
        n = counts.sum(axis=1, keepdims=True)
        if np.any(n == 0):
            raise ValueError("Perustasolle ei ole aiempia tuloksia")
        out.append(pd.DataFrame(counts / n, index=g["match_id"], columns=[f"p_{s}" for s in sel]))
    return pd.concat(out)


# ---------------------------------------------------------------------------------
FitPredict = Callable[[duckdb.DuckDBPyConnection, pd.Timestamp, pd.DataFrame], pd.DataFrame]


def walk_forward(con: duckdb.DuckDBPyConnection, frame: pd.DataFrame, fit_predict: FitPredict) -> pd.DataFrame:
    """Kutsuu fit_predict(con, t_fit, kierroksen ottelut) kierros kerrallaan aikajärjestyksessä.

    fit_predict saa käyttää vain PointInTime(con, t_fit) -dataa (tai rivikohtaista t:tä ennusteisiin)
    ja palauttaa DataFrame:n indeksinä match_id.
    """
    rounds = frame.groupby("round")["t"].min().sort_values()
    out = []
    for rid, t_fit in rounds.items():
        out.append(fit_predict(con, t_fit, frame[frame["round"] == rid]))
    return pd.concat(out)
