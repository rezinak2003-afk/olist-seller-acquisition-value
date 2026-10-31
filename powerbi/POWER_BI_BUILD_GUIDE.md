# Power BI Desktop build specification

## Status and source model

A native `.pbix` must be created, opened and validated in **Power BI Desktop for Windows**. This repository contains the import queries, model specification and DAX measures, but no PBIX is claimed as delivered. Run `python -m src.pipeline` first so `data/processed/` is current. In Power BI Desktop, create a text parameter named `ProjectRoot` containing the absolute project-folder path, then create one query for each named `let ... in` block in `PowerQuery_Load_Outputs.pq`.

The seller fact includes `origin`, `lead_type`, `business_segment`, `business_type`, `won_month`, `won_date`, `data_end`, both activation definitions, and all 90-day outcome fields. Keep unlinked outcomes blank/NULL; never turn unobserved into zero. Use the `Activation_Definition` disconnected table for the purchase-window / strict toggle.

## Model relationships

1. Create `DimOrigin` from distinct values across the funnel and seller facts, as shown in `DAX_MEASURES.dax`. Relate `DimOrigin[origin]` one-to-many to both fact tables. Do not relate the two facts directly.
2. Create `DimDate` as shown in `DAX_MEASURES.dax`. Relate `DimDate[Date]` one-to-many to `Seller_90d_Value[won_date_date]`. Mark it as the model date table.
3. Keep `Activation_Definition` disconnected; it switches the outcome used by activation measures.
4. Keep validation, pairwise tests, linkage diagnostics and model outputs disconnected unless a specific visual requires a deliberate relationship. They are supporting evidence tables, not transaction-level fact tables.

## Page 1 — Acquisition funnel

- Cards: qualified leads, closed leads, lead-to-deal conversion.
- Bar chart: qualified leads by origin; conversion rate by origin with Wilson interval and numerator/denominator in tooltip.
- Matrix: origin, qualified leads, closed leads, not-closed leads and conversion rate.
- Treat `(missing)` and `unknown` as data-quality categories, not actionable paid-media channels.

## Page 2 — Cohort maturity and seller-ID linkage

- Cards: mature seller deals, linked mature deals, unlinked mature deals, linkage percentage.
- Stacked bar: linked versus unlinked mature deals by origin.
- Matrix: mature, linked, unlinked and linkage rate by origin.
- Display the current snapshot counts (656 mature, 340 linked, 316 unlinked) with a dynamic note that the cohort is bounded by `data_end = 2018-08-28` and the 50-orders/day rule. Do not hard-code those counts into measures.

## Page 3 — Seller activation

- Add the `Activation_Definition[definition]` slicer (Purchase-window / Strict) and origin, won-month, lead-type slicers.
- Cards: activated linked sellers, linked mature denominator, activation %, Wilson lower and upper bounds.
- Bar: activation by origin. Show sample n on labels/tooltips and flag groups with n < 20 as insufficient data.
- Keep purchase-window activation and strict delivered-within-90-day activation clearly labelled. Never combine the two definitions.

## Page 4 — 90-day delivered item-price GMV

- Cards: delivered item-price GMV, median, mean and P90 (BRL).
- Bar: median GMV by origin; tooltip includes mean, P90, linked seller n and total.
- Distribution visual for `gmv_90d_delivered_only`; keep median visible beside the mean because the distribution is skewed.
- State that GMV is item price in BRL, not profit, net revenue or Olist-recognized revenue.

## Page 5 — Quality, linkage bias and statistical evidence

- Validation table: cutoff, maturity leakage, order date exceptions, negative close days and key uniqueness.
- Forest plot equivalent: show eligible pairwise origin contrasts with Newcombe confidence intervals; label each group n. Suppress or explicitly label n < 20 as insufficient.
- Display Fisher exact p-values and Holm-adjusted p-values for pairwise comparisons. Use the five-group Monte Carlo omnibus result for the overall origin test; do not report a Pearson chi-square approximation when expected cells are sparse.
- Show the activation logistic model and linkage-selection/IPW diagnostics as adjusted exploratory analyses, not causal estimates.
- Include GMV concentration (Lorenz/Gini), maturity window sensitivity and payment/status reconciliation.
- Subtitle: “Descriptive observational analysis. Origin is not randomized; missing seller-ID linkage can bias observed marketplace outcomes.”

## Global visual rules

- Show numerator and denominator beside every rate; show units and the cohort/window definition in titles.
- Treat unlinked sellers' outcomes as unobserved, not zero. Clearly state that IPW depends on a correctly specified linkage model and cannot eliminate unmeasured selection bias.
- Do not calculate CAC, ROI, payback or incremental lift: channel spend is unavailable.
- Do not imply the paid/organic association is causal or sufficient to reallocate budget.

## Final desktop QA checklist

- Save `powerbi/olist_seller_acquisition_value.pbix` from Power BI Desktop.
- Confirm all query paths load from the `ProjectRoot` parameter; the M templates use `/` separators and should work with the parameter on Windows.
- Verify slicers change the activation measures and Wilson intervals; verify numerator/denominator and n < 20 flags respond to filters.
- Verify the date/origin relationships are single-direction one-to-many and that facts are not joined directly.
- Export all five pages to `powerbi/export/olist_seller_acquisition_value.pdf`, add five page screenshots to `powerbi/screenshots/`, and commit the PBIX and exports.
- No PBIX, PDF export or Power BI screenshots are included until this desktop QA is completed.
