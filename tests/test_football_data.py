import io

import pandas as pd

from bagent.data import football_data as fd
from tests.conftest import utc

# Otsikko ja rivi kopioitu sellaisenaan tiedostosta mmz4281/2425/E0.csv (ensimmäiset sarakkeet + valitut kertoimet).
CSV = """﻿Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,FTR,PSH,PSD,PSA,AvgH,AvgD,AvgA,P>2.5,P<2.5,PSCH,PSCD,PSCA,AvgCH,AvgCD,AvgCA,PC>2.5,PC<2.5
E0,16/08/2024,20:00,Man United,Fulham,1,0,H,1.63,4.38,5.3,1.62,4.36,5.15,1.56,2.56,1.65,4.23,5.28,1.66,4.2,5.02,1.63,2.38
E0,17/08/2024,15:00,Arsenal,Wolves,2,0,H,1.2,7.0,13,1.2,7,13,1.5,2.6,1.2,7,13,1.2,7,13,1.5,2.6
E0,21/08/2024,19:30,Chelsea,Everton,0,0,D,2,3.5,3.8,2,3.5,3.8,1.9,1.9,,,,2,3.5,3.8,,
"""


def parsed():
    df = pd.read_csv(io.StringIO(CSV.lstrip("﻿")), dtype=str)
    return fd.parse(df, "EPL", 2024, "E0")


def test_kickoff_is_london_time():
    assert fd.kickoff_utc("16/08/2024", "20:00") == utc(2024, 8, 16, 19, 0)  # BST
    assert fd.kickoff_utc("14/12/2024", "15:00") == utc(2024, 12, 14, 15, 0)  # GMT
    assert fd.kickoff_utc("14/12/24", "15:00") == utc(2024, 12, 14, 15, 0)


def test_early_odds_available_at_rules():
    # Pe 20:00 -> sama perjantai 18:00 Lontoo (17:00 UTC)
    assert fd.early_odds_available_at(utc(2024, 8, 16, 19, 0)) == utc(2024, 8, 16, 17, 0)
    # La -> edeltävä perjantai
    assert fd.early_odds_available_at(utc(2024, 8, 17, 14, 0)) == utc(2024, 8, 16, 17, 0)
    # Ma -> edeltävä perjantai
    assert fd.early_odds_available_at(utc(2024, 8, 19, 19, 0)) == utc(2024, 8, 16, 17, 0)
    # Ke -> edeltävä tiistai
    assert fd.early_odds_available_at(utc(2024, 8, 21, 18, 30)) == utc(2024, 8, 20, 17, 0)
    # Ti 17:30 Lontoo: rajataan 90 min ennen aloitusta
    assert fd.early_odds_available_at(utc(2024, 8, 20, 16, 30)) == utc(2024, 8, 20, 15, 0)


def test_parse_tables():
    p = parsed()
    assert len(p["matches"]) == 3
    assert set(p["matches"]["home_id"]) == {"eng_man_united", "eng_arsenal", "eng_chelsea"}
    o = p["odds"]
    first = o[o.match_id == p["matches"].match_id[0]]
    # pinnacle: early+closing × (1x2 3 + ou 2) = 10; market_avg: vain 1x2 (fixturessa ei Avg>2.5) = 6
    assert len(first) == 10 + 6
    pin_close_h = first.query("bookmaker=='pinnacle' and phase=='closing' and selection=='H'").price.item()
    assert pin_close_h == 1.65
    # Puuttuvat Pinnaclen closing-kertoimet eivät tuota rivejä
    third = o[o.match_id == p["matches"].match_id[2]]
    assert third.query("bookmaker=='pinnacle' and phase=='closing'").empty


def test_availability_ordering():
    p = parsed()
    m = p["matches"].set_index("match_id")
    for _, r in p["odds"].iterrows():
        ko = m.loc[r.match_id, "kickoff_utc"]
        assert r.available_at <= ko
        if r.phase == "early":
            assert r.available_at < ko and r.available_at_estimated
    for _, r in p["results"].iterrows():
        assert r.available_at > m.loc[r.match_id, "kickoff_utc"]


def test_rebuild_is_idempotent_when_availability_rule_changes(mem_con):
    from bagent.data.build import replace_source_rows
    from bagent.data.store import upsert
    p = parsed()
    for t, df in p.items():
        upsert(mem_con, t, df)
    shifted = p["odds"].copy()
    shifted["available_at"] = shifted["available_at"] - pd.Timedelta(minutes=5)  # sääntö muuttui
    replace_source_rows(mem_con, p["matches"]["match_id"], "football_data")
    upsert(mem_con, "odds", shifted)
    assert mem_con.execute("SELECT count(*) FROM odds").fetchone()[0] == len(shifted)
    dup = mem_con.execute("""SELECT max(c) FROM (SELECT count(*) c FROM odds
                             GROUP BY match_id, bookmaker, market, phase, selection)""").fetchone()[0]
    assert dup == 1
