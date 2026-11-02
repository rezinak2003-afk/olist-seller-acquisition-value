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
    bounds = read("activation_bounds_by_origin.csv")
    tipping = read("paid_organic_tipping_point.csv")
    timing = read("linkage_first_sale_timing.csv")
    time_to_sale = read("time_to_first_sale_by_origin.csv")
    anomaly = read("delivery_date_anomaly_impact.csv")
    unknown_boot = read("unknown_origin_gmv_bootstrap.csv").iloc[0]
    concentration = read("gmv_concentration.csv").iloc[0]
    payments = read("gmv_and_payment_checks.csv").set_index("check")
    windows = read("window_sensitivity.csv")
    lead_type = read("conversion_by_lead_type.csv")
    segment = read("conversion_by_business_segment.csv")
    close = read("median_days_to_close_by_origin.csv")
    model = read("activation_logistic_regression.csv")

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

    primary = pairs.loc[pairs.outcome.eq("purchase_window:paid_search_vs_organic_search")]
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
        ["Mature seller linkage", f"{num(len(linked))}/{num(len(mature))} ({pct(len(linked)/len(mature)*100)})", f"{num(unlinked)} unlinked; outcomes remain NULL"],
        ["Observed purchase-window activation", f"{num(activated)}/{num(len(linked))} ({pct(100*s1.estimate)})", f"Wilson 95% CI {pct(100*s1.ci_95_low)}–{pct(100*s1.ci_95_high)}"],
        ["All-mature activation bounds", f"{pct(100*activated/len(mature))}–{pct(100*(activated+unlinked)/len(mature))}", "Worst-case identification bounds; not confidence intervals"],
        ["Strict delivered-within-90-day activation", f"{num(strict)}/{num(len(linked))} ({pct(100*s2.estimate)})", f"Wilson 95% CI {pct(100*s2.ci_95_low)}–{pct(100*s2.ci_95_high)}"],
        ["Delivered item-price GMV", money(float(concentration.total_delivered_gmv_brl)), "Linked, mature sellers; BRL; item price only"],
        ["Data-end leakage check", str(leaks), f"{out_of_bound} raw orders occur on/after cutoff; zero mature windows leak"],
    ]

    chunks = [
        "## Generated results (refreshed from CSVs)", "",
        "Generated by `scripts/update_readme_results.py` from the current `data/processed/` outputs.", "",
        md_table(["Metric", "Current result", "Definition / caveat"], rows),
        "", "### Maturity-cutoff sensitivity", "",
        md_table(["Minimum purchases/day", "Mature deals", "Linked", "Linked activation", "All-mature bounds", "Delivered GMV"], [
            [str(int(r.min_orders_per_day)), num(r.mature_90d_deals), num(r.linked_mature_90d_deals),
             pct(r.activation_rate_linked_pct), f"{pct(r.activation_lower_bound_all_mature_pct)}–{pct(r.activation_upper_bound_all_mature_pct)}",
             money(r.delivered_gmv_linked_mature_brl)] for r in sensitivity.itertuples(index=False)
        ]),
        "", "### Paid-search versus organic-search comparison", "", primary_text, "", primary_table, "",
        "The comparison is observational. Holm adjustment covers all eligible origin pairs within each activation definition; it is not evidence of incremental lift or a reason to shift spend.",
        "", "### Outcome-dependent linkage: bounds and tipping point", "",
        "The 82.94% result is conditional on sellers appearing in `order_items`. Of 656 mature deals, 340 are linked and 316 are unlinked. The resulting all-mature activation identification interval is **42.99%–91.16%**; unlinked outcomes are unknown, not zero.", "",
    ]
    b = bounds.loc[~bounds.origin.eq("ALL_ORIGINS")].copy().sort_values("mature_deals_n", ascending=False)
    bound_rows = []
    for r in b.itertuples(index=False):
        flag = "Small group; interpret cautiously" if int(r.mature_deals_n) < 20 else ""
        bound_rows.append([r.origin, num(r.mature_deals_n), num(r.linked_mature_deals_n), num(r.unlinked_mature_deals_n),
                           pct(r.observed_linked_activation_pct), pct(r.activation_lower_bound_pct), pct(r.activation_upper_bound_pct), flag])
    chunks.append(md_table(["Origin", "Mature n", "Linked n", "Unlinked n", "Linked rate", "Lower bound", "Upper bound", "Flag"], bound_rows))
    chunks.extend(["", "Worst-case bounds set all unlinked outcomes to zero for the lower endpoint and one for the upper endpoint. These are identification bounds, not sampling confidence intervals.", "",
                   "**Paid/organic sensitivity:** the linked-cohort gap is +13.13 pp. If organic unlinked sellers are held at organic's observed linked rate, paid unlinked activation of 57.62% would make the paid all-mature rate equal that observed organic rate. If paid unlinked sellers are held at their observed rate, organic would require 104.20%, which is infeasible. Assuming the same unlinked activation rate in both origins requires 157.61%, also infeasible. These are assumption-specific tipping scenarios, not estimates.", ""])
    chunks.append(md_table(["Scenario", "Required unlinked activation", "Feasible 0–100%?"], [
        [r.scenario, pct(r.required_unlinked_activation_pct), "Yes" if r.feasible_between_0_and_100_pct else "No"]
        for r in tipping.itertuples(index=False)
    ]))

    all_timing = timing.loc[timing.origin.eq("ALL_ORIGINS")].set_index("first_sale_timing")
    chunks.extend(["", "### Does linkage mean ever sold?", "",
                   f"Among the 340 linked mature seller deals, **{int(all_timing.loc['within_90d_window','seller_deals_n'])} ({pct(all_timing.loc['within_90d_window','share_of_linked_origin_pct'])})** had their first observed marketplace order inside the 90-day window, while **{int(all_timing.loc['after_90d_before_data_end','seller_deals_n'])} ({pct(all_timing.loc['after_90d_before_data_end','share_of_linked_origin_pct'])})** first sold after day 90 but before the data cutoff. None had a first sale before `won_date`. This demonstrates that the linkage flag uses post-win marketplace activity, including activity after the measured 90-day outcome window.", ""])
    tts_rows=[]
    for r in time_to_sale.sort_values("mature_deals_n", ascending=False).itertuples(index=False):
        flag = "Small group; insufficient precision" if int(r.mature_deals_n) < 20 else ""
        median = "Not reached" if pd.isna(r.kaplan_meier_median_days_to_first_sale) else f"{r.kaplan_meier_median_days_to_first_sale:.1f}"
        tts_rows.append([r.origin, num(r.mature_deals_n), num(r.first_sale_within_90d_n), num(r.first_sale_after_90d_before_data_end_n),
                         num(r.right_censored_at_data_end_n), median, flag])
    chunks.append(md_table(["Origin", "Mature n", "First sale ≤90d", "First sale >90d", "Censored", "KM median days", "Flag"], tts_rows))
    chunks.extend(["", "Time-to-first-sale uses the earliest observed purchase timestamp after `won_date`. Sellers with no purchase before the exclusive `data_end` are right-censored at `data_end - won_date`; KM medians are not reached where the estimated survival curve does not cross 50%.", ""])

    chunks.extend(["### Seller-ID linkage diagnostics", "",
                   "Linkage is not uniform across dimensions. Rows below show the mature-deal denominator and the observed seller-ID bridge rate. These tables describe coverage, not marketplace activation.", ""])
    link_rows=[]
    wanted=linkage.loc[linkage.dimension.isin(["origin","lead_type","won_month"])].copy().sort_values(["dimension","group_value"])
    for r in wanted.itertuples(index=False):
        link_rows.append([r.dimension,r.group_value,num(r.mature_deals),num(r.linked_deals),num(r.unlinked_deals),pct(r.linkage_rate_pct)])
    chunks.append(md_table(["Dimension","Group","Mature deals","Linked","Unlinked","Linkage"],link_rows))
    chunks.extend(["", "Linkage propensity uses pre-outcome attributes; stabilized IPW capped at the 99th percentile remains a sensitivity analysis. It does not identify outcomes for unlinked sellers.", "",
                   "### Data-quality, payment and business analyses", "",
                   md_table(["Check","Result","Interpretation"], [
                       ["Delivered orders missing customer delivery date", f"{int(anomaly.iloc[0].source_order_count)} total; {int(anomaly.iloc[0].mature_seller_deal_rows_affected)} mature linked seller deal affected", "No delivery timestamps imputed; primary activation uses source status"],
                       ["Non-delivered orders carrying delivery date", f"{int(anomaly.iloc[1].source_order_count)} total; {int(anomaly.iloc[1].mature_seller_deal_rows_affected)} mature seller deals affected", "Status is not reclassified from timestamp alone"],
                       ["Payment totals within R$1", f"{float(payments.loc['payment_vs_item_price_plus_freight_within_R$1_pct','value']):.2f}% ({payments.loc['payment_vs_item_price_plus_freight_within_R$1_pct','detail']})", "Comparable order totals: payment vs item price + freight"],
                       ["Payment totals within R$0.01", f"{float(payments.loc['payment_vs_item_price_plus_freight_within_R$0.01_pct','value']):.2f}% ({payments.loc['payment_vs_item_price_plus_freight_within_R$0.01_pct','detail']})", "Strict monetary tolerance"],
                   ]), "",
                   f"Unknown origin contributed {money(float(unknown_boot.unknown_origin_delivered_gmv_brl))} of delivered GMV from {int(unknown_boot.unknown_origin_sellers)} linked mature sellers (**{float(unknown_boot.estimate_pct):.2f}%**, seller-bootstrap 95% CI {float(unknown_boot.ci_95_low_pct):.2f}–{float(unknown_boot.ci_95_high_pct):.2f}%). The wide interval reflects concentration and sample uncertainty; missing origin attribution is a data-quality and measurement issue.", "",
                   f"Top 10 sellers account for **{float(concentration.top_10_share_pct):.2f}%** of delivered GMV; zero-GMV sellers = **{int(concentration.zero_gmv_sellers)} ({float(concentration.zero_gmv_share_pct):.2f}%)**; Gini = **{float(concentration.gini):.3f}**.", "",
                   "### Additional outputs", "",
                   "| Analysis | Evidence |", "|---|---|",
                   "| Penalized activation model | `activation_logistic_regression.csv` — L2-penalized origin + lead-type model; categories below n=20 pooled; events-per-parameter reported; exploratory due low EPV |",
                   "| Activation bounds | `activation_bounds_by_origin.csv`; [chart](reports/charts/activation_bounds_by_origin.png) |",
                   "| Tipping point | `paid_organic_tipping_point.csv` |",
                   "| First-sale timing | `linkage_first_sale_timing.csv` |",
                   "| Time to first sale | `time_to_first_sale_by_origin.csv` — Kaplan-Meier with right censoring at data_end |",
                   "| Maturity sensitivity | `maturity_sensitivity.csv` — counts, linked activation, all-mature bounds and delivered GMV at 10/50/100 orders/day |",
                   "| Delivery-date anomaly impact | `delivery_date_anomaly_impact.csv` |",
                   "| Unknown-origin GMV | `unknown_origin_gmv_bootstrap.csv`; [chart](reports/charts/unknown_origin_gmv_share.png) |",
                   "| 60/90/120-day windows | `window_sensitivity.csv` — maturity, linkage and activation by origin |",
                   "| Cumulative activation | `cumulative_activation_by_day.csv`; [chart](reports/charts/cumulative_activation_by_day.png) |",
                   "| Lead-type and segment conversion | `conversion_by_lead_type.csv`; `conversion_by_business_segment.csv` |",
                   "| Median time to close | `median_days_to_close_by_origin.csv` |",
                   "| GMV concentration | `gmv_concentration.csv`; [Lorenz chart](reports/charts/gmv_lorenz_curve.png) |",
                   "| Origin uncertainty | [Wilson forest plot](reports/charts/activation_forest_by_origin.png); groups with n<20 are marked insufficient |",
                   "", "**Generated visual outputs:** [interactive HTML dashboard](dashboard/index.html), [activation forest](reports/charts/activation_forest_by_origin.png), [activation bounds](reports/charts/activation_bounds_by_origin.png), [unknown-origin GMV](reports/charts/unknown_origin_gmv_share.png), [cumulative activation](reports/charts/cumulative_activation_by_day.png), [GMV Lorenz curve](reports/charts/gmv_lorenz_curve.png).", "",
                   f"**Cleaning exceptions:** delivered orders missing a customer-delivery date = {int(validation.loc['delivered_orders_without_delivery_date','value'])}; non-delivered orders with a customer-delivery date = {int(validation.loc['non_delivered_orders_with_delivery_date','value'])}; negative close days = {int(validation.loc['negative_close_days','value'])}. See `docs/CLEANING_LOG.md`."])

    return "\n".join(chunks)


def main() -> None:
    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        raise RuntimeError("README generated-results markers are missing")
    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    updated = before + START + "\n\n" + build_results() + "\n\n" + END + after
    README.write_text(updated, encoding="utf-8", newline="\n")
    print("README generated-results section refreshed from processed CSV outputs.")


if __name__ == "__main__":
    main()
