# core/portfolio.py
import json
import os
from typing import Dict, List, Optional

from storage.json_store import PORTFOLIO_PATH, write_json


def load_portfolio() -> Dict:
    """Load or initialize the portfolio file."""
    if not os.path.exists(PORTFOLIO_PATH):
        return {"positions": []}
    with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_portfolio(data: Dict) -> None:
    """Atomic save."""
    write_json(PORTFOLIO_PATH, data)


def _find_index_by_symbol(port: Dict, symbol: str) -> int:
    symbol = symbol.lower()
    for i, p in enumerate(port["positions"]):
        if p["symbol"].lower() == symbol:
            return i
    return -1


def upsert_position(
    port: Dict, *, coin_id: str, symbol: str, qty: float, cost_basis: Optional[float] = None
) -> Dict:
    """
    Add a new position or increase quantity.
    If the symbol exists and cost_basis is provided, re-compute a weighted average cost.
    """
    assert qty > 0, "Quantity must be positive."
    idx = _find_index_by_symbol(port, symbol)
    if idx == -1:
        port["positions"].append(
            {
                "id": coin_id,
                "symbol": symbol.lower(),
                "qty": float(qty),
                "cost_basis": float(cost_basis if cost_basis is not None else 0.0),
            }
        )
        return port

    pos = port["positions"][idx]
    old_qty = float(pos["qty"])
    old_cost = float(pos["cost_basis"])
    new_qty = old_qty + float(qty)

    if cost_basis is None or old_qty <= 0:
        new_cost = old_cost if old_qty > 0 else float(old_cost)
    else:
        # Weighted average cost
        new_cost = ((old_qty * old_cost) + (float(qty) * float(cost_basis))) / new_qty

    pos.update({"qty": new_qty, "cost_basis": new_cost})
    return port


def remove_qty(
    port: Dict, *, symbol: str, qty: Optional[float] = None, remove_all: bool = False
) -> Dict:
    """Remove quantity or delete the whole position with --all."""
    idx = _find_index_by_symbol(port, symbol)
    if idx == -1:
        raise ValueError(f"No position for symbol '{symbol}'.")
    if remove_all:
        del port["positions"][idx]
        return port

    assert qty is not None and qty > 0, "Use --qty with a positive number or --all."
    pos = port["positions"][idx]
    new_qty = float(pos["qty"]) - float(qty)
    if new_qty <= 0:
        del port["positions"][idx]
    else:
        pos["qty"] = new_qty
    return port


def set_fields(
    port: Dict, *, symbol: str, qty: Optional[float] = None, cost_basis: Optional[float] = None
) -> Dict:
    """Directly set qty and/or cost_basis on an existing position."""
    idx = _find_index_by_symbol(port, symbol)
    if idx == -1:
        raise ValueError(f"No position for symbol '{symbol}'.")
    if qty is not None:
        if qty < 0:
            raise ValueError("Quantity cannot be negative.")
        port["positions"][idx]["qty"] = float(qty)
    if cost_basis is not None:
        if cost_basis < 0:
            raise ValueError("Cost basis cannot be negative.")
        port["positions"][idx]["cost_basis"] = float(cost_basis)
    return port


def valuate(portfolio: Dict, prices: Dict, vs_currency: str) -> Dict:
    """Compute total and per-asset value + P/L."""
    total_value = 0.0
    report: List[Dict] = []
    for pos in portfolio["positions"]:
        pid = pos["id"]
        qty = float(pos["qty"])
        cost = float(pos["cost_basis"])
        price = float(prices.get(pid, {}).get(vs_currency, 0.0))
        value = qty * price
        pnl = value - (qty * cost)
        pnl_pct = (pnl / (qty * cost) * 100.0) if cost else 0.0
        report.append(
            {
                "symbol": pos["symbol"],
                "price": price,
                "value": value,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
            }
        )
        total_value += value
    return {"positions": report, "total_value": total_value}
