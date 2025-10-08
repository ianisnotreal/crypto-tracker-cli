# Contributing to Crypto Tracker CLI

Thank you for your interest in improving **Crypto Tracker CLI**!  
This document explains how to set up your environment, run tests, and follow our code standards.

---

## 🧰 Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/<your-username>/crypto-tracker-cli.git
   cd crypto-tracker-cli
Create a virtual environment

bash
Copy code
python -m venv venv
source venv/bin/activate        # macOS/Linux
.\venv\Scripts\activate         # Windows
Install the package in editable mode

bash
Copy code
pip install -e .
pip install pytest ruff black
Run the CLI locally

bash
Copy code
python cli.py track
✅ Running Tests
We use pytest for unit tests.

bash
Copy code
pytest -q
All new features should include tests under the tests/ directory.

🧹 Code Style
We enforce Ruff for linting and Black for formatting.

Before committing:

bash
Copy code
python -m ruff check --fix .
python -m black .
You can also install a pre-commit hook to run them automatically:

bash
Copy code
pip install pre-commit
pre-commit install
🧪 Continuous Integration
All pull requests and pushes trigger GitHub Actions:

ci.yml runs unit tests on multiple OS/Python versions.

release.yml publishes to PyPI when a tag (e.g., v0.2.0) is pushed.

Ensure all CI checks pass before merging.

🚀 Releasing a New Version
Bump version in pyproject.toml

Commit the change:

bash
Copy code
git commit -am "release: bump version to 0.X.X"
Tag and push:

bash
Copy code
git tag v0.X.X
git push && git push --tags
The release.yml workflow will automatically build and upload to PyPI.

💬 Questions or Issues
Open an issue on GitHub describing:

What you expected

What actually happened

Steps to reproduce

Thanks for helping make Crypto Tracker CLI better!