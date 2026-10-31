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
- **Marketplace linked:** seller ID appears in at least one marketplace `order_items` row; this is a cross-file ID-coverage test, not proof of trading during the post-win period.
- **Unlinked outcome:** NULL/unobserved; never set to zero.
- **Linked/no qualifying order:** zero orders/GMV and `activated = FALSE`, because transaction-table coverage exists.

## Activation definitions
1. **Purchase-window delivered activation (primary):** at least one order purchased in the 90-day purchase window with source `order_status = 'delivered'`. Delivery may complete after day 90.
2. **Delivered within 90 days (strict sensitivity):** at least one order purchased in the 90-day window with `order_delivered_customer_date` also inside that window.

The denominators for both activation rates are mature, seller-linked deals. Also show `observed successes / all mature deals` as a conservative lower bound, not as an estimated true activation rate.

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
- Logistic-model odds ratios and 95% CIs adjust for origin, lead type, business segment, business type and win month. IPW linkage adjustments are selection-bias sensitivity diagnostics, not a substitute for observed outcomes.
- GMV is highly skewed; report the median, mean, percentiles and Lorenz/Gini concentration, not the mean alone.
- No media spend or randomized assignment is supplied; CAC, ROI, payback and causal uplift cannot be calculated.
