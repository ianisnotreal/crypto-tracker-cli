import os, json
from storage import json_store

def test_write_and_read_json(tmp_path):
    path = tmp_path / "temp.json"
    data = {"a":1}
    json_store.write_json(path, data)
    out = json_store.read_json(path)
    assert out == data

def test_append_snapshot_line(tmp_path):
    json_store.SNAPSHOTS_PATH = tmp_path / "snap.jsonl"
    obj = {"ts":"now","total_value":123}
    json_store.append_snapshot_line(obj)
    assert json.loads(json_store.SNAPSHOTS_PATH.read_text()).get("total_value") == 123
