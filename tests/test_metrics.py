import numpy as np
import pytest

from bagent.eval import metrics as mt


def test_hand_computed():
    p = np.array([[0.5, 0.3, 0.2], [0.2, 0.3, 0.5]])
    y = np.array([0, 1])
    assert mt.log_loss(p, y) == pytest.approx(-(np.log(0.5) + np.log(0.3)) / 2)
    # Brier: (0.25+0.09+0.04) ja (0.04+0.49+0.25)
    assert mt.brier(p, y) == pytest.approx((0.38 + 0.78) / 2)
    # RPS: ottelu 1: F=[.5,.8], O=[1,1] -> (.25+.04)/2 ; ottelu 2: F=[.2,.5], O=[0,1] -> (.04+.25)/2
    assert mt.rps(p, y) == pytest.approx((0.145 + 0.145) / 2)


def test_perfect_forecast():
    p = np.eye(3)
    y = np.arange(3)
    assert mt.log_loss(p, y) < 1e-12 and mt.brier(p, y) == 0 and mt.rps(p, y) == 0


def test_calibration_table():
    rng = np.random.default_rng(0)
    p1 = rng.uniform(0.05, 0.95, 20000)
    y = (rng.uniform(size=p1.size) > p1).astype(int)  # luokka 0 todennäköisyydellä p1
    t = mt.calibration_table(np.c_[p1, 1 - p1], y)
    assert t["gap_pp"].abs().max() < 3


def test_rejects_unnormalised():
    with pytest.raises(ValueError):
        mt.log_loss(np.array([[0.5, 0.6]]), np.array([0]))
