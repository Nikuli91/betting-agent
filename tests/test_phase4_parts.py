"""Vaihe 4: EV, Kelly, CLV, kalibrointi ja dekorreloitu malli – käsin lasketut esimerkit ja ominaisuudet."""
import numpy as np
import pytest
from scipy.optimize import check_grad

from bagent.betting import edge, staking
from bagent.eval import clv
from bagent.models import calibration as cal
from bagent.models import decorrelated as dm


def test_ev_and_kelly_hand_examples():
    assert edge.ev(0.5, 2.2) == pytest.approx(0.1)
    # Kelly: (0.5·2.2 − 1)/(2.2 − 1) = 0.1/1.2
    assert staking.kelly(0.5, 2.2) == pytest.approx(0.1 / 1.2)
    assert staking.kelly(0.4, 2.0) == 0.0
    assert staking.kelly(0.9, 1.0) == 0.0


def test_stakes_caps():
    # ¼ Kelly: 0.25 · 0.0833 = 0.0208 -> katto 0.015
    s = staking.stakes(np.array([0.5]), np.array([2.2]), 0.25, 0.015, 0.05)
    assert s[0] == pytest.approx(0.015)
    s = staking.stakes(np.full(5, 0.5), np.full(5, 2.2), 0.25, 0.015, 0.05)
    assert s.sum() == pytest.approx(0.05) and np.allclose(s, 0.01)


def test_select_bets_threshold_and_divergence():
    p = np.array([[0.5, 0.3, 0.2], [0.5, 0.3, 0.2], [0.6, 0.25, 0.15]])
    k = np.array([[2.2, 3.0, 4.0], [2.0, 3.3, 4.0], [2.0, 3.0, 5.0]])
    ps = np.array([[0.48, 0.3, 0.22], [0.5, 0.3, 0.2], [0.45, 0.3, 0.25]])
    b = edge.select_bets(p, k, ps, 0.04, 8)
    assert list(b.sel) == [0, -1, 0]   # 1: EV 10 %; 2: paras EV −0.01 (3.3·0.3); 3: EV 20 %
    assert list(b.bet) == [True, False, False]
    assert list(b.flagged) == [False, False, True]  # 3: ero 15 pp > 8 pp


def test_clv_and_bootstrap():
    assert clv.clv(2.1, 0.5) == pytest.approx(0.05)
    assert clv.price_clv(2.1, 2.0) == pytest.approx(0.05)
    x = np.r_[np.full(50, 0.02), np.full(50, -0.01)]
    lo, hi = clv.cluster_bootstrap_mean(x, np.arange(100) // 5)
    assert lo < x.mean() < hi


def test_vector_scaling_recovers_temperature():
    rng = np.random.default_rng(0)
    truth = rng.dirichlet([3, 2, 3], 20000)
    y = (rng.random(len(truth))[:, None] > truth.cumsum(1)).sum(1)
    over = cal.VectorScaling(1.6, (0.0, 0.0, 0.0)).apply(truth)  # ylivarma ennuste
    vs = cal.fit_vector_scaling(over, y)
    assert vs.a == pytest.approx(1 / 1.6, abs=0.05)
    assert np.allclose(cal.VectorScaling.identity(3).apply(truth), truth)


def _data(n=3000, seed=1):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, 3))
    logits = np.column_stack([X @ [0.8, 0.0, 0.3], 0.2 + 0 * X[:, 0], np.zeros(n)])
    P = np.exp(logits) / np.exp(logits).sum(1, keepdims=True)
    y = (rng.random(n)[:, None] > P.cumsum(1)).sum(1)
    return X, y, P


def test_decorrelated_gradient():
    X, y, P = _data(300)
    m = dm.fit(X, y, P, c=0.0)  # vain normalisointiparametrit
    Xs = np.column_stack([(X - m.mean) / m.std, np.ones(len(X))])
    Y = np.eye(3)[y]

    def f(th):
        return dm.loss_grad(th, Xs, Y, P, 1.5, 1e-3)[0]

    def g(th):
        return dm.loss_grad(th, Xs, Y, P, 1.5, 1e-3)[1]

    th = np.random.default_rng(2).normal(0, 0.3, 8)
    assert check_grad(f, g, th) < 1e-6


def test_decorrelation_increases_distance_to_market():
    X, y, P = _data()
    d0 = np.abs(dm.fit(X, y, P, c=0.0).predict(X) - P).mean()
    d2 = np.abs(dm.fit(X, y, P, c=2.0).predict(X) - P).mean()
    assert d2 > d0


def test_phase4_test_run_lock(tmp_path, monkeypatch):
    """Testijakso ajetaan vain kerran: kirjattu ajo estää uuden."""
    from bagent.eval import phase4
    log = tmp_path / "test_runs.md"
    monkeypatch.setattr(phase4, "TEST_LOG", log)
    assert not phase4._test_already_run()
    log.write_text("| vaihe | aika |\n| phase4 | 2026-11-07 | `abc` | x |\n")
    assert phase4._test_already_run()
    monkeypatch.setattr(phase4, "git_commit", lambda: "abc")
    with pytest.raises(RuntimeError, match="jo tehty"):
        phase4.run(None, out_dir=tmp_path, test=True)
