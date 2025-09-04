# %% [markdown]
# # Crypto Event Study
# Author: Emīls Jurševics
# -
# Purpose: simply show the short term price impact of a few selected crypto events.
# Runs headless via run.ps1 -> report in /reports.

# %% [markdown]
# ## 0) Imports & Config

# %%
import os
import math
import numpy as np
import pandas as pd

from core.data import fetch_prices, ensure_symbol_frame, to_returns
from core.events import load_events_csv
from core.event_study import run_event_study, ModelCfg, Windows
from core.plots import plot_mean_ar, plot_mean_car, plot_price_with_event

RUN_MODE = os.environ.get("RUN_MODE", "interactive")
DATA_EVENTS = os.environ.get("EVENTS_CSV", "data_raw/events_sample.csv")

# focus on BTC, ETH, SOL, DOGE
SYMBOLS = ["BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD"]
BENCHMARK = "BTC-USD"  # alts vs BTC; BTC benchmarked vs itself (mean-adjusted)
INTERVAL = "1h"        # if Yahoo chokes, switch to "2h" or "1d"

# event study window setup
WINS = Windows(estimation=(-240, -24), event=(-24, 24))
CFG = ModelCfg(benchmark=BENCHMARK, use_bootstrap=True, n_boot=1000)

# figs land in reports/figures
FIGDIR = "reports/figures"
os.makedirs(FIGDIR, exist_ok=True)

# CI pretty-printer (handles NaN / missing cases)
def _format_ci(ci) -> str:
    try:
        if ci is None:
            return "CI not available (few events)"
        lo, hi = ci
        if any(pd.isna([lo, hi])):
            return "CI not available (few events)"
        return f"{float(lo):.4f} to {float(hi):.4f}"
    except Exception:
        return "CI not available (few events)"

# %% [markdown]
# ## 1) Load data

# %%
events = load_events_csv(DATA_EVENTS)
print("Events loaded:", len(events))

prices = fetch_prices(SYMBOLS, interval=INTERVAL)
print("Prices shape:", prices.shape)

# if Yahoo returns nothing, stop and hint at using coarser interval
if prices.empty:
    raise RuntimeError(
        f"No data fetched for interval={INTERVAL}. "
        "Try INTERVAL='2h' or '1d' instead."
    )

# %% [markdown]
# ## 2) Run event study per symbol

# %%
reports = {}
bench_prices = prices  # kept whole; filtering done inside run_event_study

for sym in SYMBOLS:
    evs_sym = events[events.symbol == sym]
    if evs_sym.empty:
        print(f"{sym}: no events, skipping")
        continue

    agg = run_event_study(
        prices,
        evs_sym,
        symbol=sym,
        bench_prices=bench_prices,
        cfg=CFG,
        windows=WINS,
    )
    reports[sym] = agg
    print(sym, "events:", len(agg.per_event))

# %% [markdown]
# ## 3) Save figures

# %%
for sym, agg in reports.items():
    # if no rows for this symbol, skip plotting
    if "symbol" in prices.columns:
        sym_rows = (prices["symbol"] == sym).sum()
        if sym_rows == 0:
            print(f"{sym}: no price rows; skip plots")
            continue

    # AR and CAR plots
    plot_mean_ar(agg.mean_ar, outdir=FIGDIR, title=f"{sym} - Mean AR")
    plot_mean_car(agg.mean_car, ci=agg.car_ci, outdir=FIGDIR, title=f"{sym} - Mean CAR")

    # per-event price traces
    sym_df = ensure_symbol_frame(prices, sym)
    for ev in agg.per_event:
        plot_price_with_event(
            sym_df["close"], ev.t0, outdir=FIGDIR, name=f"{sym}_{ev.event_id}_price.png"
        )

# %% [markdown]
# ## 4) Summary

# %%
lines = []
summary_rows = []
for sym, agg in reports.items():
    final = float(agg.mean_car.iloc[-1])
    ci_str = _format_ci(agg.car_ci)
    n_ev = len(agg.per_event)
    summary_rows.append({"symbol": sym, "final_car": final, "n": n_ev, "ci_str": ci_str})

    lines.append(
        f"- **{sym}**: Mean CAR at +{WINS.event[1]}h = {final:.4f} "
        f"(95% agg CI: {ci_str}) - n={n_ev} events"
    )

summary_text = "\n".join(lines) if lines else "No results. Check events CSV."
print(summary_text)

# %% [markdown]
# ## 5) Interpretation (analyst notes)

# %%
interp_lines = []

if not summary_rows:
    interp_lines.append(
        "No interpretable results. Maybe the event file is out of range or timestamps off."
    )
else:
    df_summary = pd.DataFrame(summary_rows).sort_values("final_car", ascending=False)

    # quick rank by impact
    rank_list = [f"{r.symbol} ({r.final_car:+.4f}, n={r.n})" for r in df_summary.itertuples(index=False)]
    interp_lines.append("**Ranking by +{h}h mean CAR:** ".format(h=WINS.event[1]) + ", ".join(rank_list))

    # warn if sample sizes tiny
    small = df_summary[df_summary["n"] < 5]
    if not small.empty:
        syms = ", ".join(small["symbol"])
        interp_lines.append(f"Caution: very small sample sizes for {syms}")

    # biggest mover
    pos = df_summary[df_summary["final_car"] > 0]
    neg = df_summary[df_summary["final_car"] < 0]
    if not pos.empty:
        top = pos.iloc[0]
        interp_lines.append(f"Largest positive reaction: {top.symbol} (CAR≈{top.final_car:+.4f})")
    if not neg.empty:
        worst = neg.iloc[-1]
        interp_lines.append(f"Negative reaction: {worst.symbol} (CAR≈{worst.final_car:+.4f})")

    # reminders
    interp_lines.append(
        f"Method: alts vs BTC benchmark; BTC itself uses mean-adjusted returns. "
        f"Window {WINS.estimation}h (estimation), {WINS.event}h (event)."
    )
    interp_lines.append(
        "Use case: quick check if events leave a trace in prices; not a full econometric model."
    )

interpretation_text = "\n\n".join(interp_lines) if interp_lines else "-"
print(interpretation_text)

# %% [markdown]
# ## 6) Repro notes
# - Benchmark: BTC for alts; BTC mean-adjusted for itself
# - Returns: hourly log returns
# - Estimation window: -240..-24h
# - Event window: -24..24h
# - Significance: bootstrap CI when feasible; otherwise simple spread
# - Limits: hourly data only, overlapping/confounded events, small samples