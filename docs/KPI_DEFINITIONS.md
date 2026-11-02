# KPI definitions and denominator contract

## Lead acquisition funnel
- **Qualified leads:** distinct `mql_id` in the Marketing Funnel dataset.
- **Closed deals:** distinct `mql_id` with a closed-deal row and non-null `seller_id`.
- **Lead-to-deal conversion:** closed qualified leads divided by qualified leads in the same recorded `origin` group; show numerator, denominator and Wilson 95% CI.
- `(missing)` means the source category was blank/null. `unknown` is a literal source value. Neither should be interpreted as a known paid-media channel.

## Maturity and linkage
- **Purchase window:** `[won_date, won_date + 90 days)`.
- **`data_end`:** exclusive snapshot boundary computed as the day after the last calendar day with at least 50 order purchases. It is not the absolute maximum timestamp.
- **Mature deal:** `won_date + 90 days <= data_end`.
- **Maturity sensitivity:** report mature deal counts at 10, 50 and 100 purchases per day. The 50/day cutoff is primary.
- **Marketplace linked:** seller ID appears in at least one marketplace `order_items` row at any observed date. It is not restricted to the post-win 90-day window and is therefore potentially outcome-dependent; it is not a pre-outcome identity crosswalk.
- **Unlinked outcome:** NULL/unobserved; never set to zero.
- **Linked/no qualifying order:** zero orders/GMV and `activated = FALSE`, because transaction-table coverage exists.

## Activation definitions
1. **Purchase-window delivered activation (primary):** at least one order purchased in the 90-day purchase window with source `order_status = 'delivered'`. Delivery may complete after day 90.
2. **Delivered within 90 days (strict sensitivity):** at least one order purchased in the 90-day window with `order_delivered_customer_date` also inside that window.

The denominators for both activation rates are mature, seller-linked deals. For all mature deals, report worst-case identification bounds: lower = observed linked successes / all mature deals; upper = (observed linked successes + unlinked mature deals) / all mature deals. These are not confidence intervals or adjusted point estimates. The primary 656-deal cohort has bounds of 42.99%–91.16%.

## Value measures
- **Delivered 90-day GMV (purchase-window):** sum of item `price` for delivered-status orders purchased in the post-win window.
- **Strict delivered GMV:** item `price` where both purchase and customer delivery timestamps fall in the 90-day window.
- **All-status item value:** item `price` across statuses in the purchase window; sensitivity only.
- **Freight:** `freight_value`, reported separately.
- GMV is not recognized revenue, contribution margin, profit, net settlement or ROI.

## Statistical reporting
- Use Wilson score CIs for proportions and Newcombe independent-Wilson CIs for pairwise risk differences.
- For all origin pairs with at least 20 linked mature observations, use two-sided Fisher exact tests with Holm correction applied across all eligible pairs within each definition. Run this for both purchase-window and strict activation.
- Use a five-origin fixed-margin Monte Carlo Pearson chi-square omnibus test; display the minimum expected cell count.
- The pre-specified origin comparison is paid search versus organic search. It remains observational and does not identify incremental channel lift.
- The activation model is a reduced L2-penalized binomial GLM using origin and lead type, with rare levels pooled at n<20 and alpha=0.05. It reports events, non-events and events-per-slope-parameter; conventional p-values are omitted for penalized estimates. At 58 non-events and 10 slope parameters (EPV 5.8), approximate penalized-Hessian intervals remain exploratory. IPW linkage adjustments are selection-bias sensitivity diagnostics, not a substitute for observed outcomes.
- GMV is highly skewed; report the median, mean, percentiles and Lorenz/Gini concentration, not the mean alone.
- No media spend or randomized assignment is supplied; CAC, ROI, payback and causal uplift cannot be calculated.


## Linkage and payment sensitivity metrics
- **First-sale timing:** compare earliest observed `order_purchase_timestamp` per seller with `won_date`: before win, within `[won_date, won_date+90d)`, after day 90 but before `data_end`, or no observed sale. The linked flag includes any sale date in the source snapshot.
- **Time-to-first-sale:** Kaplan–Meier event time is the first observed post-win sale; sellers with no observed sale before the exclusive `data_end` are mechanically right-censored at `data_end - won_date`. Standard KM interpretation requires independent censoring, which is doubtful because no-event sellers are also unlinked under the outcome-dependent order-item linkage rule. Pre-win first sales are separated; the median is assumption-dependent, not a population estimate.
- **Tipping point:** compute the unlinked activation rate required to equalize all-mature paid/organic rates under explicitly stated fixed-rate or common-rate assumptions. These are scenarios, not estimated unknown outcomes.
- **Payment reconciliation:** compare order-level payment total with order-level item price plus freight. Report the comparable-order denominator and tolerance separately for R$1.00 and R$0.01; do not describe tolerance matches as exact matches.
