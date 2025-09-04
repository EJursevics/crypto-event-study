from __future__ import annotations
import pandas as pd

REQUIRED_COLS = [
    "event_id", "ts_utc", "symbol", "category", "headline", "source", "direction"
]

def load_events_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Events CSV missing columns: {missing}")

    df["ts_utc"] = pd.to_datetime(df["ts_utc"], utc=True)
    df = df.sort_values("ts_utc").reset_index(drop=True)

    # normalize direction
    df["direction"] = df["direction"].str.lower().map({
        "pos": "pos", "positive": "pos",
        "neg": "neg", "negative": "neg",
        "neu": "neutral", "neutral": "neutral"
    }).fillna("neutral")

    return df