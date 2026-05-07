# Project Apex 2035 — Claude Code Context

## What this is
Streamlit portfolio dashboard for Kevin. Tracks ~71 positions across 8 brokers.
Live app: https://p6n6cb7ydd6py4j4jciqpz.streamlit.app/

## Key facts
- All position data lives in **config.py** → `INITIAL_POSITIONS`
- After ANY edit to config.py, re-seed the Google Sheet (see command below)
- GitHub: github.com/kevincccheng/apex2035
- Google Sheet ID: 1M7zNVjhI0b5NmQDNHvOso_nHML1SlBVR7lWj0zPzApg
- Service account: apex2035-sheets@apex2035.iam.gserviceaccount.com

## Re-seed command (run after editing config.py)
```bash
cd C:/Users/kevin/projects/apex2035
PYTHONIOENCODING=utf-8 python seed_sheet.py --creds service_account.json --sheet-id 1M7zNVjhI0b5NmQDNHvOso_nHML1SlBVR7lWj0zPzApg
```

## Common tasks

### Add a new stock position
Edit `config.py` → add to `INITIAL_POSITIONS` → re-seed → push to GitHub

### Add a short call option
```python
{
    "ticker": "TICKER-C{STRIKE}-{MON}{YY}",  # e.g. AAPL-C200-JUN26
    "name": "Short Call TICKER ${STRIKE} {Mon}-{YEAR}",
    "region": "US", "sector": "Options — Short Call", "barbell_class": "TACTICAL",
    "ccy": "USD",
    "brokers": [{"broker": "IBKR", "shares": -100, "avg_cost_local": PREMIUM_PER_SHARE}],
}
```
Then add to TICKER_MAP: `"TICKER-C{STRIKE}-{MON}{YY}": "TICKER{YY}{MM}{DD}C{STRIKE_8DIGITS}"`

### Remove an expired option
Delete the position from `INITIAL_POSITIONS` and its TICKER_MAP entry → re-seed → push

### Fix cost basis
Edit `avg_cost_local` in the relevant broker dict in `INITIAL_POSITIONS` → re-seed

## Architecture
- `app.py` — Streamlit UI, 6 tabs
- `config.py` — all position data + compliance rules + broker list
- `core/engine.py` — P&L calc; note: `brokers_list` column carries full broker detail
- `core/prices.py` — yfinance prices; FX uses USDHKD=X (~7.83) as divisor; timestamps in HKT
- `core/sheets.py` — Google Sheets via gspread; reads `st.secrets["gcp_service_account"]`
- `seed_sheet.py` — one-command re-seed from config.py

## Secrets (never commit)
- `service_account.json` — Google service account key
- `.streamlit/secrets.toml` — same credentials in TOML format for Streamlit
- Both are in .gitignore
