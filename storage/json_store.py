# storage/json_store.py
import io
import json
import os
import tempfile
from datetime import datetime, timezone
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


def append_snapshot_line(obj: dict) -> None:
    """Append a single JSON line to snapshots.jsonl (atomic best-effort)."""
    ensure_home()
    # write the snapshot
    line = json.dumps(obj, ensure_ascii=False)
    try:
        # create parent dir
        os.makedirs(os.path.dirname(SNAPSHOTS_PATH), exist_ok=True)
        with open(SNAPSHOTS_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        # swallow errors to avoid crashing the caller; snapshot loss is acceptable
        pass

    # NEW: incrementally update today's daily rollup
    try:
        upsert_daily_from_snapshot(obj)
    except Exception:
        # do not fail the caller if rollup update has an issue
        pass


def read_config() -> Dict[str, Any]:
    # Defaults if user hasn't created config.json
    cfg = {
        "vs_currency": "usd",
        "update_interval_sec": 600,
        "symbols_map": {"btc": "bitcoin", "eth": "ethereum", "ada": "cardano"},
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
    "symbols_map": {"btc": "bitcoin", "eth": "ethereum", "ada": "cardano"},
}


def write_config(cfg: dict):
    """Atomic write of config.json."""
    # keep only known top-level keys; ignore accidental extras
    clean = {
        "vs_currency": cfg.get("vs_currency", DEFAULT_CONFIG["vs_currency"]),
        "update_interval_sec": int(
            cfg.get("update_interval_sec", DEFAULT_CONFIG["update_interval_sec"])
        ),
        "symbols_map": dict(cfg.get("symbols_map", DEFAULT_CONFIG["symbols_map"])),
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

SNAPSHOTS_DAY_PATH = os.path.join(HOME_DIR, "snapshots_day.jsonl")


def _date_utc(ts_iso: str) -> str:
    # ts like "2025-10-08T15:22:01.123456+00:00" -> "2025-10-08"
    try:
        dt = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
    except Exception:
        # fallback: treat unknown as UTC now, but avoid crash
        dt = datetime.now(timezone.utc)
    return dt.astimezone(timezone.utc).date().isoformat()

def _read_all_daily_records() -> list[dict]:
    """Load all daily rollup rows from snapshots_day.jsonl (may return [])."""
    ensure_home()
    if not os.path.exists(SNAPSHOTS_DAY_PATH):
        return []
    out = []
    with open(SNAPSHOTS_DAY_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def _write_all_daily_records(rows: list[dict]) -> None:
    """Rewrite snapshots_day.jsonl with the provided rows (atomic)."""
    lines = [json.dumps(r, ensure_ascii=False) for r in rows]
    _atomic_write_text(SNAPSHOTS_DAY_PATH, "\n".join(lines) + ("\n" if lines else ""))


def upsert_daily_from_snapshot(snapshot: dict) -> None:
    """
    Incrementally update the daily rollup for the date of `snapshot`.
    snapshot must contain: ts (ISO-8601), total_value (float).
    Fields maintained per-day: open, close, high, low, avg, count.
    """
    ensure_home()
    # derive date + total (guard but don't crash)
    d = _date_utc(str(snapshot.get("ts", "")))
    try:
        total = float(snapshot.get("total_value", 0.0))
    except Exception:
        total = 0.0

    rows = _read_all_daily_records()

    # find existing record for this date
    idx = next((i for i, r in enumerate(rows) if r.get("date") == d), None)

    if idx is None:
        # first observation for the day
        rec = {
            "date": d,
            "open": total,
            "close": total,
            "high": total,
            "low": total,
            "avg": total,
            "count": 1,
        }
        rows.append(rec)
    else:
        rec = rows[idx]
        # recompute fields (avg via weighted running sum)
        cnt = int(rec.get("count", 0))
        prev_sum = float(rec.get("avg", 0.0)) * max(cnt, 0)
        cnt += 1
        new_sum = prev_sum + total
        rec.update(
            {
                "close": total,
                "high": max(float(rec.get("high", total)), total),
                "low": min(float(rec.get("low", total)), total),
                "avg": (new_sum / cnt) if cnt else total,
                "count": cnt,
            }
        )
        rows[idx] = rec

    # keep file sorted by date (ascending)
    rows.sort(key=lambda r: r.get("date", ""))

    _write_all_daily_records(rows)

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
        lines.append(
            json.dumps(
                {
                    "date": rec["date"],
                    "open": rec["open"],
                    "close": rec["close"],
                    "high": rec["high"],
                    "low": rec["low"],
                    "avg": avg,
                    "count": rec["count"],
                },
                ensure_ascii=False,
            )
        )

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

def read_daily_all() -> list[dict]:
    """Return all daily rollup rows (chronological)."""
    ensure_home()
    if not os.path.exists(SNAPSHOTS_DAY_PATH):
        return []
    rows = []
    with open(SNAPSHOTS_DAY_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    rows.sort(key=lambda r: r.get("date", ""))
    return rows

# --- Outlier guard ---
SNAPSHOTS_BAD_PATH = os.path.join(HOME_DIR, "snapshots_bad.jsonl")

def _read_last_totals(n: int = 10) -> list[float]:
    """Return last n total_value numbers from snapshots.jsonl (chronological tail)."""
    ensure_home()
    if not os.path.exists(SNAPSHOTS_PATH):
        return []
    rows = []
    with open(SNAPSHOTS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                rows.append(float(obj.get("total_value", 0.0)))
            except Exception:
                pass
    return rows[-n:]

def _median(vals: list[float]) -> float:
    if not vals:
        return 0.0
    vals = sorted(vals)
    m = len(vals) // 2
    if len(vals) % 2:
        return vals[m]
    return (vals[m - 1] + vals[m]) / 2.0

def _write_bad_snapshot(obj: dict) -> None:
    try:
        os.makedirs(os.path.dirname(SNAPSHOTS_BAD_PATH), exist_ok=True)
        with open(SNAPSHOTS_BAD_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception:
        pass  # never block caller

def guarded_append_snapshot_line(
    obj: dict,
    window: int | None = None,
    threshold: float | None = None,  # fraction 0..1 if provided
) -> bool:
    """
    Append snapshot with an outlier guard.
    Returns True if appended; False if skipped as outlier (logged to snapshots_bad.jsonl).
    """
    try:
        total = float(obj.get("total_value", 0.0))
    except Exception:
        total = 0.0

    # pick params (prefer explicit args; else config)
    if window is None or threshold is None:
        cfg_win, cfg_thr = _guard_params_from_config()
        window = cfg_win if window is None else window
        threshold = cfg_thr if threshold is None else threshold

    ref = _read_last_totals(int(window))
    if len(ref) < max(3, min(int(window), 10)):
        append_snapshot_line(obj)
        return True

    med = _median(ref)
    base = med if med > 0 else 1.0
    deviation = abs(total - med) / base

    if deviation > float(threshold):
        _write_bad_snapshot({
            "reason": "outlier_total_value",
            "median": med,
            "total_value": total,
            "deviation": deviation,
            "threshold": float(threshold),
            "ts": obj.get("ts"),
            "vs_currency": obj.get("vs_currency", "usd"),
            "prices": obj.get("prices", {}),
        })
        return False

    append_snapshot_line(obj)
    return True

    med = _median(ref)
    base = med if med > 0 else 1.0
    deviation = abs(total - med) / base  # e.g., 0.82 means 82% away from median

    if deviation > threshold:
        # Outlier — log to 'bad' file, skip normal append/rollup.
        _write_bad_snapshot({
            "reason": "outlier_total_value",
            "median": med,
            "total_value": total,
            "deviation": deviation,
            "threshold": threshold,
            "ts": obj.get("ts"),
            "vs_currency": obj.get("vs_currency", "usd"),
            "prices": obj.get("prices", {}),
        })
        return False

    # Normal path
    append_snapshot_line(obj)
    return True

def _guard_params_from_config() -> tuple[int, float]:
    """
    Read guard window and threshold from config.json with safe defaults.
    Returns: (window, threshold_fraction) where threshold_fraction is 0..1.
    """
    try:
        cfg = read_config()
        win = int(cfg.get("outlier_window", 10))
        thr_pct = float(cfg.get("outlier_threshold_pct", 80.0))
    except Exception:
        win, thr_pct = 10, 80.0

    # clamp to sane ranges
    win = max(3, min(win, 1000))
    thr = max(0.0, min(thr_pct / 100.0, 1.0))
    return win, thr

