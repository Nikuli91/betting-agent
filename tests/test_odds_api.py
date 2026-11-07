"""The Odds API: jäsennys, haamukerroinsuodatus, idempotentti lataus, avaimen peitto, nimikattavuus."""
import gzip
import json

import httpx
import pytest

from bagent.data import odds_api as oa
from bagent.data import team_names as tn


def _rec(fetched="2026-11-07T10:00:00+00:00", ko="2026-11-07T15:00:00Z", mlu="2026-11-07T09:55:00Z"):
    def h2h(lu=mlu):
        return {"key": "h2h", "last_update": lu, "outcomes": [
            {"name": "Arsenal", "price": 1.8}, {"name": "Chelsea", "price": 4.5}, {"name": "Draw", "price": 3.9}]}
    totals = {"key": "totals", "last_update": mlu, "outcomes": [
        {"name": "Over", "price": 1.9, "point": 2.5}, {"name": "Under", "price": 1.95, "point": 2.5},
        {"name": "Over", "price": 2.6, "point": 3.5}, {"name": "Under", "price": 1.5, "point": 3.5}]}
    return {"fetched_at": fetched, "league": "EPL", "sport": "soccer_epl", "params": {}, "usage": {},
            "data": [{"id": "ev1", "sport_key": "soccer_epl", "commence_time": ko,
                      "home_team": "Arsenal", "away_team": "Chelsea", "bookmakers": [
                          {"key": "pinnacle", "title": "Pinnacle", "last_update": mlu, "markets": [h2h(), totals]},
                          {"key": "stalebook", "title": "Stale", "last_update": mlu,
                           "markets": [h2h("2026-11-06T10:00:00Z")]}]}]}


def test_parse_maps_selections_and_lines():
    p = oa.parse_snapshot(_rec())
    ev = p["odds_api_events"].iloc[0]
    assert ev.match_id == "EPL_20261107_eng_arsenal_eng_chelsea"
    s = p["odds_snapshots"]
    assert len(s) == 3 + 4 + 3  # kaikki rivit säilyvät, myös 3.5-linja ja vanhentunut välittäjä
    pin = s[(s.bookmaker == "pinnacle") & (s.market == "h2h")].set_index("selection").price
    assert pin.to_dict() == {"H": 1.8, "A": 4.5, "D": 3.9}
    o = p["odds"]
    assert set(o.market) == {"1x2", "ou25"}
    assert (o.phase == "snapshot").all() and not o.available_at_estimated.any()
    assert len(o[o.market == "ou25"]) == 2  # vain 2.5-linja
    assert (o.available_at == ev.first_seen).all()


def test_phantom_odds_filtered_from_odds_table():
    p = oa.parse_snapshot(_rec())
    assert "stalebook" not in set(p["odds"].bookmaker)  # last_update 24 h vanha
    started = oa.parse_snapshot(_rec(fetched="2026-11-07T15:05:00+00:00"))
    assert started["odds"].empty  # ottelu alkanut -> ei pelattava kerroin
    assert not started["odds_snapshots"].empty


def test_unknown_team_skips_only_its_event():
    r = _rec()
    good = json.loads(json.dumps(r["data"][0]))
    good["id"], good["home_team"], good["away_team"] = "ev2", "Chelsea", "Arsenal"
    r["data"][0]["home_team"] = "Not A Real FC"
    r["data"].append(good)
    p = oa.parse_snapshot(r)
    assert p["unknown"] == ["Not A Real FC"]
    assert list(p["odds_api_events"].event_id) == ["ev2"]


def test_load_file_idempotent(mem_con, tmp_path):
    f = tmp_path / "s.json.gz"
    with gzip.open(f, "wt") as fh:
        json.dump(_rec(), fh)
    a = oa.load_file(mem_con, f)
    oa.load_file(mem_con, f)
    assert mem_con.execute("SELECT count(*) FROM odds_snapshots").fetchone()[0] == a["snapshot_rows"]
    assert mem_con.execute("SELECT count(*) FROM odds WHERE source='odds_api'").fetchone()[0] == a["odds_rows"]
    assert mem_con.execute("SELECT count(*) FROM odds_api_events").fetchone()[0] == 1


def test_api_key_masked_in_errors(monkeypatch):
    monkeypatch.setenv("ODDS_API_KEY", "SECRET123")
    transport = httpx.MockTransport(lambda req: httpx.Response(401, text=f"bad key {req.url}"))
    with httpx.Client(transport=transport) as c, pytest.raises(oa.OddsApiError) as e:
        oa._get(c, "/sports", {})
    assert "SECRET123" not in str(e.value) and "***" in str(e.value)


def test_current_season_teams_have_odds_api_name(real_con):
    """Jokaisella nykykauden pääsarjajoukkueella on The Odds API -nimi (muuten snapshot ei liity)."""
    from bagent.config import leagues_sql, settings
    cur = settings()["current_season"]
    ids = {r[0] for r in real_con.execute(
        f"SELECT home_id FROM matches WHERE season = ? AND league IN ({leagues_sql()})", [cur]).fetchall()}
    mapped = {tn.to_canonical("odds_api", n) for n in tn.known_names("odds_api")}
    assert ids and ids <= mapped, sorted(ids - mapped)
