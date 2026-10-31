from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = Path(os.getenv("OLIST_RAW_DIR", ROOT / "data" / "raw")).resolve()
REFERENCE_DIR = Path(os.getenv("OLIST_REFERENCE_DIR", ROOT / "data" / "reference")).resolve()
OUT_DIR = Path(os.getenv("OLIST_OUTPUT_DIR", ROOT / "data" / "processed")).resolve()
EXCEL_DIR = ROOT / "excel"

FILES = {
    "leads": "olist_marketing_qualified_leads_dataset.csv",
    "deals": "olist_closed_deals_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
}

# The latest isolated/sparse order records are not a defensible observation horizon.
# data_end is the day after the latest date with at least this many purchases.
MIN_DAILY_ORDERS = 50
MATURITY_SENSITIVITY_THRESHOLDS = (10, 50, 100)
WINDOW_DAYS = 90
