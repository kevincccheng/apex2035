# parsers/futu.py — Futu/Moomoo HK brokerage CSV parser
import io
import pandas as pd
from dateutil.parser import parse as parse_date


def parse_futu(file) -> list[dict]:
    """
    Parses Futu HK 'Transaction History' CSV export.
    Futu CSV columns (English export):
    Transaction Time | Stock Code | Stock Name | Direction | Quantity | Price | Amount | Fee | Currency
    """
    content = file.read().decode("utf-8", errors="replace")
    trades = []

    try:
        df = pd.read_csv(io.StringIO(content))
    except Exception as e:
        raise ValueError(f"Could not parse Futu CSV: {e}")

    df.columns = [c.strip() for c in df.columns]

    # Flexible column name matching
    col_map = {}
    for col in df.columns:
        cl = col.lower()
        if "time" in cl or "date" in cl:
            col_map["date"] = col
        elif "code" in cl or "ticker" in cl or "symbol" in cl:
            col_map["ticker"] = col
        elif "direction" in cl or "side" in cl or "type" in cl:
            col_map["action"] = col
        elif "qty" in cl or "quantity" in cl or "volume" in cl:
            col_map["qty"] = col
        elif "price" in cl:
            col_map["price"] = col
        elif "fee" in cl or "commission" in cl:
            col_map["fee"] = col
        elif "currency" in cl or "ccy" in cl:
            col_map["ccy"] = col

    for _, row in df.iterrows():
        try:
            raw_action = str(row.get(col_map.get("action", ""), "")).strip().upper()
            if "BUY" in raw_action or "B" == raw_action:
                action = "BUY"
            elif "SELL" in raw_action or "S" == raw_action:
                action = "SELL"
            else:
                continue

            raw_ticker = str(row.get(col_map.get("ticker", ""), "")).strip()
            ccy        = str(row.get(col_map.get("ccy", ""), "HKD")).strip()

            # Normalise HK stock code to format "0700.HK"
            if ccy == "HKD" and not raw_ticker.endswith(".HK"):
                try:
                    raw_ticker = str(int(raw_ticker)).zfill(4) + ".HK"
                except Exception:
                    pass

            qty   = abs(float(str(row.get(col_map.get("qty", ""), 0)).replace(",", "")))
            price = abs(float(str(row.get(col_map.get("price", ""), 0)).replace(",", "")))
            fee   = abs(float(str(row.get(col_map.get("fee", ""), 0)).replace(",", "") or 0))
            date  = parse_date(str(row.get(col_map.get("date", ""), ""))).strftime("%Y-%m-%d")

        except Exception:
            continue

        if qty == 0 or price == 0:
            continue

        trades.append({
            "trade_date":  date,
            "settle_date": "",
            "broker":      "Futu",
            "ticker":      raw_ticker,
            "action":      action,
            "shares":      qty,
            "price_local": price,
            "ccy":         ccy,
            "commission":  fee,
            "fx_rate":     0,
            "gross_usd":   0,
            "notes":       "",
        })

    return trades
