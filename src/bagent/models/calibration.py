"""Kalibrointi: vektoriskaalaus log-todennäköisyyksille (PLAN 6/7).

p' ∝ exp(a · log p + b), b_0 = 0. a < 1 lämmittää (vähentää varmuutta), b siirtää luokkien tasoa
(esim. tasapelien aliarviointi). Parametrit sovitetaan minimoimalla log loss.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

EPS = 1e-12


@dataclass(frozen=True)
class VectorScaling:
    a: float
    b: tuple[float, ...]

    def apply(self, p: np.ndarray) -> np.ndarray:
        z = self.a * np.log(np.clip(p, EPS, 1)) + np.array(self.b)
        z -= z.max(axis=-1, keepdims=True)
        q = np.exp(z)
        return q / q.sum(axis=-1, keepdims=True)

    @classmethod
    def identity(cls, k: int) -> "VectorScaling":
        return cls(1.0, (0.0,) * k)


def fit_vector_scaling(p: np.ndarray, y: np.ndarray) -> VectorScaling:
    k = p.shape[1]
    lp = np.log(np.clip(p, EPS, 1))

    def nll(th):
        a, b = th[0], np.concatenate([[0.0], th[1:]])
        z = a * lp + b
        z -= z.max(axis=1, keepdims=True)
        logq = z - np.log(np.exp(z).sum(axis=1, keepdims=True))
        return -logq[np.arange(len(y)), y].mean()

    r = minimize(nll, np.concatenate([[1.0], np.zeros(k - 1)]), method="L-BFGS-B")
    return VectorScaling(float(r.x[0]), tuple([0.0] + [float(v) for v in r.x[1:]]))
