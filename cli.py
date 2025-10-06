# cli.py
import argparse
from services.coingecko_client import get_prices
from core.portfolio import load_portfolio, valuate
from storage.json_store import (
    append_snapshot_line, write_cache, read_config, read_cache, read_last_snapshots
)
from utils.timeutils import utc_now_iso
from utils.logging import get_logger
from scheduler.runner import run_daemon

log = get_logger("cli")

def one_cycle(vs_currency: str):
    port = load_portfolio()
    ids = [p["id"] for p in port["positions"]]
    if not ids:
        print("No positions found. Add some to ~/.crypto_tracker/portfolio.json")
        return

    try:
        prices_resp = get_prices(ids, vs_currency=vs_currency)
        last_fetch_ts = utc_now_iso()
    except Exception as e:
        log.warning("Price fetch failed (%s). Falling back to cache.", e)
        cache = read_cache()
        prices_resp = {k: {vs_currency: v} for k, v in cache.get("last_prices", {}).items()}
        last_fetch_ts = cache.get("last_fetch_ts") or utc_now_iso()

    report = valuate(port, prices_resp, vs_currency)

    for pos in report["positions"]:
        print(f"{pos['symbol'].upper():<6} ${pos['price']:>10.2f}  P/L: {pos['pnl']:>10.2f} ({pos['pnl_pct']:>6.2f}%)")
    print(f"Total Value: ${report['total_value']:,.2f}")

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

def cmd_history(args: argparse.Namespace):
    rows = read_last_snapshots(args.last)
    if not rows:
        print("No snapshots yet. Run `python cli.py track` a few times or start the daemon.")
        return
    # compact summary
    print(f"Last {len(rows)} snapshots:")
    for r in rows:
        print(f"{r['ts']}  total={r['total_value']:,.2f} {r.get('vs_currency','usd').upper()}")

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

    p_hist = sub.add_parser("history", help="Show last N snapshots")
    p_hist.add_argument("--last", type=int, default=10, help="How many lines to show (default 10)")
    p_hist.set_defaults(func=cmd_history)

    return p

def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
