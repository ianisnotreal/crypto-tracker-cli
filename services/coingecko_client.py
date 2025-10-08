# services/coingecko_client.py
from __future__ import annotations
import time, random
from typing import Sequence, Dict, Any, Optional
import requests
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

from utils.logging import get_logger

log = get_logger("coingecko")

API_URL = "https://api.coingecko.com/api/v3/simple/price"

# Resilience tuning
MAX_RETRIES = 5                 # total attempts (first try + 4 retries)
BASE_BACKOFF = 0.6              # seconds (exponential)
MAX_BACKOFF = 8.0               # cap seconds
JITTER_RANGE = (0.0, 0.35)      # random jitter added to backoff


def _parse_retry_after(header_val: Optional[str]) -> float:
    """
    Returns seconds to wait per RFC7231 Retry-After:
      - if number: seconds
      - if HTTP-date: difference from now
      - else: 0
    """
    if not header_val:
        return 0.0
    header_val = header_val.strip()
    # numeric seconds
    if header_val.isdigit():
        try:
            return max(0.0, float(int(header_val)))
        except Exception:
            return 0.0
    # HTTP-date
    try:
        dt = parsedate_to_datetime(header_val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = (dt - now).total_seconds()
        return max(0.0, delta)
    except Exception:
        return 0.0


def _sleep_backoff(attempt: int, retry_after_hdr: Optional[str]) -> None:
    # Prefer server’s Retry-After if present and non-zero
    ra = _parse_retry_after(retry_after_hdr)
    if ra > 0:
        time.sleep(ra)
        return
    # Otherwise exponential backoff with jitter
    delay = min(MAX_BACKOFF, BASE_BACKOFF * (2 ** attempt))
    delay += random.uniform(*JITTER_RANGE)
    time.sleep(delay)


def get_prices(ids: Sequence[str], vs_currency: str = "usd",
               session: Optional[requests.Session] = None,
               timeout: tuple[float, float] = (3.0, 10.0)) -> Dict[str, Any]:
    """
    Robust price fetch with precise Retry-After handling, backoff + jitter,
    and timing logs. Returns e.g. {"bitcoin":{"usd":12345.67}, ...}
    """
    if not ids:
        return {}

    params = {"ids": ",".join(ids), "vs_currencies": vs_currency}
    sess = session or requests.Session()

    last_exc: Optional[Exception] = None
    for attempt in range(MAX_RETRIES):
        t0 = time.perf_counter()
        try:
            r = sess.get(API_URL, params=params, timeout=timeout)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            # Rate limited
            if r.status_code == 429:
                ra = r.headers.get("Retry-After")
                log.warning("429 Too Many Requests (%.1f ms). Retry-After=%s", elapsed_ms, ra)
                _sleep_backoff(attempt, ra)
                continue

            # Transient 5xx
            if 500 <= r.status_code < 600:
                log.warning("%s on attempt %d (%.1f ms). Retrying...",
                            r.status_code, attempt + 1, elapsed_ms)
                _sleep_backoff(attempt, r.headers.get("Retry-After"))
                continue

            # Other errors raise
            r.raise_for_status()

            data = r.json()
            log.info("Fetched %d ids in %.1f ms (status %d).",
                     len(ids), elapsed_ms, r.status_code)
            return data

        except requests.Timeout as e:
            last_exc = e
            log.warning("Timeout on attempt %d. Retrying...", attempt + 1)
            _sleep_backoff(attempt, None)
        except requests.RequestException as e:
            last_exc = e
            log.warning("RequestException on attempt %d: %s. Retrying...", attempt + 1, type(e).__name__)
            _sleep_backoff(attempt, None)
        except Exception as e:
            last_exc = e
            log.exception("Unexpected error on attempt %d. Retrying...", attempt + 1)
            _sleep_backoff(attempt, None)

    # Exhausted retries
    msg = f"Price fetch failed after {MAX_RETRIES} attempts."
    if last_exc:
        msg += f" Last error: {type(last_exc).__name__}"
    log.error(msg)
    raise RuntimeError(msg)
