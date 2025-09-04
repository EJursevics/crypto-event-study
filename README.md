# Short Term Price Impact On Crypto Events Small Study

<p align="center">
  <img src="docs/hero.png" width="700">
</p>

### Author: Emīls Jurševics

---

## What this project is about

This project looks at how major events in crypto (like ETF approvals, hacks, or protocol upgrades) affect the market in the short term.  

My approach: pick a few coins (BTC, ETH, SOL, DOGE), pull historical price data, align it with events, and check whether the charts show meaningful reactions.  

The output is an **auto-generated HTML report** with plots, short summaries, and analysis notes. It’s not about predicting markets, but about applying a structured method to noisy price data.  

---

## Example Output

<p align="center">
  <img src="docs/example_plot.png" width="650">
</p>

- Abnormal return (AR) and cumulative abnormal return (CAR) plots for each coin  
- Price charts around the event with a marker showing the event date  
- Short text summaries with interpretation notes  

---

## How it works

1. **Events** – stored in `data_raw/events_sample.csv`  
   Format:  
   `event_id,ts_utc,symbol,category,headline,source,direction`

   Current sample includes:  
   - ETF Approval  
   - Bitcoin Halving  
   - Solana Outage  
   - Ethereum Upgrade  
   - Exchange Hack  
   - Memecoin Listing  

2. **Prices** – pulled with yfinance (hourly, ~2 years back)  
3. **Analysis** – returns estimated, AR and CAR calculated, compared around events  
4. **Plots** – mean AR, mean CAR, and per-event price impact visualized with Matplotlib  
5. **Report** – everything compiled into an HTML file inside `reports/`  

## Running it
Clone and install:
git clone https://github.com/EJursevics/crypto-event-study.git
cd crypto-event-study
python -m venv .venv
.venv\Scripts\activate
pip install -e .

Run the study (PowerShell):
.\run.ps1

This will:
1. Fetch prices
2. Run the event study
3. Save figures into reports/figures
4. Build reports/event_study_report.html


## What is happening here
- Pipeline from raw data -> analysis -> reporting  
- A classic finance method (event study) applied to crypto  
- Python, Pandas, yfinance, Matplotlib used for analysis and visualization  
- Structured project and automated reporting for reproducibility  

### This is a student project, but I tried to keep it clean and reproducible. The goal isn’t to predict markets, its to show how structured analysis can make sense of noisy crypto price action, and to learn more about both the process and crypto itself.