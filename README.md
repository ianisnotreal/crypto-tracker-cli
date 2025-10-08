# 💰 Crypto Tracker CLI

[![CI](https://github.com/ianisnotreal/crypto-tracker-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/ianisnotreal/crypto-tracker-cli/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/crypto-tracker-cli.svg)](https://pypi.org/project/crypto-tracker-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Latest Release](https://img.shields.io/github/v/release/ianisnotreal/crypto-tracker-cli?display_name=tag&sort=semver)](https://github.com/ianisnotreal/crypto-tracker-cli/releases)


A lightweight command-line application that tracks live cryptocurrency prices, portfolio performance, alerts, and analytics — all powered by the [CoinGecko API](https://www.coingecko.com/).

---

## 🚀 Features

✅ Live crypto prices (via CoinGecko)  
✅ Portfolio tracking with P/L and % gain  
✅ Automatic data snapshots & daemon mode  
✅ Alert triggers for price thresholds  
✅ Daily rollups with OHLC & averages  
✅ Detailed performance stats (Sharpe, volatility, max drawdown)  
✅ Export to CSV for further analysis  
✅ JSON-based local storage (no database required)  
✅ Fully tested, linted, and CI/CD integrated

---

## ⚙️ Installation

### From PyPI
```bash
pip install crypto-tracker-cli
From source
bash
Copy code
git clone https://github.com/ianisnotreal/crypto-tracker-cli.git
cd crypto-tracker-cli
pip install -e .
🖥️ Usage
Run the CLI from anywhere using crypto:

bash
Copy code
crypto track
Or run directly from the repo (for development):

bash
Copy code
python cli.py track
Common Commands
Command	Description
crypto track	Fetch live prices and update snapshots
crypto daemon	Run background auto-tracker (default: 10-min intervals)
crypto add btc 0.5 --cost 30000	Add or update a position
crypto rm eth --all	Remove a crypto from portfolio
crypto config --show	Display configuration (vs_currency, interval, symbols)
crypto alert --above btc=70000	Trigger alert when price crosses target
crypto rollup --rebuild	Rebuild daily rollups from all snapshots
crypto stats	Show analytics (Sharpe, volatility, etc.)
crypto export	Export daily data to CSV

📊 Example Output
text
Copy code
Crypto Stats — last 3 day(s)
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric           ┃                 Value ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━┩
│ Days             │                     3 │
│ Start Value      │            $17,187.85 │
│ End Value        │            $30,419.50 │
│ Total Return     │               +76.98% │
│ Avg Daily Return │              +38.463% │
│ Daily Volatility │       38.723% (stdev) │
│ Sharpe Ratio     │                 0.993 │
│ Max Drawdown     │                -0.26% │
└──────────────────┴───────────────────────┘
🧪 Development
Run tests with:

bash
Copy code
pytest -q
Lint & format:

bash
Copy code
python -m ruff check --fix .
python -m black .
🚀 Release
When ready to publish a new version:

bash
Copy code
# bump version in pyproject.toml
git commit -am "release: bump version to 0.X.X"
git tag v0.X.X
git push && git push --tags
GitHub Actions (release.yml) will automatically build and publish to PyPI.

🧑‍💻 Contributing
See CONTRIBUTING.md for setup, testing, and release instructions.

📄 License
Licensed under the MIT License.
© 2025 Ian Davis

⭐ Support
If you find this project useful:

Star ⭐ the repo

Share it with other developers

Submit pull requests or ideas via Issues

Together we can make this the most powerful open-source crypto CLI available.

yaml
Copy code

---

### ✅ To add it

Run this from your project root:

```powershell
Set-Content -Path "README.md" -Value @'
# 💰 Crypto Tracker CLI

[![CI](https://github.com/ianisnotreal/crypto-tracker-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/ianisnotreal/crypto-tracker-cli/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/crypto-tracker-cli.svg)](https://pypi.org/project/crypto-tracker-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A lightweight command-line application that tracks live cryptocurrency prices, portfolio performance, alerts, and analytics — all powered by the CoinGecko API.
'@

git add README.md
git commit -m "docs: add polished README with badges, usage, and examples"
git push