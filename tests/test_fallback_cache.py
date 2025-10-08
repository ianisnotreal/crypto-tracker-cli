from services import coingecko_client as cg

def test_fallback_writes_cache(monkeypatch):
    # 1) Force CoinGecko failures by patching requests.get (so we hit fallback)
    class DummyResp:
        status_code = 500
        headers = {}
        def raise_for_status(self):
            from requests import HTTPError
            raise HTTPError("500 error")

    def fail_get(*a, **kw):
        return DummyResp()

    # Patch the actual function used by get_prices
    monkeypatch.setattr(cg.requests, "get", fail_get)

    # 2) Stub the HTML fallback to return a known value
    def fake_get_prices_html(ids):
        return {"bitcoin": {"usd": 12345.67}}

    import services.html_fallback as hf
    monkeypatch.setattr(hf, "get_prices_html", fake_get_prices_html)

    # 3) Capture write_cache calls
    writes = {}
    def fake_write_cache(obj):
        writes["last"] = obj

    import storage.json_store as js
    monkeypatch.setattr(js, "write_cache", fake_write_cache)

    # 4) Call get_prices — it should return fallback data and write cache
    data = cg.get_prices(["bitcoin"], "usd")

    assert data["bitcoin"]["usd"] == 12345.67
    assert "last" in writes
    cached = writes["last"]
    assert cached["vs_currency"] == "usd"
    assert abs(cached["prices"]["bitcoin"] - 12345.67) < 1e-9
    assert "ts" in cached
