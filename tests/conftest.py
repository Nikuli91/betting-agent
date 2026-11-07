from datetime import datetime, timezone

import pytest

from bagent.config import DB_PATH
from bagent.data.store import connect


@pytest.fixture
def mem_con():
    con = connect(":memory:")
    yield con
    con.close()


@pytest.fixture(scope="session")
def real_con():
    """Oikea tietokanta, jos se on rakennettu (`bagent data build`); muuten testi ohitetaan."""
    if not DB_PATH.exists():
        pytest.skip("data/bagent.duckdb puuttuu – aja `bagent data build`")
    import duckdb
    con = duckdb.connect(str(DB_PATH), read_only=True)
    con.execute("SET TimeZone='UTC'")
    yield con
    con.close()


def utc(*a):
    return datetime(*a, tzinfo=timezone.utc)
