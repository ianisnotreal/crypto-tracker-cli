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

Troubleshooting: PATH & venv (Windows)
“crypto : The term 'crypto' is not recognized…”

This terminal doesn’t see the installed script.

Fix A: Activate your project venv

cd C:\Users\User\PycharmProjects\crypto-tracker-cli
.\venv\Scripts\activate
cd .\crypto-tracker-cli
pip install -e .
where crypto              # should show ...\venv\Scripts\crypto.exe
crypto track


Fix B: Run via Python directly (no PATH needed)

cd C:\Users\User\PycharmProjects\crypto-tracker-cli\crypto-tracker-cli
python cli.py track


Fix C: Use full path to the script (global user install)

& "$env:LOCALAPPDATA\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\Scripts\crypto.exe" track


Fix D: Make it work in new terminals (add to PATH)

setx PATH "$env:PATH;$env:LOCALAPPDATA\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\Scripts"
# Close and open a NEW terminal after this

“ModuleNotFoundError: No module named 'requests'”

The script ran with a Python interpreter that doesn’t have deps installed.

Activate venv and install:

cd C:\Users\User\PycharmProjects\crypto-tracker-cli
.\venv\Scripts\activate
cd .\crypto-tracker-cli
pip install -r requirements.txt  # or: pip install requests beautifulsoup4 rich apscheduler


In PyCharm, set Project Interpreter to your venv:
Settings → Project → Python Interpreter → select ...\venv\Scripts\python.exe.

“error: Multiple top-level packages discovered…” when pip install -e .

Your pyproject.toml needs explicit package discovery.

Ensure your pyproject.toml has:

[tool.setuptools]
py-modules = ["cli"]

[tool.setuptools.packages.find]
where = ["."]
include = ["core*", "services*", "storage*", "scheduler*", "utils*"]


And each package dir has __init__.py:
core/, services/, storage/, scheduler/, utils/.

Rich table garbled or “black lines” in terminal

Update PSReadLine and open a fresh terminal:

Install-Module PSReadLine -MinimumVersion 2.0.3 -Scope CurrentUser -Force

Two daemons at once

The second should exit with: “Another crypto daemon is already running (lock present).”
If you crashed and the lock remains, ensure no daemon is running, then delete:

C:\Users\User\.crypto_tracker\daemon.lock

Price fetch fails / offline

The app auto-falls back to cache.json for last prices.

Try again later or run crypto daemon to refresh when connectivity returns.

Release Checklist

Bump version
In pyproject.toml, update:

[project]
version = "0.1.X"


Commit: chore: bump version to 0.1.X.

Smoke test (local)

# fresh venv
python -m venv venv
.\venv\Scripts\activate
pip install -e .
crypto track
crypto price btc,eth
crypto history --table
crypto alert --use <if any> || crypto alert --above btc=1 --every 1
# Ctrl+C to stop watch/daemon/alert loops


Run basic tests (add when ready)

Unit tests: portfolio math (weighted cost, P/L), JSON atomic writes, client retry/429.

Integration: track with mocked API; one daemon cycle with lock file.

pytest -q


Build artifacts

# from the folder with pyproject.toml
pip install build
python -m build
# produces dist/*.whl and dist/*.tar.gz


Tag the release

git add .
git commit -m "release: 0.1.X"
git tag v0.1.X
git push && git push --tags


(Optional) Publish to PyPI

pip install twine
twine upload dist/*


Make sure your package name (project.name in pyproject.toml) is unique on PyPI.

Consider a scoped name if needed (e.g., yourname-crypto-tracker-cli).

Update README

Add new features/flags.

Add an upgrade note:

pip install -U crypto-tracker-cli


Post-release sanity

New venv test:

python -m venv clean
.\clean\Scripts\activate
pip install crypto-tracker-cli
crypto track


Confirm crypto runs, config path is correct, and commands behave as expected.

Notes & Credits

Pricing via CoinGecko’s public API.

TUI and tables via rich.

No cloud, no accounts — all data is local to your user profile.