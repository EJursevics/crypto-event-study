param([string]$EventsCsv = "data_raw/events_sample.csv")

# Stop on first error
$ErrorActionPreference = "Stop"

# Ensure venv exists and activate
if (-not (Test-Path .\.venv\Scripts\Activate.ps1)) { python -m venv .venv }
.\.venv\Scripts\Activate.ps1

# Install project deps
python -m pip install --upgrade pip
pip install -e .

# Ensure reports dirs
New-Item -ItemType Directory -Force -Path reports | Out-Null
New-Item -ItemType Directory -Force -Path reports\figures | Out-Null

# Env for batch mode custom events CSV
$env:RUN_MODE = "batch"
$env:EVENTS_CSV = $EventsCsv

# Convert Jupytext .py => .ipynb
python -m jupytext --to ipynb notebooks/01_event_study.py -o reports/01_event_study.ipynb

# Execute notebook with our venv kernel (installed earlier)
python -m papermill reports/01_event_study.ipynb reports/01_event_study_executed.ipynb -k "crypto-venv"

# Convert executed notebook to HTML (place output directly in reports/)
python -m nbconvert --to html --output-dir reports --output event_study_report.html reports/01_event_study_executed.ipynb

Write-Host "Done -> reports/event_study_report.html"
