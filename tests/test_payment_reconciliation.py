"""Tests for order-payment versus item-price-plus-freight reconciliation."""
import numpy as np
import pandas as pd

from src.analytics import status_and_payment_checks


def test_payment_reconciliation_calculates_both_tolerances_and_comparable_n():
    linked = pd.DataFrame({
        "gmv_90d_all_statuses": [10.0],
        "gmv_90d_delivered_only": [8.0],
    })
    orders = pd.DataFrame({"order_id": ["a", "b", "c", "d", "no_items"]})
    items = pd.DataFrame({
        "order_id": ["a", "b", "c", "d"],
        "price": [80.0, 60.0, 70.0, 90.0],
        "freight_value": [20.0, 40.0, 30.0, 10.0],
    })
    payments = pd.DataFrame({
        "order_id": ["a", "b", "c", "d"],
        "payment_value": [100.0, 100.005, 100.50, 101.50],
    })

    result = status_and_payment_checks(linked, orders, items, payments).set_index("check")

    assert result.loc["payment_reconciliation_comparable_orders", "value"] == 4
    assert result.loc["payment_vs_item_price_plus_freight_within_R$1_pct", "value"] == 75.0
    assert result.loc["payment_vs_item_price_plus_freight_within_R$0.01_pct", "value"] == 50.0


def test_payment_reconciliation_is_explicit_when_source_is_absent():
    linked = pd.DataFrame({
        "gmv_90d_all_statuses": [10.0],
        "gmv_90d_delivered_only": [8.0],
    })
    orders = pd.DataFrame({"order_id": ["a"]})
    items = pd.DataFrame({"order_id": ["a"], "price": [8.0], "freight_value": [2.0]})

    result = status_and_payment_checks(linked, orders, items, None).set_index("check")
    assert np.isnan(result.loc["payment_vs_item_price_plus_freight_within_R$1_pct", "value"])
    assert "not found" in result.loc["payment_vs_item_price_plus_freight_within_R$1_pct", "detail"]
