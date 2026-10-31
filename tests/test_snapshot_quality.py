"""Quality regressions recalculated from a small committed synthetic fixture."""
from pathlib import Path
import pandas as pd

from src.pipeline import calculate_data_end, normalize_sources, build_lead_funnel, build_seller_value

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "synthetic_olist"


def read_source(filename):
    return pd.read_csv(FIXTURE / filename, low_memory=False)


def derive_fixture():
    leads = read_source("olist_marketing_qualified_leads_dataset.csv")
    deals = read_source("olist_closed_deals_dataset.csv")
    orders = read_source("olist_orders_dataset.csv")
    items = read_source("olist_order_items_dataset.csv")
    leads, deals, orders, items = normalize_sources(leads, deals, orders, items)
    data_end = calculate_data_end(orders, 50)
    deal_leads = deals.merge(leads[["mql_id", "first_contact_date", "origin"]], on="mql_id", how="left")
    deal_leads["close_days"] = (deal_leads.won_date - deal_leads.first_contact_date).dt.days
    item_orders = items.merge(
        orders[["order_id", "order_purchase_timestamp", "order_status", "order_delivered_customer_date"]],
        on="order_id", how="left", validate="many_to_one"
    )
    seller = build_seller_value(deal_leads, item_orders, data_end)
    return leads, deals, orders, items, data_end, seller


def test_fixture_funnel_is_recomputed_from_source_rows():
    leads, deals, *_ = derive_fixture()
    funnel = build_lead_funnel(leads, deals)
    assert int(funnel.qualified_leads.sum()) == leads.mql_id.nunique()
    assert int(funnel.closed_leads.sum()) == deals.loc[deals.seller_id.notna(), "mql_id"].nunique()
    assert int(funnel.not_closed_leads.sum()) == int(funnel.qualified_leads.sum()-funnel.closed_leads.sum())


def test_fixture_maturity_and_seller_linkage_reconcile():
    _, deals, _, _, data_end, seller = derive_fixture()
    assert len(seller) == deals.loc[deals.seller_id.notna() & deals.won_date.notna(), "mql_id"].nunique()
    assert data_end == pd.Timestamp("2020-06-30")
    mature = seller.loc[seller.mature_90d]
    linked = mature.loc[mature.seller_linked_to_order_items]
    unlinked = mature.loc[~mature.seller_linked_to_order_items]
    assert len(linked)+len(unlinked) == len(mature)
    assert len(linked) == mature.seller_id.isin(set(read_source("olist_order_items_dataset.csv").seller_id)).sum()
    assert (mature.window_end_exclusive <= data_end).all()


def test_fixture_unlinked_outcomes_stay_null_and_strict_is_subset():
    _, _, _, _, _, seller = derive_fixture()
    unlinked = seller.loc[~seller.seller_linked_to_order_items]
    assert unlinked.gmv_90d_delivered_only.isna().all()
    assert unlinked.activated_90d.isna().all()
    linked = seller.loc[seller.mature_90d & seller.seller_linked_to_order_items]
    assert linked.gmv_90d_delivered_within_90d.sum() <= linked.gmv_90d_delivered_only.sum()+.01
    assert (linked.activated_delivered_within_90d <= linked.activated_90d).all()
