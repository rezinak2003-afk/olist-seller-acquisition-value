"""Regression tests for SQL/Python reconciliation coercion helpers."""
import numpy as np
import pandas as pd

from scripts.run_postgres import _bool_series


def test_bool_series_handles_nullable_float_csv_values_and_postgres_bools():
    values = pd.Series(
        [1.0, 0.0, np.nan, True, False, "TRUE", "false", "1", "0", "1.0", "yes", None],
        dtype="object",
    )

    actual = _bool_series(values).tolist()

    assert actual == [True, False, False, True, False, True, False, True, False, True, True, False]


def test_bool_series_handles_numpy_scalars_and_common_null_spellings():
    values = pd.Series(
        [np.float64(1), np.int64(1), np.float32(0), " 1.00 ", "0.0", "No", "<NA>"],
        dtype="object",
    )

    assert _bool_series(values).tolist() == [True, True, False, True, False, False, False]


def test_sql_python_reconciliation_treats_float_one_as_true():
    from scripts.run_postgres import _compare_frames

    python_mart = pd.DataFrame({"mql_id": ["m1", "m2"], "activated_90d": [1.0, 0.0]})
    sql_mart = pd.DataFrame({"mql_id": ["m1", "m2"], "activated_90d": [True, False]})

    checks = _compare_frames("seller_mart", python_mart, sql_mart, "mql_id")

    assert all(row["status"] == "PASS" for row in checks), checks
