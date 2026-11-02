"""Selection-bias bounds, first-sale timing and data-quality impact analyses."""
from __future__ import annotations

import numpy as np
import pandas as pd


def activation_bounds_by_origin(mature: pd.DataFrame) -> pd.DataFrame:
    """Worst-case Manski bounds when outcomes are unknown for unlinked sellers.

    Lower bound sets every unlinked seller to not activated; upper bound sets
    every unlinked seller to activated. These are identification bounds, not
    confidence intervals and not estimates of the unknown outcomes.
    """
    required = {"origin", "seller_linked_to_order_items", "activated_90d"}
    missing = required.difference(mature.columns)
    if missing:
        raise ValueError(f"mature is missing required columns: {sorted(missing)}")

    rows: list[dict] = []
    groups = [(str(origin), group) for origin, group in mature.groupby("origin", dropna=False)]
    groups.append(("ALL_ORIGINS", mature))
    for origin, group in groups:
        n_all = int(len(group))
        linked_mask = group["seller_linked_to_order_items"].fillna(False).astype(bool)
        linked = group.loc[linked_mask]
        n_linked = int(len(linked))
        n_unlinked = n_all - n_linked
        successes = int(pd.to_numeric(linked["activated_90d"], errors="coerce").fillna(0).sum())
        lower = successes / n_all if n_all else np.nan
        upper = (successes + n_unlinked) / n_all if n_all else np.nan
        observed = successes / n_linked if n_linked else np.nan
        rows.append({
            "origin": origin,
            "mature_deals_n": n_all,
            "linked_mature_deals_n": n_linked,
            "unlinked_mature_deals_n": n_unlinked,
            "observed_activated_linked_n": successes,
            "observed_linked_activation_pct": 100 * observed if pd.notna(observed) else np.nan,
            "activation_lower_bound_pct": 100 * lower if pd.notna(lower) else np.nan,
            "activation_upper_bound_pct": 100 * upper if pd.notna(upper) else np.nan,
            "unlinked_share_pct": 100 * n_unlinked / n_all if n_all else np.nan,
            "bound_type": "Worst-case Manski identification bounds; not confidence intervals",
        })
    return pd.DataFrame(rows)


def paid_organic_tipping_point(bounds: pd.DataFrame) -> pd.DataFrame:
    """Scenarios for the unlinked outcomes needed to erase the observed gap.

    Scenarios are intentionally explicit: one-origin-at-a-time holds the other
    origin at its observed linked-cohort rate; common-rate assumes the same
    unknown activation probability for unlinked paid and organic sellers.
    """
    by_origin = bounds.set_index("origin")
    required_origins = {"paid_search", "organic_search"}
    if not required_origins.issubset(by_origin.index):
        return pd.DataFrame([{"scenario": "not_calculated", "status": "Required origins unavailable"}])

    p = by_origin.loc["paid_search"]
    o = by_origin.loc["organic_search"]
    np_all, no_all = int(p.mature_deals_n), int(o.mature_deals_n)
    up, uo = int(p.unlinked_mature_deals_n), int(o.unlinked_mature_deals_n)
    kp, ko = int(p.observed_activated_linked_n), int(o.observed_activated_linked_n)
    rp = float(p.observed_linked_activation_pct) / 100
    ro = float(o.observed_linked_activation_pct) / 100
    observed_gap_pp = (rp - ro) * 100

    rows: list[dict] = []
    paid_only = ((ro * np_all - kp) / up) if up else np.nan
    rows.append({
        "scenario": "paid_unlinked_varies_organic_held_at_observed_linked_rate",
        "origin_with_unknown_rate": "paid_search",
        "comparison_origin": "organic_search",
        "comparison_rate_basis": "organic linked-cohort observed rate",
        "observed_linked_gap_paid_minus_organic_pp": observed_gap_pp,
        "required_unlinked_activation_pct": 100 * paid_only if pd.notna(paid_only) else np.nan,
        "feasible_between_0_and_100_pct": bool(pd.notna(paid_only) and 0 <= paid_only <= 1),
        "interpretation": "Paid-search unlinked activation rate needed for the paid all-mature rate to equal organic's observed linked-cohort rate.",
    })
    organic_only = ((rp * no_all - ko) / uo) if uo else np.nan
    rows.append({
        "scenario": "organic_unlinked_varies_paid_held_at_observed_linked_rate",
        "origin_with_unknown_rate": "organic_search",
        "comparison_origin": "paid_search",
        "comparison_rate_basis": "paid linked-cohort observed rate",
        "observed_linked_gap_paid_minus_organic_pp": observed_gap_pp,
        "required_unlinked_activation_pct": 100 * organic_only if pd.notna(organic_only) else np.nan,
        "feasible_between_0_and_100_pct": bool(pd.notna(organic_only) and 0 <= organic_only <= 1),
        "interpretation": "Organic-search unlinked activation rate needed for the organic all-mature rate to equal paid's observed linked-cohort rate.",
    })
    denominator = (up / np_all) - (uo / no_all) if np_all and no_all else np.nan
    common = ((ko / no_all) - (kp / np_all)) / denominator if pd.notna(denominator) and not np.isclose(denominator, 0) else np.nan
    rows.append({
        "scenario": "same_unlinked_activation_rate_in_both_origins",
        "origin_with_unknown_rate": "paid_search_and_organic_search",
        "comparison_origin": "paid_search_vs_organic_search",
        "comparison_rate_basis": "same unknown activation rate applied to unlinked deals in both origins",
        "observed_linked_gap_paid_minus_organic_pp": observed_gap_pp,
        "required_unlinked_activation_pct": 100 * common if pd.notna(common) else np.nan,
        "feasible_between_0_and_100_pct": bool(pd.notna(common) and 0 <= common <= 1),
        "interpretation": "Common unlinked activation probability required to equalize the all-mature rates; values outside 0–100% mean no feasible common-rate tipping point.",
    })
    return pd.DataFrame(rows)


def linkage_first_sale_timing(mature: pd.DataFrame, item_orders: pd.DataFrame,
                              data_end: pd.Timestamp, window_days: int = 90) -> pd.DataFrame:
    """Show when the first observed seller order occurs relative to the win date."""
    first = (item_orders.dropna(subset=["seller_id", "order_purchase_timestamp"])
             .groupby("seller_id", as_index=True)["order_purchase_timestamp"].min())
    d = mature.loc[mature["seller_linked_to_order_items"].fillna(False).astype(bool)].copy()
    d["first_order_date"] = d["seller_id"].map(first)
    end = d["won_date"] + pd.Timedelta(days=window_days)
    cats = [
        d["first_order_date"] < d["won_date"],
        (d["first_order_date"] >= d["won_date"]) & (d["first_order_date"] < end),
        (d["first_order_date"] >= end) & (d["first_order_date"] < data_end),
        d["first_order_date"] >= data_end,
    ]
    d["first_sale_timing"] = np.select(
        cats,
        ["before_won_date", "within_90d_window", "after_90d_before_data_end", "on_or_after_data_end"],
        default="no_first_order_date",
    )
    rows: list[dict] = []
    for origin, group in list(d.groupby("origin", dropna=False)) + [("ALL_ORIGINS", d)]:
        n = int(len(group))
        counts = group["first_sale_timing"].value_counts()
        for label in ["before_won_date", "within_90d_window", "after_90d_before_data_end",
                      "on_or_after_data_end", "no_first_order_date"]:
            count = int(counts.get(label, 0))
            rows.append({"origin": str(origin), "first_sale_timing": label,
                         "linked_mature_deals_n": n, "seller_deals_n": count,
                         "share_of_linked_origin_pct": 100 * count / n if n else np.nan,
                         "window_days": window_days,
                         "data_end_exclusive": data_end,
                         "linkage_definition": "Seller ID appears in order_items at any observed date"})
    return pd.DataFrame(rows)


def _km_summary(durations: np.ndarray, events: np.ndarray) -> tuple[float, float]:
    """Return Kaplan-Meier median and 90-day restricted mean event-free time."""
    if len(durations) == 0:
        return np.nan, np.nan
    order = np.argsort(durations)
    durations = durations[order].astype(float)
    events = events[order].astype(int)
    survival = 1.0
    last_t = 0.0
    area = 0.0
    median = np.nan
    for t in np.unique(durations):
        # Restricted mean is integrated only through day 90, while the KM
        # median is allowed to use all observed event times before data_end.
        area += survival * max(0.0, min(float(t), 90.0) - min(last_t, 90.0))
        at_risk = int(np.sum(durations >= t))
        event_n = int(np.sum((durations == t) & (events == 1)))
        if at_risk and event_n:
            survival *= (1 - event_n / at_risk)
            if pd.isna(median) and survival <= 0.5:
                median = float(t)
        last_t = float(t)
    if last_t < 90:
        area += survival * (90.0 - last_t)
    return median, area


def time_to_first_sale_by_origin(mature: pd.DataFrame, item_orders: pd.DataFrame,
                                 data_end: pd.Timestamp) -> pd.DataFrame:
    """Kaplan-Meier time-to-first-order analysis over the observed horizon.

    Deals with no first order before the exclusive data_end are mechanically
    right-censored at data_end - won_date. Standard Kaplan-Meier interpretation
    additionally requires independent/non-informative censoring. That assumption
    is doubtful here because every no-event observation is also unlinked under
    the outcome-dependent seller/order-item linkage definition. The estimates
    must therefore be labelled assumption-dependent diagnostics, not population
    estimates. The output also separates events inside/outside 90d.
    """
    first = (item_orders.dropna(subset=["seller_id", "order_purchase_timestamp"])
             .groupby("seller_id", as_index=True)["order_purchase_timestamp"].min())
    d = mature.copy()
    d["first_order_date"] = d["seller_id"].map(first)
    observed_horizon = (data_end - d["won_date"]).dt.total_seconds() / 86400
    has_event = (d["first_order_date"].notna() &
                 (d["first_order_date"] >= d["won_date"]) &
                 (d["first_order_date"] < data_end))
    # A pre-win first order would indicate an already-active seller; report it
    # separately and do not treat it as a new-sale event.
    preexisting = d["first_order_date"].notna() & (d["first_order_date"] < d["won_date"])
    durations = np.where(
        has_event,
        (d["first_order_date"] - d["won_date"]).dt.total_seconds() / 86400,
        observed_horizon,
    )
    event_flag = has_event.astype(int).to_numpy()
    d["_duration_days"] = durations
    d["_event"] = event_flag
    d["_preexisting"] = preexisting
    rows: list[dict] = []
    for origin, group in list(d.groupby("origin", dropna=False)) + [("ALL_ORIGINS", d)]:
        eligible = group.loc[~group["_preexisting"]]
        dur = eligible["_duration_days"].to_numpy(float)
        evt = eligible["_event"].to_numpy(int)
        km_median, rmst90 = _km_summary(dur, evt)
        events_n = int(evt.sum())
        censored_n = int(len(evt) - events_n)
        within_90 = int(((eligible["_event"].eq(1)) & (eligible["_duration_days"] < 90)).sum())
        after_90 = events_n - within_90
        rows.append({
            "origin": str(origin), "mature_deals_n": int(len(group)),
            "preexisting_before_win_n": int(group["_preexisting"].sum()),
            "eligible_new_seller_n": int(len(eligible)),
            "first_sale_observed_before_data_end_n": events_n,
            "first_sale_within_90d_n": within_90,
            "first_sale_after_90d_before_data_end_n": after_90,
            "right_censored_at_data_end_n": censored_n,
            "kaplan_meier_median_days_to_first_sale": km_median,
            "restricted_mean_event_free_days_to_90d": rmst90,
            "censoring_note": (
                "No first order before the exclusive data_end; mechanically right-censored at "
                "data_end - won_date. Standard KM interpretation requires independent/non-informative "
                "censoring, which is doubtful because no-event observations are unlinked under the "
                "outcome-dependent order-item linkage rule. Treat the KM median as assumption-dependent "
                "and exploratory, not a population estimate. Pre-win orders are reported separately."
            ),
            "censoring_assumption_status": (
                "Likely informative / unverified: no-event sellers are exactly the unlinked sellers; "
                "comparable future-sale hazard cannot be assumed from these data"
            ),
            "interpretation_status": "Assumption-dependent exploratory diagnostic; not a population median",
        })
    return pd.DataFrame(rows)


def delivery_date_anomaly_impact(mature: pd.DataFrame, orders: pd.DataFrame,
                                 items: pd.DataFrame) -> pd.DataFrame:
    """Quantify delivery-date exceptions affecting mature closed-deal sellers."""
    mature_seller_ids = set(mature["seller_id"].dropna().astype(str))
    rows = []
    anomaly_masks = {
        "delivered_status_missing_customer_delivery_date": (
            orders["order_status"].eq("delivered") & orders["order_delivered_customer_date"].isna()
        ),
        "non_delivered_status_has_customer_delivery_date": (
            ~orders["order_status"].eq("delivered") & orders["order_delivered_customer_date"].notna()
        ),
    }
    item_ref = items[["order_id", "seller_id"]].dropna().drop_duplicates()
    for anomaly, mask in anomaly_masks.items():
        anomaly_orders = orders.loc[mask, "order_id"].dropna().unique()
        affected_items = item_ref.loc[item_ref["order_id"].isin(anomaly_orders)]
        affected_sellers = set(affected_items["seller_id"].astype(str)).intersection(mature_seller_ids)
        affected_deals = int(mature["seller_id"].astype("string").isin(affected_sellers).sum())
        rows.append({
            "anomaly_type": anomaly,
            "source_order_count": int(len(anomaly_orders)),
            "orders_with_item_rows": int(affected_items["order_id"].nunique()),
            "distinct_item_seller_ids": int(affected_items["seller_id"].nunique()),
            "mature_deal_sellers_affected": len(affected_sellers),
            "mature_seller_deal_rows_affected": affected_deals,
            "primary_activation_policy": "Primary activation follows purchase-window order_status='delivered'; delivery-date strict metric is reported separately. No timestamps are imputed.",
        })
    return pd.DataFrame(rows)


def unknown_origin_gmv_bootstrap(linked_mature: pd.DataFrame, reps: int = 5000,
                                 seed: int = 42) -> pd.DataFrame:
    """Bootstrap unknown-origin share of delivered GMV across linked mature sellers."""
    d = linked_mature.loc[linked_mature["gmv_90d_delivered_only"].notna(),
                          ["origin", "gmv_90d_delivered_only"]].copy()
    if d.empty or d["gmv_90d_delivered_only"].sum() <= 0:
        return pd.DataFrame([{"n_sellers": len(d), "estimate_pct": np.nan,
                              "ci_95_low_pct": np.nan, "ci_95_high_pct": np.nan,
                              "method": "Not calculated: no observed delivered GMV"}])
    values = pd.to_numeric(d["gmv_90d_delivered_only"], errors="coerce").fillna(0).to_numpy(float)
    is_unknown = d["origin"].astype(str).eq("unknown").to_numpy()
    rng = np.random.default_rng(seed)
    estimates = np.empty(reps, dtype=float)
    n = len(values)
    for i in range(reps):
        idx = rng.integers(0, n, size=n)
        denominator = values[idx].sum()
        estimates[i] = values[idx][is_unknown[idx]].sum() / denominator if denominator else np.nan
    total = float(values.sum())
    unknown_total = float(values[is_unknown].sum())
    valid = estimates[np.isfinite(estimates)]
    return pd.DataFrame([{
        "n_sellers": n, "unknown_origin_sellers": int(is_unknown.sum()),
        "total_delivered_gmv_brl": total, "unknown_origin_delivered_gmv_brl": unknown_total,
        "estimate_pct": 100 * unknown_total / total,
        "ci_95_low_pct": 100 * float(np.quantile(valid, 0.025)),
        "ci_95_high_pct": 100 * float(np.quantile(valid, 0.975)),
        "method": f"Seller-level nonparametric percentile bootstrap; {reps:,} resamples; seed={seed}; ratio of unknown-origin GMV to total GMV",
    }])
