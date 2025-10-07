from core import portfolio

def test_upsert_new_and_existing():
    port = {"positions": []}

    # Add new BTC
    port = portfolio.upsert_position(port, coin_id="bitcoin", symbol="btc", qty=1, cost_basis=20000)
    assert port["positions"][0]["cost_basis"] == 20000

    # Add more BTC at higher price (weighted avg)
    port = portfolio.upsert_position(port, coin_id="bitcoin", symbol="btc", qty=1, cost_basis=30000)
    pos = port["positions"][0]
    assert round(pos["cost_basis"], 2) == 25000.00  # weighted avg of 20k + 30k

def test_remove_qty_and_all():
    port = {"positions": [{"id":"bitcoin","symbol":"btc","qty":2,"cost_basis":25000}]}
    port = portfolio.remove_qty(port, symbol="btc", qty=1)
    assert port["positions"][0]["qty"] == 1
    port = portfolio.remove_qty(port, symbol="btc", remove_all=True)
    assert not port["positions"]
