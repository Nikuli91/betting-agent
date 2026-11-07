import glob
from pathlib import Path

import pytest

from bagent.config import RAW_DIR
from bagent.data import team_names as tn
from bagent.data.football_data import read_raw


def test_unknown_team_raises():
    with pytest.raises(tn.UnknownTeamError):
        tn.to_canonical("football_data", "Not A Real FC")


def test_registry_ids_unique_and_prefixed():
    ids = tn.all_team_ids()
    assert len(ids) > 40
    assert all(i.startswith(("eng_", "ger_")) for i in ids)


def test_every_downloaded_team_name_maps():
    files = glob.glob(str(RAW_DIR / "football_data" / "*" / "*.csv"))
    if not files:
        pytest.skip("Raakadataa ei ole ladattu")
    missing = set()
    for f in files:
        df = read_raw(Path(f))
        for n in set(df.HomeTeam) | set(df.AwayTeam):
            try:
                tn.to_canonical("football_data", n)
            except tn.UnknownTeamError:
                missing.add(n)
    assert not missing, f"Mappaamattomat nimet: {sorted(missing)}"


def test_no_match_without_pair(real_con):
    """Jokaisella ottelulla on kanoninen koti- ja vierasjoukkue, eikä ottelu-id:tä ole kahdesti."""
    n_bad = real_con.execute(
        "SELECT count(*) FROM matches WHERE home_id IS NULL OR away_id IS NULL OR home_id = away_id").fetchone()[0]
    assert n_bad == 0
    ids = tn.all_team_ids()
    used = {r[0] for r in real_con.execute("SELECT home_id FROM matches UNION SELECT away_id FROM matches").fetchall()}
    assert used <= ids
