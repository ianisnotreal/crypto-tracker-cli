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

def test_outlier_guard(tmp_path, monkeypatch):
    # redirect files to temp
    monkeypatch.setattr(js, "SNAPSHOTS_PATH", tmp_path / "snaps.jsonl")
    monkeypatch.setattr(js, "SNAPSHOTS_DAY_PATH", tmp_path / "snaps_day.jsonl")
    monkeypatch.setattr(js, "SNAPSHOTS_BAD_PATH", tmp_path / "snaps_bad.jsonl")
    monkeypatch.setattr(js, "HOME_DIR", str(tmp_path))

    # seed baseline: totals around 1000
    for t in [1000.0, 1020.0, 980.0, 1010.0]:
        js.append_snapshot_line(_snap(t))

    # outlier: >80% away from median (~1000) -> e.g., 120
    saved = js.guarded_append_snapshot_line(_snap(120.0), window=4, threshold=0.80)
    assert saved is False  # skipped

    # non-outlier: within 80% -> e.g., 1300 (~30% high)
    saved2 = js.guarded_append_snapshot_line(_snap(1300.0), window=4, threshold=0.80)
    assert saved2 is True  # accepted

    # verify main file has 5 snapshots (4 baseline + 1 accepted), not 6
    with open(js.SNAPSHOTS_PATH, "r", encoding="utf-8") as f:
        main_count = sum(1 for _ in f if _.strip())
    assert main_count == 5

    # verify bad file captured the outlier once
    with open(js.SNAPSHOTS_BAD_PATH, "r", encoding="utf-8") as f:
        bad = [json.loads(line) for line in f if line.strip()]
    assert len(bad) == 1
    assert bad[0]["reason"] == "outlier_total_value"
