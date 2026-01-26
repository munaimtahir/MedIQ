"""IRT 2PL and 3PL probability functions and constraints."""

from __future__ import annotations

import math
from typing import overload

import numpy as np


def softplus(x: float) -> float:
    """Softplus: log(1 + exp(x)). Ensures positive a via a = softplus(raw_a)."""
    if x > 20:
        return x
    if x < -20:
        return 0.0
    return math.log(1.0 + math.exp(x))


def sigmoid(x: float) -> float:
    """Logistic sigmoid 1 / (1 + exp(-x))."""
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    ex = math.exp(x)
    return ex / (1.0 + ex)


def _cap_c(c_raw: float, k: int) -> float:
    """Cap c in [0, 1/K]. Use c = sigmoid(c_raw) * (1/K)."""
    p = sigmoid(c_raw)
    return p * (1.0 / max(1, k))


@overload
def p_2pl(theta: float, a: float, b: float) -> float: ...
@overload
def p_2pl(theta: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray: ...


def p_2pl(
    theta: float | np.ndarray,
    a: float | np.ndarray,
    b: float | np.ndarray,
) -> float | np.ndarray:
    """
    2PL: P(correct) = sigmoid(a * (theta - b)).
    a > 0 enforced by caller (e.g. softplus).
    """
    if isinstance(theta, np.ndarray):
        x = a * (theta - b)
        return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))
    return sigmoid(float(a) * (float(theta) - float(b)))


@overload
def p_3pl(theta: float, a: float, b: float, c: float) -> float: ...
@overload
def p_3pl(theta: np.ndarray, a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray: ...


def p_3pl(
    theta: float | np.ndarray,
    a: float | np.ndarray,
    b: float | np.ndarray,
    c: float | np.ndarray,
) -> float | np.ndarray:
    """
    3PL: P = c + (1 - c) * sigmoid(a * (theta - b)).
    a > 0, c in [0, 1/K] enforced by caller.
    """
    base = p_2pl(theta, a, b)
    if isinstance(theta, np.ndarray):
        return c + (1.0 - c) * base
    return float(c) + (1.0 - float(c)) * float(base)
