# services/coingecko_client.py
import time
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import requests  # keep module import so tests can monkeypatch requests.get

log = logging.getLogger("coingecko")

COINGECKO_SIMPLE_PRICE = "https://api.coingecko.com/api/v3/simple/price"


def _parse_retry_after(value: str | None) -> float:
    """
    Parse an HTTP Retry-After header value.

    Accepts either:
      - a number of seconds (e.g., "5")
      - an HTTP-date (RFC 7231 / RFC 1123), e.g., "Wed, 21 Oct 2015 07:28:00 GMT"

    Returns a non-negative float number of seconds until retry.
    """
    if not value:
        return 0.0
    value = value.strip()
    # Numeric seconds
    try:
        secs = float(value)
        return max(0.0, secs)
    except ValueError:
        pass

    # HTTP-date
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = (dt - now).total_seconds()
        return max(0.0, float(delta))
    except Exception:
        return 0.0


def get_prices(ids, vs_currency: str = "usd", timeout: int = 10) -> dict:
    """
    Fetch prices via CoinGecko /simple/price.

    - Accepts a list/tuple or comma-separated string of ids.
    - Returns {id: {vs_currency: price}}
    - Retries once on HTTP 429, honoring Retry-After header (seconds or HTTP-date).
    """
    if isinstance(ids, (list, tuple)):
        ids_param = ",".join(str(x) for x in ids)
    else:
        ids_param = str(ids)

    params = {
        "ids": ids_param,
        "vs_currencies": vs_currency,
        "include_last_updated_at": "false",
    }

    t0 = time.perf_counter()
    resp = requests.get(COINGECKO_SIMPLE_PRICE, params=params, timeout=timeout)

    if resp.status_code == 429:
        delay = _parse_retry_after(resp.headers.get("Retry-After"))
        if delay > 0:
            time.sleep(delay)
        # retry once
        resp = requests.get(COINGECKO_SIMPLE_PRICE, params=params, timeout=timeout)

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    status = resp.status_code

    if status != 200:
        log.warning("Fetch failed in %.1f ms (status %s).", elapsed_ms, status)
        resp.raise_for_status()

    data = resp.json()
    log.info("Fetched %d ids in %.1f ms (status %s).", len(ids_param.split(",")), elapsed_ms, status)
    return data
