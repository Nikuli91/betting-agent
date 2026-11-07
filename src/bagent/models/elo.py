"""Oma Elo football-data.co.uk:n tuloksista (ClubElo ei ole saatavilla ajoympäristössä).

Pääsarja ja syöttösarja lasketaan samaan maakohtaiseen pooliin, jotta nousijoilla on luku.
Ottelua edeltävä luku käyttää vain tuloksia, joiden available_at < ottelun aloitus.
Parametrit ovat lähtöarvoja; ne viritetään vaiheessa 3 validointijaksolla.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class EloParams:
    k: float = 20.0
    home_adv: float = 60.0
    init_top: float = 1500.0
    init_feeder: float = 1350.0  # ensimmäinen havainto syöttösarjassa
    season_regress: float = 0.2  # kauden vaihteessa kohti pooliin tulotasoa
    use_goal_diff: bool = True


def expected_home(r_home: float, r_away: float, home_adv: float) -> float:
    return 1.0 / (1.0 + 10 ** (-(r_home + home_adv - r_away) / 400.0))


def _gd_mult(gd: int) -> float:
    gd = abs(gd)
    if gd <= 1:
        return 1.0
    if gd == 2:
        return 1.5
    return (11 + gd) / 8.0


def _safe(fn, label, default):
    """Asetuksissa olematon tunnus (esim. testidata) -> oletus."""
    try:
        return fn(label)
    except KeyError:
        return default


def compute_pre_match(matches: pd.DataFrame, results: pd.DataFrame,
                      params: EloParams = EloParams()) -> pd.DataFrame:
    """Palauttaa match_id, home_elo, away_elo, home_games, away_games, available_at.

    matches: match_id, league, division, season, kickoff_utc, home_id, away_id
    results: match_id, home_goals, away_goals, available_at
    Pooli = asetusten pool (maa): esim. EPL ja CHAMPIONSHIP -> ENG, BUNDESLIGA ja BUNDESLIGA_FEEDER -> GER.
    Joukkue, joka nähdään ensimmäisen kerran alemmalla sarjatasolla, saa init_feeder-luvun.
    """
    m = matches.copy()
    from bagent.config import league_pool, league_tier
    labels = m["league"].unique()
    pools = {lb: _safe(league_pool, lb, lb.removesuffix("_FEEDER")) for lb in labels}
    tiers = {lb: _safe(league_tier, lb, 2 if lb.endswith("_FEEDER") else 1) for lb in labels}
    m["pool"] = m["league"].map(pools)
    m["is_feeder"] = m["league"].map(tiers) > 1
    m = m.merge(results[["match_id", "home_goals", "away_goals", "available_at"]],
                on="match_id", how="left")
    out = []
    for pool, g in m.groupby("pool"):
        g = g.sort_values(["kickoff_utc", "match_id"]).reset_index(drop=True)
        rating: dict[str, float] = {}
        games: dict[str, int] = {}
        last_season: dict[str, int] = {}
        # Tulokset päivitetään vasta, kun available_at on ohitettu -> jono.
        pending: list[tuple] = []  # (available_at, home, away, delta)
        last_used_at = pd.Timestamp.min.tz_localize("UTC")

        def flush(until):
            nonlocal last_used_at
            pending.sort(key=lambda x: x[0])
            while pending and pending[0][0] < until:
                at, h, a, d = pending.pop(0)
                rating[h] += d
                rating[a] -= d
                games[h] = games.get(h, 0) + 1
                games[a] = games.get(a, 0) + 1
                last_used_at = max(last_used_at, at)

        for row in g.itertuples(index=False):
            flush(row.kickoff_utc)
            for t in (row.home_id, row.away_id):
                if t not in rating:
                    rating[t] = params.init_feeder if row.is_feeder else params.init_top
                    games[t] = 0
                elif last_season.get(t) is not None and last_season[t] != row.season:
                    mean = sum(rating.values()) / len(rating)
                    rating[t] = rating[t] + params.season_regress * (mean - rating[t])
                last_season[t] = row.season
            rh, ra = rating[row.home_id], rating[row.away_id]
            out.append(dict(match_id=row.match_id, home_elo=rh, away_elo=ra,
                            home_games=games[row.home_id], away_games=games[row.away_id],
                            available_at=last_used_at))
            if not pd.isna(row.home_goals):
                hg, ag = int(row.home_goals), int(row.away_goals)
                s = 1.0 if hg > ag else 0.5 if hg == ag else 0.0
                e = expected_home(rh, ra, params.home_adv)
                mult = _gd_mult(hg - ag) if params.use_goal_diff else 1.0
                pending.append((row.available_at, row.home_id, row.away_id, params.k * mult * (s - e)))
    df = pd.DataFrame(out)
    # Ottelu ilman yhtäkään aiempaa tulosta: available_at = epoch (ei tietoa käytetty)
    df["available_at"] = df["available_at"].where(
        df["available_at"] > pd.Timestamp("1900-01-01", tz="UTC"), pd.Timestamp("1970-01-01", tz="UTC"))
    return df

