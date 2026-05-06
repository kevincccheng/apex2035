# Project Apex 2035 — Setup Guide

## Prerequisites
- Python 3.10+
- A Google account
- Git (for deployment)

---

## Step 1: Install dependencies

```bash
cd apex2035
pip install -r requirements.txt
```

---

## Step 2: Set up Google Cloud service account

This gives the app permission to read/write your Google Sheet.

1. Go to https://console.cloud.google.com
2. Create a new project called `apex2035`
3. Enable these two APIs:
   - **Google Sheets API**
   - **Google Drive API**
4. Go to **IAM & Admin → Service Accounts → Create Service Account**
   - Name: `apex2035-bot`
   - Role: `Editor`
5. Click the service account → **Keys → Add Key → JSON**
6. Download the JSON file — save it as `service_account.json` in this folder
   (DO NOT commit this file to Git — it's in .gitignore)

---

## Step 3: Create and seed the Google Sheet

```bash
python seed_sheet.py --creds service_account.json
```

This will:
- Create a Google Sheet called `Apex2035_Master`
- Write all 70 current positions to `Holdings_Master`
- Print the sheet URL

**Important:** Open the printed URL and share the sheet with your personal
Google account (so you can view it). The sheet is owned by the service account
by default.

---

## Step 4: Run locally

Create a file `.streamlit/secrets.toml` with your service account credentials:

```toml
[gcp_service_account]
type = "service_account"
project_id = "YOUR_PROJECT_ID"
private_key_id = "YOUR_KEY_ID"
private_key = "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n"
client_email = "apex2035-bot@YOUR_PROJECT.iam.gserviceaccount.com"
client_id = "YOUR_CLIENT_ID"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/apex2035-bot%40YOUR_PROJECT.iam.gserviceaccount.com"
```

(Copy all values from your downloaded `service_account.json`)

Then run:
```bash
streamlit run app.py
```

The app opens at http://localhost:8501

---

## Step 5: Deploy to Streamlit Community Cloud (free)

1. Push this folder to a **private** GitHub repository:
   ```bash
   git init
   git add .
   git commit -m "Initial Apex 2035 deploy"
   git remote add origin https://github.com/YOUR_USERNAME/apex2035.git
   git push -u origin main
   ```

2. Go to https://share.streamlit.io
3. Click **New app** → select your repo → `app.py`
4. Under **Advanced settings → Secrets**, paste the full contents of your
   `.streamlit/secrets.toml`
5. Click **Deploy**

Your dashboard is now live at `https://YOUR_APP.streamlit.app` — accessible
from phone or desktop.

---

## Weekly workflow (after setup)

### Option A: Manual trade entry (recommended for 1-3 trades)
1. Open the dashboard
2. Go to **Trade Entry** tab
3. Fill in broker, ticker, shares, price → Confirm
4. Done — positions update instantly

### Option B: CSV upload (for bulk reconciliation)
1. Export activity from broker:
   - **Schwab**: History → Export (Transactions CSV)
   - **IBKR**: Reports → Activity → CSV
   - **Futu**: Transaction History → Export CSV
   - **Moomoo**: Orders → Transaction Details → Export
2. Go to **Trade Entry** tab → Upload CSV
3. Review parsed trades → Import

### Option C: Tell an AI (Claude/Gemini)
If Claude has access to your Google Sheet via the Sheets API, you can say:
> "I bought 100 shares of Tencent at HKD 472 through IBKR today"
and Claude will write it directly to the Trades_Ledger sheet.

---

## Monthly workflow (legacy accounts)

For HSBC, BOC, Webull, Citi — upload the PDF statement when you get it.
These are flagged as "Legacy" in the Broker Recon tab with a lock icon.
Update the Google Sheet manually for these (Holdings_Master tab, find the
row, update total_shares and avg_cost_local).

---

## Upgrading to LSEG Workspace prices (optional, future)

In `config.py`, change:
```python
PRICE_SOURCE = "lseg"
```

Then in `core/prices.py`, implement `get_price_lseg()` using:
```python
import lseg.data as ld
ld.open_session(app_key="YOUR_APP_KEY")
```

The rest of the app requires zero changes.

---

## File structure

```
apex2035/
├── app.py                  ← Main Streamlit app (run this)
├── config.py               ← All positions, targets, rules
├── seed_sheet.py           ← One-time Google Sheet initializer
├── requirements.txt
├── SETUP.md                ← This file
├── .gitignore
├── .streamlit/
│   └── secrets.toml        ← Google credentials (never commit)
├── core/
│   ├── prices.py           ← yfinance price fetching
│   ├── sheets.py           ← Google Sheets read/write
│   └── engine.py           ← P&L, compliance, analytics
└── parsers/
    ├── __init__.py
    ├── schwab.py
    ├── ibkr.py
    ├── futu.py
    └── moomoo.py
```
