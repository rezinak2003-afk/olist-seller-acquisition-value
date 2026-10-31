"""Diagnostics for the incomplete seller-ID bridge between deal and order data."""
from __future__ import annotations
import warnings
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss

LINKAGE_FEATURES = ["origin", "lead_type", "business_segment", "won_month"]


def _categorical_frame(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    x = pd.DataFrame(index=df.index)
    for col in columns:
        if col in df:
            x[col] = df[col].astype("string").fillna("(missing)").replace("", "(missing)")
        else:
            x[col] = "(missing)"
    return pd.get_dummies(x, drop_first=True, dtype=float)


def build_linkage_diagnostics(seller_value: pd.DataFrame, min_n: int = 1) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return linkage tables, IPW activation-by-origin, and model diagnostics.

    Weights are stabilized inverse probabilities among linked mature deals,
    calculated as marginal link prevalence / predicted link probability. They
    are truncated at the 99th percentile to limit single-row domination.
    """
    mature = seller_value.loc[seller_value["mature_90d"].astype(bool)].copy()
    if mature.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    mature["linked"] = mature["seller_linked_to_order_items"].astype(bool).astype(int)
    mature["won_month"] = pd.to_datetime(mature["won_date"], errors="coerce").dt.to_period("M").astype("string")

    group_frames = []
    for col in ["origin", "lead_type", "business_segment", "won_month"]:
        tmp = mature.copy()
        if col not in tmp:
            tmp[col] = "(missing)"
        tmp[col] = tmp[col].astype("string").fillna("(missing)").replace("", "(missing)")
        grouped = tmp.groupby(col, dropna=False).agg(
            mature_deals=("mql_id", "size"),
            linked_deals=("linked", "sum"),
        ).reset_index().rename(columns={col: "group_value"})
        grouped.insert(0, "dimension", col)
        grouped["unlinked_deals"] = grouped.mature_deals - grouped.linked_deals
        grouped["linkage_rate_pct"] = 100*grouped.linked_deals/grouped.mature_deals
        group_frames.append(grouped.loc[grouped.mature_deals >= min_n])
    linkage_table = pd.concat(group_frames, ignore_index=True) if group_frames else pd.DataFrame()

    # Model linkage selection using pre-outcome categorical fields only.
    x = _categorical_frame(mature, LINKAGE_FEATURES)
    y = mature["linked"].astype(int)
    keep = x.nunique(dropna=False).gt(1)
    x = x.loc[:, keep]
    if x.shape[1] == 0 or y.nunique() < 2:
        mature["link_probability"] = float(y.mean())
        auc = np.nan
        brier = np.nan
        model_status = "Not fit: no variable features or one linkage class"
    else:
        model = LogisticRegression(C=1e6, solver="lbfgs", max_iter=3000)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.fit(x, y)
        p = model.predict_proba(x)[:, 1]
        mature["link_probability"] = np.clip(p, 0.01, 0.99)
        auc = float(roc_auc_score(y, p)) if y.nunique() == 2 else np.nan
        brier = float(brier_score_loss(y, p))
        model_status = "Fit: logistic regression on origin, lead_type, business_segment and won_month"

    prevalence = float(y.mean())
    linked = mature.loc[mature["linked"].eq(1)].copy()
    linked["ipw_stabilized"] = prevalence/linked["link_probability"].clip(lower=0.01)
    cap = float(linked["ipw_stabilized"].quantile(.99)) if len(linked) else np.nan
    linked["ipw_stabilized_truncated"] = linked["ipw_stabilized"].clip(upper=cap) if len(linked) else []

    rows = []
    for origin, g in linked.groupby("origin", dropna=False):
        g = g.dropna(subset=["activated_90d"])
        if g.empty:
            continue
        weights = g["ipw_stabilized_truncated"].to_numpy(float)
        outcomes = g["activated_90d"].to_numpy(float)
        rows.append({
            "origin": origin, "linked_mature_n": len(g),
            "observed_activated_n": int(outcomes.sum()),
            "observed_activation_pct": 100*float(outcomes.mean()),
            "ipw_activation_pct": 100*float(np.average(outcomes, weights=weights)),
            "ipw_effective_sample_size": float(weights.sum()**2/(weights**2).sum()),
            "mean_stabilized_ipw": float(weights.mean()),
            "ipw_99pct_cap": cap,
        })
    ipw = pd.DataFrame(rows)
    model_info = pd.DataFrame([{
        "model": "linked ~ origin + lead_type + business_segment + won_month",
        "mature_deal_n": len(mature), "linked_n": int(y.sum()),
        "linkage_prevalence": prevalence, "auc_in_sample": auc,
        "brier_score_in_sample": brier, "status": model_status,
        "weighting": "Stabilized inverse probability of linkage; 99th percentile upper truncation",
        "warning": "Selection adjustment depends on measured covariates and model specification; it does not identify outcomes for unlinked sellers.",
    }])
    return linkage_table, ipw, model_info
