# Methodology and statistical decision log

## Grain and joins
- Qualified leads are analysed at distinct `mql_id` grain.
- Closed deals are analysed at `mql_id` / `seller_id` grain. The source snapshot has unique MQL and seller identifiers in the closed-deal table.
- Orders are at `order_id` grain; order items are item-line grain. Order timestamps/status are joined many-to-one to item rows, then aggregated before linking to seller deals.
- Reviews are used for source profiling only; they are not joined to the seller-value mart.
- Missing categorical values are normalized to the literal `(missing)`; the source category `unknown` remains distinct.

## Date, maturity and value decisions
- Timestamps are parsed year-first (`dayfirst=False`).
- The seller's 90-day purchase window is half-open: `[won_date, won_date + 90 days)`. An order exactly at day 90 is excluded.
- `data_end` is an **exclusive** cutoff, not the maximum timestamp in the file. Resample order purchases by calendar day, keep dates with at least `MIN_DAILY_ORDERS = 50`, then set `data_end = max(qualifying_day) + 1 calendar day`. This excludes the sparse tail after the last date with material order volume.
- Under the supplied snapshot, the last qualifying purchase day is 2018-08-27 and `data_end` is **2018-08-28 00:00:00**. Eighty-three raw order records fall on/after this boundary; no deal flagged mature has a 90-day window ending after it.
- Maturity sensitivity is reported at 10, 50 and 100 purchases/day. The 50/day rule is the primary specification; results are regenerated when it changes.
- A deal is mature only when `won_date + 90 days <= data_end`.
- Primary activation counts orders purchased in the 90-day window and marked `delivered` in the source snapshot. Strict activation also requires `order_delivered_customer_date` to be within that same window.
- Delivered GMV is the sum of order-item `price` in BRL. Freight is separate; this is not seller profit, recognized platform revenue or ROI.
- If a seller ID has no row in `order_items`, marketplace outcome fields remain NULL. If the seller is linked but has no order in the period, zero is a valid observed result.

## Statistical analysis
- Wilson score 95% intervals are used for proportions.
- Pairwise comparisons include every origin with at least 20 linked mature sellers, within each activation definition. Two-sided Fisher exact tests are used for each pair, with Holm adjustment across the pairwise family for that definition.
- Risk-difference confidence intervals use Newcombe's independent-Wilson method. Both purchase-window and strict definitions are reported.
- Five-origin omnibus comparisons use a fixed-margin Monte Carlo Pearson chi-square test. The minimum expected cell count is recorded; the Monte Carlo method avoids relying on an asymptotic chi-square approximation when expected counts are below five.
- The primary planned origin comparison is paid search versus organic search. The remaining eligible origin pairs are exploratory.
- Mean and median GMV uncertainty uses 5,000 percentile-bootstrap resamples with seed 42.
- The activation model is a reduced L2-penalized binomial GLM using origin and lead type only. Category levels with fewer than 20 observations are pooled. The model uses alpha=0.05 and reports odds ratios, approximate penalized-Hessian intervals, events, non-events and events-per-slope-parameter. Penalized coefficients do not receive conventional Wald p-values; group inference is reported separately using Fisher tests with Holm correction. With 58 non-events and 10 slope parameters (EPV=5.8), it remains exploratory, not a stable causal or predictive model.
- Linkage selection is modelled as `linked ~ origin + lead_type + business_segment + won_month`. Stabilized inverse-probability weights are capped at the 99th percentile. The IPW result is a sensitivity analysis; it cannot identify unobserved outcomes for unlinked sellers.
- GMV distribution across sufficiently sized origin groups is compared with Kruskal-Wallis H and epsilon-squared. This is descriptive and observational.

## Validation and provenance
- Validate primary keys and composite item keys, lead/deal and order/item join coverage, source timestamp parsing, delivery-date consistency, negative close durations, order purchases outside `data_end`, and mature-window leakage.
- The delivered-status exception counts are recorded, not silently imputed: delivered orders with no customer-delivery date and non-delivered orders with a customer-delivery date.
- Reconcile every seller-mart and channel-summary column plus `close_days` aggregates and the control totals in `05_reconciliation.sql` against Python outputs. The PostgreSQL runner writes `sql_python_reconciliation.csv` and exits non-zero if any row is not PASS.
- The raw CSVs are sourced from Kaggle under CC BY-NC-SA 4.0. Keep them out of Git; record their hashes and cite Olist. Check source conditions before redistributing data or using the materials commercially.


## Outcome-dependent seller linkage: bounds and timing

- A seller deal is marked linked when its `seller_id` appears in any observed `order_items` row. This definition is not restricted to the 90-day post-win window; therefore, linkage can depend on marketplace activity after the primary outcome window.
- For the 656 mature deals, 340 are linked and 316 are unlinked. Observed purchase-window activation among linked sellers is 282/340 = 82.94%.
- Worst-case (Manski-style) all-mature identification bounds use observed activations as the lower endpoint and assume every unlinked seller did not activate; the upper endpoint assumes every unlinked seller activated: `282/656 = 42.99%` to `(282 + 316)/656 = 91.16%`. These are identification bounds, not confidence intervals or point estimates. The same calculations are produced by origin.
- Paid/organic tipping-point scenarios vary unknown activation rates among unlinked sellers under explicit assumptions. With organic unlinked sellers held at the organic linked-cohort rate, paid unlinked activation of 57.62% equalizes the paid all-mature rate with that observed organic benchmark. Holding paid unlinked sellers at the paid linked-cohort rate would require 104.20% organic activation; a common unlinked rate would need 157.61%. The latter two are infeasible. These are sensitivity scenarios, not inferred rates.
- First-sale timing uses the earliest observed order-item purchase per linked seller. Of 340 linked mature sellers, 284 (83.53%) first sold within 90 days of `won_date`, while 56 (16.47%) first sold after day 90 but before the exclusive data cutoff. Thus, the link flag includes sellers whose first observed sale occurs after the measured outcome window.
- Time-to-first-sale uses the full mature cohort. A first observed post-win order before `data_end` is an event; sellers with no observed order before `data_end` are mechanically right-censored at `data_end - won_date`. Standard Kaplan–Meier interpretation requires independent/non-informative censoring. That assumption is doubtful here because all 316 no-event sellers are also unlinked under the outcome-dependent order-item linkage definition. The 127.6-day median and 69.0-day 90-day restricted mean are therefore assumption-dependent exploratory diagnostics, not population estimates. Pre-win activity is reported separately; none was observed in this mature cohort.
- Unknown-origin GMV share is the ratio of unknown-origin sellers' delivered item-price GMV to total delivered item-price GMV among linked mature sellers. Its uncertainty is estimated with 5,000 seller-level bootstrap resamples (seed 42); the interval is wide and is descriptive, not causal attribution.

## Sensitivity outputs

`maturity_sensitivity.csv` includes mature, linked and unlinked counts; linked-cohort activation; worst-case all-mature bounds; strict activation; and delivered GMV/median for 10, 50 and 100 purchases/day. Delivery-date anomaly impact is separately quantified in `delivery_date_anomaly_impact.csv`.
