"""Vaiheen 2 raportti: perustaso ja markkina, kalibrointi, katediagnostiikka.

Käyttää vain opetus- ja validointikausia. Testikaudet ovat lukittuja (PLAN 7); ainoa
poikkeus on Pinnacle vs. Betfair Exchange -vertailu, joka käyttää vain kertoimia, ei tuloksia.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from bagent.config import ROOT, settings  # noqa: E402
from bagent.eval import backtest as bt  # noqa: E402
from bagent.eval import metrics as mt  # noqa: E402
from bagent.log.forecast_log import git_commit  # noqa: E402
from bagent.markets.devig import METHODS, devig_matrix  # noqa: E402

SHARP = ["pinnacle", "betfair_exchange"]
SEED = 20261107


def bootstrap_mean_ci(x: np.ndarray, n_boot: int = 2000, alpha: float = 0.05, seed: int = SEED) -> tuple[float, float]:
    x = np.asarray(x, dtype=float)
    if len(x) == 0:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    means = rng.choice(x, size=(n_boot, len(x)), replace=True).mean(axis=1)
    return float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2))


def _y(frame: pd.DataFrame, market: str) -> pd.Series:
    return frame.set_index("match_id")[f"y_{market}"]


def _score(probs: pd.DataFrame, frame: pd.DataFrame, market: str, name: str) -> list[dict]:
    sel = bt.SELECTIONS[market]
    rows = []
    for split, g in [("train", frame[frame.split == "train"]), ("validation", frame[frame.split == "validation"]),
                     ("train+validation", frame)]:
        ids = g["match_id"][g["match_id"].isin(probs.index)]
        if len(ids) == 0:
            continue
        p = probs.loc[ids, [f"p_{s}" for s in sel]].to_numpy()
        y = _y(g, market).loc[ids].to_numpy()
        m = mt.all_metrics(p, y, ordered=market == "1x2")
        m.update(dict(market=market, predictor=name, split=split, coverage=len(ids) / len(g)))
        rows.append(m)
    return rows


def evaluate(con: duckdb.DuckDBPyConnection, frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    rows, keep = [], {}
    for market in ("1x2", "ou25"):
        rows += _score(bt.base_rate(con, frame, market), frame, market, "perustaso (liigan jakauma, 3 v)")
        early = bt.asof_odds(con, frame, phase="early", market=market)
        close = bt.asof_odds(con, frame, phase="closing", market=market, time_col="kickoff_utc", inclusive=True)
        for method in METHODS:
            for label, odds, books in (("aikainen terävä", early, SHARP + ["market_avg"]),
                                       ("aikainen keskiarvo", early, ["market_avg"]),
                                       ("sulkeutuva terävä*", close, SHARP + ["market_avg"]),
                                       ("sulkeutuva keskiarvo*", close, ["market_avg"])):
                p = bt.market_probs(odds, market, books, method)
                rows += _score(p, frame, market, f"{label} / {method}")
                keep[(market, label, method)] = p
    return pd.DataFrame(rows), keep


def calibration_section(frame: pd.DataFrame, keep: dict, out_dir: Path, tag: str) -> tuple[str, Path]:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), dpi=130)
    md = []
    for ax, (label, color) in zip(axes, (("aikainen terävä", "#3b6fb6"), ("sulkeutuva terävä*", "#c0504d"))):
        p = keep[("1x2", label, "power")]
        ids = frame["match_id"][frame["match_id"].isin(p.index)]
        P = p.loc[ids, ["p_H", "p_D", "p_A"]].to_numpy()
        y = _y(frame, "1x2").loc[ids].to_numpy()
        tab = mt.calibration_table(P, y)
        ax.plot([0, 1], [0, 1], color="#999", lw=1, ls="--")
        ax.plot(tab["predicted"], tab["observed"], "o-", color=color, ms=4)
        ax.set_title(f"1X2 {label.rstrip('*')} (power)", fontsize=10)
        ax.set_xlabel("ennustettu todennäköisyys")
        ax.set_ylabel("toteutunut osuus")
        ax.grid(alpha=0.3)
        md.append(f"**{label} / power** (1X2, kaikki lopputulokset, 2020/21–2023/24)\n\n"
                  + tab.to_markdown(index=False, floatfmt=".3f") + "\n")
        draw_pred, draw_obs = P[:, 1].mean(), (y == 1).mean()
        md.append(f"Tasapeli: ennuste keskimäärin {draw_pred:.3f}, toteutunut {draw_obs:.3f} "
                  f"(ero {100 * (draw_obs - draw_pred):+.2f} pp).\n")
    fig.tight_layout()
    png = out_dir / f"phase2_calibration_{tag}.png"
    fig.savefig(png)
    plt.close(fig)
    return "\n".join(md), png


def margin_diagnostic(con: duckdb.DuckDBPyConnection, frame: pd.DataFrame) -> str:
    cfg = settings()
    thr = cfg["core"]["ev_threshold"]
    md = []
    for market, t_key in (("1x2", "h2h"), ("ou25", "totals")):
        th = thr[t_key]
        sel = bt.SELECTIONS[market]
        early = bt.asof_odds(con, frame, phase="early", market=market)
        close = bt.asof_odds(con, frame, phase="closing", market=market, time_col="kickoff_utc", inclusive=True)
        pe = bt.market_probs(early, market, SHARP, "power")
        pc = bt.market_probs(close, market, SHARP, "power")
        ids = pe.index.intersection(pc.index)
        PE = pe.loc[ids, [f"p_{s}" for s in sel]].to_numpy()
        PC = pc.loc[ids, [f"p_{s}" for s in sel]].to_numpy()
        n_sel = PE.size
        rows = []
        for book in cfg["margin_diagnostic"]["soft_books"] + ["market_avg", "market_max"]:
            k = bt.book_matrix(early, book, market).reindex(ids)
            ok = k.notna().all(axis=1).to_numpy()
            if not ok.any():  # välittäjällä ei ole tätä markkinaa football-datassa
                continue
            K = k.to_numpy()[ok]
            margin = (1 / K).sum(axis=1).mean() - 1
            ev_fore = PC[ok] * K - 1
            ev_sig = PE[ok] * K - 1
            hit = ev_sig >= th
            clv = ev_fore[hit]
            lo, hi = bootstrap_mean_ci(clv)
            rows.append({
                "kerroin": book, "kate": f"{100 * margin:.1f} %",
                "EV≥kynnys tiedolla sulkeutumisesta": f"{100 * (ev_fore >= th).mean():.2f} %",
                "signaali: EV≥kynnys aikaista terävää vastaan (kpl)": int(hit.sum()),
                "signaalien CLV ka.": f"{100 * clv.mean():+.2f} %" if len(clv) else "–",
                "95 % LV": f"[{100 * lo:+.2f}, {100 * hi:+.2f}]" if len(clv) else "–",
            })
        syn = []
        for m in cfg["margin_diagnostic"]["synthetic_margins"]:
            K = 1 / (PE * (1 + m))
            ev_fore = PC * K - 1
            syn.append({"synteettinen kate": f"{100 * m:.0f} %",
                        "EV≥kynnys tiedolla sulkeutumisesta": f"{100 * (ev_fore >= th).mean():.2f} %",
                        "tarvittava sulkeutumisliike p_c/p_e": f"≥ {(1 + th) * (1 + m):.3f}"})
        moves = PC / PE
        md.append(f"#### {market.upper()} (kynnys {100 * th:.0f} %, {len(ids)} ottelua, {n_sel} valintaa)\n\n"
                  "Todelliset aikaiset kertoimet (pe/ti-iltapäivä):\n\n"
                  + pd.DataFrame(rows).to_markdown(index=False) + "\n\n"
                  "Synteettinen kate aikaisen terävän reilun kertoimen päälle:\n\n"
                  + pd.DataFrame(syn).to_markdown(index=False) + "\n\n"
                  f"Terävän todennäköisyyden suhteellinen muutos aikaisesta sulkeutumiseen (p_c/p_e): "
                  f"mediaani {np.median(moves):.3f}, 90. persentiili {np.quantile(moves, .9):.3f}, "
                  f"99. persentiili {np.quantile(moves, .99):.3f}.\n")
    return "\n".join(md)


def sharp_agreement(con: duckdb.DuckDBPyConnection) -> str:
    """Pinnacle vs Betfair Exchange sulkeutuva, päällekkäinen jakso. Vain kertoimet, ei tuloksia."""
    df = con.execute("""
        SELECT o.match_id, o.bookmaker, o.selection, o.price, o.available_at FROM odds o JOIN matches m USING (match_id)
        WHERE o.market='1x2' AND o.phase='closing' AND o.bookmaker IN ('pinnacle','betfair_exchange')
          AND m.league IN ('EPL','BUNDESLIGA') AND m.season >= 2024""").df()
    if df.empty:
        return "Ei päällekkäistä dataa."
    w = {b: bt.book_matrix(df, b, "1x2") for b in ("pinnacle", "betfair_exchange")}
    ids = w["pinnacle"].index.intersection(w["betfair_exchange"].index)
    pp = devig_matrix(w["pinnacle"].loc[ids].to_numpy(), "power")
    pb = devig_matrix(w["betfair_exchange"].loc[ids].to_numpy(), "power")
    mb = (1 / w["betfair_exchange"].loc[ids].to_numpy()).sum(axis=1).mean() - 1
    mp = (1 / w["pinnacle"].loc[ids].to_numpy()).sum(axis=1).mean() - 1
    d = np.abs(pp - pb)
    return (f"{len(ids)} ottelua (2024/25–1/2026). Katteeton todennäköisyys (power), keskimääräinen itseisero "
            f"{100 * d.mean():.2f} pp, 95. persentiili {100 * np.quantile(d, .95):.2f} pp, "
            f"maksimi {100 * d.max():.2f} pp. Keskimääräinen kate: Pinnacle {100 * mp:.2f} %, "
            f"Betfair Exchange {100 * mb:.2f} %.")


def run(con: duckdb.DuckDBPyConnection, out_dir: Path | None = None) -> Path:
    out_dir = out_dir or ROOT / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    s = settings()["splits"]
    frame = bt.load_frame(con, s["train"] + s["validation"])
    res, keep = evaluate(con, frame)
    commit = git_commit()
    tag = commit[:12]
    cal_md, png = calibration_section(frame, keep, out_dir, tag)
    fmt = res.copy()
    tables = []
    for market in ("1x2", "ou25"):
        for split in ("train", "validation", "train+validation"):
            t = fmt[(fmt.market == market) & (fmt.split == split)]
            cols = ["predictor", "n", "coverage", "log_loss", "brier"] + (["rps"] if market == "1x2" else [])
            t = t[cols].sort_values("log_loss")
            tables.append(f"#### {market.upper()} – {split}\n\n" + t.to_markdown(index=False, floatfmt=".4f") + "\n")
    path = out_dir / f"phase2_{tag}.md"
    path.write_text(f"""# Vaihe 2 – markkina ja perustasot

Commit: `{commit}`. Kaudet: opetus {s['train']}, validointi {s['validation']}. Testikaudet {s['test']} ovat lukittuja eivätkä ole mukana.
Ennustehetki = aloitus − {settings()['schedule']['lock_minutes_before_kickoff']} min. Kaikki rivit liitetty ehdolla available_at < ennustehetki.
\\* = vertailutaso, joka käyttää aloitushetken tietoa (sulkeutuva kerroin); ei ole saatavilla lukitushetkellä.
"Terävä" = Pinnacle, varalla Betfair Exchange ja sitten markkinakeskiarvo (kausilla 2020–2023 käytännössä aina Pinnacle).

## 1. Mittarit (pienempi on parempi)

{chr(10).join(tables)}

## 2. Kalibrointi

![kalibrointi]({png.name})

{cal_md}

## 3. Katediagnostiikka

Kysymys: kuinka usein EV-kynnys olisi edes periaatteessa ylittynyt käyttäjän välittäjän kaltaisilla kertoimilla?

- *EV≥kynnys tiedolla sulkeutumisesta* = osuus valinnoista, joissa EV = p_sulkeutuva_terävä · k − 1 ≥ kynnys. Tämä on yläraja: täydellinen tieto sulkeutumisesta.
- *Signaali* = pelataan, kun aikainen kerroin ylittää aikaisen terävän reilun kertoimen kynnyksen verran (Kaunitz-tyyppinen, ilman omaa mallia). *CLV* = EV sulkeutuvaa terävää vastaan (PLAN 7).
- `market_max` on monen välittäjän maksimi, jota yksi pelaaja ei voi saada; mukana vain ylärajana.

{margin_diagnostic(con, frame)}

## 4. Pinnacle vs. Betfair Exchange (sulkeutuva, päällekkäinen jakso)

{sharp_agreement(con)}
""", encoding="utf-8")
    res.to_csv(out_dir / f"phase2_{tag}_metrics.csv", index=False)
    return path
