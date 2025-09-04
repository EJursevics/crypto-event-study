import pandas as pd
import numpy as np
from datetime import timezone

from core.event_study import run_event_study, ModelCfg, Windows


def _synth_prices(symbol: str = "ALT-USD", hours: int = 400, jump_at: int = 300, jump_size: float = 0.05):
    idx = pd.date_range("2024-01-01", periods=hours, freq="h", tz="UTC")
    # random walk
    rets = np.random.normal(0, 0.002, size=hours)
    rets[jump_at] += jump_size
    price = 100 * np.exp(np.cumsum(rets))
    df = pd.DataFrame({
        "symbol": symbol,
        "open": price,
        "high": price,
        "low": price,
        "close": price,
        "volume": 1.0,
    }, index=idx)
    return df


def test_event_jump_detected():
    prices = _synth_prices()
    events = pd.DataFrame({
        "event_id": ["test"],
        "ts_utc": [prices.index[300]],
        "symbol": ["ALT-USD"],
        "category": ["Test"],
        "headline": ["Synthetic jump"],
        "source": ["unit"],
        "direction": ["pos"],
    })

    agg = run_event_study(prices, events, symbol="ALT-USD", bench_prices=None,
                          cfg=ModelCfg(benchmark=None, use_bootstrap=False),
                          windows=Windows(estimation=(-240,-24), event=(-24,24)))

    assert agg.mean_car.iloc[-1] > 0.02  # CAR should capture the jump
    assert len(agg.per_event) == 1