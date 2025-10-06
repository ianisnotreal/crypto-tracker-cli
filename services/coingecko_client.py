import requests
import time

API_URL = "https://api.coingecko.com/api/v3/simple/price"

def get_prices(ids, vs_currency="usd"):
    params = {"ids": ",".join(ids), "vs_currencies": vs_currency}
    for attempt in range(3):
        try:
            r = requests.get(API_URL, params=params, timeout=(3, 10))
            if r.status_code == 429:
                retry_after = int(r.headers.get("Retry-After", "1"))
                time.sleep(retry_after)
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            time.sleep(2 ** attempt)
    raise RuntimeError("Price fetch failed after retries.")