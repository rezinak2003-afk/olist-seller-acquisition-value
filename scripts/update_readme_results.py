"""Regenerate the README results section exclusively from processed CSV outputs."""
from __future__ import annotations
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"
README = ROOT / "README.md"
START = "<!-- BEGIN GENERATED RESULTS -->"
END = "<!-- END GENERATED RESULTS -->"


def read(name: str) -> pd.DataFrame:
    path = OUT / name
    if not path.exists():
        raise FileNotFoundError(f"Run `python -m src.pipeline` before refreshing README results: {path}")
    return pd.read_csv(path)


def pct(value: float, digits: int = 2) -> str:
    return "—" if pd.isna(value) else f"{value:.{digits}f}%"


def money(value: float) -> str:
    return "—" if pd.isna(value) else f"R${value:,.2f}"


def num(value: float) -> str:
    return "—" if pd.isna(value) else f"{int(value):,}"


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"]*len(headers)) + "|"]
    out.extend("| " + " | ".join(map(str, row)) + " |" for row in rows)
    return "\n".join(out)


def build_results() -> str:
    funnel = read("acquisition_funnel.csv")
    seller = read("seller_90d_value.csv")
    validation = read("validation_summary.csv").set_index("check")
    stats = read("statistics_summary.csv").set_index("metric")
    sensitivity = read("maturity_sensitivity.csv")
    pairs = read("pairwise_comparisons.csv")
    linkage = read("linkage_diagnostics.csv")
    concentration = read("gmv_concentration.csv").iloc[0]
    payments = read("gmv_and_payment_checks.csv").set_index("check")
    windows = read("window_sensitivity.csv")
    lead_type = read("conversion_by_lead_type.csv")
    segment = read("conversion_by_business_segment.csv")
    close = read("median_days_to_close_by_origin.csv")

    total_leads = int(funnel.qualified_leads.sum())
    closed = int(funnel.closed_leads.sum())
    mature = seller.loc[seller.mature_90d.astype(bool)]
    linked = mature.loc[mature.seller_linked_to_order_items.astype(bool)]
    activated = int(linked.activated_90d.sum())
    strict = int(linked.activated_delivered_within_90d.sum())
    unlinked = len(mature)-len(linked)
    data_end = str(validation.loc["data_end", "value"])
    out_of_bound = int(validation.loc["orders_outside_data_end", "value"])
    leaks = int(validation.loc["mature_windows_ending_after_data_end", "value"])
    data_end_date = pd.Timestamp(data_end).strftime("%Y-%m-%d %H:%M")

    s1 = stats.loc["purchase_window_delivered_activation"]
    s2 = stats.loc["delivery_completed_within_90d_activation"]
    primary = pairs.loc[
        pairs.outcome.eq("purchase_window:paid_search_vs_organic_search")
    ]
    if primary.empty:
        primary_text = "No eligible paid-search / organic-search pair met the minimum sample-size rule."
        primary_table = ""
    else:
        p = primary.iloc[0]
        primary_text = (
            f"Paid search was {p.rate_a_pct:.2f}% ({int(p.successes_a)}/{int(p.n_a)}) versus "
            f"organic search {p.rate_b_pct:.2f}% ({int(p.successes_b)}/{int(p.n_b)}), "
            f"difference **{p.risk_difference_a_minus_b_pp:+.2f} percentage points** "
            f"(Newcombe 95% CI {p.risk_difference_ci_95_low_pp:+.2f} to "
            f"{p.risk_difference_ci_95_high_pp:+.2f} pp; Fisher p={p.p_value:.4f}; "
            f"Holm-adjusted p={p.p_value_holm_adjusted:.4f})."
        )
        primary_table = md_table(
            ["Definition", "Paid search", "Organic search", "Difference (95% Newcombe CI)", "Fisher p", "Holm p"],
            [["Purchase-window", f"{p.rate_a_pct:.2f}% ({int(p.successes_a)}/{int(p.n_a)})",
              f"{p.rate_b_pct:.2f}% ({int(p.successes_b)}/{int(p.n_b)})",
              f"{p.risk_difference_a_minus_b_pp:+.2f} pp [{p.risk_difference_ci_95_low_pp:+.2f}, {p.risk_difference_ci_95_high_pp:+.2f}]",
              f"{p.p_value:.4f}", f"{p.p_value_holm_adjusted:.4f}"]]
        )

    rows = [
        ["Qualified leads", num(total_leads), "Distinct `mql_id`"],
        ["Closed seller deals", num(closed), f"{closed/total_leads*100:.2f}% of qualified leads"],
        ["Maturity cutoff", f"`{data_end_date}` (exclusive)", "Day after last calendar day with ≥50 purchases"],
        ["Mature 90-day deals", num(len(mature)), f"{num(len(seller)-len(mature))} immature deals excluded"],
        ["Mature seller linkage", f"{num(len(linked))}/{num(len(mature))} ({pct(len(linked)/len(mature)*100)})",
         f"{num(unlinked)} unlinked; outcomes remain NULL"],
        ["Observed purchase-window activation", f"{num(activated)}/{num(len(linked))} ({pct(100*s1.estimate)})",
         f"Wilson 95% CI {pct(100*s1.ci_95_low)}–{pct(100*s1.ci_95_high)}"],
        ["All-mature activation lower bound", f"{num(activated)}/{num(len(mature))} ({pct(100*activated/len(mature))})",
         "Conservative descriptive bound; unlinked outcomes are unknown"],
        ["Strict delivered-within-90-day activation", f"{num(strict)}/{num(len(linked))} ({pct(100*s2.estimate)})",
         f"Wilson 95% CI {pct(100*s2.ci_95_low)}–{pct(100*s2.ci_95_high)}"],
        ["Delivered item-price GMV", money(float(concentration.total_delivered_gmv_brl)), "Linked, mature sellers; BRL; item price only"],
        ["Data-end leakage check", str(leaks), f"{out_of_bound} raw orders occur on/after cutoff; zero mature windows leak"],
    ]
    chunks = [
        "## Generated results (refreshed from CSVs)",
        "",
        "The table below is generated by `scripts/update_readme_results.py`; regenerate the pipeline first so reported values stay aligned with the committed CSVs.",
        "",
        md_table(["Metric", "Current result", "Definition / caveat"], rows),
        "",
        "### Maturity-cutoff sensitivity",
        "",
        md_table(["Minimum purchases/day", "Exclusive `data_end`", "Mature 90-day deals"], [
            [str(int(r.min_orders_per_day)), str(r.data_end_exclusive), num(r.mature_90d_deals)]
            for r in sensitivity.itertuples(index=False)
        ]),
        "",
        "### Paid-search versus organic-search comparison",
        "",
        primary_text,
        "",
        primary_table,
        "",
        "The comparison is observational. Holm adjustment covers all eligible origin pairs within each activation definition; it is not evidence of incremental lift or a reason to shift spend.",
        "",
        "### Seller-ID linkage diagnostics",
        "",
        "Linkage is not uniform across dimensions. Rows below show the mature-deal denominator and the observed seller-ID bridge rate. These tables describe coverage, not marketplace activation.",
        "",
    ]
    link_rows = []
    wanted = linkage.loc[linkage.dimension.isin(["origin", "lead_type", "won_month"])].copy()
    wanted = wanted.sort_values(["dimension", "group_value"])
    for r in wanted.itertuples(index=False):
        link_rows.append([r.dimension, r.group_value, num(r.mature_deals), num(r.linked_deals),
                          num(r.unlinked_deals), pct(r.linkage_rate_pct)])
    chunks.append(md_table(["Dimension", "Group", "Mature deals", "Linked", "Unlinked", "Linkage"], link_rows))
    chunks.extend([
        "",
        "The linked-only activation rates are also reweighted by a logistic linkage-propensity model using origin, lead type, business segment and win month. The IPW estimates are sensitivity diagnostics only: weights are stabilized and capped at the 99th percentile, and measured-covariate adjustment cannot recover outcomes for unlinked sellers.",
        "",
        "### Additional business analyses",
        "",
        "| Analysis | Current outputs |",
        "|---|---|",
        f"| Logistic activation model | `activation_logistic_regression.csv` — adjusted odds ratios and robust 95% CIs for origin, lead type, business segment, business type and win month |",
        f"| 60/90/120-day windows | `window_sensitivity.csv` — mature and linked denominators and activation by origin |",
        f"| Cumulative activation | `cumulative_activation_by_day.csv`; [chart](reports/charts/cumulative_activation_by_day.png) |",
        f"| Lead-type and segment conversion | `conversion_by_lead_type.csv`; `conversion_by_business_segment.csv` |",
        f"| Median time to close | `median_days_to_close_by_origin.csv` |",
        f"| GMV concentration | Top 10 sellers = **{float(concentration.top_10_share_pct):.2f}%** of GMV; zero-GMV sellers = **{int(concentration.zero_gmv_sellers)} ({float(concentration.zero_gmv_share_pct):.2f}%)**; Gini = **{float(concentration.gini):.3f}**; [Lorenz chart](reports/charts/gmv_lorenz_curve.png) |",
        f"| All-status vs delivered GMV | {money(float(payments.loc['purchase_window_gmv_all_statuses_brl','value']))} vs {money(float(payments.loc['purchase_window_gmv_delivered_only_brl','value']))}; gap {money(float(payments.loc['all_status_vs_delivered_gap_brl','value']))} |",
        f"| Payments reconciliation | {float(payments.loc['payment_vs_item_price_plus_freight_within_R$1_pct','value']):.2f}% of {int(payments.loc['payment_reconciliation_comparable_orders','value']):,} comparable orders within R$1 of item price + freight |",
        "| Origin uncertainty plot | [Forest plot with Wilson 95% intervals](reports/charts/activation_forest_by_origin.png); n<20 groups are explicitly marked insufficient |",
        "",
        "### Generated visual outputs",
        "",
        "- [Interactive HTML dashboard](dashboard/index.html) — filter origins, activation definition and minimum n; KPIs and charts recalculate in-browser.",
        "- [Activation forest plot](reports/charts/activation_forest_by_origin.png)",
        "- [Cumulative activation by day](reports/charts/cumulative_activation_by_day.png)",
        "- [GMV Lorenz curve](reports/charts/gmv_lorenz_curve.png)",
        "",
        f"**Cleaning exceptions:** delivered orders missing a customer-delivery date = {int(validation.loc['delivered_orders_without_delivery_date','value'])}; non-delivered orders carrying a customer-delivery date = {int(validation.loc['non_delivered_orders_with_delivery_date','value'])}; negative close days = {int(validation.loc['negative_close_days','value'])}. See `docs/CLEANING_LOG.md`.",
    ])
    return "\n".join(chunks)


def main() -> None:
    text = README.read_text(encoding="utf-8")
    start = text.find(START)
    end = text.find(END)
    if start < 0 or end < 0 or end <= start:
        raise RuntimeError(f"README markers missing or malformed: {START} / {END}")
    content = build_results()
    updated = text[:start] + START + "\n\n" + content + "\n\n" + END + text[end+len(END):]
    README.write_text(updated, encoding="utf-8")
    print("README generated results refreshed from data/processed/*.csv")


if __name__ == "__main__":
    main()
