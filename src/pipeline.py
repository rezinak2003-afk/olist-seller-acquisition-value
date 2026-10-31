"""Run the Olist acquisition funnel, seller 90-day value and audit outputs."""
from __future__ import annotations
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from .config import (ROOT, RAW_DIR, REFERENCE_DIR, OUT_DIR, FILES, WINDOW_DAYS,
                     MIN_DAILY_ORDERS, MATURITY_SENSITIVITY_THRESHOLDS)
from .workbook import build_workbook
from .statistics import wilson_interval, bootstrap_stat_ci, channel_omnibus_tests
from .linkage import build_linkage_diagnostics
from .analytics import (conversion_by_dimension, activation_logistic_regression,
                        window_sensitivity, cumulative_activation_by_day,
                        gmv_concentration, status_and_payment_checks)

REQUIRED = {
    "leads": ["mql_id", "first_contact_date", "origin"],
    "deals": ["mql_id", "seller_id", "won_date"],
    "orders": ["order_id", "order_purchase_timestamp", "order_status"],
    "items": ["order_id", "seller_id", "price", "freight_value"],
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_source(key: str, required: bool = True) -> pd.DataFrame | None:
    if key == "payments":
        path = REFERENCE_DIR / FILES[key]
        if not path.exists():
            path = RAW_DIR / FILES[key]
    else:
        path = RAW_DIR / FILES[key]
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Missing {path}. Download the source file and follow DATA_SOURCES.md.")
        return None
    df = pd.read_csv(path, low_memory=False)
    missing = set(REQUIRED.get(key, []))-set(df.columns)
    if missing:
        raise ValueError(f"{path.name} is missing required columns: {sorted(missing)}")
    return df


def profile(name: str, df: pd.DataFrame) -> dict:
    return {"table": name, "rows": len(df), "columns": len(df.columns),
            "duplicate_rows": int(df.duplicated().sum()),
            "null_cells": int(df.isna().sum().sum()),
            "null_cell_pct": round(float(df.isna().sum().sum()/max(df.size, 1)*100), 4)}


def calculate_data_end(orders: pd.DataFrame, min_daily_orders: int = MIN_DAILY_ORDERS) -> pd.Timestamp:
    """Exclusive observation boundary: day after last date with >= threshold orders."""
    purchases = pd.to_datetime(orders["order_purchase_timestamp"], errors="coerce").dropna()
    if purchases.empty:
        return pd.NaT
    daily = pd.Series(1, index=pd.DatetimeIndex(purchases)).resample("D").sum()
    qualifying_days = daily.loc[daily >= int(min_daily_orders)]
    if qualifying_days.empty:
        return pd.NaT
    return qualifying_days.index.max() + pd.Timedelta(days=1)


def normalize_sources(leads, deals, orders, items):
    leads, deals, orders, items = leads.copy(), deals.copy(), orders.copy(), items.copy()
    for df, col in [(leads, "mql_id"), (deals, "mql_id"), (deals, "seller_id"),
                    (orders, "order_id"), (items, "order_id"), (items, "seller_id")]:
        df[col] = df[col].astype("string").str.strip()
        df.loc[df[col].eq(""), col] = pd.NA
    leads["first_contact_date"] = pd.to_datetime(leads["first_contact_date"], errors="coerce")
    deals["won_date"] = pd.to_datetime(deals["won_date"], errors="coerce")
    orders["order_purchase_timestamp"] = pd.to_datetime(orders["order_purchase_timestamp"], errors="coerce")
    for c in ["order_delivered_customer_date", "order_delivered_carrier_date", "order_approved_at"]:
        if c in orders:
            orders[c] = pd.to_datetime(orders[c], errors="coerce")
        elif c == "order_delivered_customer_date":
            orders[c] = pd.NaT
    for c in ["price", "freight_value"]:
        items[c] = pd.to_numeric(items[c], errors="coerce")
    return leads, deals, orders, items


def build_lead_funnel(leads: pd.DataFrame, deals: pd.DataFrame) -> pd.DataFrame:
    """Distinct MQL-level funnel counts and Wilson intervals by recorded origin."""
    closed_ids = set(deals.loc[deals["seller_id"].notna(), "mql_id"].dropna().astype(str))
    base = leads[["mql_id", "origin"]].copy()
    base["origin"] = base["origin"].fillna("(missing)").replace("", "(missing)")
    base["is_closed"] = base["mql_id"].astype(str).isin(closed_ids)
    rows = []
    for origin, g in base.groupby("origin", dropna=False):
        total = int(g["mql_id"].nunique())
        closed = int(g.loc[g["is_closed"], "mql_id"].nunique())
        lo, hi = wilson_interval(closed, total)
        rows.append({"origin": origin, "qualified_leads": total, "closed_leads": closed,
                     "lead_to_deal_conversion_pct": closed/total*100 if total else np.nan,
                     "conversion_ci_95_low_pct": lo*100, "conversion_ci_95_high_pct": hi*100,
                     "not_closed_leads": total-closed})
    return pd.DataFrame(rows).sort_values("qualified_leads", ascending=False).reset_index(drop=True)


def build_seller_value(deal_leads: pd.DataFrame, item_orders: pd.DataFrame,
                       data_end: pd.Timestamp, window_days: int = WINDOW_DAYS) -> pd.DataFrame:
    """One row per closed seller deal, with explicit NULL outcomes for unlinked IDs."""
    seller_deal = deal_leads.dropna(subset=["seller_id", "won_date"]).copy()
    item_seller = item_orders.dropna(subset=["seller_id", "order_purchase_timestamp"]).copy()
    items_by_seller = {sid: grp for sid, grp in item_seller.groupby("seller_id", sort=False)}
    parts = []
    for r in seller_deal.itertuples(index=False):
        start = r.won_date
        end = start + pd.Timedelta(days=window_days)
        mature = bool(pd.notna(data_end) and end <= data_end)
        seller_items = items_by_seller.get(r.seller_id)
        linked = seller_items is not None
        if not linked:
            orders = delivered_orders = delivered_by_day90_orders = items_90d = np.nan
            all_status_gmv = delivered_status_gmv = delivered_by_day90_gmv = freight = np.nan
            activated = activated_any = activated_by_day90 = np.nan
        else:
            window = seller_items[(seller_items["order_purchase_timestamp"] >= start) &
                                  (seller_items["order_purchase_timestamp"] < end)]
            delivered = window.loc[window["order_status"].eq("delivered")]
            delivered_by_day90 = delivered.loc[
                delivered["order_delivered_customer_date"].notna() &
                (delivered["order_delivered_customer_date"] >= start) &
                (delivered["order_delivered_customer_date"] < end)
            ]
            orders = int(window["order_id"].nunique())
            delivered_orders = int(delivered["order_id"].nunique())
            delivered_by_day90_orders = int(delivered_by_day90["order_id"].nunique())
            items_90d = int(len(window))
            all_status_gmv = float(window["price"].fillna(0).sum())
            delivered_status_gmv = float(delivered["price"].fillna(0).sum())
            delivered_by_day90_gmv = float(delivered_by_day90["price"].fillna(0).sum())
            freight = float(window["freight_value"].fillna(0).sum())
            activated = float(delivered_orders > 0)
            activated_any = float(orders > 0)
            activated_by_day90 = float(delivered_by_day90_orders > 0)
        lead_type = getattr(r, "lead_type", pd.NA)
        business_segment = getattr(r, "business_segment", pd.NA)
        business_type = getattr(r, "business_type", pd.NA)
        parts.append({
            "mql_id": r.mql_id, "seller_id": r.seller_id,
            "origin": r.origin if pd.notna(r.origin) and str(r.origin).strip() else "(missing)",
            "lead_type": lead_type if pd.notna(lead_type) and str(lead_type).strip() else "(missing)",
            "business_segment": business_segment if pd.notna(business_segment) and str(business_segment).strip() else "(missing)",
            "business_type": business_type if pd.notna(business_type) and str(business_type).strip() else "(missing)",
            "won_month": start.strftime("%Y-%m") if pd.notna(start) else "(missing)",
            "first_contact_date": r.first_contact_date, "won_date": start, "close_days": r.close_days,
            "window_start_inclusive": start, "window_end_exclusive": end,
            "data_end": data_end, "mature_90d": mature,
            "seller_linked_to_order_items": bool(linked), "orders_90d": orders,
            "delivered_orders_90d": delivered_orders,
            "orders_delivered_within_90d": delivered_by_day90_orders, "items_90d": items_90d,
            "activated_90d": activated, "activated_90d_any_status": activated_any,
            "activated_delivered_within_90d": activated_by_day90,
            "gmv_90d_all_statuses": all_status_gmv,
            "gmv_90d_delivered_only": delivered_status_gmv,
            "gmv_90d_delivered_within_90d": delivered_by_day90_gmv,
            "gmv_90d_non_delivered_proxy": all_status_gmv-delivered_status_gmv if linked else np.nan,
            "freight_90d_all_statuses": freight,
        })
    return pd.DataFrame(parts)


def build_channel_summary(seller_value: pd.DataFrame) -> pd.DataFrame:
    mature = seller_value.loc[seller_value["mature_90d"].astype(bool)].copy()
    rows = []
    for origin, g in mature.groupby("origin", dropna=False):
        linked = g.loc[g["seller_linked_to_order_items"].astype(bool)].copy()
        n_linked = len(linked)
        n_activated = int(linked["activated_90d"].sum()) if n_linked else 0
        lo, hi = wilson_interval(n_activated, n_linked)
        strict_n = int(linked["activated_delivered_within_90d"].sum()) if n_linked else 0
        strict_lo, strict_hi = wilson_interval(strict_n, n_linked)
        vals = linked["gmv_90d_delivered_only"].dropna()
        rows.append({
            "origin": origin, "mature_seller_deals": len(g),
            "linked_mature_seller_deals": n_linked,
            "unlinked_mature_seller_deals": int((~g["seller_linked_to_order_items"].astype(bool)).sum()),
            "marketplace_linkage_rate_pct": n_linked/len(g)*100 if len(g) else np.nan,
            "activated_sellers_90d": n_activated,
            "non_activated_linked_sellers_90d": n_linked-n_activated,
            "activation_rate_pct": n_activated/n_linked*100 if n_linked else np.nan,
            "activation_ci_95_low_pct": lo*100, "activation_ci_95_high_pct": hi*100,
            "activated_delivered_within_90d": strict_n,
            "delivery_within_90d_rate_pct": strict_n/n_linked*100 if n_linked else np.nan,
            "delivery_within_90d_ci_95_low_pct": strict_lo*100,
            "delivery_within_90d_ci_95_high_pct": strict_hi*100,
            "median_gmv_90d": float(vals.median()) if len(vals) else np.nan,
            "mean_gmv_90d": float(vals.mean()) if len(vals) else np.nan,
            "p90_gmv_90d": float(vals.quantile(.9)) if len(vals) else np.nan,
            "total_gmv_90d": float(vals.sum()) if len(vals) else np.nan,
            "total_gmv_delivered_within_90d": float(linked["gmv_90d_delivered_within_90d"].sum()) if n_linked else np.nan,
            "mean_gmv_delivered_within_90d": float(linked["gmv_90d_delivered_within_90d"].mean()) if n_linked else np.nan,
            "median_close_days_all_mature_deals": float(g["close_days"].median()) if g["close_days"].notna().any() else np.nan,
        })
    return pd.DataFrame(rows).sort_values("mature_seller_deals", ascending=False).reset_index(drop=True)


def _write_sensitivity(orders: pd.DataFrame, seller_deals: pd.DataFrame, out: Path):
    rows = []
    for threshold in MATURITY_SENSITIVITY_THRESHOLDS:
        end = calculate_data_end(orders, threshold)
        eligible = seller_deals.dropna(subset=["seller_id", "won_date"])
        n = int((eligible.won_date + pd.Timedelta(days=WINDOW_DAYS) <= end).sum()) if pd.notna(end) else 0
        rows.append({"min_orders_per_day": threshold, "data_end_exclusive": end,
                     "mature_90d_deals": n,
                     "rule":"day after latest calendar date with at least threshold order purchases"})
    pd.DataFrame(rows).to_csv(out/"maturity_sensitivity.csv", index=False)


def run() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    leads = read_source("leads")
    deals = read_source("deals")
    orders = read_source("orders")
    items = read_source("items")
    reviews = read_source("reviews", required=False)
    payments = read_source("payments", required=False)
    frames = {"leads": leads, "deals": deals, "orders": orders, "items": items}
    if reviews is not None: frames["reviews"] = reviews
    if payments is not None: frames["payments"] = payments
    pd.DataFrame([profile(k, v) for k, v in frames.items()]).to_csv(OUT_DIR/"table_profile.csv", index=False)

    manifest = []
    for key, frame in frames.items():
        search_dirs = [REFERENCE_DIR, RAW_DIR] if key == "payments" else [RAW_DIR]
        p = next((d/FILES[key] for d in search_dirs if (d/FILES[key]).exists()), None)
        manifest.append({"dataset_key": key, "filename": p.name if p else FILES[key],
                         "bytes": p.stat().st_size if p else np.nan,
                         "sha256": sha256(p) if p else "not_available",
                         "retrieval_date_recorded_by_user": "not_recorded", "source_url": "See DATA_SOURCES.md"})
    pd.DataFrame(manifest).to_csv(OUT_DIR/"source_manifest.csv", index=False)

    leads, deals, orders, items = normalize_sources(leads, deals, orders, items)
    if payments is not None:
        payments = payments.copy()
        payments["payment_value"] = pd.to_numeric(payments["payment_value"], errors="coerce")
    data_end = calculate_data_end(orders, MIN_DAILY_ORDERS)
    daily = pd.Series(1, index=pd.DatetimeIndex(orders["order_purchase_timestamp"].dropna())).resample("D").sum()
    qualifying_days = daily.loc[daily >= MIN_DAILY_ORDERS]
    last_qualifying_day = qualifying_days.index.max() if len(qualifying_days) else pd.NaT

    item_orders = items.merge(
        orders[["order_id", "order_purchase_timestamp", "order_status", "order_delivered_customer_date"]],
        on="order_id", how="left", validate="many_to_one", indicator="_order_match")
    deal_leads = deals.merge(leads[["mql_id", "first_contact_date", "origin"]], on="mql_id", how="left",
                             validate="many_to_one", indicator="_lead_match")
    deal_leads["origin"] = deal_leads["origin"].astype("string").fillna("(missing)").replace("", "(missing)")
    for c in ["lead_type", "business_segment", "business_type"]:
        if c not in deal_leads: deal_leads[c] = "(missing)"
        deal_leads[c] = deal_leads[c].astype("string").fillna("(missing)").replace("", "(missing)")
    deal_leads["close_days_raw"] = (deal_leads["won_date"]-deal_leads["first_contact_date"]).dt.days
    bad_close = deal_leads["close_days_raw"].isna() | (deal_leads["close_days_raw"] < 0)
    exceptions = deal_leads.loc[bad_close, ["mql_id", "seller_id", "first_contact_date", "won_date", "close_days_raw"]].copy()
    exceptions["exception_type"] = np.where(exceptions["close_days_raw"].isna(), "missing_date", "won_date_before_first_contact")
    exceptions.to_csv(OUT_DIR/"close_duration_exceptions.csv", index=False)
    deal_leads["close_days"] = deal_leads["close_days_raw"].where(deal_leads["close_days_raw"] >= 0, np.nan)
    deal_leads["won_month"] = deal_leads["won_date"].dt.strftime("%Y-%m")

    funnel = build_lead_funnel(leads, deals)
    funnel.to_csv(OUT_DIR/"acquisition_funnel.csv", index=False)
    seller_value = build_seller_value(deal_leads, item_orders, data_end)
    seller_value.to_csv(OUT_DIR/"seller_90d_value.csv", index=False)
    channel = build_channel_summary(seller_value)
    channel.to_csv(OUT_DIR/"channel_90d_summary.csv", index=False)
    _write_sensitivity(orders, deal_leads, OUT_DIR)

    mature = seller_value.loc[seller_value["mature_90d"].astype(bool)].copy()
    linked_mature = mature.loc[mature["seller_linked_to_order_items"].astype(bool)].copy()
    stat_rows = []
    for metric, values in [
        ("purchase_window_delivered_activation", linked_mature["activated_90d"]),
        ("delivery_completed_within_90d_activation", linked_mature["activated_delivered_within_90d"]),
    ]:
        n = int(values.notna().sum()); successes = int(values.fillna(0).sum())
        lo, hi = wilson_interval(successes, n)
        stat_rows.append({"metric": metric, "n": n, "successes": successes,
                          "estimate": successes/n if n else np.nan, "ci_95_low": lo,
                          "ci_95_high": hi, "method": "Wilson score interval; 95% confidence"})
    for metric, values, fn in [
        ("mean_delivered_gmv_90d_brl", linked_mature["gmv_90d_delivered_only"], "mean"),
        ("median_delivered_gmv_90d_brl", linked_mature["gmv_90d_delivered_only"], "median"),
    ]:
        ci = bootstrap_stat_ci(values, statistic=fn, reps=5000, seed=42)
        stat_rows.append({"metric": metric, "n": ci["n"], "successes": np.nan,
                          "estimate": ci["estimate"], "ci_95_low": ci["ci_low"],
                          "ci_95_high": ci["ci_high"],
                          "method": f"Percentile bootstrap {fn}; 5,000 resamples; seed=42"})
    pd.DataFrame(stat_rows).to_csv(OUT_DIR/"statistics_summary.csv", index=False)
    tests = channel_omnibus_tests(linked_mature, min_group_n=20, monte_carlo_reps=100_000)
    tests.to_csv(OUT_DIR/"inferential_tests.csv", index=False)
    tests.loc[tests.origin_a.ne("") & tests.origin_a.notna()].to_csv(OUT_DIR/"pairwise_comparisons.csv", index=False)

    # Linkage selection diagnostics; unlinked outcomes remain unobserved.
    linkage, ipw, linkage_model = build_linkage_diagnostics(seller_value)
    linkage.to_csv(OUT_DIR/"linkage_diagnostics.csv", index=False)
    ipw.to_csv(OUT_DIR/"ipw_activation_by_origin.csv", index=False)
    linkage_model.to_csv(OUT_DIR/"linkage_model.csv", index=False)

    # Additional analytical depth requested in the audit.
    conversion_by_dimension(deal_leads, leads, deals, "lead_type").to_csv(OUT_DIR/"conversion_by_lead_type.csv", index=False)
    conversion_by_dimension(deal_leads, leads, deals, "business_segment").to_csv(OUT_DIR/"conversion_by_business_segment.csv", index=False)
    close_by_origin = deal_leads.groupby("origin", dropna=False).close_days.agg(
        deal_rows="count", median_days_to_close="median", mean_days_to_close="mean").reset_index()
    close_by_origin.to_csv(OUT_DIR/"median_days_to_close_by_origin.csv", index=False)
    activation_logistic_regression(linked_mature).to_csv(OUT_DIR/"activation_logistic_regression.csv", index=False)
    window_sensitivity(deal_leads, item_orders, data_end).to_csv(OUT_DIR/"window_sensitivity.csv", index=False)
    cumulative_activation_by_day(deal_leads, item_orders, data_end).to_csv(OUT_DIR/"cumulative_activation_by_day.csv", index=False)
    concentration, lorenz = gmv_concentration(linked_mature)
    concentration.to_csv(OUT_DIR/"gmv_concentration.csv", index=False)
    lorenz.to_csv(OUT_DIR/"gmv_lorenz_curve.csv", index=False)
    status_and_payment_checks(linked_mature, orders, items, payments).to_csv(OUT_DIR/"gmv_and_payment_checks.csv", index=False)

    seller_ids_all = set(items["seller_id"].dropna())
    delivered_no_date = int((orders.order_status.eq("delivered") & orders.order_delivered_customer_date.isna()).sum())
    non_delivered_with_date = int((~orders.order_status.eq("delivered") & orders.order_delivered_customer_date.notna()).sum())
    outside_data_end = int((orders.order_purchase_timestamp >= data_end).sum()) if pd.notna(data_end) else np.nan
    mature_window_leaks = int((seller_value.loc[seller_value.mature_90d.astype(bool), "window_end_exclusive"] > data_end).sum()) if pd.notna(data_end) else np.nan
    linked_count = int(mature["seller_linked_to_order_items"].sum()) if len(mature) else 0
    activated_count = int(linked_mature["activated_90d"].sum()) if len(linked_mature) else 0
    validation = [
        {"check":"lead_mql_id_unique", "value":bool(leads.mql_id.is_unique), "detail":f"duplicate keys={int(leads.mql_id.duplicated().sum())}"},
        {"check":"deal_mql_id_unique", "value":bool(deals.mql_id.is_unique), "detail":f"duplicate keys={int(deals.mql_id.duplicated().sum())}"},
        {"check":"closed_deal_seller_id_unique", "value":bool(deals.seller_id.is_unique), "detail":f"duplicate seller IDs={int(deals.seller_id.duplicated().sum())}"},
        {"check":"order_id_unique", "value":bool(orders.order_id.is_unique), "detail":f"duplicate keys={int(orders.order_id.duplicated().sum())}"},
        {"check":"order_item_composite_key_unique", "value":bool(not items.duplicated(["order_id", "order_item_id"]).any()) if "order_item_id" in items else np.nan, "detail":"Duplicate (order_id, order_item_id) rows"},
        {"check":"deals_with_matching_lead_pct", "value":round(float(deal_leads._lead_match.eq("both").mean()*100), 2), "detail":"Share of deal rows with matching qualified-lead record"},
        {"check":"order_items_with_matching_order_pct", "value":round(float(item_orders._order_match.eq("both").mean()*100), 2), "detail":"Share of order-item rows with matching order record"},
        {"check":"max_order_purchase_timestamp", "value":str(orders.order_purchase_timestamp.max()), "detail":"Absolute latest purchase timestamp; includes sparse tail"},
        {"check":"last_qualifying_purchase_day", "value":str(last_qualifying_day), "detail":f"Last day with at least {MIN_DAILY_ORDERS} orders"},
        {"check":"data_end", "value":str(data_end), "detail":"Exclusive maturity boundary: qualifying day + 1 calendar day"},
        {"check":"min_daily_orders_rule", "value":MIN_DAILY_ORDERS, "detail":"Minimum order count on a calendar day to support maturity"},
        {"check":"orders_outside_data_end", "value":outside_data_end, "detail":"Raw order records with purchase timestamp >= exclusive data_end"},
        {"check":"mature_windows_ending_after_data_end", "value":mature_window_leaks, "detail":"Must equal zero"},
        {"check":"unparsed_lead_contact_dates", "value":int(leads.first_contact_date.isna().sum()), "detail":"Source date strings failing parsing"},
        {"check":"unparsed_deal_won_dates", "value":int(deals.won_date.isna().sum()), "detail":"Source dates failing parsing"},
        {"check":"unparsed_order_purchase_timestamps", "value":int(orders.order_purchase_timestamp.isna().sum()), "detail":"Source timestamps failing parsing"},
        {"check":"delivered_orders_without_delivery_date", "value":delivered_no_date, "detail":"Delivered status but no customer-delivery timestamp"},
        {"check":"non_delivered_orders_with_delivery_date", "value":non_delivered_with_date, "detail":"Non-delivered status but customer-delivery timestamp exists"},
        {"check":"deals_without_seller_id", "value":int(deals.seller_id.isna().sum()), "detail":"Excluded from seller outcomes; never assigned zero"},
        {"check":"closed_deal_sellers_found_in_order_items_count", "value":int(deals.seller_id.isin(seller_ids_all).sum()), "detail":"Closed-deal seller IDs present in any order-item row"},
        {"check":"closed_deal_sellers_found_in_order_items_pct", "value":round(float(deals.seller_id.isin(seller_ids_all).mean()*100), 2), "detail":"Cross-dataset linkage rate; unmatched sellers are unobserved"},
        {"check":"mature_seller_deals", "value":len(mature), "detail":"Deals with complete 90-day purchase observation window under 50/day cutoff"},
        {"check":"mature_seller_deals_linked_to_order_items_count", "value":linked_count, "detail":"Mature deals with seller ID appearing in order_items"},
        {"check":"mature_seller_linkage_rate_pct", "value":round(linked_count/len(mature)*100, 2) if len(mature) else np.nan, "detail":"Denominator is all mature seller deals"},
        {"check":"observed_activated_linked_mature_sellers", "value":activated_count, "detail":"Observed successes; unlinked outcomes excluded"},
        {"check":"activation_lower_bound_all_mature_pct", "value":round(activated_count/len(mature)*100, 2) if len(mature) else np.nan, "detail":"Conservative lower bound treating every unlinked mature seller as not yet observed, not as a true zero"},
        {"check":"immature_seller_deals_excluded", "value":int((~seller_value.mature_90d.astype(bool)).sum()), "detail":"Excluded from mature seller outcomes, not treated as zero"},
        {"check":"negative_close_days", "value":int((deal_leads.close_days_raw < 0).sum()), "detail":"Won date precedes first contact date"},
        {"check":"invalid_or_negative_close_days", "value":int(bad_close.sum()), "detail":"Missing dates or won date preceding first contact date"},
        {"check":"seller_value_mql_id_unique", "value":bool(seller_value.mql_id.is_unique), "detail":"Seller mart grain is one row per closed deal/MQL"},
        {"check":"negative_item_price_rows", "value":int((items.price < 0).sum()), "detail":"Rows requiring review; retained unless source definition indicates otherwise"},
        {"check":"null_item_price_rows", "value":int(items.price.isna().sum()), "detail":"Null item-price rows; zero-filled only for aggregate summation"},
    ]
    pd.DataFrame(validation).to_csv(OUT_DIR/"validation_summary.csv", index=False)
    build_workbook(OUT_DIR, ROOT/"excel"/"olist_validation_workbook.xlsx")
    print(f"Pipeline complete. {len(leads):,} leads; {len(deals):,} deals; {len(mature):,} mature deals; {linked_count:,} linked mature deals.")
    print(f"Maturity cutoff: {data_end} exclusive ({MIN_DAILY_ORDERS} orders/day minimum).")
    print(f"Outputs written to {OUT_DIR}")


if __name__ == "__main__":
    run()
