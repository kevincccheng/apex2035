# parsers/schwab.py — Schwab brokerage activity CSV parser
import io
import pandas as pd
from dateutil.parser import parse as parse_date


def parse_schwab(file) -> list[dict]:
    """
    Parses a Schwab 'Transactions' CSV export.
    Schwab format has a header section then a table starting with 'Date'.
    """
    content = file.read().decode("utf-8", errors="replace")
    trades = []

    # Find the data table — skip Schwab's preamble rows
    lines = content.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if line.startswith('"Date"') or line.startswith("Date"):
            header_idx = i
            break

    if header_idx is None:
        raise ValueError("Could not find data table in Schwab CSV. "
                         "Please export 'Transactions' from the History tab.")

    data_str = "\n".join(lines[header_idx:])
    df = pd.read_csv(io.StringIO(data_str))
    df.columns = [c.strip().strip('"') for c in df.columns]

    # Schwab columns: Date, Action, Symbol, Description, Quantity, Price, Fees & Comm, Amount
    action_map = {
        "Buy":             "BUY",
        "Sell":            "SELL",
        "Reinvest Shares": "BUY",
        "Stock Split":     None,   # skip
        "Dividend":        None,   # skip
        "Credit Interest": None,
        "MoneyLink Transfer": None,
        "Wire Funds":      None,
    }

    for _, row in df.iterrows():
        raw_action = str(row.get("Action", "")).strip()
        action = action_map.get(raw_action)
        if action is None:
            continue

        symbol = str(row.get("Symbol", "")).strip()
        if not symbol or symbol.lower() == "nan":
            continue

        try:
            qty   = abs(float(str(row.get("Quantity", 0)).replace(",", "")))
            price = abs(float(str(row.get("Price", 0)).replace("$", "").replace(",", "")))
            comm  = abs(float(str(row.get("Fees & Comm", 0)).replace("$", "").replace(",", "") or 0))
            date  = parse_date(str(row.get("Date", ""))).strftime("%Y-%m-%d")
        except Exception:
            continue

        if qty == 0 or price == 0:
            continue

        trades.append({
            "trade_date":   date,
            "settle_date":  "",
            "broker":       "Schwab",
            "ticker":       symbol,
            "action":       action,
            "shares":       qty,
            "price_local":  price,
            "ccy":          "USD",
            "commission":   comm,
            "fx_rate":      1.0,
            "gross_usd":    round(qty * price, 2),
            "notes":        str(row.get("Description", "")),
        })

    return trades
