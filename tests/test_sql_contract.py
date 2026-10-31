"""Database integration assertions; SQL execution is performed by run_postgres.py."""
import os
from pathlib import Path
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.getenv("OLIST_OUTPUT_DIR", ROOT / "data" / "processed"))


@pytest.mark.integration
def test_postgres_sql_python_reconciliation_passes_all_mart_columns_and_totals():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not configured; CI PostgreSQL 16 job executes this integration check")
    path = OUT / "sql_python_reconciliation.csv"
    assert path.exists(), "Run scripts/run_postgres.py after the Python pipeline"
    checks = pd.read_csv(path)
    assert not checks.empty
    assert checks.status.eq("PASS").all(), checks.loc[checks.status.ne("PASS")].to_string(index=False)
    names = set(checks.check.astype(str))
    assert "seller_mart.mql_id.row_key_parity" in names
    assert "channel_summary.origin.row_key_parity" in names
    assert "sql_05.close_days_sum" in names
    assert "sql_05.close_days_n" in names
    assert "sql_05.data_end_epoch_seconds" in names
    assert any(name.startswith("seller_mart.") for name in names)
    assert any(name.startswith("channel_summary.") for name in names)
