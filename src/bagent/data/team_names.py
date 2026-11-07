"""Joukkueiden nimet -> yksi kanoninen id.

Rekisteri on tiedostossa team_registry.csv (versionhallinnassa). Jokaisella lähteellä on
oma sarakkeensa; tyhjä solu = nimeä ei vielä todennettu kyseisestä lähteestä.
Tuntematon nimi on aina virhe (UnknownTeamError), ei hiljainen arvaus.
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

REGISTRY_PATH = Path(__file__).with_name("team_registry.csv")
SOURCES = ("football_data", "odds_api", "understat")


class UnknownTeamError(KeyError):
    pass


@lru_cache(maxsize=1)
def _registry() -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    by_source: dict[str, dict[str, str]] = {s: {} for s in SOURCES}
    display: dict[str, str] = {}
    with open(REGISTRY_PATH, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            tid = row["team_id"].strip()
            if tid in display:
                raise ValueError(f"team_id kahdesti rekisterissä: {tid}")
            display[tid] = row["display_name"].strip()
            for s in SOURCES:
                for name in filter(None, (n.strip() for n in (row.get(s) or "").split("|"))):
                    if name in by_source[s] and by_source[s][name] != tid:
                        raise ValueError(f"{s}: nimi {name!r} kahdelle id:lle")
                    by_source[s][name] = tid
    return by_source, display


def to_canonical(source: str, name: str) -> str:
    by_source, _ = _registry()
    try:
        return by_source[source][name.strip()]
    except KeyError:
        raise UnknownTeamError(f"{source}: tuntematon joukkue {name!r}; lisää team_registry.csv:hen") from None


def display_name(team_id: str) -> str:
    return _registry()[1][team_id]


def known_names(source: str) -> set[str]:
    return set(_registry()[0][source])


def all_team_ids() -> set[str]:
    return set(_registry()[1])
