import json
from datetime import datetime, timezone
import storage.json_store as js

def _snap(total):
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "vs_currency": "usd",
        "total_value": total,
        "prices": {"bitcoin": total},
    }

# tests/test_guard_config.py  (replace the top part accordingly)

def test_guard_uses_config(tmp_path, monkeypatch):
    # redirect data files
    monkeypatch.setattr(js, "SNAPSHOTS_PATH", tmp_path / "snaps.jsonl")
    monkeypatch.setattr(js, "SNAPSHOTS_DAY_PATH", tmp_path / "snaps_day.jsonl")
    monkeypatch.setattr(js, "SNAPSHOTS_BAD_PATH", tmp_path / "snaps_bad.jsonl")
    monkeypatch.setattr(js, "HOME_DIR", str(tmp_path))
    monkeypatch.setattr(js, "CONFIG_PATH", tmp_path / "config.json")  # OK to keep

    # stricter threshold (50%), small window (4)
    cfg = {
        "vs_currency": "usd",
        "update_interval_sec": 600,
        "symbols_map": {"btc": "bitcoin"},
        "outlier_window": 4,
        "outlier_threshold_pct": 50.0,
    }
    js.write_config(cfg)

    # Force the guard to read this exact config
    monkeypatch.setattr(js, "read_config", lambda: cfg)

    # seed baseline around 1000
    for t in [1000.0, 1020.0, 980.0, 1010.0]:
        js.append_snapshot_line(_snap(t))

    # 60% deviation vs median ~1005 -> should be skipped under 50% threshold
    saved = js.guarded_append_snapshot_line(_snap(400.0))
    assert saved is False

    # 30% deviation -> accepted
    saved2 = js.guarded_append_snapshot_line(_snap(1300.0))
    assert saved2 is True

    # main file: 4 baseline + 1 accepted = 5
    with open(js.SNAPSHOTS_PATH, "r", encoding="utf-8") as f:
        assert sum(1 for ln in f if ln.strip()) == 5

    # bad file captured the outlier
    with open(js.SNAPSHOTS_BAD_PATH, "r", encoding="utf-8") as f:
        bad = [json.loads(ln) for ln in f if ln.strip()]
    assert len(bad) == 1
    assert bad[0]["reason"] == "outlier_total_value"
