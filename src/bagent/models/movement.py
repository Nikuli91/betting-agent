"""Kerroinliikemalli: ennustaa terävän sulkeutumistodennäköisyyden aikaisista kertoimista.

    log p̂_close,k = log p_sharp_early,k + b_k + Σ_j β_j · x_jk   (normalisoitu softmaxilla)

x_jk = piirre j valinnalle k, esim. log p_keskiarvo,k − log p_terävä,k (mihin suuntaan muu markkina
poikkeaa terävästä). b_k = valintakohtainen ajautuma (esim. tasapelit liikkuvat systemaattisesti).
β ja b sovitetaan minimoimalla ristientropia katteetonta sulkeutumistodennäköisyyttä vastaan.
β = 0 ja b = 0 tarkoittaa "aikainen terävä on paras ennuste sulkeutumisesta".
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

EPS = 1e-12


def _logits(log_p0, X, beta, b):
    return log_p0 + b[None, :] + np.einsum("nkj,j->nk", X, beta)


def _softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


@dataclass(frozen=True)
class MovementModel:
    beta: np.ndarray
    b: np.ndarray
    names: tuple[str, ...]

    def predict(self, p_early: np.ndarray, X: np.ndarray) -> np.ndarray:
        return _softmax(_logits(np.log(np.clip(p_early, EPS, 1)), X, self.beta, self.b))


def loss_grad(th, log_p0, X, T, l2):
    n, k, j = X.shape
    beta, b = th[:j], np.concatenate([[0.0], th[j:]])
    P = _softmax(_logits(log_p0, X, beta, b))
    f = -np.sum(T * np.log(np.clip(P, EPS, 1))) / n + 0.5 * l2 * np.sum(th ** 2)
    G = (P - T) / n                       # dL/dz
    g_beta = np.einsum("nk,nkj->j", G, X)
    g_b = G.sum(axis=0)[1:]
    return f, np.concatenate([g_beta, g_b]) + l2 * th


def fit(p_early: np.ndarray, X: np.ndarray, p_close: np.ndarray, names: tuple[str, ...],
        l2: float = 1e-4) -> MovementModel:
    n, k, j = X.shape
    r = minimize(loss_grad, np.zeros(j + k - 1), args=(np.log(np.clip(p_early, EPS, 1)), X, p_close, l2),
                 jac=True, method="L-BFGS-B")
    return MovementModel(r.x[:j], np.concatenate([[0.0], r.x[j:]]), names)
