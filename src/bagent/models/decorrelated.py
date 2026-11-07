"""Dekorreloitu malli (Hubáček & Šír 2023), PLAN 6.

Multinomiaalinen logistinen regressio piirteillä x (mallin A log λ:t ja Elo-ero), häviö
    L = CE(p, y) − c · mean_i Σ_k (p_ik − p_markkina,ik)²
c > 0 palkitsee eroamisesta markkinasta, jolloin malli virheineen on vähemmän korreloitunut
markkinan kanssa. Markkinan todennäköisyys on vain häviössä, ei piirteenä.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

EPS = 1e-12


def _softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


@dataclass
class DecorrelatedModel:
    W: np.ndarray       # (d+1) × K, viimeinen luokka referenssi (nollat)
    mean: np.ndarray
    std: np.ndarray

    def predict(self, X: np.ndarray) -> np.ndarray:
        Xs = np.column_stack([(X - self.mean) / self.std, np.ones(len(X))])
        return _softmax(Xs @ self.W)


def loss_grad(th, Xs, Y, p_market, c, l2):
    d, k = Xs.shape[1], Y.shape[1]
    W = np.column_stack([th.reshape(d, k - 1), np.zeros(d)])
    P = _softmax(Xs @ W)
    n = len(Y)
    ce = -np.sum(Y * np.log(np.clip(P, EPS, 1))) / n
    diff = P - p_market
    f = ce - c * np.sum(diff ** 2) / n + 0.5 * l2 * np.sum(W ** 2)
    # dL/dz: CE -> (P − Y); dekorrelointi -> −2c · J^T diff, J = diag(P) − P P^T
    g_dec = P * diff - P * np.sum(P * diff, axis=1, keepdims=True)
    G = ((P - Y) - 2 * c * g_dec) / n
    gW = Xs.T @ G + l2 * W
    return f, gW[:, :k - 1].ravel()


def fit(X: np.ndarray, y: np.ndarray, p_market: np.ndarray, c: float, l2: float = 1e-3) -> DecorrelatedModel:
    k = p_market.shape[1]
    mean, std = X.mean(axis=0), X.std(axis=0) + 1e-9
    Xs = np.column_stack([(X - mean) / std, np.ones(len(X))])
    d = Xs.shape[1]
    Y = np.zeros((len(y), k))
    Y[np.arange(len(y)), y] = 1

    r = minimize(loss_grad, np.zeros(d * (k - 1)), args=(Xs, Y, p_market, c, l2), jac=True, method="L-BFGS-B")
    W = np.column_stack([r.x.reshape(d, k - 1), np.zeros(d)])
    return DecorrelatedModel(W, mean, std)
