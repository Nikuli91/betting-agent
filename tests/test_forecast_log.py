from datetime import timedelta

import pytest

from bagent.log.forecast_log import (ForecastLog, ForecastTooLateError, LockedRowError,
                                     TamperedLogError)
from tests.conftest import utc

KO = utc(2026, 11, 8, 14)
NOW = KO - timedelta(hours=2)


def _log(con):
    log = ForecastLog(con)
    fid = log.append(match_id="m1", kickoff_utc=KO, model_version="A-0.1", payload={"p": [0.5, 0.3, 0.2]},
                     now=NOW, commit="abc")
    log.append(match_id="m2", kickoff_utc=KO, model_version="A-0.1", payload={"p": [0.4, 0.3, 0.3]},
               now=NOW, commit="abc")
    return log, fid


def test_append_and_verify(mem_con):
    log, _ = _log(mem_con)
    log.verify()
    assert [r["seq"] for r in log.rows()] == [1, 2]
    assert log.rows()[1]["prev_hash"] == log.rows()[0]["content_hash"]


def test_too_late_rejected(mem_con):
    log = ForecastLog(mem_con)
    with pytest.raises(ForecastTooLateError):
        log.append(match_id="m1", kickoff_utc=KO, model_version="x", payload={}, now=KO, commit="c")


def test_locked_row_cannot_be_modified_via_api(mem_con):
    log, fid = _log(mem_con)
    with pytest.raises(LockedRowError):
        log.update(fid, payload={"p": [1, 0, 0]})
    with pytest.raises(LockedRowError):
        log.delete(fid)


@pytest.mark.parametrize("sql", [
    "UPDATE forecast_log SET payload = '{\"p\":[0.9,0.05,0.05]}' WHERE seq = 1",
    "UPDATE forecast_log SET created_at = created_at - INTERVAL 1 DAY WHERE seq = 1",
    "DELETE FROM forecast_log WHERE seq = 1",
])
def test_direct_tampering_detected_and_blocks_writes(mem_con, sql):
    log, _ = _log(mem_con)
    mem_con.execute(sql)
    with pytest.raises(TamperedLogError):
        log.verify()
    with pytest.raises(TamperedLogError):
        log.append(match_id="m3", kickoff_utc=KO, model_version="x", payload={}, now=NOW, commit="c")


def test_correction_is_new_row(mem_con):
    log, fid = _log(mem_con)
    new = log.correct(fid, match_id="m1", kickoff_utc=KO, model_version="A-0.1",
                      payload={"p": [0.45, 0.3, 0.25]}, now=NOW, commit="abc")
    rows = log.rows()
    assert len(rows) == 3 and rows[0]["forecast_id"] == fid
    assert rows[2]["supersedes"] == fid and rows[2]["forecast_id"] == new
    log.verify()


def test_jsonl_roundtrip_and_tamper_detection(tmp_path):
    import json as _json
    from datetime import datetime, timedelta, timezone
    from bagent.data.store import connect
    from bagent.log import forecast_log as fl
    now = datetime(2026, 11, 7, 9, tzinfo=timezone.utc)
    p = tmp_path / "log.jsonl"
    log = fl.ForecastLog(connect(":memory:"))
    log.append(match_id="m1", kickoff_utc=now + timedelta(hours=5), model_version="v", payload={"p": [0.5, 0.3, 0.2]},
               now=now, commit="c")
    assert fl.export_jsonl(log, p) == 1
    log.append(match_id="m2", kickoff_utc=now + timedelta(hours=6), model_version="v", payload={"p": [0.4]},
               now=now, commit="c")
    assert fl.export_jsonl(log, p) == 1  # vain uusi rivi lisätään
    log2 = fl.load_jsonl(connect(":memory:"), p)
    assert [r["match_id"] for r in log2.rows()] == ["m1", "m2"]
    lines = p.read_text().splitlines()
    r = _json.loads(lines[0])
    r["payload"]["p"][0] = 0.9
    lines[0] = _json.dumps(r)
    p.write_text("\n".join(lines) + "\n")
    with pytest.raises(fl.TamperedLogError):
        fl.load_jsonl(connect(":memory:"), p)
