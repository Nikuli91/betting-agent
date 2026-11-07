"""Malli A: Dixon–Coles aikapainotuksella ja Elo-priorilla (PLAN 6).

log λ_koti   = μ + γ + att_koti + def_vieras
log λ_vieras = μ       + att_vieras + def_koti

- Ottelun paino w = exp(−ξ · Δt_päivinä) sovitushetkestä taaksepäin.
- Goals-variantti: Poisson-uskottavuus + DC-korjaus τ(ρ) matalille tuloksille.
- xG-variantti: pseudo-Poisson (y log λ − λ, y = xG ei-kokonaisluku), ρ = 0, koska τ on
  määritelty vain kokonaislukutuloksille.
- Tunnistettavuus: Σ att = 0 ja Σ def = 0 sakkoterminä.
- Elo-prior: att_i ~ N(c·e_i, 1/τ_i), def_i ~ N(−c·e_i, 1/τ_i), e_i = (Elo_i − ka.)/100, c sovitetaan
  samassa optimoinnissa. τ_i = τ_early · max(0, 1 − n_i/early_rounds) + τ_ridge, missä n_i on joukkueen
  kuluvan kauden ottelut ennen sovitushetkeä. Prior vaikuttaa siis lähinnä kauden 6 ensimmäisellä
  kierroksella ja nousijoilla, joista ei ole pääsarjadataa.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import minimize

SUM_PENALTY = 100.0


@dataclass(frozen=True)
class DCParams:
    xi: float = 0.002            # 1/vrk; puoliintumisaika ln2/ξ ≈ 347 vrk
    tau_early: float = 20.0      # Elo-priorin tarkkuus kauden alussa
    tau_ridge: float = 0.5       # pieni kutistus aina (vakaus)
    early_rounds: int = 6
    window_days: int = 4 * 365
    variant: str = "goals"       # goals | xg


@dataclass
class DCFit:
    teams: list[str]
    mu: float
    gamma: float
    rho: float
    c: float
    att: np.ndarray
    dfn: np.ndarray
    elo_e: dict[str, float] = field(default_factory=dict)
    converged: bool = True

    def strengths(self, team: str) -> tuple[float, float]:
        if team in self._idx:
            i = self._idx[team]
            return self.att[i], self.dfn[i]
        e = self.elo_e.get(team, 0.0)  # tuntematon joukkue: Elo-priorin keskiarvo
        return self.c * e, -self.c * e

    def __post_init__(self):
        self._idx = {t: i for i, t in enumerate(self.teams)}

    def lambdas(self, home: list[str], away: list[str]) -> tuple[np.ndarray, np.ndarray]:
        sh = np.array([self.strengths(t) for t in home]).reshape(-1, 2)
        sa = np.array([self.strengths(t) for t in away]).reshape(-1, 2)
        lh = np.exp(self.mu + self.gamma + sh[:, 0] + sa[:, 1])
        la = np.exp(self.mu + sa[:, 0] + sh[:, 1])
        return lh, la


def _nll_grad(theta, hi, ai, yh, ya, w, n, e, tau, use_rho):
    att, dfn = theta[:n], theta[n:2 * n]
    mu, gamma, rho, c = theta[2 * n:2 * n + 4]
    eh = mu + gamma + att[hi] + dfn[ai]
    ea = mu + att[ai] + dfn[hi]
    lh, la = np.exp(eh), np.exp(ea)
    ll = yh * eh - lh + ya * ea - la
    gh = yh - lh
    ga = ya - la
    grho = np.zeros_like(lh)
    if use_rho:
        t = np.ones_like(lh)
        dth = np.zeros_like(lh)  # dτ/d log λh
        dta = np.zeros_like(lh)
        dtr = np.zeros_like(lh)
        m00 = (yh == 0) & (ya == 0)
        m01 = (yh == 0) & (ya == 1)
        m10 = (yh == 1) & (ya == 0)
        m11 = (yh == 1) & (ya == 1)
        p = lh * la
        t[m00] = 1 - p[m00] * rho
        dth[m00] = dta[m00] = -p[m00] * rho
        dtr[m00] = -p[m00]
        t[m01] = 1 + lh[m01] * rho
        dth[m01] = lh[m01] * rho
        dtr[m01] = lh[m01]
        t[m10] = 1 + la[m10] * rho
        dta[m10] = la[m10] * rho
        dtr[m10] = la[m10]
        t[m11] = 1 - rho
        dtr[m11] = -1
        t = np.clip(t, 1e-10, None)
        ll = ll + np.log(t)
        gh = gh + dth / t
        ga = ga + dta / t
        grho = dtr / t
    f = -np.sum(w * ll)
    wgh, wga = w * gh, w * ga
    g_att = -(np.bincount(hi, wgh, n) + np.bincount(ai, wga, n))
    g_def = -(np.bincount(ai, wgh, n) + np.bincount(hi, wga, n))
    g_mu = -(wgh.sum() + wga.sum())
    g_gamma = -wgh.sum()
    g_rho = -np.sum(w * grho)
    # Elo-prior ja kutistus
    ra, rd = att - c * e, dfn + c * e
    f += 0.5 * np.sum(tau * (ra ** 2 + rd ** 2))
    g_att += tau * ra
    g_def += tau * rd
    g_c = -np.sum(tau * (ra * e - rd * e))
    # Summarajoitteet
    sa, sd = att.sum(), dfn.sum()
    f += 0.5 * SUM_PENALTY * (sa ** 2 + sd ** 2)
    g_att += SUM_PENALTY * sa
    g_def += SUM_PENALTY * sd
    return f, np.concatenate([g_att, g_def, [g_mu, g_gamma, g_rho, g_c]])


def fit(train: pd.DataFrame, t_fit: pd.Timestamp, params: DCParams,
        elo: dict[str, float] | None = None, season_games: dict[str, int] | None = None,
        extra_teams: list[str] | None = None) -> DCFit:
    """train: home_id, away_id, kickoff_utc, y_home, y_away (maalit tai xG). Vain data ennen t_fit."""
    elo = elo or {}
    season_games = season_games or {}
    teams = sorted(set(train["home_id"]) | set(train["away_id"]))
    n = len(teams)
    idx = {t: i for i, t in enumerate(teams)}
    mean_elo = np.mean(list(elo.values())) if elo else 0.0
    elo_e = {t: (v - mean_elo) / 100.0 for t, v in elo.items()}
    e = np.array([elo_e.get(t, 0.0) for t in teams])
    games = np.array([season_games.get(t, 0) for t in teams])
    tau = params.tau_early * np.clip(1 - games / params.early_rounds, 0, None) + params.tau_ridge
    age = (t_fit - train["kickoff_utc"]).dt.total_seconds().to_numpy() / 86400.0
    w = np.exp(-params.xi * age)
    hi = train["home_id"].map(idx).to_numpy()
    ai = train["away_id"].map(idx).to_numpy()
    yh = train["y_home"].to_numpy(float)
    ya = train["y_away"].to_numpy(float)
    use_rho = params.variant == "goals"
    base = np.log(max((yh * w).sum() + (ya * w).sum(), 1e-9) / (2 * w.sum()))
    theta0 = np.concatenate([np.zeros(2 * n), [base, 0.25, -0.05 if use_rho else 0.0, 0.0]])
    bounds = [(None, None)] * (2 * n) + [(None, None), (-1, 1), (-0.3, 0.3) if use_rho else (0, 0), (None, None)]
    res = minimize(_nll_grad, theta0, args=(hi, ai, yh, ya, w, n, e, tau, use_rho), jac=True,
                   method="L-BFGS-B", bounds=bounds, options={"maxiter": 2000})
    th = res.x
    return DCFit(teams=teams, mu=th[2 * n], gamma=th[2 * n + 1], rho=th[2 * n + 2], c=th[2 * n + 3],
                 att=th[:n], dfn=th[n:2 * n], elo_e=elo_e, converged=bool(res.success))
