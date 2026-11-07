"""Vaiheen 3 raportti: malli A (Dixon–Coles) walk-forward ja poolipaino w.

Menettely (testikaudet lukittuja, PLAN 7):
1. Hyperparametrit (ξ, τ_early) valitaan opetuskausien 2020/21–2022/23 walk-forward-log lossilla
   (1X2 + yli/alle). Validointikautta ei käytetä valintaan.
2. Validointikausi 2023/24 ennustetaan valituilla parametreilla.
3. w sovitetaan validointikaudella kolmesti: (1) aikaista terävää vastaan, kohde lopputulos;
   (2) aikaista terävää vastaan, kohde katteeton sulkeutuva todennäköisyys; (3) sulkeutuvaa vastaan,
   kohde lopputulos (odotus ≈ 0). Klusteroitu bootstrap kierroksittain. Lisäksi w opetuskausilla
   ja sen siirto validointiin (otoksen ulkopuolinen tarkistus).
"""
from __future__ import annotations

import itertools
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, replace
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from bagent.config import DB_PATH, ROOT, settings  # noqa: E402
from bagent.eval import backtest as bt  # noqa: E402
from bagent.eval import metrics as mt  # noqa: E402
from bagent.eval import model_a as ma  # noqa: E402
from bagent.log.forecast_log import git_commit  # noqa: E402
from bagent.models import pooling as pl  # noqa: E402
from bagent.models.dixon_coles import DCParams  # noqa: E402

SHARP = ["pinnacle", "betfair_exchange", "market_avg"]
GRID = {"xi": [0.0005, 0.001, 0.0015, 0.002, 0.003, 0.004], "tau_early": [0.0, 2.0, 5.0, 10.0, 20.0, 50.0]}
COLS = {"1x2": ["p_H", "p_D", "p_A"], "ou25": ["p_O", "p_U"]}
XG_MIN_COVERAGE = 0.95


def _ro_con():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    con.execute("SET TimeZone='UTC'")
    return con


def _score(p: pd.DataFrame, frame: pd.DataFrame) -> dict[str, float]:
    y = frame.set_index("match_id").loc[p.index]
    a = mt.all_metrics(p[COLS["1x2"]].to_numpy(), y["y_1x2"].to_numpy())
    b = mt.all_metrics(p[COLS["ou25"]].to_numpy(), y["y_ou25"].to_numpy(), ordered=False)
    return {"n": a["n"], "ll_1x2": a["log_loss"], "brier_1x2": a["brier"], "rps_1x2": a["rps"],
            "ll_ou": b["log_loss"], "brier_ou": b["brier"]}


def _grid_job(args):
    params, seasons = args
    con = _ro_con()
    h = ma.load_history(con)
    frame = bt.load_frame(con, seasons)
    p = ma.walk_forward(h, frame, params)
    return {**asdict(params), **_score(p, frame)}


def tune(seasons: list[int], variant: str = "goals", workers: int = 4) -> pd.DataFrame:
    jobs = [(DCParams(xi=x, tau_early=t, variant=variant), seasons)
            for x, t in itertools.product(GRID["xi"], GRID["tau_early"])]
    with ProcessPoolExecutor(workers) as ex:
        rows = list(ex.map(_grid_job, jobs))
    df = pd.DataFrame(rows)
    df["ll_sum"] = df["ll_1x2"] + df["ll_ou"]
    return df.sort_values("ll_sum").reset_index(drop=True)


def xg_coverage(con, seasons: list[int]) -> float:
    s = ", ".join(map(str, seasons))
    return con.execute(f"""SELECT avg((x.match_id IS NOT NULL)::INT) FROM matches m
        LEFT JOIN (SELECT DISTINCT match_id FROM xg) x USING (match_id)
        WHERE m.league IN ('EPL','BUNDESLIGA') AND m.season IN ({s})""").fetchone()[0] or 0.0


def market(con, frame: pd.DataFrame, mkt: str, phase: str) -> pd.DataFrame:
    if phase == "early":
        o = bt.asof_odds(con, frame, phase="early", market=mkt)
    else:  # vertailutaso: aloitushetken tieto
        o = bt.asof_odds(con, frame, phase="closing", market=mkt, time_col="kickoff_utc", inclusive=True)
    return bt.market_probs(o, mkt, SHARP, settings()["devig_method"])


def w_table(pa: pd.DataFrame, early: dict, close: dict, frame: pd.DataFrame, n_boot: int) -> pd.DataFrame:
    rows = []
    f = frame.set_index("match_id")
    for mkt in ("1x2", "ou25"):
        cols = COLS[mkt]
        ids = pa.index.intersection(early[mkt].index).intersection(close[mkt].index)
        A = pa.loc[ids, cols].to_numpy()
        E = early[mkt].loc[ids, cols].to_numpy()
        C = close[mkt].loc[ids, cols].to_numpy()
        Y = pl.one_hot(f.loc[ids, f"y_{mkt}"].to_numpy(), len(cols))
        groups = f.loc[ids, "round"].to_numpy()
        for name, B, T in (("(1) aikainen, kohde tulos", E, Y),
                           ("(2) aikainen, kohde sulkeutuva p", E, C),
                           ("(3) sulkeutuva*, kohde tulos", C, Y)):
            w = pl.fit_w(A, B, T)
            lo, hi, _ = pl.bootstrap_w(A, B, T, n_boot=n_boot, groups=groups)
            ce_b = pl.cross_entropy(B, T)
            ce_p = pl.cross_entropy(pl.pool(A, B, w), T)
            rows.append({"markkina": mkt, "sovitus": name, "n": len(ids), "w": w, "95 % LV": f"[{lo:.3f}, {hi:.3f}]",
                         "CE markkina": ce_b, "CE pooli": ce_p, "parannus ×1000": 1000 * (ce_b - ce_p)})
    return pd.DataFrame(rows)


def run(con: duckdb.DuckDBPyConnection, out_dir: Path | None = None, n_boot: int = 500,
        workers: int = 4) -> Path:
    out_dir = out_dir or ROOT / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    s = settings()["splits"]
    commit = git_commit()
    tag = commit[:12]

    # 1. Viritys opetuskausilla
    grid = tune(s["train"], workers=workers)
    best = grid.iloc[0]
    params = DCParams(xi=float(best["xi"]), tau_early=float(best["tau_early"]))
    no_prior = replace(params, tau_early=0.0)

    h = ma.load_history(con)
    tr = bt.load_frame(con, s["train"])
    va = bt.load_frame(con, s["validation"])
    pa_tr = ma.walk_forward(h, tr, params)
    pa_va = ma.walk_forward(h, va, params)
    pa_va_np = ma.walk_forward(h, va, no_prior)

    # 2. Mittarit
    rows = []
    for split, frame, pa in (("opetus (viritetty tällä)", tr, pa_tr), ("validointi", va, pa_va)):
        base = {m: bt.base_rate(con, frame, m) for m in ("1x2", "ou25")}
        early = {m: market(con, frame, m, "early") for m in ("1x2", "ou25")}
        close = {m: market(con, frame, m, "closing") for m in ("1x2", "ou25")}
        for name, pr in (("perustaso", base), ("malli A (maalit)", None), ("aikainen terävä", early),
                         ("sulkeutuva terävä*", close)):
            if pr is None:
                p = pa
            else:
                p = pd.concat([pr["1x2"][COLS["1x2"]], pr["ou25"][COLS["ou25"]]], axis=1).dropna()
            ids = p.index.intersection(pa.index)
            rows.append({"jakso": split, "ennustaja": name, **_score(p.loc[ids], frame)})
    metrics = pd.DataFrame(rows)

    # 3. Elo-priorin vaikutus validoinnissa: kauden 6 ensimmäistä kierrosta vs. loput
    va_idx = va.set_index("match_id")
    rnd_in_season = va.groupby("league")["round"].transform(lambda r: pd.factorize(r)[0])
    early_ids = va.loc[rnd_in_season < 6, "match_id"]
    prior_rows = []
    for label, ids in (("kierrokset 1–6", early_ids), ("kierrokset 7–", va.loc[rnd_in_season >= 6, "match_id"])):
        for nm, p in ((f"τ_early = {params.tau_early:g}", pa_va), ("τ_early = 0", pa_va_np)):
            prior_rows.append({"jakso": label, "prior": nm, **_score(p.loc[ids], va)})
    prior_tab = pd.DataFrame(prior_rows)

    # 4. Poolipaino w
    early_va = {m: market(con, va, m, "early") for m in ("1x2", "ou25")}
    close_va = {m: market(con, va, m, "closing") for m in ("1x2", "ou25")}
    early_tr = {m: market(con, tr, m, "early") for m in ("1x2", "ou25")}
    close_tr = {m: market(con, tr, m, "closing") for m in ("1x2", "ou25")}
    w_va = w_table(pa_va, early_va, close_va, va, n_boot)
    w_tr = w_table(pa_tr, early_tr, close_tr, tr, n_boot)
    # Siirto: opetuskauden w validointiin
    transfer = []
    for (_, r_tr), (_, r_va) in zip(w_tr.iterrows(), w_va.iterrows()):
        mkt = r_tr["markkina"]
        cols = COLS[mkt]
        B = (early_va if "aikainen" in r_tr["sovitus"] else close_va)[mkt]
        ids = pa_va.index.intersection(B.index).intersection(close_va[mkt].index)
        A = pa_va.loc[ids, cols].to_numpy()
        Bm = B.loc[ids, cols].to_numpy()
        T = (close_va[mkt].loc[ids, cols].to_numpy() if "sulkeutuva p" in r_tr["sovitus"]
             else pl.one_hot(va_idx.loc[ids, f"y_{mkt}"].to_numpy(), len(cols)))
        ce_b = pl.cross_entropy(Bm, T)
        ce_p = pl.cross_entropy(pl.pool(A, Bm, r_tr["w"]), T)
        transfer.append({"markkina": mkt, "sovitus": r_tr["sovitus"], "w (opetus)": r_tr["w"],
                         "parannus validoinnissa ×1000": 1000 * (ce_b - ce_p)})
    transfer = pd.DataFrame(transfer)

    # 5. Kalibrointi (validointi)
    y = va_idx.loc[pa_va.index, "y_1x2"].to_numpy()
    P = pa_va[COLS["1x2"]].to_numpy()
    cal = mt.calibration_table(P, y)
    fig, ax = plt.subplots(figsize=(5, 4.6), dpi=130)
    ax.plot([0, 1], [0, 1], color="#999", lw=1, ls="--")
    ax.plot(cal["predicted"], cal["observed"], "o-", color="#3b6fb6", ms=4)
    ax.set_title("Malli A, 1X2, validointi 2023/24", fontsize=10)
    ax.set_xlabel("ennustettu todennäköisyys")
    ax.set_ylabel("toteutunut osuus")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    png = out_dir / f"phase3_calibration_{tag}.png"
    fig.savefig(png)
    plt.close(fig)
    draw = f"Tasapeli: ennuste keskimäärin {P[:, 1].mean():.3f}, toteutunut {(y == 1).mean():.3f}."

    # 6. xG-variantti
    cov = xg_coverage(con, s["train"] + s["validation"])
    if cov >= XG_MIN_COVERAGE:
        xg_note = "xG-variantti ajettava erikseen (TODO)."
    else:
        xg_note = (f"**Ei ajettu.** xG-kattavuus kausilla 2020/21–2023/24 on {100 * cov:.1f} %. Kaggle-aineisto "
                   "(`data/raw/understat_kaggle/game_stats.csv`) puuttuu tästä ympäristöstä, koska `data/` ei ole "
                   "versionhallinnassa. Koodi tukee varianttia (`DCParams(variant='xg')`, pseudo-Poisson, ρ = 0).")

    f4 = dict(index=False, floatfmt=".4f")
    gcols = ["xi", "tau_early", "n", "ll_1x2", "rps_1x2", "ll_ou", "ll_sum"]
    path = out_dir / f"phase3_{tag}.md"
    path.write_text(f"""# Vaihe 3 – malli A (Dixon–Coles)

Commit: `{commit}`. Opetus {s['train']}, validointi {s['validation']}; testikaudet {s['test']} lukittuja.
Ennustehetki = aloitus − {settings()['schedule']['lock_minutes_before_kickoff']} min; malli sovitetaan kierroksen alussa datalla, jonka available_at < sovitushetki.
Terävä = Pinnacle (varalla Betfair Exchange, markkinakeskiarvo), katteenpoisto `{settings()['devig_method']}`. \\* = aloitushetken tieto, vain vertailuksi.

## 1. Hyperparametrit (valittu opetuskausilla, 10 parasta)

Valittu: **ξ = {params.xi:g}** (puoliintumisaika {np.log(2) / params.xi:.0f} vrk), **τ_early = {params.tau_early:g}**, τ_ridge = {params.tau_ridge:g}, ikkuna {params.window_days} vrk.

{grid[gcols].head(10).to_markdown(**f4)}

## 2. Walk-forward-mittarit (pienempi on parempi)

{metrics.to_markdown(**f4)}

## 3. Poolipaino w (p ∝ p_A^w · p_markkina^(1−w)), validointi 2023/24

CE = ristientropia kohdetta vastaan. Parannus > 0 tarkoittaa, että pooli on parempi kuin markkina yksin. LV = klusteroitu bootstrap kierroksittain ({n_boot} toistoa).

{w_va.to_markdown(**f4)}

### Sama opetuskausilla (in-sample mallin hyperparametrien osalta)

{w_tr.to_markdown(**f4)}

### Otoksen ulkopuolinen tarkistus: opetuskausien w validointiin

{transfer.to_markdown(**f4)}

**Tulkinta:** w > 0 voi syntyä myös siitä, että markkina on hieman ylivarma ja pooli "lämmittää" sitä, vaikka malli A ei toisi omaa informaatiota (ks. `tests/test_model_a.py`). Siksi sovitus (2) on tärkein: se mittaa, ennustaako malli A *markkinan liikettä*.

## 4. Elo-priorin vaikutus (validointi)

{prior_tab.to_markdown(**f4)}

## 5. Kalibrointi (malli A, 1X2, validointi)

![kalibrointi]({png.name})

{cal.to_markdown(index=False, floatfmt=".3f")}

{draw}

## 6. xG-variantti

{xg_note}
""", encoding="utf-8")
    grid.to_csv(out_dir / f"phase3_{tag}_grid.csv", index=False)
    pa_va.to_csv(out_dir / f"phase3_{tag}_validation_predictions.csv")
    return path
