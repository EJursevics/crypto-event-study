from __future__ import annotations
import datetime as dt
from typing import Iterable, Optional

import numpy as np
import pandas as pd
import yfinance as yf


def _normalize_datetime_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure there is a lowercase 'datetime' column as UTC tz-aware.
    Handles yfinance variants: 'Date', 'Datetime', unnamed index after reset, etc.
    """
    # common cases after reset_index()
    for cand in ["datetime", "Datetime", "date", "Date"]:
        if cand in df.columns:
            df = df.rename(columns={cand: "datetime"})
            break
    else:
        # sometimes reset_index creates a column literally named 'index'
        if "index" in df.columns:
            df = df.rename(columns={"index": "datetime"})
        else:
            # last resort: assume first column is the timestamp
            first_col = df.columns[0]
            df = df.rename(columns={first_col: "datetime"})

    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    return df


def fetch_prices(
    symbols: Iterable[str],
    start: Optional[str | dt.datetime] = None,
    end: Optional[str | dt.datetime] = None,
    interval: str = "1h",
    auto_adjust: bool = True,
) -> pd.DataFrame:
    """
    Fetch OHLCV for multiple symbols as a tidy DataFrame.

    Returns columns: [symbol, datetime(index UTC), open, high, low, close, volume]
    """
    symbols = list(symbols)
    if start is None:
        start = (pd.Timestamp.utcnow() - pd.Timedelta(days=365 * 2)).strftime("%Y-%m-%d")
    if end is None:
        end = pd.Timestamp.utcnow().strftime("%Y-%m-%d")

    # --- choose query style based on interval constraints ---
    dl_kwargs = dict(
        tickers=symbols,
        auto_adjust=auto_adjust,
        group_by="ticker",
        threads=True,
        progress=False,
        interval=interval,
    )

    # 1h bars: Yahoo only serves about 730 days; use 720d for safety
    if interval.lower() in ("1h", "60m", "60min"):
        dl_kwargs.update(period="720d")
        # ignore start/end for 1h; 'period' is safer and simpler
        dl_kwargs.pop("start", None)
        dl_kwargs.pop("end", None)
    else:
        # daily or other intervals: keep start/end logic
        if start is None:
            start = (pd.Timestamp.utcnow() - pd.Timedelta(days=365 * 2)).strftime("%Y-%m-%d")
        if end is None:
            end = pd.Timestamp.utcnow().strftime("%Y-%m-%d")
        dl_kwargs.update(start=start, end=end)

    df = yf.download(**dl_kwargs)

    def _cleanup_cols(cols):
        return [str(c).strip().lower().replace(" ", "_") for c in cols]

    if isinstance(df.columns, pd.MultiIndex):
        # Multi-ticker shape
        frames = []
        for sym in symbols:
            if sym not in df.columns.levels[0]:
                continue
            sub = df[sym].copy()
            sub.columns = _cleanup_cols(sub.columns)
            sub = sub.reset_index()
            sub = _normalize_datetime_column(sub)
            sub["symbol"] = sym
            frames.append(sub)
        if not frames:
            raise ValueError("No data returned for requested symbols.")
        out = pd.concat(frames, ignore_index=True)
    else:
        # Single-ticker shape
        out = df.copy().reset_index()
        out.columns = _cleanup_cols(out.columns)
        out = _normalize_datetime_column(out)
        out["symbol"] = symbols[0]

    # prefer adjusted if present
    if "adj_close" in out.columns and "close" in out.columns:
        out["close"] = out["adj_close"]

    # keep tidy columns only
    keep = ["symbol", "datetime", "open", "high", "low", "close", "volume"]
    out = out[[c for c in keep if c in out.columns]]

    # drop rows with missing close, sort, set UTC index
    out = (
        out.dropna(subset=["close"])
           .sort_values(["symbol", "datetime"])
           .reset_index(drop=True)
           .set_index("datetime")
           .sort_index()
    )
    if out.index.tz is None:
        out.index = out.index.tz_localize("UTC")

    if out.empty:
        raise ValueError(f"No price data returned (interval='{interval}'). "
                         f"Try a shorter lookback or a coarser interval (e.g., '2h','4h','1d').")
    return out


def to_returns(prices: pd.Series) -> pd.Series:
    """Hourly log returns from a price series."""
    return np.log(prices).diff().dropna()


def ensure_symbol_frame(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Filter to one symbol and ensure required columns exist."""
    if "symbol" not in df.columns:
        raise ValueError("Input prices DataFrame must have a 'symbol' column.")
    sub = df[df["symbol"] == symbol].copy()
    need = {"open", "high", "low", "close"}
    missing = need - set(sub.columns)
    if missing:
        raise ValueError(f"Missing columns for {symbol}: {missing}")
    return sub
