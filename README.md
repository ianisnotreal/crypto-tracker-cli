# crypto-tracker-cli
CLI app to track live cryptocurrency prices from CoinGecko and manage a local portfolio.

Crypto Tracker CLI

A fast, local-first command-line crypto tracker.
Fetch live prices (CoinGecko), track a portfolio, log snapshots, run an auto-refresh daemon, set alerts, export history to CSV, and watch a live updating TUI table.

Features

Live pricing via CoinGecko (batched)

Portfolio CRUD: add, rm, set

Valuation & P/L with append-only snapshots (snapshots.jsonl)

Offline cache fallback

Auto-refresh daemon (interval + jitter)

Single-instance lock (prevents concurrent daemons)

Pretty tables with rich

Alerts (above/below) + saved alert sets

History views (--table) and CSV export

Config management from the CLI

Install
Option A — Run from source
# Windows PowerShell
cd C:\Users\User\PycharmProjects\crypto-tracker-cli
python -m venv venv
.\venv\Scripts\activate
cd .\crypto-tracker-cli
pip install -r requirements.txt
python cli.py track

Option B — Install as a real command (crypto)
# inside the project (where pyproject.toml lives)
pip install -e .
# now you can run:
crypto track


If crypto isn’t recognized, either activate your venv and reinstall (pip install -e .),
or add your Python Scripts folder to PATH (see Troubleshooting).

Quick Start

Create your portfolio (auto-created as you use add, or manually here):

Windows: C:\Users\<you>\.crypto_tracker\portfolio.json
macOS/Linux: ~/.crypto_tracker/portfolio.json


Example:

{
  "positions": [
    {"id": "bitcoin", "symbol": "btc", "qty": 0.25, "cost_basis": 30000},
    {"id": "ethereum", "symbol": "eth", "qty": 0.8, "cost_basis": 1800}
  ]
}


Then:

crypto track

Commands
Portfolio
crypto add btc 0.05 --cost 27000     # add/increase position (weighted cost)
crypto rm eth --qty 0.2               # remove part of a position
crypto rm eth --all                   # remove entire position
crypto set btc --qty 0.25 --cost 30000# set absolute qty/cost

Pricing & Views
crypto price btc,eth,sol              # quick quotes
crypto history --last 10              # recent totals
crypto history --last 20 --table      # pretty table with deltas
crypto export --last 100 --out snapshots.csv

Daemon & Locking
crypto daemon                         # run every N seconds from config
# Single-instance lock prevents two daemons from writing at once

Alerts
# one-shot checks
crypto alert --above btc=70000 --below eth=3000

# watch mode (polls until Ctrl+C)
crypto alert --above btc=70000 --every 60

# saved alert sets
crypto alert --save swing --above btc=70000 --below eth=3000
crypto alert --list
crypto alert --use swing               # one-shot using saved set
crypto alert --use swing --every 45    # watch using saved set
crypto alert --delete swing

Live Watch (TUI)
crypto watch                           # portfolio coins, refresh 5s
crypto watch --symbols btc,eth,sol --every 3
crypto watch --symbols btc,eth --above btc=70000 --below eth=3000 --every 10

Config
crypto config --show
crypto config --path
crypto config --set vs_currency=usd update_interval_sec=900
crypto config --add-symbol sol=solana doge=dogecoin
crypto config --rm-symbol doge sol

Configuration

config.json lives here:

Windows: C:\Users\<you>\.crypto_tracker\config.json
macOS/Linux: ~/.crypto_tracker/config.json


Default:

{
  "vs_currency": "usd",
  "update_interval_sec": 600,
  "symbols_map": { "btc": "bitcoin", "eth": "ethereum", "ada": "cardano" }
}


Edit via CLI (recommended):

crypto config --set vs_currency=usd update_interval_sec=900
crypto config --add-symbol sol=solana

Data Files

All local in your home folder:

…\.crypto_tracker\portfolio.json     # your holdings
…\.crypto_tracker\snapshots.jsonl    # append-only run history
…\.crypto_tracker\cache.json         # last fetched prices (offline fallback)
…\.crypto_tracker\alerts.json        # saved alert sets (optional)
…\.crypto_tracker\crypto.log         # daemon logs
…\.crypto_tracker\daemon.lock        # single-instance lock file

Troubleshooting

crypto: command not found

Activate venv:
.\venv\Scripts\activate
then pip install -e .

Or run via Python:
python cli.py track

Or add the Python Scripts folder to PATH (Windows):
setx PATH "$env:PATH;$env:LOCALAPPDATA\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\Scripts"
(open a new terminal after running)

Two daemons running?
The second will exit with “lock present.” Delete daemon.lock only if you’re sure no daemon is running.

API rate limits (429)
The client retries with basic backoff; daemon will try again next cycle. Cache allows offline read.

Windows terminal rendering issues
Update PSReadLine as suggested in the terminal message, or use a newer terminal.

Development

Project layout:

crypto-tracker-cli/
  cli.py
  core/            # portfolio math + storage ops
  services/        # coingecko client
  storage/         # json store, cache, snapshots, alerts
  scheduler/       # daemon loop with lock
  utils/           # logging, time, lock
  tests/           # (add tests here)
  pyproject.toml   # packaging; provides 'crypto' console script

Editable install
pip install -e .


Now changes to source reflect immediately when running crypto.

Run locally
python cli.py track

Suggested tests to add

Portfolio math (weighted cost, P/L edge cases)

Atomic JSON writes (temp→replace)

CoinGecko client (mock responses / 429 handling)

Daemon tick (fake time; ensure lock respected)

Notes & Credits

Pricing via CoinGecko’s public API.

TUI and tables via rich.

No cloud, no accounts — all data is local to your user profile.