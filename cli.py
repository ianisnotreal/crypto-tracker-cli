# cli.py
import time
import argparse
from services.coingecko_client import get_prices
from core.portfolio import (
    load_portfolio, save_portfolio, valuate,
    upsert_position, remove_qty, set_fields
)
from storage.json_store import (
    append_snapshot_line, write_cache, read_config, read_cache, read_last_snapshots, write_config, ensure_config_exists, read_alerts, write_alerts
)
from utils.timeutils import utc_now_iso
from utils.logging import get_logger
from scheduler.runner import run_daemon

log = get_logger("cli")

def _resolve_symbol_to_id(symbol: str, cfg: dict) -> str:
    m = cfg.get("symbols_map", {})
    sid = m.get(symbol.lower())
    if not sid:
        raise ValueError(
            f"Unknown symbol '{symbol}'. Add it to ~/.crypto_tracker/config.json under symbols_map."
        )
    return sid

def _print_report(report: dict):
    try:
        from rich.table import Table
        from rich.console import Console
        table = Table(title="Crypto Tracker")
        table.add_column("Symbol", justify="left")
        table.add_column("Price (USD)", justify="right")
        table.add_column("Value", justify="right")
        table.add_column("P/L", justify="right")
        table.add_column("P/L %", justify="right")

        for pos in report["positions"]:
            table.add_row(
                pos["symbol"].upper(),
                f"${pos['price']:,.2f}",
                f"${pos['value']:,.2f}",
                f"${pos['pnl']:,.2f}",
                f"{pos['pnl_pct']:,.2f}%"
            )
        table.add_row("", "", "", "", "")
        table.add_row("[b]TOTAL[/b]", "", f"[b]${report['total_value']:,.2f}[/b]", "", "")
        Console().print(table)
    except Exception:
        # Fallback plain print if rich isn't available
        for pos in report["positions"]:
            print(f"{pos['symbol'].upper():<6} ${pos['price']:>10.2f}  P/L: {pos['pnl']:>10.2f} ({pos['pnl_pct']:>6.2f}%)")
        print(f"Total Value: ${report['total_value']:,.2f}")


def _snapshot_and_cache(ids, prices_resp, vs_currency, report):
    last_fetch_ts = utc_now_iso()
    snapshot_obj = {
        "ts": last_fetch_ts,
        "prices": {pid: prices_resp.get(pid, {}).get(vs_currency, 0.0) for pid in ids},
        "total_value": report["total_value"],
        "positions": report["positions"],
        "vs_currency": vs_currency
    }
    append_snapshot_line(snapshot_obj)
    flat_prices = {pid: prices_resp.get(pid, {}).get(vs_currency, 0.0) for pid in ids}
    write_cache(flat_prices, last_fetch_ts)

def one_cycle(vs_currency: str):
    port = load_portfolio()
    ids = [p["id"] for p in port["positions"]]
    if not ids:
        print("No positions found. Add some to ~/.crypto_tracker/portfolio.json or use `add`.")
        return

    try:
        prices_resp = get_prices(ids, vs_currency=vs_currency)
    except Exception as e:
        log.warning("Price fetch failed (%s). Falling back to cache.", e)
        cache = read_cache()
        prices_resp = {k: {vs_currency: v} for k, v in cache.get("last_prices", {}).items()}

    report = valuate(port, prices_resp, vs_currency)
    _print_report(report)
    _snapshot_and_cache(ids, prices_resp, vs_currency, report)

# -------- Commands --------

def cmd_track(args: argparse.Namespace):
    cfg = read_config()
    vs = args.fiat or cfg.get("vs_currency", "usd")
    one_cycle(vs_currency=vs)

def cmd_daemon(args: argparse.Namespace):
    cfg = read_config()
    vs = args.fiat or cfg.get("vs_currency", "usd")
    interval = args.interval or int(cfg.get("update_interval_sec", 600))
    jitter = args.jitter
    def job(): one_cycle(vs_currency=vs)
    run_daemon(job_fn=job, interval_sec=interval, jitter_sec=jitter)

def cmd_add(args: argparse.Namespace):
    cfg = read_config()
    vs = args.fiat or cfg.get("vs_currency", "usd")
    coin_id = _resolve_symbol_to_id(args.symbol, cfg)

    port = load_portfolio()
    port = upsert_position(
        port,
        coin_id=coin_id,
        symbol=args.symbol.lower(),
        qty=float(args.qty),
        cost_basis=float(args.cost) if args.cost is not None else None
    )
    save_portfolio(port)
    print(f"Added/updated {args.symbol.upper()} qty={args.qty}" + (f" cost={args.cost}" if args.cost is not None else ""))

    one_cycle(vs_currency=vs)

def cmd_rm(args: argparse.Namespace):
    cfg = read_config()
    vs = args.fiat or cfg.get("vs_currency", "usd")

    port = load_portfolio()
    try:
        port = remove_qty(
            port,
            symbol=args.symbol.lower(),
            qty=float(args.qty) if args.qty is not None else None,
            remove_all=bool(args.all)
        )
    except ValueError as e:
        print(str(e))
        return
    save_portfolio(port)

    if args.all:
        print(f"Removed ALL of {args.symbol.upper()}.")
    else:
        print(f"Removed {args.qty} of {args.symbol.upper()}.")

    one_cycle(vs_currency=vs)

def cmd_set(args: argparse.Namespace):
    cfg = read_config()
    vs = args.fiat or cfg.get("vs_currency", "usd")

    port = load_portfolio()
    try:
        port = set_fields(
            port,
            symbol=args.symbol.lower(),
            qty=float(args.qty) if args.qty is not None else None,
            cost_basis=float(args.cost) if args.cost is not None else None
        )
    except ValueError as e:
        print(str(e))
        return
    save_portfolio(port)
    print(f"Set {args.symbol.upper()} " +
          (f"qty={args.qty} " if args.qty is not None else "") +
          (f"cost={args.cost}" if args.cost is not None else ""))

    one_cycle(vs_currency=vs)

def cmd_price(args: argparse.Namespace):
    cfg = read_config()
    vs = args.fiat or cfg.get("vs_currency", "usd")

    # parse comma-separated symbols: "btc,eth,ada"
    syms = [s.strip().lower() for s in args.symbols.split(",") if s.strip()]
    if not syms:
        print("Provide symbols, e.g., python cli.py price btc,eth --fiat usd")
        return

    # resolve each symbol -> coingecko id
    ids = []
    for s in syms:
        ids.append(_resolve_symbol_to_id(s, cfg))

    prices = get_prices(ids, vs_currency=vs)
    # print results in symbol order
    for s, cid in zip(syms, ids):
        p = prices.get(cid, {}).get(vs, 0.0)
        print(f"{s.upper():<6} ${p:,.4f}")

def cmd_history(args: argparse.Namespace):
    rows = read_last_snapshots(args.last)
    if not rows:
        print("No snapshots yet. Run `crypto track` or start the daemon.")
        return

    if args.table:
        try:
            from rich.table import Table
            from rich.console import Console
            t = Table(title=f"Last {len(rows)} snapshots")
            t.add_column("Timestamp", justify="left")
            t.add_column("Total Value", justify="right")
            t.add_column("Δ vs prev", justify="right")

            prev = None
            for r in rows:
                total = float(r.get("total_value", 0.0))
                if prev is None:
                    delta = "–"
                else:
                    diff = total - prev
                    pct = (diff / prev * 100.0) if prev else 0.0
                    delta = f"{diff:+,.2f} ({pct:+.2f}%)"
                t.add_row(r["ts"], f"${total:,.2f}", delta)
                prev = total
            Console().print(t)
        except Exception:
            print(f"Last {len(rows)} snapshots:")
            for r in rows:
                print(f"{r['ts']}  total={r['total_value']:,.2f} {r.get('vs_currency','usd').upper()}")
    else:
        print(f"Last {len(rows)} snapshots:")
        prev = None
        for r in rows:
            total = float(r.get("total_value", 0.0))
            if prev is None:
                delta = ""
            else:
                diff = total - prev
                pct = (diff / prev * 100.0) if prev else 0.0
                delta = f"  Δ {diff:+,.2f} ({pct:+.2f}%)"
            print(f"{r['ts']}  total={total:,.2f} {r.get('vs_currency','usd').upper()}{delta}")
            prev = total
def cmd_export(args: argparse.Namespace):
    import csv, os
    rows = read_last_snapshots(args.last)
    if not rows:
        print("No snapshots to export. Run `crypto track` first.")
        return

    # Collect union of coin ids across snapshots
    coin_ids = set()
    for r in rows:
        for cid in (r.get("prices") or {}).keys():
            coin_ids.add(cid)
    coin_ids = sorted(coin_ids)

    header = ["ts", "vs_currency", "total_value"] + coin_ids
    out_path = os.path.abspath(args.out)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            vs = (r.get("vs_currency") or "usd").lower()
            total = float(r.get("total_value", 0.0))
            row = [r.get("ts", ""), vs, f"{total:.2f}"]
            prices = r.get("prices") or {}
            for cid in coin_ids:
                val = prices.get(cid)
                row.append("" if val is None else f"{float(val):.6f}")
            w.writerow(row)

    print(f"Exported {len(rows)} snapshots → {out_path}")

    def _parse_kv_list(pairs: list[str]) -> dict:
        out = {}
        for item in pairs or []:
            if "=" not in item:
                raise ValueError(f"Expected key=value, got '{item}'")
            k, v = item.split("=", 1)
            out[k.strip()] = v.strip()
        return out

def _parse_kv_list(pairs: list[str]) -> dict:
    out = {}
    for item in pairs or []:
        if "=" not in item:
            raise ValueError(f"Expected key=value, got '{item}'")
        k, v = item.split("=", 1)
        out[k.strip()] = v.strip()
    return out

def _parse_symbol_thresholds(items: list[str]) -> dict[str, float]:
    """Parse key=value like btc=70000 into {'btc': 70000.0}."""
    out: dict[str, float] = {}
    for item in items or []:
        if "=" not in item:
            raise ValueError(f"Expected key=value, got '{item}'")
        k, v = item.split("=", 1)
        k = k.strip().lower()
        try:
            out[k] = float(v.strip().replace(",", ""))
        except ValueError:
            raise ValueError(f"Threshold for '{k}' must be a number.")
    return out

def _parse_csv_syms(s: str | None) -> list[str]:
    if not s:
        return []
    return [x.strip().lower() for x in s.split(",") if x.strip()]

def _resolve_many_symbols_to_ids(symbols: list[str], cfg: dict) -> list[str]:
    ids = []
    for s in symbols:
        cid = cfg.get("symbols_map", {}).get(s.lower())
        if not cid:
            raise ValueError(f"Unknown symbol '{s}'. Add it via `crypto config --add-symbol {s}=<coingecko_id>`.")
        ids.append(cid)
    return ids

def cmd_config(args: argparse.Namespace):
        # Always ensure there is a config file to work with
        ensure_config_exists()
        cfg = read_config()

        if args.path:
            # Show where the config file lives
            from storage.json_store import CONFIG_PATH
            print(CONFIG_PATH)
            return

        did_change = False

        # --set supports vs_currency=... and update_interval_sec=...
        if args.set:
            kv = _parse_kv_list(args.set)
            for k, v in kv.items():
                if k == "vs_currency":
                    if not v:
                        raise ValueError("vs_currency cannot be empty.")
                    cfg["vs_currency"] = v.lower()
                    did_change = True
                elif k == "update_interval_sec":
                    try:
                        sec = int(v)
                    except ValueError:
                        raise ValueError("update_interval_sec must be an integer.")
                    if sec < 30:
                        raise ValueError("update_interval_sec must be >= 30.")
                    cfg["update_interval_sec"] = sec
                    did_change = True
                else:
                    raise ValueError(f"Unknown key '{k}'. Allowed: vs_currency, update_interval_sec")

        # --add-symbol supports entries like btc=bitcoin
        if args.add_symbol:
            kv = _parse_kv_list(args.add_symbol)
            sm = dict(cfg.get("symbols_map", {}))
            for sym, cid in kv.items():
                if not sym or not cid:
                    raise ValueError("symbols_map entries must be like btc=bitcoin (non-empty).")
                sm[sym.lower()] = cid
                did_change = True
            cfg["symbols_map"] = sm

        # --rm-symbol removes keys by symbol (e.g., btc eth)
        if args.rm_symbol:
            sm = dict(cfg.get("symbols_map", {}))
            for sym in args.rm_symbol:
                sm.pop(sym.lower(), None)
                did_change = True
            cfg["symbols_map"] = sm

        if did_change:
            write_config(cfg)
            print("Config updated.")

        # Show current config (default or if --show was passed)
        if args.show or not (args.set or args.add_symbol or args.rm_symbol):
            # pretty print
            import json
            print(json.dumps(cfg, indent=2, ensure_ascii=False))

def cmd_alert(args: argparse.Namespace):
    cfg = read_config()
    vs = (args.fiat or cfg.get("vs_currency", "usd")).lower()

    # Load saved sets if requested
    saved = read_alerts()  # {"saved": {...}}
    above = {}
    below = {}

    if args.use:
        name = args.use.lower()
        preset = saved["saved"].get(name)
        if not preset:
            print(f"No saved alert set named '{name}'. Use `crypto alert --list` to see options.")
            return
        vs = (preset.get("vs_currency") or vs).lower()
        above.update(preset.get("above") or {})
        below.update(preset.get("below") or {})

    # Merge inline thresholds (CLI args win)
    above.update(_parse_symbol_thresholds(args.above))
    below.update(_parse_symbol_thresholds(args.below))

    # List or delete saved sets and exit (no run)
    if args.list:
        names = sorted(saved["saved"].keys())
        if not names:
            print("No saved alert sets.")
        else:
            print("Saved alert sets:")
            for n in names:
                print(" -", n)
        return

    if args.delete:
        n = args.delete.lower()
        if n in saved["saved"]:
            del saved["saved"][n]
            write_alerts(saved)
            print(f"Deleted saved set '{n}'.")
        else:
            print(f"No saved set named '{n}'.")
        return

    # Must have at least one threshold to run or save
    if not above and not below:
        print("Provide thresholds with --above/--below or use --use <name>.")
        return

    # Save current set if requested
    if args.save:
        name = args.save.lower()
        saved["saved"][name] = {"vs_currency": vs, "above": above, "below": below}
        write_alerts(saved)
        print(f"Saved alert set '{name}'.")
        # Note: keep running a check after saving

    syms = sorted(set(list(above.keys()) + list(below.keys())))
    ids = _resolve_many_symbols_to_ids(syms, cfg)

    def check_once():
        prices = get_prices(ids, vs_currency=vs)
        triggered = []
        for s, cid in zip(syms, ids):
            p = float(prices.get(cid, {}).get(vs, 0.0))
            if s in above and p >= above[s]:
                triggered.append((s, p, f">= {above[s]:,.2f}"))
            if s in below and p <= below[s]:
                triggered.append((s, p, f"<= {below[s]:,.2f}"))
        if triggered:
            for (s, p, cond) in triggered:
                print(f"\aALERT {s.upper():<5} ${p:,.2f}  (hit {cond})")
        else:
            print("No alerts triggered.")
        return triggered

    if args.every:
        try:
            import time
            print(f"Watching every {args.every}s (Ctrl+C to stop). Fiat={vs.upper()}")
            while True:
                _ = check_once()
                time.sleep(args.every)
        except KeyboardInterrupt:
            print("\nStopped.")
    else:
        check_once()

def cmd_watch(args: argparse.Namespace):
    # Which coins to show?
    cfg = read_config()
    vs = (args.fiat or cfg.get("vs_currency", "usd")).lower()

    # If user passed symbols, resolve them; else use portfolio coins.
    syms = _parse_csv_syms(args.symbols)
    if syms:
        ids = _resolve_many_symbols_to_ids(syms, cfg)
    else:
        port = load_portfolio()
        syms = [p["symbol"].lower() for p in port.get("positions", [])]
        ids  = [p["id"] for p in port.get("positions", [])]
        if not ids:
            print("No positions and no --symbols provided. Try: crypto watch --symbols btc,eth")
            return

    # Optional alert thresholds
    above = _parse_symbol_thresholds(args.above)
    below = _parse_symbol_thresholds(args.below)

    # Lazy import rich (fallback to plain loop if unavailable)
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.live import Live
        console = Console()

        def render_table(prices_dict: dict[str, float]) -> Table:
            t = Table(title=f"Crypto Watch  (fiat={vs.upper()}, refresh={args.every}s)")
            t.add_column("Symbol", justify="left")
            t.add_column("Price", justify="right")
            t.add_column("Alert", justify="left")
            for s, cid in zip(syms, ids):
                p = float(prices_dict.get(cid, 0.0))
                alert_txt = ""
                if s in above and p >= above[s]:
                    alert_txt = f"[bold green]>= {above[s]:,.2f}[/bold green]"
                elif s in below and p <= below[s]:
                    alert_txt = f"[bold red]<= {below[s]:,.2f}[/bold red]"
                t.add_row(s.upper(), f"${p:,.2f}", alert_txt)
            return t

        with Live(console=console, refresh_per_second=max(1, int(10/args.every))):
            while True:
                prices_resp = get_prices(ids, vs_currency=vs)
                flat = {cid: prices_resp.get(cid, {}).get(vs, 0.0) for cid in ids}
                console.print(render_table(flat), justify="left")
                time.sleep(args.every)
    except Exception:
        # Plain fallback (prints each tick)
        print(f"(plain mode) Refreshing every {args.every}s; fiat={vs.upper()}. Press Ctrl+C to stop.")
        try:
            while True:
                prices_resp = get_prices(ids, vs_currency=vs)
                for s, cid in zip(syms, ids):
                    p = prices_resp.get(cid, {}).get(vs, 0.0)
                    tag = ""
                    if s in above and p >= above[s]: tag = f"  ALERT >= {above[s]:,.2f}"
                    if s in below and p <= below[s]: tag = f"  ALERT <= {below[s]:,.2f}"
                    print(f"{s.upper():<6} ${p:>12,.2f}{tag}")
                print("-" * 40)
                time.sleep(args.every)
        except KeyboardInterrupt:
            print("\nStopped.")


# -------- Parser --------

def build_parser():
    p = argparse.ArgumentParser(prog="crypto", description="Crypto Tracker CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_track = sub.add_parser("track", help="Fetch once, print, and persist snapshot")
    p_track.add_argument("--fiat", help="Fiat currency (default from config.json, usually usd)")
    p_track.set_defaults(func=cmd_track)

    p_daemon = sub.add_parser("daemon", help="Run auto-refresh loop (every 10 minutes by default)")
    p_daemon.add_argument("--interval", type=int, help="Seconds between runs (overrides config)")
    p_daemon.add_argument("--fiat", help="Fiat currency (default from config.json)")
    p_daemon.add_argument("--jitter", type=int, default=30, help="±seconds jitter (default 30)")
    p_daemon.set_defaults(func=cmd_daemon)

    p_add = sub.add_parser("add", help="Add/increase a position")
    p_add.add_argument("symbol", help="e.g., btc, eth (must exist in config symbols_map)")
    p_add.add_argument("qty", type=float, help="Quantity to add")
    p_add.add_argument("--cost", type=float, help="Cost basis for this added amount (optional)")
    p_add.add_argument("--fiat", help="Fiat currency for valuation after update")
    p_add.set_defaults(func=cmd_add)

    p_rm = sub.add_parser("rm", help="Remove quantity or delete a position")
    p_rm.add_argument("symbol", help="e.g., btc, eth")
    g = p_rm.add_mutually_exclusive_group(required=True)
    g.add_argument("--qty", type=float, help="Quantity to remove")
    g.add_argument("--all", action="store_true", help="Remove the entire position")
    p_rm.add_argument("--fiat", help="Fiat currency for valuation after update")
    p_rm.set_defaults(func=cmd_rm)

    p_set = sub.add_parser("set", help="Set fields (qty/cost) for an existing position")
    p_set.add_argument("symbol", help="e.g., btc, eth")
    p_set.add_argument("--qty", type=float, help="New absolute quantity")
    p_set.add_argument("--cost", type=float, help="New absolute cost basis")
    p_set.add_argument("--fiat", help="Fiat currency for valuation after update")
    p_set.set_defaults(func=cmd_set)

    p_price = sub.add_parser("price", help="Quote live prices for comma-separated symbols")
    p_price.add_argument("symbols", help="Comma-separated symbols, e.g., btc,eth,ada")
    p_price.add_argument("--fiat", help="Fiat currency (default from config.json)")
    p_price.set_defaults(func=cmd_price)

    p_hist = sub.add_parser("history", help="Show last N snapshots")
    p_hist.add_argument("--last", type=int, default=10, help="How many lines to show (default 10)")
    p_hist.add_argument("--table", action="store_true", help="Pretty table output")
    p_hist.set_defaults(func=cmd_history)

    p_exp = sub.add_parser("export", help="Export last N snapshots to CSV")
    p_exp.add_argument("--last", type=int, default=100, help="How many snapshots to export (default 100)")
    p_exp.add_argument("--out", required=True, help="Output CSV path, e.g., snapshots.csv")
    p_exp.set_defaults(func=cmd_export)

    p_cfg = sub.add_parser("config", help="Show or edit configuration")
    p_cfg.add_argument("--show", action="store_true", help="Show current config")
    p_cfg.add_argument("--set", nargs="*", help="Set key=value (vs_currency, update_interval_sec). Ex: --set vs_currency=usd update_interval_sec=600")
    p_cfg.add_argument("--add-symbol", nargs="*", help="Add symbol mapping key=value. Ex: --add-symbol sol=solana doge=dogecoin")
    p_cfg.add_argument("--rm-symbol", nargs="*", help="Remove symbol(s) from symbols_map. Ex: --rm-symbol sol doge")
    p_cfg.add_argument("--path", action="store_true", help="Print the config file path and exit")
    p_cfg.set_defaults(func=cmd_config)

    p_alert = sub.add_parser("alert", help="Check/watch price alerts")
    p_alert.add_argument("--above", nargs="*", help="Symbol thresholds like btc=70000 eth=5000")
    p_alert.add_argument("--below", nargs="*", help="Symbol thresholds like btc=60000 eth=3000")
    p_alert.add_argument("--every", type=int, help="Poll every N seconds (omit for one-shot)")
    p_alert.add_argument("--fiat", help="Fiat currency (default from config)")
    # saved sets
    p_alert.add_argument("--save", help="Save the provided thresholds under a name")
    p_alert.add_argument("--use", help="Use a saved threshold set by name")
    p_alert.add_argument("--list", action="store_true", help="List saved alert sets")
    p_alert.add_argument("--delete", help="Delete a saved alert set by name")
    p_alert.set_defaults(func=cmd_alert)

    p_watch = sub.add_parser("watch", help="Live-updating price table")
    p_watch.add_argument("--symbols", help="Comma-separated symbols (default: your portfolio), e.g., btc,eth,ada")
    p_watch.add_argument("--every", type=int, default=5, help="Refresh interval in seconds (default 5)")
    p_watch.add_argument("--fiat", help="Fiat currency (default from config)")
    p_watch.add_argument("--above", nargs="*", help="Alert thresholds like btc=70000 eth=5000")
    p_watch.add_argument("--below", nargs="*", help="Alert thresholds like btc=60000 eth=3000")
    p_watch.set_defaults(func=cmd_watch)

    return p

def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
