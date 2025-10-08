import json
from datetime import datetime, timedelta, timezone

import storage.json_store as js

def _snap(ts, total):
    return {
        "ts": ts,
        "total_value": total,
        "vs_currency": "usd",
        "prices": {"bitcoin": total},  # content doesn't matter for rollup math
    }

def test_incremental_upsert_updates_today(tmp_path, monkeypatch):
    # point store to temp files
    monkeypatch.setattr(js, "SNAPSHOTS_PATH", tmp_path / "snaps.jsonl")
    monkeypatch.setattr(js, "SNAPSHOTS_DAY_PATH", tmp_path / "snaps_day.jsonl")
    monkeypatch.setattr(js, "HOME_DIR", str(tmp_path))  # ensure_home uses this

    # Two snapshots on day1, one on day2
    day1 = datetime(2025, 10, 7, 10, 0, tzinfo=timezone.utc)
    day2 = datetime(2025, 10, 8, 10, 0, tzinfo=timezone.utc)

    s1 = _snap(day1.isoformat(), 100.0)
    s2 = _snap((day1 + timedelta(hours=2)).isoformat(), 120.0)
    s3 = _snap(day2.isoformat(), 90.0)

    js.append_snapshot_line(s1)
    js.append_snapshot_line(s2)
    js.append_snapshot_line(s3)

    # read daily file
    with open(js.SNAPSHOTS_DAY_PATH, "r", encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]

    # should have two days
    assert len(rows) == 2

    d1 = next(r for r in rows if r["date"] == "2025-10-07")
    d2 = next(r for r in rows if r["date"] == "2025-10-08")

    # day1: open=100, close=120, high=120, low=100, avg=(100+120)/2=110, count=2
    assert d1["open"] == 100.0
    assert d1["close"] == 120.0
    assert d1["high"] == 120.0
    assert d1["low"] == 100.0
    assert abs(d1["avg"] - 110.0) < 1e-9
    assert d1["count"] == 2

    # day2: single observation
    assert d2["open"] == 90.0
    assert d2["close"] == 90.0
    assert d2["high"] == 90.0
    assert d2["low"] == 90.0
    assert d2["avg"] == 90.0
    assert d2["count"] == 1
