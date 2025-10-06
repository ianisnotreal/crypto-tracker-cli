import json
import os

PORTFOLIO_PATH = os.path.expanduser("~/.crypto_tracker/portfolio.json")

def load_portfolio():
    """Load or initialize the portfolio."""
    if not os.path.exists(PORTFOLIO_PATH):
        return {"positions": []}
    with open(PORTFOLIO_PATH) as f:
        return json.load(f)

def valuate(portfolio, prices, vs_currency):
    """Compute total and per-asset value + P/L."""
    total_value = 0
    report = []
    for pos in portfolio["positions"]:
        pid = pos["id"]
        qty = pos["qty"]
        cost = pos["cost_basis"]
        price = prices.get(pid, {}).get(vs_currency, 0)
        value = qty * price
        pnl = value - (qty * cost)
        pnl_pct = (pnl / (qty * cost)) * 100 if cost else 0
        report.append({
            "symbol": pos["symbol"],
            "price": price,
            "value": value,
            "pnl": pnl,
            "pnl_pct": pnl_pct
        })
        total_value += value
    return {"positions": report, "total_value": total_value}