# parsers/__init__.py
# Each parser receives an uploaded file object and returns
# a list of trade dicts normalised to the Trades_Ledger schema.
#
# Required fields per trade dict:
#   trade_date, broker, ticker, action (BUY|SELL),
#   shares, price_local, ccy, commission
#
# Optional: settle_date, notes

from parsers.schwab  import parse_schwab
from parsers.ibkr    import parse_ibkr
from parsers.futu    import parse_futu
from parsers.moomoo  import parse_moomoo

PARSER_MAP = {
    "Schwab": parse_schwab,
    "IBKR":   parse_ibkr,
    "Futu":   parse_futu,
    "Moomoo": parse_moomoo,
}
