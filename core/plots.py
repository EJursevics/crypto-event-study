# core/plots.py
from __future__ import annotations
import os
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def _ensure_outdir(outdir: str) -> None:
    os.makedirs(outdir, exist_ok=True)


def _finalize(fig, ax, title: Optional[str]) -> None:
    if title:
        ax.set_title(title)
    ax.grid(True, alpha=0.25)


def plot_mean_ar(mean_ar: pd.Series, outdir: str, title: Optional[str] = None,
                 name: str | None = None, show: bool = True) -> str:
    """
    Plot mean Abnormal Return (AR) across events.
    Saves PNG and (optionally) shows for inline embedding in the notebook/HTML.
    """
    _ensure_outdir(outdir)
    if name is None:
        name = "mean_ar.png"

    rel_hours = np.arange(len(mean_ar)) - (len(mean_ar) // 2)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(rel_hours, mean_ar.values)
    ax.axvline(0, linestyle="--")
    ax.set_xlabel("Hours relative to event")
    ax.set_ylabel("Mean AR")
    _finalize(fig, ax, title)

    path = os.path.join(outdir, name)
    fig.savefig(path, dpi=120, bbox_inches="tight")
    if show:
        plt.show()
    plt.close(fig)
    return path


def plot_mean_car(mean_car: pd.Series, ci: Optional[Tuple[float, float]],
                  outdir: str, title: Optional[str] = None,
                  name: str | None = None, show: bool = True) -> str:
    """
    Plot mean Cumulative Abnormal Return (CAR) with optional 95% CI band (as two hlines if provided).
    """
    _ensure_outdir(outdir)
    if name is None:
        name = "mean_car.png"

    rel_hours = np.arange(len(mean_car)) - (len(mean_car) // 2)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(rel_hours, mean_car.values, label="Mean CAR")
    ax.axvline(0, linestyle="--")
    if ci is not None:
        lo, hi = ci
        if pd.notna(lo) and pd.notna(hi):
            ax.hlines([lo, hi], xmin=rel_hours.min(), xmax=rel_hours.max(), linestyles=":", label="95% CI")

    ax.set_xlabel("Hours relative to event")
    ax.set_ylabel("Mean CAR")
    _finalize(fig, ax, title)
    ax.legend(loc="best")

    path = os.path.join(outdir, name)
    fig.savefig(path, dpi=120, bbox_inches="tight")
    if show:
        plt.show()
    plt.close(fig)
    return path


def plot_price_with_event(price: pd.Series, t0: pd.Timestamp,
                          outdir: str, name: str = "price_event.png",
                          title: Optional[str] = None, hours: int = 48,
                          show: bool = True) -> str:
    """
    Plot price around a single event (±hours) and mark t0.
    """
    _ensure_outdir(outdir)

    if not isinstance(price.index, pd.DatetimeIndex):
        raise ValueError("`price` must be indexed by DatetimeIndex.")

    win = slice(t0 - pd.Timedelta(hours=hours), t0 + pd.Timedelta(hours=hours))
    s = price.loc[win].dropna()
    if title is None:
        title = f"Price around event @ {t0}"

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(s.index, s.values)
    ax.axvline(t0, linestyle="--")
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("Price")
    _finalize(fig, ax, title)

    path = os.path.join(outdir, name)
    fig.savefig(path, dpi=120, bbox_inches="tight")
    if show:
        plt.show()
    plt.close(fig)
    return path
