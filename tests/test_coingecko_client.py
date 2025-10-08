from datetime import datetime, timedelta, timezone

import requests

from services import coingecko_client as cg


class DummyResp:
    def __init__(self, status, json_data=None, headers=None):
        self.status_code = status
        self._json = json_data or {}
        self.headers = headers or {}

    def json(self):
        return self._json

    def raise_for_status(self):
        # mimic requests.Response.raise_for_status()
        if 400 <= self.status_code:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def test_get_prices_success(monkeypatch):
    def fake_get(url, params=None, **kwargs):  # accept **kwargs (timeout, etc.)
        return DummyResp(200, {"bitcoin": {"usd": 50000}})

    monkeypatch.setattr(cg.requests, "get", fake_get)
    data = cg.get_prices(["bitcoin"], "usd")
    assert data["bitcoin"]["usd"] == 50000


def test_get_prices_429_then_success(monkeypatch):
    calls = {"n": 0}

    def fake_get(url, params=None, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            # include Retry-After header
            return DummyResp(429, headers={"Retry-After": "0"})
        return DummyResp(200, {"bitcoin": {"usd": 50000}})

    monkeypatch.setattr(cg.requests, "get", fake_get)
    data = cg.get_prices(["bitcoin"], "usd")
    assert calls["n"] >= 2
    assert data["bitcoin"]["usd"] == 50000


def test_parse_retry_after_numeric():
    assert cg._parse_retry_after("5") >= 5.0


def test_parse_retry_after_date():
    # 2 seconds in the future
    future = (datetime.now(timezone.utc) + timedelta(seconds=2)).strftime(
        "%a, %d %b %Y %H:%M:%S GMT"
    )
    val = cg._parse_retry_after(future)
    assert 0.5 <= val <= 2.5  # within a loose window
