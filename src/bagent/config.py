"""Asetukset ja polut."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(os.environ.get("BAGENT_ROOT", Path(__file__).resolve().parents[2]))
CONFIG_PATH = ROOT / "config" / "settings.yaml"
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "bagent.duckdb"


@lru_cache(maxsize=1)
def settings() -> dict[str, Any]:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def secret(name: str) -> str | None:
    """Salaisuus ympäristömuuttujasta tai .env-tiedostosta. Arvoa ei koskaan tulosteta."""
    val = os.environ.get(name)
    if val:
        return val.strip()
    env = ROOT / ".env"
    if env.exists():
        from dotenv import dotenv_values
        val = dotenv_values(env).get(name)
    return val.strip() if val else None


def season_code(start_year: int) -> str:
    """2020 -> '2021' (football-data.co.uk:n kausikoodi kaudelle 2020/21)."""
    return f"{start_year % 100:02d}{(start_year + 1) % 100:02d}"


def season_label(start_year: int) -> str:
    return f"{start_year}/{(start_year + 1) % 100:02d}"
