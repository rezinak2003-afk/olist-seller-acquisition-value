#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python -m src.pipeline
pytest -q
python -m src.make_charts
python scripts/build_dashboard.py
printf '\nSuccess. See data/processed, excel, reports/charts and dashboard/index.html.\n'
