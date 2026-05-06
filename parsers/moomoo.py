# parsers/moomoo.py — Moomoo activity CSV parser
# Moomoo export is very similar to Futu but with slightly different column names
import io
import pandas as pd
from dateutil.parser import parse as parse_date


def parse_moomoo(file) -> list[dict]:
    """
    Parses Moomoo 'Today's Orders' or 'Transaction Details' CSV.
    Typical columns: Date | Symbol | Name | Side | Qty | Avg Price | Amount | Fee | Currency
    """
    content = file.read().decode("utf-8", errors="replace")
    trades = []

    try:
        df = pd.read_csv(io.StringIO(content))
    except Exception as e:
        raise ValueError(f"Could not parse Moomoo CSV: {e}")

    df.columns = [c.strip() for c in df.columns]

    col_map = {}
    for col in df.columns:
        cl = col.lower()
        if "date" in cl or "time" in cl:
            col_map.setdefault("date", col)
        elif "symbol" in cl or "ticker" in cl or "code" in cl:
            col_map.setdefault("ticker", col)
        elif "side" in cl or "direction" in cl or "type" in cl or "action" in cl:
            col_map.setdefault("action", col)
        elif "qty" in cl or "quantity" in cl or "filled" in cl or "shares" in cl:
            col_map.setdefault("qty", col)
        elif "avg" in cl and "price" in cl:
            col_map.setdefault("price", col)
        elif "price" in cl and "price" not in col_map:
            col_map.setdefault("price", col)
        elif "fee" in cl or "commission" in cl:
            col_map.setdefault("fee", col)
        elif "currency" in cl or "ccy" in cl:
            col_map.setdefault("ccy", col)

    for _, row in df.iterrows():
        try:
            raw_action = str(row.get(col_map.get("action", ""), "")).strip().upper()
            if "BUY" in raw_action:
                action = "BUY"
            elif "SELL" in raw_action:
                action = "SELL"
            else:
                continue

            raw_ticker = str(row.get(col_map.get("ticker", ""), "")).strip()
            ccy        = str(row.get(col_map.get("ccy", ""), "USD")).strip()

            # Normalise HK codes
            if ccy == "HKD" and not raw_ticker.endswith(".HK"):
                try:
                    raw_ticker = str(int(raw_ticker)).zfill(4) + ".HK"
                except Exception:
                    pass

            qty   = abs(float(str(row.get(col_map.get("qty", ""), 0)).replace(",", "")))
            price = abs(float(str(row.get(col_map.get("price", ""), 0)).replace(",", "").replace("$", "")))
            fee   = abs(float(str(row.get(col_map.get("fee", ""), 0) or 0)))
            date  = parse_date(str(row.get(col_map.get("date", ""), ""))).strftime("%Y-%m-%d")

        except Exception:
            continue

        if qty == 0 or price == 0:
            continue

        fx   = 0
        gusd = 0
        if ccy == "USD":
            fx   = 1.0
            gusd = round(qty * price, 2)

        trades.append({
            "trade_date":  date,
            "settle_date": "",
            "broker":      "Moomoo",
            "ticker":      raw_ticker,
            "action":      action,
            "shares":      qty,
            "price_local": price,
            "ccy":         ccy,
            "commission":  fee,
            "fx_rate":     fx,
            "gross_usd":   gusd,
            "notes":       "",
        })

    return trades
