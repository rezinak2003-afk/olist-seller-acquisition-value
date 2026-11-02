"""Decision-support analyses built from the seller mart and source tables."""
from __future__ import annotations
import warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf


def conversion_by_dimension(deal_leads: pd.DataFrame, leads: pd.DataFrame,
                            deals: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """Qualified-to-closed conversion by a lead/deal attribute."""
    lead_cols = ["mql_id"]
    if dimension in leads.columns:
        lead_cols.append(dimension)
        base = leads[lead_cols].drop_duplicates("mql_id").copy()
        base[dimension] = base[dimension].astype("string").fillna("(missing)").replace("", "(missing)")
    elif dimension in deals.columns:
        d = deals[["mql_id", dimension]].drop_duplicates("mql_id")
        base = leads[["mql_id"]].drop_duplicates().merge(d, on="mql_id", how="left")
        base[dimension] = base[dimension].astype("string").fillna("(missing)").replace("", "(missing)")
    else:
        return pd.DataFrame(columns=[dimension, "qualified_leads", "closed_leads", "conversion_pct"])
    closed_ids = set(deals.loc[deals["seller_id"].notna(), "mql_id"].dropna().astype(str))
    base["closed"] = base.mql_id.astype(str).isin(closed_ids)
    out = base.groupby(dimension, dropna=False).agg(
        qualified_leads=("mql_id", "nunique"), closed_leads=("closed", "sum")
    ).reset_index()
    out["conversion_pct"] = 100*out.closed_leads/out.qualified_leads
    return out.sort_values("qualified_leads", ascending=False)


def activation_logistic_regression(linked_mature: pd.DataFrame) -> pd.DataFrame:
    """Parsimonious ridge-logistic sensitivity model with approximate Wald CIs.

    Only origin and lead_type are retained. Rare levels (<20) are pooled. The
    L2 penalty reduces separation and coefficient explosion; events-per-slope
    parameter is reported so readers can judge residual small-sample limits.
    This is adjusted association, not a causal effect.
    """
    from scipy.special import expit
    from scipy.stats import norm

    cols = ["activated_90d", "origin", "lead_type"]
    d = linked_mature.copy()
    for c in cols:
        if c not in d:
            d[c] = "(missing)"
    d = d[cols].dropna(subset=["activated_90d"]).copy()
    if d.empty or d.activated_90d.nunique() < 2:
        return pd.DataFrame([{"term": "(model)", "odds_ratio": np.nan,
                              "ci_95_low": np.nan, "ci_95_high": np.nan,
                              "p_value": np.nan,
                              "status": "Not fit: outcome has fewer than two classes"}])
    for c in ["origin", "lead_type"]:
        d[c] = d[c].astype("string").fillna("(missing)").replace("", "(missing)").astype(str)
        counts = d[c].value_counts(dropna=False)
        d[c] = d[c].where(d[c].map(counts).ge(20), "(pooled: n<20)")
    d["activated_90d"] = d["activated_90d"].astype(int)
    formula = "activated_90d ~ C(origin) + C(lead_type)"
    # Use a lighter penalty than the previous alpha=0.5 specification.
    # Coefficients and penalized-Hessian intervals remain exploratory; do not
    # attach conventional Wald p-values to penalized estimates.
    alpha = 0.05
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = smf.glm(formula, data=d, family=sm.families.Binomial())
            fit = model.fit_regularized(alpha=alpha, L1_wt=0.0, maxiter=2000, cnvrg_tol=1e-10)
        x = np.asarray(model.exog, dtype=float)
        beta = np.asarray(fit.params, dtype=float)
        mu = expit(np.clip(x @ beta, -30, 30))
        weights = mu * (1 - mu)
        penalty = np.eye(x.shape[1], dtype=float) * alpha
        penalty[0, 0] = 0.0  # retain an unpenalized intercept
        covariance = np.linalg.pinv(x.T @ (weights[:, None] * x) + penalty)
        standard_errors = np.sqrt(np.maximum(0.0, np.diag(covariance)))
        z = norm.ppf(0.975)
        events = int(d["activated_90d"].sum())
        non_events = int(len(d) - events)
        slope_parameters = max(1, x.shape[1] - 1)
        epv = min(events, non_events) / slope_parameters
        model_status = (
            "Fit: L2-penalized binomial GLM (alpha=0.05), origin + lead_type only; "
            "rare levels pooled at n<20; approximate penalized-Hessian intervals, "
            "not frequentist confidence intervals; p-values intentionally omitted. "
            + ("Low EPV; exploratory only." if epv < 10 else "")
        )
        rows = []
        for idx, term in enumerate(model.exog_names):
            coef = float(beta[idx])
            se = float(standard_errors[idx])
            rows.append({
                "term": term,
                "odds_ratio": float(np.exp(np.clip(coef, -30, 30))),
                "ci_95_low": float(np.exp(np.clip(coef - z * se, -30, 30))),
                "ci_95_high": float(np.exp(np.clip(coef + z * se, -30, 30))),
                "p_value": np.nan,
                "inference_note": "Not reported for L2-penalized coefficients; use Fisher/Holm tests for group comparisons",
                "n": int(len(d)), "events": events, "non_events": non_events,
                "slope_parameters": slope_parameters, "events_per_parameter": epv,
                "regularization_alpha": alpha,
                "status": model_status,
                "reference_levels": "Statsmodels treatment coding; first sorted category per factor",
                "formula": formula,
            })
        return pd.DataFrame(rows)
    except Exception as exc:
        return pd.DataFrame([{"term": "(model)", "odds_ratio": np.nan,
                              "ci_95_low": np.nan, "ci_95_high": np.nan,
                              "p_value": np.nan, "n": len(d),
                              "status": f"Not fit: {type(exc).__name__}: {exc}"}])


def window_sensitivity(deal_leads: pd.DataFrame, item_orders: pd.DataFrame,
                       data_end: pd.Timestamp, windows=(60, 90, 120)) -> pd.DataFrame:
    """Purchase-window activation sensitivity with mature, linked denominators."""
    rows = []
    deals = deal_leads.dropna(subset=["seller_id", "won_date"]).copy()
    item_seller = item_orders.dropna(subset=["seller_id", "order_purchase_timestamp"]).copy()
    lookup = {sid: grp for sid, grp in item_seller.groupby("seller_id", sort=False)}
    for days in windows:
        end_delta = pd.Timedelta(days=days)
        mature = deals.loc[deals.won_date + end_delta <= data_end]
        for origin, grp in mature.groupby("origin", dropna=False):
            linked_n = success = 0
            for r in grp.itertuples(index=False):
                data = lookup.get(r.seller_id)
                if data is None:
                    continue
                linked_n += 1
                w = data.loc[(data.order_purchase_timestamp >= r.won_date) &
                             (data.order_purchase_timestamp < r.won_date+end_delta)]
                success += int(w.loc[w.order_status.eq("delivered"), "order_id"].nunique() > 0)
            rows.append({"window_days":days, "origin":origin,
                         "mature_deals":len(grp), "linked_mature_deals":linked_n,
                         "activated_linked_deals":success,
                         "activation_pct":100*success/linked_n if linked_n else np.nan})
    return pd.DataFrame(rows)


def cumulative_activation_by_day(deal_leads: pd.DataFrame, item_orders: pd.DataFrame,
                                 data_end: pd.Timestamp, window_days: int = 90) -> pd.DataFrame:
    """Cumulative share of linked mature sellers by first delivered-order purchase day."""
    deals = deal_leads.dropna(subset=["seller_id", "won_date"]).copy()
    deals = deals.loc[deals.won_date + pd.Timedelta(days=window_days) <= data_end]
    items = item_orders.dropna(subset=["seller_id", "order_purchase_timestamp"]).copy()
    grouped = {sid: g for sid, g in items.groupby("seller_id", sort=False)}
    first_days = []
    for r in deals.itertuples(index=False):
        seller_orders = grouped.get(r.seller_id)
        if seller_orders is None:
            continue
        window = seller_orders.loc[
            (seller_orders.order_purchase_timestamp >= r.won_date) &
            (seller_orders.order_purchase_timestamp < r.won_date+pd.Timedelta(days=window_days)) &
            seller_orders.order_status.eq("delivered")
        ]
        if not window.empty:
            day = int((window.order_purchase_timestamp.min().normalize()-r.won_date.normalize()).days)
            first_days.append({"origin":r.origin, "first_activation_day":day})
    events = pd.DataFrame(first_days)
    rows = []
    for origin, grp in deals.groupby("origin", dropna=False):
        linked_n = int(grp.seller_id.isin(grouped).sum())
        origin_events = events.loc[events.origin.eq(origin), "first_activation_day"] if not events.empty else pd.Series(dtype=float)
        for day in range(window_days+1):
            successes = int(origin_events.le(day).sum())
            rows.append({"origin":origin, "day_since_win":day, "linked_mature_denominator":linked_n,
                         "cumulative_activated":successes,
                         "cumulative_activation_pct":100*successes/linked_n if linked_n else np.nan})
    return pd.DataFrame(rows)


def gini_coefficient(values) -> float:
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0 or np.allclose(x.sum(), 0):
        return float("nan")
    if np.min(x) < 0:
        x = x - x.min()
    x = np.sort(x)
    n = len(x)
    return float((2*np.sum((np.arange(1, n+1))*x)/(n*np.sum(x))) - (n+1)/n)


def gmv_concentration(linked_mature: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    x = linked_mature.gmv_90d_delivered_only.dropna().clip(lower=0).sort_values(ascending=False)
    total = float(x.sum())
    top10 = float(x.head(10).sum())
    lorenz = np.r_[0, np.cumsum(np.sort(x.to_numpy()))/total] if total else np.array([0])
    lorenz_df = pd.DataFrame({"seller_share_pct":np.linspace(0, 100, len(lorenz)),
                              "cumulative_gmv_share_pct":100*lorenz})
    summary = pd.DataFrame([{
        "linked_mature_sellers_with_observed_gmv":len(x), "total_delivered_gmv_brl":total,
        "top_10_sellers_gmv_brl":top10, "top_10_share_pct":100*top10/total if total else np.nan,
        "zero_gmv_sellers":int(x.eq(0).sum()), "zero_gmv_share_pct":100*float(x.eq(0).mean()) if len(x) else np.nan,
        "gini":gini_coefficient(x),
    }])
    return summary, lorenz_df


def status_and_payment_checks(linked_mature: pd.DataFrame, orders: pd.DataFrame,
                              items: pd.DataFrame, payments: pd.DataFrame | None) -> pd.DataFrame:
    rows = []
    rows.append({"check":"purchase_window_gmv_all_statuses_brl",
                 "value":float(linked_mature.gmv_90d_all_statuses.sum()),
                 "detail":"Linked mature sellers; item price; all order statuses"})
    rows.append({"check":"purchase_window_gmv_delivered_only_brl",
                 "value":float(linked_mature.gmv_90d_delivered_only.sum()),
                 "detail":"Linked mature sellers; delivered status only"})
    rows.append({"check":"all_status_vs_delivered_gap_brl",
                 "value":float(linked_mature.gmv_90d_all_statuses.sum()-linked_mature.gmv_90d_delivered_only.sum()),
                 "detail":"All-status item price minus delivered-status item price"})
    if payments is not None and not payments.empty:
        item_totals = items.groupby("order_id", as_index=False).agg(item_price=("price", "sum"), freight=("freight_value", "sum"))
        pay = payments.groupby("order_id", as_index=False).agg(payment_value=("payment_value", "sum"))
        check = orders[["order_id"]].drop_duplicates().merge(item_totals, on="order_id", how="left").merge(pay, on="order_id", how="left")
        comparable = check.dropna(subset=["item_price", "freight", "payment_value"]).copy()
        comparable["absolute_difference"] = (comparable.payment_value-(comparable.item_price+comparable.freight)).abs()
        reconciled = int(comparable.absolute_difference.le(.01).sum())
        reconciled_1 = int(comparable.absolute_difference.le(1.00).sum())
        rows.append({"check":"payment_vs_item_price_plus_freight_within_R$1_pct",
                     "value":100*reconciled_1/len(comparable) if len(comparable) else np.nan,
                     "detail":f"{reconciled_1}/{len(comparable)} orders within R$1.00; only orders with both item and payment totals"})
        rows.append({"check":"payment_vs_item_price_plus_freight_within_R$0.01_pct",
                     "value":100*reconciled/len(comparable) if len(comparable) else np.nan,
                     "detail":f"{reconciled}/{len(comparable)} orders within R$0.01; only orders with both item and payment totals"})
        rows.append({"check":"payment_reconciliation_comparable_orders",
                     "value":len(comparable), "detail":"Orders with non-null item, freight and payment totals"})
    else:
        rows.append({"check":"payment_vs_item_price_plus_freight_within_R$1_pct",
                     "value":np.nan, "detail":"Not calculated: supplementary payments CSV was not found"})
        rows.append({"check":"payment_vs_item_price_plus_freight_within_R$0.01_pct",
                     "value":np.nan, "detail":"Not calculated: supplementary payments CSV was not found"})
    return pd.DataFrame(rows)
