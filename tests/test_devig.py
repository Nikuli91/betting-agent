import numpy as np
import pytest

from bagent.markets import devig as dv

CASES = [[1.65, 4.23, 5.28], [2.1, 3.4, 3.6], [1.2, 7.0, 13.0], [1.9, 1.9], [1.5, 2.6], [1.01, 30, 80]]


@pytest.mark.parametrize("odds", CASES)
@pytest.mark.parametrize("method", dv.METHODS)
def test_sums_to_one_and_in_range(odds, method):
    p = dv.devig(odds, method)
    assert abs(p.sum() - 1) < 1e-10
    assert np.all((p > 0) & (p < 1))


@pytest.mark.parametrize("odds", CASES)
def test_shin_z_nonnegative(odds):
    assert dv.shin_z(odds) >= 0


def test_no_margin_returns_implied():
    odds = [2.0, 4.0, 4.0]  # Σ1/k = 1
    for m in dv.METHODS:
        np.testing.assert_allclose(dv.devig(odds, m), [0.5, 0.25, 0.25], atol=1e-10)
    assert dv.shin_z(odds) == 0


def test_known_multiplicative():
    # q = [0.5, 0.3, 0.25], Σ = 1.05
    np.testing.assert_allclose(dv.multiplicative([2.0, 1 / 0.3, 4.0]), np.array([0.5, 0.3, 0.25]) / 1.05)


def test_symmetric_two_way_is_half():
    for m in dv.METHODS:
        np.testing.assert_allclose(dv.devig([1.9, 1.9], m), [0.5, 0.5], atol=1e-12)


def test_power_and_shin_shift_mass_to_favourite():
    """Power ja Shin korjaavat longshot-vinoumaa: suosikki saa enemmän kuin multiplicative."""
    odds = [1.2, 7.0, 13.0]
    m, p, s = (dv.devig(odds, x) for x in dv.METHODS)
    assert p[0] > m[0] and s[0] > m[0]
    assert p[2] < m[2] and s[2] < m[2]


def test_power_exact_exponent():
    """Tunnettu esimerkki: q = [0.6, 0.5] -> k, jolla 0.6^k + 0.5^k = 1."""
    p = dv.power([1 / 0.6, 1 / 0.5])
    k = np.log(p[0]) / np.log(0.6)
    assert abs(0.6 ** k + 0.5 ** k - 1) < 1e-10
    assert abs(np.log(p[1]) / np.log(0.5) - k) < 1e-9


def test_shin_known_value():
    """Shin kahden lopputuloksen markkinalle: suljettu muoto z = (Σq−1)(... ) tarkistetaan yhtälöstä."""
    odds = [1.5, 2.6]
    z = dv.shin_z(odds)
    q = 1 / np.array(odds)
    s = q.sum()
    p = (np.sqrt(z * z + 4 * (1 - z) * q * q / s) - z) / (2 * (1 - z))
    assert abs(p.sum() - 1) < 1e-10 and 0 < z < 0.2


def test_matrix_matches_rowwise():
    o = np.array(CASES[:3])
    for m in dv.METHODS:
        np.testing.assert_allclose(dv.devig_matrix(o, m), np.vstack([dv.devig(r, m) for r in o]))


def test_rejects_bad_odds():
    with pytest.raises(ValueError):
        dv.devig([1.0, 2.0])
    with pytest.raises(ValueError):
        dv.devig([2, 2], "foo")
