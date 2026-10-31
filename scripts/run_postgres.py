"""Load source CSVs, execute PostgreSQL models, and compare every mart column."""
from __future__ import annotations
import os
from pathlib import Path
import numpy as np
import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
RAW = Path(os.getenv("OLIST_RAW_DIR", ROOT/"data"/"raw")).resolve()
OUT = Path(os.getenv("OLIST_OUTPUT_DIR", ROOT/"data"/"processed")).resolve()
TABLES = {
    "marketing_qualified_leads": ("olist_marketing_qualified_leads_dataset.csv", ["mql_id", "first_contact_date", "landing_page_id", "origin"]),
    "closed_deals": ("olist_closed_deals_dataset.csv", ["mql_id", "seller_id", "sdr_id", "sr_id", "won_date", "business_segment", "lead_type", "lead_behaviour_profile", "has_company", "has_gtin", "average_stock", "business_type", "declared_product_catalog_size", "declared_monthly_revenue"]),
    "orders": ("olist_orders_dataset.csv", ["order_id", "customer_id", "order_status", "order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date"]),
    "order_items": ("olist_order_items_dataset.csv", ["order_id", "order_item_id", "product_id", "seller_id", "shipping_limit_date", "price", "freight_value"]),
}
BOOL_COLS = {"mature_90d", "seller_linked_to_order_items", "activated_90d", "activated_90d_any_status", "activated_delivered_within_90d"}
DATETIME_COLS = {"first_contact_date", "won_date", "window_start_inclusive", "window_end_exclusive", "data_end"}
MONEY_COLS = {"gmv_90d_all_statuses", "gmv_90d_delivered_only", "gmv_90d_delivered_within_90d", "gmv_90d_non_delivered_proxy", "freight_90d_all_statuses", "median_gmv_90d", "mean_gmv_90d", "p90_gmv_90d", "total_gmv_90d", "total_gmv_delivered_within_90d", "mean_gmv_delivered_within_90d"}


def query_frame(conn, sql: str) -> pd.DataFrame:
    cur = conn.execute(sql)
    return pd.DataFrame(cur.fetchall(), columns=[x.name for x in cur.description])


def _bool_series(s: pd.Series) -> pd.Series:
    return s.astype("string").str.lower().isin(["true", "1", "t"])


def _compare_frames(name: str, python_df: pd.DataFrame, sql_df: pd.DataFrame,
                    key: str, money_tolerance: float = 0.01) -> list[dict]:
    checks = []
    py = python_df.sort_values(key).reset_index(drop=True)
    sql = sql_df.sort_values(key).reset_index(drop=True)
    py_keys = py[key].astype("string").fillna("(null)")
    sql_keys = sql[key].astype("string").fillna("(null)")
    checks.append({"check": f"{name}.{key}.row_key_parity", "python_value": len(py),
                   "sql_value": len(sql), "absolute_difference": abs(len(py)-len(sql)),
                   "tolerance": 0, "status": "PASS" if py_keys.equals(sql_keys) else "FAIL",
                   "detail": "Primary-key sequence and row count"})
    if not py_keys.equals(sql_keys):
        return checks
    for col in [c for c in py.columns if c != key]:
        a, b = py[col], sql[col]
        if col in BOOL_COLS:
            aa, bb = _bool_series(a), _bool_series(b)
            na, nb = a.isna(), b.isna()
            mismatches = int((aa.ne(bb) | na.ne(nb)).sum())
            tol = 0.0
        elif col in DATETIME_COLS:
            aa, bb = pd.to_datetime(a, errors="coerce"), pd.to_datetime(b, errors="coerce")
            na, nb = aa.isna(), bb.isna()
            mismatches = int(((aa.ne(bb) & ~(na & nb)) | na.ne(nb)).sum())
            tol = 0.0
        elif pd.api.types.is_numeric_dtype(a) or pd.api.types.is_numeric_dtype(b):
            aa, bb = pd.to_numeric(a, errors="coerce"), pd.to_numeric(b, errors="coerce")
            na, nb = aa.isna(), bb.isna()
            absdiff = (aa-bb).abs()
            tol = money_tolerance if col in MONEY_COLS else 1e-6
            mismatches = int(((absdiff.gt(tol) & ~(na & nb)) | na.ne(nb)).sum())
        else:
            aa, bb = a.astype("string").fillna("(null)"), b.astype("string").fillna("(null)")
            mismatches = int(aa.ne(bb).sum())
            tol = 0.0
        checks.append({"check": f"{name}.{col}", "python_value": "rowwise values",
                       "sql_value": "rowwise values", "absolute_difference": mismatches,
                       "tolerance": 0, "status": "PASS" if mismatches == 0 else "FAIL",
                       "detail": f"Row-level mismatches={mismatches}; tolerance={tol}"})
    return checks


def _reconcile_source_totals(source_df: pd.DataFrame, python_values: dict[str, float]) -> list[dict]:
    checks = []
    for row in source_df.itertuples(index=False):
        metric = str(row.metric)
        sql_value = float(row.value) if pd.notna(row.value) else np.nan
        py_value = python_values.get(metric, np.nan)
        tolerance = 0.01 if "sum" in metric or "gmv" in metric or "freight" in metric else (1e-6 if "epoch" in metric else 0)
        if pd.isna(py_value) and pd.isna(sql_value):
            delta, status = 0.0, "PASS"
        elif pd.isna(py_value) or pd.isna(sql_value):
            delta, status = np.inf, "FAIL"
        else:
            delta = abs(float(py_value)-sql_value)
            status = "PASS" if delta <= tolerance else "FAIL"
        checks.append({"check": f"sql_05.{metric}", "python_value": py_value,
                       "sql_value": sql_value, "absolute_difference": delta,
                       "tolerance": tolerance, "status": status,
                       "detail": "SQL control total compared with raw source or Python mart"})
    return checks


def main():
    load_dotenv(ROOT/".env")
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set. Copy .env.example to .env and set your PostgreSQL connection string.")
    missing = [str(RAW/name) for name, _ in TABLES.values() if not (RAW/name).exists()]
    if missing:
        raise FileNotFoundError("Missing source CSVs:\n"+"\n".join(missing)+"\nSee DATA_SOURCES.md and place the original CSVs in data/raw/.")
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("Install dependencies with: pip install -r requirements.txt") from exc
    OUT.mkdir(parents=True, exist_ok=True)

    with psycopg.connect(dsn) as conn:
        # Recreate schemas from the single DDL source so reruns cannot inherit stale columns.
        conn.execute("DROP SCHEMA IF EXISTS mart CASCADE")
        conn.execute("DROP SCHEMA IF EXISTS raw CASCADE")
        conn.execute((ROOT/"sql"/"00_schema.sql").read_text())
        for table, (filename, columns) in TABLES.items():
            col_sql = ", ".join('"'+c+'"' for c in columns)
            copy_sql = f"COPY raw.{table} ({col_sql}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE)"
            with conn.cursor().copy(copy_sql) as cp, (RAW/filename).open("rb") as fh:
                for chunk in iter(lambda: fh.read(1024*1024), b""):
                    cp.write(chunk)
        for script in ["01_validation.sql", "02_acquisition_funnel.sql", "03_seller_90d_value.sql", "04_channel_summary.sql", "06_assertions.sql"]:
            conn.execute((ROOT/"sql"/script).read_text())
        outputs = {
            "sql_acquisition_funnel.csv": query_frame(conn, "SELECT * FROM mart.acquisition_funnel ORDER BY origin"),
            "sql_seller_90d_value.csv": query_frame(conn, "SELECT * FROM mart.seller_90d_value ORDER BY mql_id"),
            "sql_channel_90d_summary.csv": query_frame(conn, "SELECT * FROM mart.channel_90d_summary ORDER BY origin"),
            "sql_seller_first_sale.csv": query_frame(conn, "SELECT * FROM mart.seller_first_sale ORDER BY seller_id"),
            "sql_cumulative_activation_by_day.csv": query_frame(conn, "SELECT * FROM mart.cumulative_activation_by_day ORDER BY origin,day_since_win"),
            "sql_reconciliation_source.csv": query_frame(conn, (ROOT/"sql"/"05_reconciliation.sql").read_text()),
        }
        for filename, df in outputs.items():
            df.to_csv(OUT/filename, index=False)

    # Exact row-level parity across every Python seller-mart and channel-summary column.
    py_seller = pd.read_csv(OUT/"seller_90d_value.csv")
    sql_seller = pd.read_csv(OUT/"sql_seller_90d_value.csv")
    py_channel = pd.read_csv(OUT/"channel_90d_summary.csv")
    sql_channel = pd.read_csv(OUT/"sql_channel_90d_summary.csv")
    checks = _compare_frames("seller_mart", py_seller, sql_seller, "mql_id")
    checks += _compare_frames("channel_summary", py_channel, sql_channel, "origin")

    # Close-day reconciliation plus every metric returned by 05_reconciliation.sql.
    py_close = pd.to_numeric(py_seller.close_days, errors="coerce")
    source = pd.read_csv(OUT/"sql_reconciliation_source.csv")
    py_funnel = pd.read_csv(OUT/"acquisition_funnel.csv")
    py_orders = pd.read_csv(RAW/"olist_orders_dataset.csv")
    py_items = pd.read_csv(RAW/"olist_order_items_dataset.csv")
    py_deals = pd.read_csv(RAW/"olist_closed_deals_dataset.csv")
    py_mature = py_seller.mature_90d.astype(bool)
    py_linked = py_mature & py_seller.seller_linked_to_order_items.astype(bool)
    data_end = pd.to_datetime(py_seller.data_end, errors="coerce").dropna()
    values = {
        "qualified_leads": float(py_funnel.qualified_leads.sum()),
        "closed_deals": float(py_deals.mql_id.nunique()),
        "orders": float(py_orders.order_id.nunique()),
        "order_items": float(len(py_items)),
        "item_price_sum": float(pd.to_numeric(py_items.price, errors="coerce").sum()),
        "freight_sum": float(pd.to_numeric(py_items.freight_value, errors="coerce").sum()),
        "seller_mart_rows": float(len(py_seller)),
        "data_end_epoch_seconds": float(data_end.iloc[0].value/1e9) if len(data_end) else np.nan,
        "mature_deals": float(py_mature.sum()),
        "linked_mature_deals": float(py_linked.sum()),
        "activated_linked_mature_deals": float(pd.to_numeric(py_seller.loc[py_linked, "activated_90d"]).sum()),
        "strict_activated_linked_mature_deals": float(pd.to_numeric(py_seller.loc[py_linked, "activated_delivered_within_90d"]).sum()),
        "delivered_gmv_90d": float(pd.to_numeric(py_seller.loc[py_linked, "gmv_90d_delivered_only"]).sum()),
        "strict_delivered_gmv_90d": float(pd.to_numeric(py_seller.loc[py_linked, "gmv_90d_delivered_within_90d"]).sum()),
        "close_days_sum": float(py_close.sum()),
        "close_days_n": float(py_close.notna().sum()),
    }
    checks += _reconcile_source_totals(source, values)
    checks_df = pd.DataFrame(checks)
    checks_df.to_csv(OUT/"sql_python_reconciliation.csv", index=False)
    if checks_df.status.ne("PASS").any():
        failed = checks_df.loc[checks_df.status.ne("PASS")]
        raise AssertionError("SQL/Python reconciliation failed; inspect data/processed/sql_python_reconciliation.csv\n"+failed.to_string(index=False))
    print(f"PostgreSQL 16 workflow and all {len(checks_df)} reconciliation checks completed: 100% PASS.")
    print(checks_df.to_string(index=False))


if __name__ == "__main__":
    main()
