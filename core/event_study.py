from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple, List

import numpy as np
import pandas as pd

from .data import ensure_symbol_frame, to_returns
from .stats import ols_alpha_beta, bootstrap_car_ci


@dataclass
class Windows:
    # hours relative to event time t0
    estimation: tuple[int, int] = (-240, -24)
    event: tuple[int, int] = (-24, 24)


@dataclass
class ModelCfg:
    benchmark: Optional[str] = "BTC-USD"   # None -> mean-adjusted model
    use_bootstrap: bool = True
    n_boot: int = 1000


@dataclass
class EventResult:
    event_id: str
    symbol: str
    t0: pd.Timestamp
    ar: pd.Series
    car: pd.Series
    alpha: float
    beta: float
    car_ci: Tuple[float, float]


@dataclass
class AggregateResult:
    mean_ar: pd.Series
    mean_car: pd.Series
    car_ci: Tuple[float, float]
    per_event: List[EventResult]


def _slice_window(s: pd.Series, t0: pd.Timestamp, window: tuple[int, int]) -> pd.Series:
    # Align to hourly frequency and reindex to exact relative hours
    s = s.asfreq("h")
    idx = pd.date_range(
        t0 + pd.Timedelta(hours=window[0]),
        t0 + pd.Timedelta(hours=window[1]),
        freq="h",
        tz="UTC",
    )
    return s.reindex(idx)


def _market_model_ar(
    target_rets: pd.Series,
    bench_rets: Optional[pd.Series],
    t0: pd.Timestamp,
    windows: Windows,
) -> tuple[pd.Series, float, float]:
    est = _slice_window(target_rets, t0, windows.estimation).dropna()

    if bench_rets is None:
        # mean-adjusted model
        mu = est.mean() if len(est) > 0 else 0.0
        ar = _slice_window(target_rets, t0, windows.event) - mu
        return ar, float(mu), 0.0

    est_b = _slice_window(bench_rets, t0, windows.estimation)
    alpha, beta = ols_alpha_beta(est_b, est)

    ev_t = _slice_window(target_rets, t0, windows.event)
    ev_b = _slice_window(bench_rets, t0, windows.event)
    fitted = alpha + beta * ev_b
    ar = ev_t - fitted
    return ar, alpha, beta


def run_event_study(
    prices: pd.DataFrame,
    events: pd.DataFrame,
    symbol: str,
    bench_prices: Optional[pd.DataFrame] = None,
    cfg: Optional[ModelCfg] = None,
    windows: Optional[Windows] = None,
) -> AggregateResult:
    cfg = cfg or ModelCfg()
    windows = windows or Windows()

    sym_df = ensure_symbol_frame(prices, symbol)
    sym_ret = to_returns(sym_df["close"]).rename("ret")

    bench_ret = None
    if cfg.benchmark and bench_prices is not None and symbol != cfg.benchmark:
        bdf = ensure_symbol_frame(bench_prices, cfg.benchmark)
        bench_ret = to_returns(bdf["close"]).rename("bench_ret")

    per_event: List[EventResult] = []

    for _, row in events.iterrows():
        if row.symbol != symbol:
            continue
        t0: pd.Timestamp = pd.to_datetime(row.ts_utc, utc=True)

        ar, alpha, beta = _market_model_ar(sym_ret, bench_ret, t0, windows)
        car = ar.cumsum()

        # Bootstrap CI for CAR over the full event window (optional)
        ci = (np.nan, np.nan)
        if cfg.use_bootstrap:
            full_len = len(ar.dropna())
            est_series = _slice_window(sym_ret, t0, windows.estimation).dropna()
            if full_len > 3 and len(est_series) > full_len + 10:
                low, high = bootstrap_car_ci(est_series, full_len, n_iter=cfg.n_boot)
                ci = (low, high)

        per_event.append(
            EventResult(
                event_id=str(row.event_id),
                symbol=symbol,
                t0=t0,
                ar=ar,
                car=car,
                alpha=float(alpha),
                beta=float(beta),
                car_ci=(float(ci[0]) if pd.notna(ci[0]) else np.nan,
                        float(ci[1]) if pd.notna(ci[1]) else np.nan),
            )
        )

    if not per_event:
        raise ValueError(f"No events for {symbol}")

    # Align AR by relative hour across events
    aligned_ar = pd.concat(
        [e.ar.reset_index(drop=True).rename(e.event_id) for e in per_event],
        axis=1,
    )
    mean_ar = aligned_ar.mean(axis=1)
    mean_ar.index = pd.RangeIndex(
        start=windows.event[0], stop=windows.event[1] + 1, step=1
    )
    mean_car = mean_ar.cumsum()

    # Aggregate CI from dispersion of final CARs across events
    final_cars = [e.car.dropna().iloc[-1] if len(e.car.dropna()) else np.nan for e in per_event]
    final_cars = [x for x in final_cars if pd.notna(x)]
    if len(final_cars) >= 5:
        agg_low, agg_high = np.nanpercentile(final_cars, [2.5, 97.5])
    else:
        agg_low, agg_high = (np.nan, np.nan)

    return AggregateResult(
        mean_ar=mean_ar,
        mean_car=mean_car,
        car_ci=(float(agg_low), float(agg_high)),
        per_event=per_event,
    )