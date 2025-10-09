from services import notify

class DummyResp:
    def __init__(self, status=200): self.status_code=status
    def raise_for_status(self):
        if self.status_code >= 400:
            from requests import HTTPError; raise HTTPError("bad")

def test_slack_payload(monkeypatch):
    captured = {}
    def fake_post(url, json=None, headers=None, timeout=None):
        captured["json"] = json; return DummyResp(200)
    import requests
    monkeypatch.setattr(requests, "post", fake_post)
    ok = notify.send_webhook("https://hooks.slack.com/services/AAA/BBB/CCC", "hello")
    assert ok is True
    assert captured["json"] == {"text": "hello"}

def test_discord_payload(monkeypatch):
    captured = {}
    def fake_post(url, json=None, headers=None, timeout=None):
        captured["json"] = json; return DummyResp(200)
    import requests
    monkeypatch.setattr(requests, "post", fake_post)
    ok = notify.send_webhook("https://discord.com/api/webhooks/123/abc", "hi")
    assert ok is True
    assert captured["json"] == {"content": "hi"}
