# services/html_fallback.py
from __future__ import annotations
import re
from typing import Dict, Sequence, Any
import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# Map common CoinGecko ids -> Yahoo Finance symbols (USD pairs)
YF_SYMBOLS = {
    "bitcoin": "BTC-USD",
    "ethereum": "ETH-USD",
    "solana": "SOL-USD",
    "dogecoin": "DOGE-USD",
    "cardano": "ADA-USD",
    # extend as needed...
}

# Regexes that reliably hit Yahoo's embedded JSON
RE_PRICE_1 = re.compile(r'"regularMarketPrice"\s*:\s*\{"raw"\s*:\s*([0-9]+(?:\.[0-9]+)?)')
RE_PRICE_2 = re.compile(r'"currentPrice"\s*:\s*\{"raw"\s*:\s*([0-9]+(?:\.[0-9]+)?)')

def _fetch_yahoo_symbol(symbol: str, timeout: tuple[float, float] = (3.0, 10.0)) -> float | None:
    url = f"https://finance.yahoo.com/quote/{symbol}/"
    r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
    r.raise_for_status()
    html = r.text
    m = RE_PRICE_1.search(html) or RE_PRICE_2.search(html)
    if not m:
        return None
    return float(m.group(1))

def get_prices_html(ids: Sequence[str]) -> Dict[str, Any]:
    """
    HTML fallback prices for a subset of coins (USD only).
    Returns: {"bitcoin": {"usd": 12345.67}, ...} for any ids we could fetch.
    """
    out: Dict[str, Any] = {}
    for cid in ids:
        sym = YF_SYMBOLS.get(cid.lower())
        if not sym:
            continue
        try:
            px = _fetch_yahoo_symbol(sym)
            if px is not None:
                out[cid] = {"usd": px}
        except Exception:
            # swallow per-id; this is a best-effort fallback
            pass
    return out
