"""Malli A: tulosmatriisi, Dixon–Coles (gradientti, parametrien palautus), pooli."""
import numpy as np
import pandas as pd
import pytest
from scipy.optimize import check_grad

from bagent.models import dixon_coles as dc
from bagent.models import pooling as pl
from bagent.models import scoreline as sl


def test_score_matrix_sums_and_markets():
    m = sl.score_matrix([1.5, 0.8], [1.1, 2.0], rho=-0.1)
    assert m.shape == (2, 11, 11)
    assert np.allclose(m.sum(axis=(1, 2)), 1)
    p = sl.probs_1x2(m)
    assert np.allclose(p.sum(axis=1), 1)
    assert p[0, 0] > p[0, 2] and p[1, 2] > p[1, 0]
    ou = sl.probs_ou(m)
    assert np.allclose(ou.sum(axis=1), 1)
    # rho = 0: riippumattomat Poissonit; P(0–0) = e^{-λh-λa}
    m0 = sl.score_matrix(1.2, 0.9, 0.0)
    assert m0[0, 0] == pytest.approx(np.exp(-2.1), rel=1e-6)
    # Yli 2,5 riippumattomilla Poissoneilla = 1 − P(summa ≤ 2), summa ~ Poisson(2.1)
    from scipy.stats import poisson
    assert sl.probs_ou(m0)[0] == pytest.approx(1 - poisson.cdf(2, 2.1), abs=1e-6)


def test_dc_tau_raises_draw_for_negative_rho():
    a = sl.probs_1x2(sl.score_matrix(1.3, 1.1, 0.0))
    b = sl.probs_1x2(sl.score_matrix(1.3, 1.1, -0.12))
    assert b[1] > a[1]


@pytest.mark.parametrize("use_rho", [True, False])
def test_gradient_matches_numeric(use_rho):
    rng = np.random.default_rng(0)
    n, m = 6, 80
    hi, ai = rng.integers(0, n, m), rng.integers(0, n, m)
    yh, ya = rng.poisson(1.4, m).astype(float), rng.poisson(1.1, m).astype(float)
    if not use_rho:
        yh, ya = yh + rng.random(m), ya + rng.random(m)
    w, e, tau = rng.random(m), rng.normal(size=n), rng.random(n) + 0.1
    th = np.concatenate([rng.normal(0, .2, 2 * n), [0.2, 0.25, -0.05 if use_rho else 0.0, 0.1]])
    f = lambda x: dc._nll_grad(x, hi, ai, yh, ya, w, n, e, tau, use_rho)[0]  # noqa: E731
    g = lambda x: dc._nll_grad(x, hi, ai, yh, ya, w, n, e, tau, use_rho)[1]  # noqa: E731
    assert check_grad(f, g, th) / np.linalg.norm(g(th)) < 1e-5


def _simulate(seed=1, n_teams=20, seasons=8):
    rng = np.random.default_rng(seed)
    att = rng.normal(0, 0.3, n_teams); att -= att.mean()
    dfn = rng.normal(0, 0.3, n_teams); dfn -= dfn.mean()
    mu, gamma, rho = 0.1, 0.3, -0.1
    rows = []
    t0 = pd.Timestamp("2020-08-01", tz="UTC")
    day = 0
    for _ in range(seasons):
        for h in range(n_teams):
            for a in range(n_teams):
                if h == a:
                    continue
                lh, la = np.exp(mu + gamma + att[h] + dfn[a]), np.exp(mu + att[a] + dfn[h])
                m = sl.score_matrix(lh, la, rho).ravel()
                k = rng.choice(m.size, p=m)
                rows.append(dict(home_id=f"t{h:02d}", away_id=f"t{a:02d}", kickoff_utc=t0 + pd.Timedelta(days=day),
                                 y_home=k // 11, y_away=k % 11))
                day += 1 if len(rows) % 6 == 0 else 0
    return pd.DataFrame(rows), att, dfn, mu, gamma, rho


def test_dixon_coles_recovers_parameters():
    df, att, dfn, mu, gamma, rho = _simulate()
    t = df["kickoff_utc"].max() + pd.Timedelta(days=1)
    f = dc.fit(df, t, dc.DCParams(xi=0.0, tau_early=0.0, tau_ridge=0.0, window_days=10**6))
    assert f.converged
    assert f.gamma == pytest.approx(gamma, abs=0.06)
    assert f.rho == pytest.approx(rho, abs=0.06)
    assert f.mu == pytest.approx(mu, abs=0.06)
    assert np.abs(f.att - att).max() < 0.15
    assert np.abs(f.dfn - dfn).max() < 0.15


def test_unknown_team_uses_elo_prior():
    df, *_ = _simulate(seasons=1)
    t = df["kickoff_utc"].max() + pd.Timedelta(days=1)
    _, att, dfn, *_ = _simulate(seasons=1)
    elo = {f"t{i:02d}": 1500 + 300 * (att[i] - dfn[i]) for i in range(len(att))}
    elo |= {"new_strong": 1800, "new_weak": 1300}
    f = dc.fit(df, t, dc.DCParams(xi=0.0, tau_early=5.0), elo=elo)
    assert f.c > 0  # Elo on simuloitu vahvuudesta -> c > 0
    lh_s, _ = f.lambdas(["new_strong"], ["t00"])
    lh_w, _ = f.lambdas(["new_weak"], ["t00"])
    assert lh_s[0] > lh_w[0]


def test_pool_and_fit_w():
    rng = np.random.default_rng(3)
    n = 4000
    truth = rng.dirichlet([4, 3, 3], n)
    y = np.array([rng.choice(3, p=p) for p in truth])
    noisy = np.array([rng.dirichlet(p * 30) for p in truth])  # B: lähellä totuutta
    junk = rng.dirichlet([3, 3, 3], n)  # A: ei informaatiota
    assert np.allclose(pl.pool(junk, noisy, 0.0), noisy / noisy.sum(1, keepdims=True))
    assert np.allclose(pl.pool(junk, noisy, 0.3).sum(1), 1)
    # B kalibroitu totuus, A kohinaa -> w ≈ 0; päinvastoin -> w ≈ 1
    assert pl.fit_w(junk, truth, pl.one_hot(y, 3)) < 0.05
    assert pl.fit_w(truth, junk, pl.one_hot(y, 3)) > 0.9
    # Huom: ylivarma B + informaatioton A antaa w > 0 pelkän "lämmityksen" vuoksi
    assert pl.fit_w(junk, noisy, pl.one_hot(y, 3)) > 0.05
    # Pehmeä kohde: kohde on B itse -> w = 0
    assert pl.fit_w(truth, noisy, noisy) < 0.01


def test_walk_forward_ignores_future_rows():
    """Vuototesti: tulos, jonka available_at ≥ t_fit, ei vaikuta kierroksen ennusteeseen."""
    from bagent.eval import model_a as ma
    df, *_ = _simulate(seasons=2)
    df = df.assign(match_id=[f"m{i}" for i in range(len(df))], league="EPL", season=2020,
                   home_goals=df.y_home, away_goals=df.y_away,
                   available_at=df.kickoff_utc + pd.Timedelta(minutes=150))
    t_fit = df.kickoff_utc.iloc[500] - pd.Timedelta(minutes=60)
    elo = pd.DataFrame(columns=["league", "kickoff_utc", "team_id", "elo", "available_at"])
    h = ma.History(df, pd.DataFrame(columns=["match_id", "home_xg", "away_xg", "available_at"]), elo)
    rnd = df.iloc[500:505].assign(t=t_fit)
    p1 = ma.predict_round(h, t_fit, rnd, dc.DCParams())
    future = df.available_at >= t_fit
    df2 = df.copy()
    df2.loc[future, ["home_goals", "away_goals"]] = 9
    p2 = ma.predict_round(ma.History(df2, h.xg, elo), t_fit, rnd, dc.DCParams())
    pd.testing.assert_frame_equal(p1, p2)
    df3 = df.copy()
    df3.loc[~future & (df.available_at > t_fit - pd.Timedelta(days=30)), ["home_goals", "away_goals"]] = 9
    p3 = ma.predict_round(ma.History(df3, h.xg, elo), t_fit, rnd, dc.DCParams())
    assert not np.allclose(p1.p_H, p3.p_H)  # kontrolli: menneisyyden muutos näkyy
