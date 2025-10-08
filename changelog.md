# 🧾 Changelog

All notable changes to this project will be documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]
### Added
- Upcoming features and improvements go here before the next release.

---

## [v0.2.0] - 2025-10-08
### Added
- `crypto stats` command: live analytics with Sharpe ratio, volatility, and max drawdown.
- Automated CI pipeline using GitHub Actions for testing on multiple OS/Python versions.
- Release workflow for publishing to PyPI via version tags.
- Ruff and Black integration for linting and formatting.
- `CONTRIBUTING.md`, `LICENSE`, and `README.md` documentation.

### Fixed
- Minor edge cases in API error handling and retry logic.
- CLI argument parsing errors for `config` subcommands.

---

## [v0.1.0] - 2025-10-01
### Added
- Initial release of **Crypto Tracker CLI**.
- Portfolio tracking with P/L and total value.
- CoinGecko API integration for real-time crypto data.
- JSON-based local storage and daily rollup generation.
- Daemon mode for automatic 10-minute updates.
- Basic alert system and export functionality.

---

## [v0.0.1] - 2025-09-30
### Prototype
- Core CLI prototype built and tested locally.
- Basic portfolio JSON structure implemented.
- Proof of concept for API integration and data scheduling.

---

### 📦 Release Automation

Each new version is published by:
1. Bumping the version in `pyproject.toml`
2. Committing with a message like  
   `release: bump version to 0.3.0`
3. Tagging the release:  
   ```bash
   git tag v0.3.0
   git push && git push --tags
GitHub Actions (release.yml) builds and publishes to PyPI automatically.

🕓 Historical Context
Version	Date	Summary
v0.2.0	2025-10-08	Stats + CI/CD integration
v0.1.0	2025-10-01	First public release
v0.0.1	2025-09-30	Local prototype

🧑‍💻 Maintainer
Ian Davis — github.com/ianisnotreal

yaml
Copy code

---

### ✅ To add it

Run this from your project root:

```powershell
Set-Content -Path "CHANGELOG.md" -Value @'
# 🧾 Changelog

All notable changes to this project will be documented here.
'@

git add CHANGELOG.md
git commit -m "docs: add CHANGELOG for versions v0.0.1–v0.2.0"
git push