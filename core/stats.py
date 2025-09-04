from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Tuple


def ols_alpha_beta(x: pd.Series, y: pd.Series) -> Tuple[float, float]:
    """Return (alpha, beta) for y ~ alpha + beta * x.
    Drops NaNs and aligns indices.
    """
    xy = pd.concat([x, y], axis=1).dropna()
    if len(xy) < 10:
        return 0.0, 0.0
    X = np.vstack([np.ones(len(xy)), xy.iloc[:, 0].values]).T
    yv = xy.iloc[:, 1].values
    beta = np.linalg.lstsq(X, yv, rcond=None)[0]
    alpha, slope = beta[0], beta[1]
    return float(alpha), float(slope)


def rolling_std(s: pd.Series) -> float:
    return float(np.nanstd(s.values, ddof=1))


def bootstrap_car_ci(
    returns: pd.Series,
    window_len: int,
    n_iter: int = 1000,
    random_state: int = 42,
) -> tuple[float, float]:
    """Bootstrap CI for CAR using random consecutive windows from returns.
    Returns (low, high) for ~95% CI.
    """
    rng = np.random.default_rng(random_state)
    if len(returns) < window_len + 10:
        return (np.nan, np.nan)
    starts = rng.integers(0, len(returns) - window_len, size=n_iter)
    sums = [returns.iloc[s:s+window_len].sum() for s in starts]
    low, high = np.nanpercentile(sums, [2.5, 97.5])
    return float(low), float(high)