# services/coingecko_client.py
import time
import logging
import requests  # keep as module import so tests can monkeypatch requests.get

log = logging.getLogger("coingecko")

COINGECKO_SIMPLE_PRICE = "https://api.coingecko.com/api/v3/simple/price"


def get_prices(ids, vs_currency: str = "usd", timeout: int = 10) -> dict:
    """
    Fetch prices via CoinGecko /simple/price.

    - Accepts a list/tuple or comma-separated string of ids.
    - Returns {id: {vs_currency: price}}
    - Retries once on HTTP 429, honoring Retry-After header (seconds).
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
        retry_after = resp.headers.get("Retry-After", "0")
        try:
            delay = max(0.0, float(retry_after))
        except ValueError:
            delay = 0.0
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
