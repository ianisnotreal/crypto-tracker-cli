from types import SimpleNamespace as NS
import cli
from services import coingecko_client as cg

def test_alert_sends_webhook(monkeypatch):
    # Prices that will trigger above/below
    def fake_prices(ids, vs_currency="usd"):
        return {"bitcoin": {"usd": 71000.0}, "ethereum": {"usd": 2900.0}}
    monkeypatch.setattr(cg, "get_prices", fake_prices)

    # Capture webhook text
    captured = {"text": None, "url": None}
    def fake_send(url, text):
        captured["url"] = url; captured["text"] = text; return True
    monkeypatch.setattr(cli, "send_webhook", fake_send)

    # No config webhook; supply via flag
    monkeypatch.setattr(cli, "read_config", lambda: {})

    args = NS(above=["btc=70000"], below=["eth=3000"], watch=False, webhook="https://hooks.slack.com/services/AAA/BBB/CCC")
    cli.cmd_alert(args)

    assert captured["url"].startswith("https://hooks.slack.com/")
    assert "ALERT BTC" in captured["text"]
    assert "ALERT ETH" in captured["text"]
