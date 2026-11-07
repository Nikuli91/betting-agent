"""Vaihe 4: yhdistäminen, kalibrointi, vertailustrategiat ja CLV (PLAN 9.4).

Kehitys (opetus 2020–2022, validointi 2023) ja testi (2024–2025) erotetaan:
- `run(con)` käyttää vain opetus- ja validointikausia. Kalibrointi ja dekorreloitu malli opetetaan
  opetuskausilla ja arvioidaan validoinnissa; dekorreloinnin c valitaan validoinnissa.
- `run(con, test=True)` ajaa testijakson kerran jäädytetyillä asetuksilla (settings.phase4). Ajo kirjataan
  tiedostoon docs/test_runs.md, ja toinen ajo kielletään (PLAN 7: yksi ajo, ei viritystä testin perusteella).
  Testissä kalibrointi ja dekorreloitu malli opetetaan kausilla 2020–2023, ei koskaan testikausilla.

Kertoimet (PLAN 7): pelattava kerroin on käyttäjän välittäjien kerroin; historiassa sitä ei ole, joten
käytetään välittäjiä, joiden kate on lähimpänä (settings.phase4.proxy_books: paras kerroin niistä).
Markkinakeskiarvo ja -maksimi raportoidaan ylärajoina. Kerroin = aikainen (pe/ti), joka on saatavilla
ennen lukitushetkeä. CLV mitataan katteettomaan terävään sulkeutumiseen.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from bagent.betting import edge
from bagent.config import ROOT, settings
from bagent.eval import backtest as bt
from bagent.eval import clv as cl
from bagent.eval import model_a as ma
from bagent.log.forecast_log import git_commit
from bagent.markets.devig import devig_matrix
from bagent.models import calibration as cal
from bagent.models import decorrelated as dm
from bagent.models import movement as mvm
from bagent.models.dixon_coles import DCParams

SHARP = ["pinnacle", "betfair_exchange"]
FALLBACK = "market_avg"
MARKETS = {"1x2": ["H", "D", "A"], "ou25": ["O", "U"]}
TEST_LOG = ROOT / "docs" / "test_runs.md"


def cfg() -> dict:
    return settings()["phase4"]


def _devig_book(odds: pd.DataFrame, books: list[str], market: str) -> tuple[pd.DataFrame, pd.Series]:
    p = bt.market_probs(odds, market, books, settings()["devig_method"])
    return p[[f"p_{s}" for s in MARKETS[market]]], p["source_book"]


def best_price(odds: pd.DataFrame, books: list[str], market: str) -> pd.DataFrame:
    """Paras kerroin valinnoittain annetuista välittäjistä (käyttäjä valitsee välittäjän per valinta)."""
    o = odds[odds["bookmaker"].isin(books)].sort_values("available_at")
    last = o.groupby(["match_id", "bookmaker", "selection"])["price"].last().reset_index()
    return last.pivot_table(index="match_id", columns="selection", values="price", aggfunc="max") \
        .reindex(columns=MARKETS[market])


def build(con: duckdb.DuckDBPyConnection, seasons: list[int], allow_test: bool = False,
          leagues: list[str] | None = None) -> dict[str, pd.DataFrame]:
    """Taulu per markkina: indeksi match_id; sarakkeina todennäköisyydet, kertoimet ja tulos."""
    frame = bt.load_frame(con, seasons, allow_test=allow_test,
                          leagues=leagues or settings()["original_leagues"])
    c = cfg()
    dc = DCParams(xi=c["model_a"]["xi"], tau_early=c["model_a"]["tau_early"])
    pa = ma.walk_forward(ma.load_history(con), frame, dc)
    out = {}
    for market, sel in MARKETS.items():
        early = bt.asof_odds(con, frame, phase="early", market=market)
        close = bt.asof_odds(con, frame, phase="closing", market=market, time_col="kickoff_utc", inclusive=True)
        ps, src_e = _devig_book(early, SHARP + [FALLBACK], market)
        pc, src_c = _devig_book(close, SHARP + [FALLBACK], market)
        pavg, _ = _devig_book(early, [FALLBACK], market)
        pb365, _ = _devig_book(early, ["bet365"], market)
        proxy = c["proxy_books"][market]
        k = {"proxy": best_price(early, proxy, market), "avg": bt.book_matrix(early, "market_avg", market),
             "max": bt.book_matrix(early, "market_max", market)}
        k_close_proxy = best_price(close, proxy, market)
        ids = ps.index.intersection(pc.index).intersection(pavg.index).intersection(k["proxy"].dropna().index)
        ids = frame["match_id"][frame["match_id"].isin(ids)]
        f = frame.set_index("match_id").loc[ids]
        d = pd.DataFrame(index=ids)
        d["season"], d["split"], d["round"], d["y"] = f["season"], f["split"], f["round"], f[f"y_{market}"]
        d["league"] = f["league"]
        d["close_book"], d["early_book"] = src_c.loc[ids].to_numpy(), src_e.loc[ids].to_numpy()
        for s in sel:
            d[f"ps_{s}"] = ps.loc[ids, f"p_{s}"]
            d[f"pc_{s}"] = pc.loc[ids, f"p_{s}"]
            d[f"pavg_{s}"] = pavg.loc[ids, f"p_{s}"]
            for name, kk in k.items():
                d[f"k{name}_{s}"] = kk.reindex(ids)[s].to_numpy()
            d[f"kcproxy_{s}"] = k_close_proxy.reindex(ids)[s].to_numpy()
            d[f"pb365_{s}"] = pb365.reindex(ids)[f"p_{s}"].to_numpy()
            d[f"pA_{s}"] = pa.loc[ids, f"p_{s}"].to_numpy()
        km = _mat(d, "kmax", market)
        q = 1 / km
        for i, s in enumerate(sel):
            d[f"pmaxn_{s}"] = q[:, i] / q.sum(axis=1)
        d["log_lh"] = np.log(pa.loc[ids, "lambda_h"].to_numpy())
        d["log_la"] = np.log(pa.loc[ids, "lambda_a"].to_numpy())
        out[market] = d
    return out


def _mat(d: pd.DataFrame, prefix: str, market: str) -> np.ndarray:
    return d[[f"{prefix}_{s}" for s in MARKETS[market]]].to_numpy(float)


MOVE_FEATURES = ("keskiarvo − terävä", "maksimi − terävä", "bet365 − terävä", "malli A − terävä")


def movement_features(d: pd.DataFrame, market: str) -> np.ndarray:
    """(n × K × J): log-erot terävään aikaiseen. Puuttuva (esim. maksimi tai bet365) -> 0 = ei signaalia."""
    lps = np.log(_mat(d, "ps", market))
    feats = []
    for pref in ("pavg", "pmaxn", "pb365", "pA"):
        x = np.log(np.clip(_mat(d, pref, market), 1e-12, 1)) - lps
        feats.append(np.nan_to_num(x, nan=0.0))
    return np.stack(feats, axis=-1)


def strategies(train: dict, target: dict, c_dec: dict[str, float]) -> dict[str, dict[str, np.ndarray]]:
    """p per strategia ja markkina kohdejaksolle. Kalibrointi ja dekorreloitu malli opetetaan train-jaksolla."""
    out: dict[str, dict[str, np.ndarray]] = {}
    for market in MARKETS:
        tr, ta = train[market], target[market]
        ps_tr, ps_ta = _mat(tr, "ps", market), _mat(ta, "ps", market)
        vs = cal.fit_vector_scaling(ps_tr, tr["y"].to_numpy(int))
        X_tr, X_ta = tr[["log_lh", "log_la"]].to_numpy(), ta[["log_lh", "log_la"]].to_numpy()
        dec = dm.fit(X_tr, tr["y"].to_numpy(int), ps_tr, c=c_dec[market])
        out.setdefault("markkina (terävä aikainen)", {})[market] = ps_ta
        out.setdefault("markkina + kalibrointi", {})[market] = vs.apply(ps_ta)
        out.setdefault("Kaunitz (konsensus = keskiarvo)", {})[market] = _mat(ta, "pavg", market)
        out.setdefault(f"dekorreloitu malli", {})[market] = dec.predict(X_ta)
        mv = mvm.fit(ps_tr, movement_features(tr, market), _mat(tr, "pc", market), MOVE_FEATURES)
        out.setdefault("kerroinliikemalli", {})[market] = mv.predict(ps_ta, movement_features(ta, market))
        out.setdefault("_calibration", {})[market] = vs
        out.setdefault("_movement", {})[market] = mv
    return out


def bet_table(d: pd.DataFrame, market: str, p: np.ndarray, odds: str, threshold: float) -> dict:
    sel = MARKETS[market]
    k = _mat(d, f"k{odds}", market)
    b = edge.select_bets(p, k, _mat(d, "ps", market), threshold, settings()["core"]["divergence_warning_pp"])
    m = b["bet"].to_numpy()
    if not m.any():
        return {"vetoja": 0, "varoituksia": int(b["flagged"].sum())}
    i = np.flatnonzero(m)
    s = b["sel"].to_numpy()[i]
    kb = k[i, s]
    pc = _mat(d, "pc", market)[i, s]
    c = cl.clv(kb, pc)
    lo, hi = cl.cluster_bootstrap_mean(c, d["round"].to_numpy()[i])
    won = d["y"].to_numpy(int)[i] == s
    row = {"vetoja": int(m.sum()), "varoituksia": int(b["flagged"].sum()), "ka. kerroin": float(kb.mean()),
           "ka. EV (ennuste)": float(b["ev"].to_numpy()[i].mean()), "CLV ka.": float(c.mean()),
           "CLV 95 % LV": f"[{100 * lo:+.2f} %, {100 * hi:+.2f} %]", "CLV > 0 %": float((c > 0).mean()),
           "tuotto (tasapanos)": float(np.where(won, kb - 1, -1).mean())}
    if odds == "proxy":
        kc = _mat(d, "kcproxy", market)[i, s]
        ok = ~np.isnan(kc)
        row["kerroin-CLV (sama välittäjä)"] = float(cl.price_clv(kb[ok], kc[ok]).mean()) if ok.any() else np.nan
    return row


def evaluate(target: dict, strat: dict, thresholds: dict[str, list[float]]) -> pd.DataFrame:
    rows = []
    for name, ps in strat.items():
        if name.startswith("_"):
            continue
        for market in MARKETS:
            for odds in ("proxy", "avg", "max"):
                for th in thresholds[market]:
                    rows.append({"strategia": name, "markkina": market, "kerroin": odds, "kynnys": th,
                                 **bet_table(target[market], market, ps[market], odds, th)})
    return pd.DataFrame(rows)


def choose_c(train: dict, val: dict, grid: list[float]) -> tuple[dict[str, float], pd.DataFrame]:
    """c valitaan validoinnissa: keskimääräinen CLV kaikille valinnoille, joiden EV ≥ 0 välittäjäproxylla.
    EV ≥ 0 -rajalla vetoja on enemmän kuin varsinaisella kynnyksellä, joten valinta on vähemmän kohinainen."""
    rows = []
    for market in MARKETS:
        for c in grid:
            p = strategies(train, val, {m: c for m in MARKETS})["dekorreloitu malli"][market]
            r = bet_table(val[market], market, p, "proxy", 0.0)
            rows.append({"markkina": market, "c": c, **{k: r.get(k) for k in ("vetoja", "CLV ka.", "CLV 95 % LV")}})
    df = pd.DataFrame(rows)
    min_bets = cfg()["decorrelation_min_bets"]  # muuten valinta suosii c:tä, joka karsii lähes kaikki vedot
    best = {}
    for m in MARKETS:
        ok = df[(df["markkina"] == m) & (df["vetoja"] >= min_bets)]
        best[m] = float(ok.sort_values("CLV ka.", ascending=False).iloc[0]["c"]) if len(ok) else 0.0
    return best, df


def calibration_check(target: dict, strat: dict) -> pd.DataFrame:
    from bagent.eval import metrics as mt
    rows = []
    for market in MARKETS:
        y = target[market]["y"].to_numpy(int)
        for name in ("markkina (terävä aikainen)", "markkina + kalibrointi", "Kaunitz (konsensus = keskiarvo)",
                     "dekorreloitu malli", "kerroinliikemalli"):
            m = mt.all_metrics(strat[name][market], y, ordered=market == "1x2")
            rows.append({"markkina": market, "ennustaja": name, "n": m["n"], "log loss": m["log_loss"],
                         "Brier": m["brier"]})
    return pd.DataFrame(rows)


def movement_check(target: dict, strat: dict) -> pd.DataFrame:
    """Ennustaako malli sulkeutumista paremmin kuin aikainen terävä? CE vs. katteeton sulkeutuminen."""
    from bagent.models.pooling import cross_entropy
    rows = []
    for market in MARKETS:
        d = target[market]
        T, P0 = _mat(d, "pc", market), _mat(d, "ps", market)
        P1 = strat["kerroinliikemalli"][market]
        mv = strat["_movement"][market]
        move, pred = (T - P0).ravel(), (P1 - P0).ravel()
        rows.append({"markkina": market, "n": len(d), "CE aikainen terävä": cross_entropy(P0, T),
                     "CE kerroinliikemalli": cross_entropy(P1, T),
                     "parannus ×1000": 1000 * (cross_entropy(P0, T) - cross_entropy(P1, T)),
                     "corr(ennustettu, toteutunut liike)": float(np.corrcoef(pred, move)[0, 1]),
                     "liikkeen keskihajonta pp": 100 * float(move.std()),
                     **{f"β {n}": float(v) for n, v in zip(mv.names, mv.beta)},
                     "ajautuma b": tuple(round(float(x), 4) for x in mv.b)})
    return pd.DataFrame(rows)


def margins(d: dict) -> pd.DataFrame:
    rows = []
    for market in MARKETS:
        for odds in ("proxy", "avg", "max"):
            k = _mat(d[market], f"k{odds}", market)
            ok = ~np.isnan(k).any(axis=1)
            rows.append({"markkina": market, "kerroin": odds, "kate": float((1 / k[ok]).sum(1).mean() - 1)})
    return pd.DataFrame(rows)


def _concat(parts: list[dict]) -> dict:
    return {m: pd.concat([p[m] for p in parts]) for m in MARKETS}


def _split(d: dict, splits: list[str]) -> dict:
    return {m: v[v["split"].isin(splits)] for m, v in d.items()}


def _fmt(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in ("ka. EV (ennuste)", "CLV ka.", "CLV > 0 %", "tuotto (tasapanos)", "kerroin-CLV (sama välittäjä)", "kynnys", "kate"):
        if c in df:
            df[c] = df[c].map(lambda v: "" if pd.isna(v) else f"{100 * v:+.2f} %" if c != "CLV > 0 %" else f"{100 * v:.0f} %")
    return df


def _test_already_run(kind: str = "phase4") -> bool:
    return TEST_LOG.exists() and f"| {kind} |" in TEST_LOG.read_text(encoding="utf-8")


def by_league(target: dict, strat: dict, th_main: dict) -> pd.DataFrame:
    rows = []
    for name in ("markkina (terävä aikainen)", "Kaunitz (konsensus = keskiarvo)", "kerroinliikemalli"):
        for market in MARKETS:
            d = target[market]
            for lg, idx in d.groupby("league").indices.items():
                for th in (0.0, th_main[market]):
                    r = bet_table(d.iloc[idx], market, strat[name][market][idx], "proxy", th)
                    rows.append({"strategia": name, "markkina": market, "sarja": lg, "kynnys": th,
                                 **{k: r.get(k) for k in ("vetoja", "CLV ka.", "CLV 95 % LV")}})
    return pd.DataFrame(rows)


def run(con: duckdb.DuckDBPyConnection, out_dir: Path | None = None, test: bool = False,
        new_leagues: bool = False) -> Path:
    """new_leagues=True: jäädytetyt strategiat (opetus EPL+BL 2020–2023) uusien sarjojen kausille 2020–2025."""
    kind = "phase4_new_leagues" if new_leagues else "phase4"
    test = test or new_leagues
    out_dir = out_dir or ROOT / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    s = settings()["splits"]
    c = cfg()
    commit = git_commit()
    tag = commit[:12]
    if test:
        if commit.endswith("-dirty"):
            raise RuntimeError("Testiajo vaatii puhtaan commitin (jäädytetyt asetukset)")
        if _test_already_run(kind):
            raise RuntimeError(f"Vaiheen 4 testiajo ({kind}) on jo tehty (ks. {TEST_LOG}); PLAN 7 sallii yhden ajon")
    th_main = {"1x2": settings()["core"]["ev_threshold"]["h2h"], "ou25": settings()["core"]["ev_threshold"]["totals"]}
    thresholds = {m: sorted({0.0, 0.02, th_main[m]}) for m in MARKETS}

    dev = build(con, s["train"] + s["validation"])
    tr, va = _split(dev, ["train"]), _split(dev, ["validation"])
    if not test:
        c_best, c_tab = choose_c(tr, va, c["decorrelation_grid"])
        strat = strategies(tr, va, c_best)
        target, label = va, f"validointi {s['validation']}"
    else:
        c_best = c["decorrelation_c"]
        c_tab = None
        if new_leagues:
            nl = settings()["new_leagues"]
            seasons = s["train"] + s["validation"] + s["test"]
            target = build(con, seasons, allow_test=True, leagues=nl)
            label = f"UUDET SARJAT {nl}, kaudet {seasons[0]}–{seasons[-1]} (yksi ajo)"
        else:
            target = build(con, s["test"], allow_test=True)
            label = f"TESTI {s['test']} (yksi ajo)"
        strat = strategies(dev, target, c_best)
    res = evaluate(target, strat, thresholds)
    main = res[res.apply(lambda r: r["kynnys"] == th_main[r["markkina"]], axis=1)]
    vs = strat["_calibration"]
    fb = {m: int((target[m]["close_book"] == FALLBACK).sum()) for m in MARKETS}
    n = {m: len(target[m]) for m in MARKETS}
    ccols = ["strategia", "markkina", "kerroin", "vetoja", "varoituksia", "ka. kerroin", "ka. EV (ennuste)",
             "CLV ka.", "CLV 95 % LV", "CLV > 0 %", "kerroin-CLV (sama välittäjä)", "tuotto (tasapanos)"]
    ccols = [x for x in ccols if x in main]
    c_text = "" if c_tab is None else (
        f"c valittu validoinnissa: suurin keskimääräinen CLV (EV ≥ 0, proxy-kerroin) niistä, joilla vähintään "
        f"{c['decorrelation_min_bets']} vetoa:\n\n" + _fmt(c_tab).to_markdown(index=False))
    name = f"{kind}_{'test' if test else 'dev'}_{tag}"
    league_tab = by_league(target, strat, th_main)
    path = out_dir / f"{name}.md"
    path.write_text(f"""# Vaihe 4 – strategiat ja CLV ({label})

Commit: `{commit}`. Ennustehetki = aloitus − {settings()['schedule']['lock_minutes_before_kickoff']} min. Pelattava kerroin = aikainen (pe/ti) kerroin, saatavilla ennen lukitusta.
CLV = k · p_sulkeutuva_terävä − 1 (Pinnacle → Betfair Exchange → markkinakeskiarvo; varavaihtoehto käytössä 1X2 {fb['1x2']}/{n['1x2']}, yli/alle {fb['ou25']}/{n['ou25']} ottelussa). LV = klusteroitu bootstrap kierroksittain.

**Kertoimet:**
- `proxy` = paras aikainen kerroin välittäjiltä {c['proxy_books']['1x2']} (1X2) ja {c['proxy_books']['ou25']} (yli/alle). Kate on hieman suurempi kuin käyttäjän välittäjien parhaan kertoimen kate (ks. taulukko), joten arvio on varovainen. **Portti mitataan tällä.**
- `avg` = markkinakeskiarvo (yksi välittäjä keskimäärin).
- `max` = markkinamaksimi, jota yksi pelaaja ei käytännössä saa. **Vain yläraja.**

{_fmt(margins(target)).to_markdown(index=False)}

Käyttäjän välittäjien (coolbet, unibet_se, betsson, nordicbet, leovegas_se) paras kerroin snapshoteista: 1X2 noin 3,0 %, yli/alle noin 4,3 % (36 ottelua, 7.11.2026).

## 1. Pääkynnyksellä (1X2 {100 * th_main['1x2']:.0f} %, yli/alle {100 * th_main['ou25']:.0f} %)

{_fmt(main[ccols]).to_markdown(index=False, floatfmt=".3f")}

## 2. Kaikki kynnykset (ennalta määrätyt: 0 %, 2 %, pääkynnys)

{_fmt(res[[x for x in ['strategia', 'markkina', 'kerroin', 'kynnys', 'vetoja', 'CLV ka.', 'CLV 95 % LV', 'tuotto (tasapanos)'] if x in res]]).to_markdown(index=False, floatfmt=".3f")}

## 3. Kalibrointi (vektoriskaalaus, opetettu {'opetuskausilla' if not test else 'kausilla 2020–2023'})

1X2: a = {vs['1x2'].a:.3f}, b = {tuple(round(x, 3) for x in vs['1x2'].b)}; yli/alle: a = {vs['ou25'].a:.3f}, b = {tuple(round(x, 3) for x in vs['ou25'].b)}.
a < 1 = markkina on ylivarma, b_D > 0 = tasapelit aliarvioitu.

Ennustetarkkuus kohdejaksolla (pienempi on parempi):

{calibration_check(target, strat).to_markdown(index=False, floatfmt=".4f")}

## 4. Dekorreloitu malli

Piirteet: mallin A (maalit, ξ = {c['model_a']['xi']}, τ_early = {c['model_a']['tau_early']}) log λ_koti ja log λ_vieras. c = {c_best}.
{c_text}

## 5. Kerroinliikemalli

log p̂_sulkeutuva = log p_terävä_aikainen + b + Σ β_j · x_j (piirteet log-eroina terävään aikaiseen), opetettu {'opetuskausilla' if not test else 'kausilla 2020–2023'} katteetonta terävää sulkeutumista vastaan. Strategia: EV = p̂_sulkeutuva · k − 1.

{movement_check(target, strat).T.to_markdown(floatfmt=".4f")}

## 6. Sarjoittain (proxy-kerroin)

{_fmt(league_tab).to_markdown(index=False)}

Poolipaino w = 0 vaiheessa 3, joten pooli (malli A + markkina) on sama kuin markkina eikä sitä raportoida erikseen.
""", encoding="utf-8")
    res.to_csv(out_dir / f"{name}.csv", index=False)
    if test:
        TEST_LOG.parent.mkdir(parents=True, exist_ok=True)
        if not TEST_LOG.exists():
            TEST_LOG.write_text("# Testijakson ajot (PLAN 7: yksi ajo per vaihe)\n\n| vaihe | aika (UTC) | commit | raportti |\n|---|---|---|---|\n",
                                encoding="utf-8")
        with open(TEST_LOG, "a", encoding="utf-8") as f:
            f.write(f"| {kind} | {datetime.now(timezone.utc):%Y-%m-%d %H:%M} | `{commit}` | reports/{path.name} |\n")
    return path
