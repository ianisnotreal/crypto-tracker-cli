def fmt_currency(value: float, symbol: str = "$") -> str:
    return f"{symbol}{value:,.2f}"

def fmt_pct(value: float) -> str:
    return f"{value:+.2f}%"