from services import html_fallback as hf

class FakeResp:
    def __init__(self, text, status=200):
        self.text = text
        self.status_code = status
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception("HTTP error")

def test_get_prices_html_parses_regularMarketPrice(monkeypatch):
    sample = '<script>..."regularMarketPrice":{"raw":54321.12,"fmt":"54,321.12"}...</script>'
    def fake_get(url, headers=None, timeout=None):
        return FakeResp(sample, 200)
    import requests
    monkeypatch.setattr(requests, "get", fake_get)
    out = hf.get_prices_html(["bitcoin"])
    assert out["bitcoin"]["usd"] == 54321.12
