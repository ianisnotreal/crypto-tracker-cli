from services.coingecko_client import get_prices
from core.portfolio import load_portfolio, valuate

def main():
    portfolio = load_portfolio()
    ids = [p["id"] for p in portfolio["positions"]]
    prices = get_prices(ids)
    report = valuate(portfolio, prices, "usd")

    for pos in report["positions"]:
        print(f"{pos['symbol'].upper():<6} ${pos['price']:>10.2f}  P/L: {pos['pnl']:>10.2f} ({pos['pnl_pct']:>6.2f}%)")
    print(f"Total Value: ${report['total_value']:,.2f}")

if __name__ == "__main__":
    main()