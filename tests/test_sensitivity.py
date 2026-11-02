import numpy as np
import pandas as pd

from src.sensitivity import (
    activation_bounds_by_origin,
    paid_organic_tipping_point,
    linkage_first_sale_timing,
    time_to_first_sale_by_origin,
    delivery_date_anomaly_impact,
    unknown_origin_gmv_bootstrap,
)


def _mature_fixture():
    start = pd.Timestamp("2024-01-01")
    return pd.DataFrame({
        "mql_id": ["m1", "m2", "m3", "m4"],
        "seller_id": ["s1", "s2", "s3", "s4"],
        "origin": ["paid_search", "paid_search", "organic_search", "organic_search"],
        "won_date": [start] * 4,
        "window_end_exclusive": [start + pd.Timedelta(days=90)] * 4,
        "mature_90d": [True] * 4,
        "seller_linked_to_order_items": [True, False, True, False],
        "activated_90d": [1.0, np.nan, 0.0, np.nan],
        "gmv_90d_delivered_only": [100.0, np.nan, 0.0, np.nan],
    })


def test_activation_bounds_keep_unlinked_outcomes_unknown_and_bound_them():
    b = activation_bounds_by_origin(_mature_fixture()).set_index("origin")
    assert b.loc["paid_search", "mature_deals_n"] == 2
    assert b.loc["paid_search", "observed_linked_activation_pct"] == 100.0
    assert b.loc["paid_search", "activation_lower_bound_pct"] == 50.0
    assert b.loc["paid_search", "activation_upper_bound_pct"] == 100.0
    assert b.loc["organic_search", "activation_lower_bound_pct"] == 0.0
    assert b.loc["organic_search", "activation_upper_bound_pct"] == 50.0
    assert b.loc["ALL_ORIGINS", "activation_lower_bound_pct"] == 25.0
    assert b.loc["ALL_ORIGINS", "activation_upper_bound_pct"] == 75.0


def test_tipping_point_emits_explicit_assumption_scenarios():
    b = activation_bounds_by_origin(_mature_fixture())
    t = paid_organic_tipping_point(b)
    assert set(t.scenario) == {
        "paid_unlinked_varies_organic_held_at_observed_linked_rate",
        "organic_unlinked_varies_paid_held_at_observed_linked_rate",
        "same_unlinked_activation_rate_in_both_origins",
    }
    assert "feasible_between_0_and_100_pct" in t


def test_first_sale_timing_separates_in_window_and_after_window():
    m = _mature_fixture().iloc[[0, 1]].copy()
    m.loc[m.index[1], "seller_linked_to_order_items"] = True
    items = pd.DataFrame({
        "seller_id": ["s1", "s2"],
        "order_purchase_timestamp": [pd.Timestamp("2024-02-01"), pd.Timestamp("2024-05-01")],
    })
    timing = linkage_first_sale_timing(m, items, pd.Timestamp("2024-12-31"))
    all_rows = timing.loc[timing.origin.eq("ALL_ORIGINS")].set_index("first_sale_timing")
    assert all_rows.loc["within_90d_window", "seller_deals_n"] == 1
    assert all_rows.loc["after_90d_before_data_end", "seller_deals_n"] == 1


def test_time_to_first_sale_marks_no_sale_as_right_censored():
    m = _mature_fixture()
    items = pd.DataFrame({
        "seller_id": ["s1", "s3"],
        "order_purchase_timestamp": [pd.Timestamp("2024-02-01"), pd.Timestamp("2024-04-15")],
    })
    out = time_to_first_sale_by_origin(m, items, pd.Timestamp("2024-06-30"))
    all_row = out.loc[out.origin.eq("ALL_ORIGINS")].iloc[0]
    assert all_row.first_sale_observed_before_data_end_n == 2
    assert all_row.right_censored_at_data_end_n == 2
    assert all_row.first_sale_within_90d_n == 1
    assert "right-censored" in all_row.censoring_note
    assert "independent/non-informative" in all_row.censoring_note
    assert "not a population median" in all_row.interpretation_status


def test_delivery_anomaly_impact_counts_linked_mature_sellers_only():
    mature = pd.DataFrame({"seller_id": ["s1", "s2"]})
    orders = pd.DataFrame({
        "order_id": ["o1", "o2", "o3"],
        "order_status": ["delivered", "cancelled", "delivered"],
        "order_delivered_customer_date": [pd.NaT, pd.Timestamp("2024-02-03"), pd.NaT],
    })
    items = pd.DataFrame({"order_id": ["o1", "o2", "o3"], "seller_id": ["s1", "s3", "s4"]})
    out = delivery_date_anomaly_impact(mature, orders, items).set_index("anomaly_type")
    assert out.loc["delivered_status_missing_customer_delivery_date", "source_order_count"] == 2
    assert out.loc["delivered_status_missing_customer_delivery_date", "mature_seller_deal_rows_affected"] == 1
    assert out.loc["non_delivered_status_has_customer_delivery_date", "mature_seller_deal_rows_affected"] == 0


def test_unknown_origin_bootstrap_is_bounded_and_reproducible():
    m = pd.DataFrame({
        "origin": ["unknown", "unknown", "paid_search", "organic_search"],
        "gmv_90d_delivered_only": [100.0, 50.0, 200.0, 150.0],
    })
    a = unknown_origin_gmv_bootstrap(m, reps=500, seed=42).iloc[0]
    b = unknown_origin_gmv_bootstrap(m, reps=500, seed=42).iloc[0]
    assert 0 <= a.ci_95_low_pct <= a.estimate_pct <= a.ci_95_high_pct <= 100
    assert a.ci_95_low_pct == b.ci_95_low_pct
    assert a.ci_95_high_pct == b.ci_95_high_pct


def test_regularized_activation_model_has_bounded_effect_estimates():
    from src.analytics import activation_logistic_regression

    rows = []
    for origin, successes, n in [("paid_search", 79, 87), ("organic_search", 80, 103),
                                 ("unknown", 59, 73), ("social", 24, 26)]:
        for i in range(n):
            rows.append({
                "origin": origin,
                "lead_type": "online_medium" if i % 3 else "offline",
                "activated_90d": int(i < successes),
            })
    result = activation_logistic_regression(pd.DataFrame(rows))
    assert result.odds_ratio.notna().all()
    assert result.ci_95_low.notna().all() and result.ci_95_high.notna().all()
    assert result.odds_ratio.max() < 100
    assert result.ci_95_high.max() < 100
    assert (result.events_per_parameter > 0).all()
    assert result.status.str.contains("L2-penalized").all()
