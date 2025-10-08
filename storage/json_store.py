# storage/json_store.py
import json, os, tempfile, io
from typing import Any, Dict

HOME_DIR = os.path.expanduser("~/.crypto_tracker")
CACHE_PATH = os.path.join(HOME_DIR, "cache.json")
SNAPSHOTS_PATH = os.path.join(HOME_DIR, "snapshots.jsonl")
CONFIG_PATH = os.path.join(HOME_DIR, "config.json")
PORTFOLIO_PATH = os.path.join(HOME_DIR, "portfolio.json")

def ensure_home():
    os.makedirs(HOME_DIR, exist_ok=True)

def _atomic_write_text(path: str, text: str):
    ensure_home()
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".tmp-", text=True)
    try:
        with io.open(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

def write_json(path: str, data: Dict[str, Any]):
    _atomic_write_text(path, json.dumps(data, ensure_ascii=False))

def read_json(path: str, default: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if not os.path.exists(path):
        return default or {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_cache(last_prices: Dict[str, Any], last_fetch_ts: str):
    write_json(CACHE_PATH, {"last_prices": last_prices, "last_fetch_ts": last_fetch_ts})

def read_cache() -> Dict[str, Any]:
    return read_json(CACHE_PATH, {"last_prices": {}, "last_fetch_ts": None})

def append_snapshot_line(obj: Dict[str, Any]):
    ensure_home()
    with open(SNAPSHOTS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def read_config() -> Dict[str, Any]:
    # Defaults if user hasn't created config.json
    cfg = {
        "vs_currency": "usd",
        "update_interval_sec": 600,
        "symbols_map": { "btc": "bitcoin", "eth": "ethereum", "ada": "cardano" }
    }
    disk = read_json(CONFIG_PATH, {})
    cfg.update(disk)
    return cfg
def read_last_snapshots(n: int = 10):
    ensure_home()
    path = SNAPSHOTS_PATH
    if not os.path.exists(path):
        return []
    # efficient-ish tail read
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out[-n:]

# ---- Config helpers ----

DEFAULT_CONFIG = {
    "vs_currency": "usd",
    "update_interval_sec": 600,
    "symbols_map": {"btc": "bitcoin", "eth": "ethereum", "ada": "cardano"}
}

def write_config(cfg: dict):
    """Atomic write of config.json."""
    # keep only known top-level keys; ignore accidental extras
    clean = {
        "vs_currency": cfg.get("vs_currency", DEFAULT_CONFIG["vs_currency"]),
        "update_interval_sec": int(cfg.get("update_interval_sec", DEFAULT_CONFIG["update_interval_sec"])),
        "symbols_map": dict(cfg.get("symbols_map", DEFAULT_CONFIG["symbols_map"]))
    }
    write_json(CONFIG_PATH, clean)

def ensure_config_exists():
    """Create config.json with defaults if missing."""
    if not os.path.exists(CONFIG_PATH):
        write_config(DEFAULT_CONFIG.copy())

# ---- Alerts (optional persistence) ----
ALERTS_PATH = os.path.join(HOME_DIR, "alerts.json")

def read_alerts():
    return read_json(ALERTS_PATH, {"saved": {}})

def write_alerts(data: dict):
    write_json(ALERTS_PATH, data)

# ---- Daily rollups ----
from datetime import datetime, timezone
SNAPSHOTS_DAY_PATH = os.path.join(HOME_DIR, "snapshots_day.jsonl")

def _date_utc(ts_iso: str) -> str:
    # ts like "2025-10-08T15:22:01.123456+00:00" -> "2025-10-08"
    try:
        dt = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
    except Exception:
        # fallback: treat unknown as UTC now, but avoid crash
        dt = datetime.now(timezone.utc)
    return dt.astimezone(timezone.utc).date().isoformat()

def rebuild_daily_rollups():
    """Rebuild snapshots_day.jsonl from snapshots.jsonl (idempotent)."""
    ensure_home()
    if not os.path.exists(SNAPSHOTS_PATH):
        # nothing to do
        _atomic_write_text(SNAPSHOTS_DAY_PATH, "")
        return {"days": 0, "snapshots": 0}

    # Aggregate in-memory per date
    per_day = {}  # date -> dict
    total_snapshots = 0
    with open(SNAPSHOTS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total_snapshots += 1
            try:
                row = json.loads(line)
            except Exception:
                continue
            d = _date_utc(row.get("ts", ""))
            total = float(row.get("total_value", 0.0))
            rec = per_day.get(d)
            if rec is None:
                rec = {
                    "date": d,
                    "open": total,
                    "close": total,
                    "high": total,
                    "low": total,
                    "sum": total,
                    "count": 1,
                }
                per_day[d] = rec
            else:
                # update OHLC + average
                rec["close"] = total
                rec["high"] = max(rec["high"], total)
                rec["low"] = min(rec["low"], total)
                rec["sum"] += total
                rec["count"] += 1

    # Write out as jsonl in date order
    days_sorted = sorted(per_day.keys())
    lines = []
    for d in days_sorted:
        rec = per_day[d]
        avg = rec["sum"] / rec["count"] if rec["count"] else rec["close"]
        lines.append(json.dumps({
            "date": rec["date"],
            "open": rec["open"],
            "close": rec["close"],
            "high": rec["high"],
            "low": rec["low"],
            "avg": avg,
            "count": rec["count"],
        }, ensure_ascii=False))

    _atomic_write_text(SNAPSHOTS_DAY_PATH, "\n".join(lines) + ("\n" if lines else ""))
    return {"days": len(days_sorted), "snapshots": total_snapshots}

def read_last_daily(n: int = 14):
    """Tail the daily rollups file (rebuild first if missing/empty)."""
    ensure_home()
    if not os.path.exists(SNAPSHOTS_DAY_PATH):
        # lazy build once
        rebuild_daily_rollups()
    if not os.path.exists(SNAPSHOTS_DAY_PATH):
        return []
    out = []
    with open(SNAPSHOTS_DAY_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out[-n:]
