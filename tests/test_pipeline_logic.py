import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests

from src.pipeline import (
    build_lead_funnel, build_seller_value, build_channel_summary, calculate_data_end,
)
from src.statistics import (
    wilson_interval, channel_omnibus_tests, newcombe_difference_ci,
)


def test_lead_funnel_uses_distinct_mql_and_excludes_deals_without_seller():
    leads = pd.DataFrame({
        "mql_id": ["m1", "m2", "m3"],
        "origin": ["paid_search", "paid_search", None],
    })
    deals = pd.DataFrame({"mql_id": ["m1", "m3"], "seller_id": ["s1", None]})
    out = build_lead_funnel(leads, deals).set_index("origin")
    assert out.loc["paid_search", "qualified_leads"] == 2
    assert out.loc["paid_search", "closed_leads"] == 1
    assert out.loc["(missing)", "closed_leads"] == 0
    assert 0 < out.loc["paid_search", "conversion_ci_95_low_pct"]


def test_seller_mart_window_unlinked_nulls_and_delivery_timing():
    start = pd.Timestamp("2023-01-01")
    deals = pd.DataFrame({
        "mql_id": ["m1", "m2"], "seller_id": ["s1", "s2"],
        "won_date": [start, start], "origin": ["paid_search", "organic_search"],
        "first_contact_date": [start-pd.Timedelta(days=5)]*2, "close_days": [5, 5]
    })
    items = pd.DataFrame({
        "order_id": ["o1", "o2", "o3"], "seller_id": ["s1", "s1", "s1"],
        "order_purchase_timestamp": [start+pd.Timedelta(days=10), start+pd.Timedelta(days=20), start+pd.Timedelta(days=90)],
        "order_status": ["delivered", "delivered", "delivered"],
        "order_delivered_customer_date": [start+pd.Timedelta(days=15), start+pd.Timedelta(days=95), start+pd.Timedelta(days=95)],
        "price": [100.0, 200.0, 300.0], "freight_value": [10.0, 20.0, 30.0]
    })
    out = build_seller_value(deals, items, start+pd.Timedelta(days=200)).set_index("mql_id")
    assert bool(out.loc["m1", "seller_linked_to_order_items"])
    assert out.loc["m1", "orders_90d"] == 2
    assert out.loc["m1", "gmv_90d_delivered_only"] == 300.0
    assert out.loc["m1", "activated_90d"] == 1.0
    assert out.loc["m1", "activated_delivered_within_90d"] == 1.0
    assert np.isnan(out.loc["m2", "gmv_90d_delivered_only"])
    assert np.isnan(out.loc["m2", "activated_90d"])


def test_maturity_and_channel_denominators_are_explicit():
    start = pd.Timestamp("2023-01-01")
    deals = pd.DataFrame({"mql_id":["m1","m2"],"seller_id":["s1","s2"],"won_date":[start,start],
                          "origin":["a","a"],"first_contact_date":[start,start],"close_days":[0,0]})
    items = pd.DataFrame({"order_id":["o1"],"seller_id":["s1"],"order_purchase_timestamp":[start+pd.Timedelta(days=5)],
                          "order_status":["delivered"],"order_delivered_customer_date":[start+pd.Timedelta(days=8)],
                          "price":[50.0],"freight_value":[5.0]})
    seller = build_seller_value(deals,items,start+pd.Timedelta(days=91))
    assert seller["mature_90d"].all()
    channel = build_channel_summary(seller).iloc[0]
    assert channel["mature_seller_deals"] == 2
    assert channel["linked_mature_seller_deals"] == 1
    assert channel["unlinked_mature_seller_deals"] == 1
    assert channel["activation_rate_pct"] == 100.0


def test_data_end_ignores_sparse_tail_and_maturity_cannot_leak_past_cutoff():
    anchor = pd.Timestamp("2024-01-01")
    orders = pd.DataFrame({
        "order_purchase_timestamp": [anchor]*50 + [anchor+pd.Timedelta(days=80)]
    })
    data_end = calculate_data_end(orders, min_daily_orders=50)
    assert data_end == anchor + pd.Timedelta(days=1)

    deals = pd.DataFrame({
        "mql_id": ["matures_at_boundary", "crosses_boundary"],
        "seller_id": ["s1", "s2"],
        "won_date": [anchor-pd.Timedelta(days=89), anchor-pd.Timedelta(days=88)],
        "origin": ["paid_search", "organic_search"],
        "first_contact_date": [anchor-pd.Timedelta(days=100)]*2,
        "close_days": [11, 12],
    })
    items = pd.DataFrame(columns=["order_id", "seller_id", "order_purchase_timestamp", "order_status",
                                  "order_delivered_customer_date", "price", "freight_value"])
    mart = build_seller_value(deals, items, data_end)
    mature = mart.loc[mart.mature_90d]
    assert mature.mql_id.tolist() == ["matures_at_boundary"]
    assert (mature.window_end_exclusive <= data_end).all()
    assert not bool(mart.loc[mart.mql_id.eq("crosses_boundary"), "mature_90d"].iloc[0])


def test_wilson_and_newcombe_intervals_are_bounded():
    lo, hi = wilson_interval(8, 10)
    assert 0 < lo < .8 < hi < 1
    diff_lo, diff_hi = newcombe_difference_ci(79, 87, 80, 103)
    assert -1 <= diff_lo < (79/87-80/103) < diff_hi <= 1


def test_empty_omnibus_has_guarded_result():
    empty = pd.DataFrame(columns=["origin", "activated_90d", "gmv_90d_delivered_only"])
    result = channel_omnibus_tests(empty)
    assert result.iloc[0]["test"] == "Not run"


def test_paid_vs_organic_uses_fisher_holm_and_matches_statsmodels():
    rows=[]
    for origin, activated, n in [("paid_search", 79, 87), ("organic_search", 80, 103)]:
        rows.extend({"origin":origin,"activated_90d":int(i < activated),
                     "activated_delivered_within_90d":int(i < activated-6),
                     "gmv_90d_delivered_only":float(i*10)} for i in range(n))
    result=channel_omnibus_tests(pd.DataFrame(rows), min_group_n=20, monte_carlo_reps=1000)
    primary=result.loc[result.outcome.eq("purchase_window:paid_search_vs_organic_search")].iloc[0]
    expected=multipletests([primary.p_value], method="holm")[1][0]
    assert primary["test"] == "Fisher exact (two-sided)"
    assert primary.n == 190
    assert np.isclose(primary.p_value_holm_adjusted, expected)
    assert primary.risk_difference_ci_95_low_pp < primary.risk_difference_a_minus_b_pp < primary.risk_difference_ci_95_high_pp
    strict=result.loc[result.outcome.eq("strict_within_90d:paid_search_vs_organic_search")].iloc[0]
    assert np.isfinite(strict.p_value_holm_adjusted)


def test_origin_omnibus_uses_fixed_margin_monte_carlo():
    records=[]
    for origin, activated in [("a", 0), ("b", 1), ("c", 2)]:
        records.extend({"origin":origin,"activated_90d":int(i<activated),
                        "activated_delivered_within_90d":int(i<max(0, activated-1)),
                        "gmv_90d_delivered_only":float(i)} for i in range(20))
    result=channel_omnibus_tests(pd.DataFrame(records), min_group_n=20, monte_carlo_reps=1000)
    omnibus=result.loc[result.outcome.eq("purchase_window:origin_omnibus")].iloc[0]
    assert omnibus["test"].startswith("Monte Carlo Pearson chi-square")
    assert omnibus["p_value"] >= 0
    assert omnibus["minimum_expected_cell"] < 5


def test_eventual_delivery_after_day_90_is_separate_from_strict_activation_and_maturity():
    start = pd.Timestamp("2023-01-01")
    deals = pd.DataFrame({"mql_id":["m1","m2"],"seller_id":["s1","s2"],"won_date":[start,start],
                          "origin":["paid_search","organic_search"],"first_contact_date":[start,start],"close_days":[0,0]})
    items = pd.DataFrame({"order_id":["o1"],"seller_id":["s1"],
                          "order_purchase_timestamp":[start+pd.Timedelta(days=20)],
                          "order_status":["delivered"],
                          "order_delivered_customer_date":[start+pd.Timedelta(days=95)],
                          "price":[100.0],"freight_value":[10.0]})
    seller = build_seller_value(deals,items,start+pd.Timedelta(days=91)).set_index("mql_id")
    assert bool(seller.loc["m1","mature_90d"])
    assert seller.loc["m1","activated_90d"] == 1.0
    assert seller.loc["m1","activated_delivered_within_90d"] == 0.0
    assert not bool(seller.loc["m2","seller_linked_to_order_items"])
    assert bool(seller.loc["m2","mature_90d"])
    immature = build_seller_value(deals.iloc[[0]],items,start+pd.Timedelta(days=89))
    assert not bool(immature.iloc[0]["mature_90d"])
