"""IRT 2PL/3PL estimation via joint MAP with SciPy."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import numpy as np
from scipy import optimize

from app.learning_engine.config import (
    IRT_C_PRIOR_IMPLIED_BY_1K,
    IRT_INIT_A_MODEST,
    IRT_PRIOR_A_MEAN,
    IRT_PRIOR_B_MEAN,
    IRT_PRIOR_B_SD,
    IRT_PRIOR_THETA_MEAN,
    IRT_PRIOR_THETA_SD,
)
from app.learning_engine.irt.prob import p_2pl, p_3pl

logger = logging.getLogger(__name__)


@dataclass
class FitConfig:
    """IRT fit configuration (priors, etc.)."""

    prior_theta_mean: float = IRT_PRIOR_THETA_MEAN.value
    prior_theta_sd: float = IRT_PRIOR_THETA_SD.value
    prior_a_mean: float = IRT_PRIOR_A_MEAN.value
    prior_b_mean: float = IRT_PRIOR_B_MEAN.value
    prior_b_sd: float = IRT_PRIOR_B_SD.value
    init_a: float = IRT_INIT_A_MODEST.value
    c_1k: float = IRT_C_PRIOR_IMPLIED_BY_1K.value
    maxiter: int = 2000
    ftol: float = 1e-6


@dataclass
class FitResult:
    """Result of IRT fit."""

    item_a: dict[UUID, float] = field(default_factory=dict)
    item_b: dict[UUID, float] = field(default_factory=dict)
    item_c: dict[UUID, float] = field(default_factory=dict)
    item_a_se: dict[UUID, float] = field(default_factory=dict)
    item_b_se: dict[UUID, float] = field(default_factory=dict)
    item_c_se: dict[UUID, float] = field(default_factory=dict)
    user_theta: dict[UUID, float] = field(default_factory=dict)
    user_theta_se: dict[UUID, float] = field(default_factory=dict)
    item_option_count: dict[UUID, int] = field(default_factory=dict)
    neg_loglik: float = 0.0
    n_obs: int = 0


def _sigmoid(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, -500, 500)
    return 1.0 / (1.0 + np.exp(-x))


def _softplus(x: np.ndarray) -> np.ndarray:
    return np.logaddexp(0, x)


def _cap_c_vec(c_raw: np.ndarray, k_vec: np.ndarray) -> np.ndarray:
    p = _sigmoid(c_raw)
    return p / np.maximum(k_vec, 1)


def _init_b_from_pvalue(p: float) -> float:
    """Map empirical p-value to b via logit. Guarded."""
    eps = 1e-6
    p = max(eps, min(1 - eps, p))
    return float(np.log(p / (1 - p)))


def fit_irt(
    rows: list[Any],
    model_type: str,
    *,
    seed: int = 42,
    config: FitConfig | None = None,
    elo_difficulty: dict[UUID, float] | None = None,
) -> FitResult:
    """
    Fit 2PL or 3PL via joint MAP (theta + item params) with priors.

    - a > 0: softplus reparameterization.
    - c in [0, 1/K]: sigmoid * (1/K).
    - Cold-start b: from ELO difficulty if available, else from p-value.
    - Theta ~ N(0,1) prior; scale anchored via standardization post-fit.
    """
    config = config or FitConfig()
    rng = np.random.default_rng(seed)

    # Build index maps
    user_ids = list({r.user_id for r in rows})
    item_ids = list({r.question_id for r in rows})
    u2i = {u: i for i, u in enumerate(user_ids)}
    q2i = {q: i for i, q in enumerate(item_ids)}

    # Option count per item (assume stored on row or default 5)
    k_per_item = np.ones(len(item_ids), dtype=float) * 5
    for r in rows:
        i = q2i[r.question_id]
        k_per_item[i] = getattr(r, "option_count", 5)
    k_per_item = np.maximum(1, k_per_item)

    # Observations: (user_ix, item_ix, correct)
    obs = []
    for r in rows:
        ui = u2i[r.user_id]
        qi = q2i[r.question_id]
        obs.append((ui, qi, r.correct))
    obs = np.array(obs, dtype=np.int64)
    n_obs = len(obs)

    n_user = len(user_ids)
    n_item = len(item_ids)
    is_3pl = model_type.upper() == "IRT_3PL"

    # Init theta, b
    theta = rng.normal(config.prior_theta_mean, config.prior_theta_sd, n_user).astype(np.float64)
    b = np.zeros(n_item)
    for qid, i in q2i.items():
        if elo_difficulty and qid in elo_difficulty:
            # Map ELO rating to IRT b roughly: same scale, 0-centered
            b[i] = float(elo_difficulty[qid])
        else:
            p = np.mean([r.correct for r in rows if r.question_id == qid])
            b[i] = _init_b_from_pvalue(p)
    b = b.astype(np.float64)

    # a: softplus(raw_a), init near prior mean
    raw_a = np.full(n_item, np.log(np.exp(config.init_a) - 1) if config.init_a > 0 else 0.0, dtype=np.float64)
    a = _softplus(raw_a)

    # c (3PL only): sigmoid(raw_c) * (1/K)
    raw_c = np.zeros(n_item, dtype=np.float64)
    c = _cap_c_vec(raw_c, k_per_item) if is_3pl else np.zeros(n_item)

    def obj(x: np.ndarray) -> float:
        th = x[:n_user]
        rb = x[n_user : n_user + n_item]
        ra = x[n_user + n_item : n_user + 2 * n_item]
        rc = x[n_user + 2 * n_item :] if is_3pl else None
        a_ = _softplus(ra)
        b_ = rb
        c_ = _cap_c_vec(rc, k_per_item) if is_3pl else np.zeros(n_item)
        ll = 0.0
        for (ui, qi, y) in obs:
            t = th[ui]
            aa, bb, cc = a_[qi], b_[qi], c_[qi]
            if is_3pl:
                p = cc + (1 - cc) * _sigmoid(aa * (t - bb))
            else:
                p = _sigmoid(aa * (t - bb))
            p = np.clip(p, 1e-15, 1 - 1e-15)
            ll += y * np.log(p) + (1 - y) * np.log(1 - p)
        # Priors
        ll += np.sum(-0.5 * ((th - config.prior_theta_mean) / config.prior_theta_sd) ** 2)
        ll += np.sum(-0.5 * ((rb - config.prior_b_mean) / config.prior_b_sd) ** 2)
        ll += np.sum(-0.5 * ((ra - np.log(np.exp(config.prior_a_mean) - 1)) ** 2))
        return -ll

    def pack(th: np.ndarray, rb: np.ndarray, ra: np.ndarray, rc: np.ndarray | None) -> np.ndarray:
        if is_3pl and rc is not None:
            return np.concatenate([th, rb, ra, rc])
        return np.concatenate([th, rb, ra])

    def unpack(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray | None]:
        th = x[:n_user]
        rb = x[n_user : n_user + n_item]
        ra = x[n_user + n_item : n_user + 2 * n_item]
        rc = x[n_user + 2 * n_item :] if is_3pl else None
        return th, rb, ra, rc

    x0 = pack(theta, b, raw_a, raw_c if is_3pl else None)
    res = optimize.minimize(obj, x0, method="L-BFGS-B", options={"maxiter": config.maxiter, "ftol": config.ftol})
    th, rb, ra, rc = unpack(res.x)
    a_f = _softplus(ra)
    b_f = rb
    c_f = _cap_c_vec(rc, k_per_item) if is_3pl else np.zeros(n_item)

    # Standardize theta post-fit: theta ~ N(0,1)
    mu_t = float(np.mean(th))
    sd_t = float(np.std(th))
    if sd_t < 1e-9:
        sd_t = 1.0
    th_std = (th - mu_t) / sd_t
    b_f = b_f * sd_t + mu_t
    a_f = a_f / sd_t

    # Placeholder SEs (could use Hessian later)
    se_a = 0.1
    se_b = 0.1
    se_c = 0.05 if is_3pl else 0.0
    se_theta = 0.1

    out = FitResult(neg_loglik=float(res.fun), n_obs=n_obs)
    for i, qid in enumerate(item_ids):
        out.item_a[qid] = float(a_f[i])
        out.item_b[qid] = float(b_f[i])
        out.item_c[qid] = float(c_f[i]) if is_3pl else 0.0
        out.item_a_se[qid] = se_a
        out.item_b_se[qid] = se_b
        if is_3pl:
            out.item_c_se[qid] = se_c
        out.item_option_count[qid] = int(k_per_item[i])
    for i, uid in enumerate(user_ids):
        out.user_theta[uid] = float(th_std[i])
        out.user_theta_se[uid] = se_theta
    return out
