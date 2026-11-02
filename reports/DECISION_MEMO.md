# Decision memo — seller acquisition, linkage risk and value concentration

**Decision audience:** acquisition, seller growth and analytics leadership  
**Scope:** Olist marketing funnel joined to the supplied marketplace snapshot  
**Primary cohort:** 656 mature closed seller deals; seller outcomes are observed for 340 linked seller IDs

## Executive recommendation

Do not increase paid-search allocation based on the observed activation gap alone. Paid search has higher observed purchase-window activation than organic search among linked sellers, but the all-pairs Holm-adjusted p-value is 0.1773, and only 51.83% of mature deals link to order-item seller IDs. The linked group may be selected on post-win selling behaviour.

The most defensible next move is to improve measurement: validate the seller-ID crosswalk, capture channel spend/campaign attribution and seller registration/go-live dates, then test paid-search versus organic-search in a pre-registered holdout.

## 1. Channel result is a hypothesis, not a budget rule

| Measure | Paid search | Organic search |
|---|---:|---:|
| Mature deals | 144 | 204 |
| Linked mature deals | 87 | 103 |
| Linked activation | 90.80% (79/87) | 77.67% (80/103) |
| Unlinked mature deals | 57 | 101 |
| All-mature worst-case bounds | 54.86%–94.44% | 39.22%–88.73% |

Observed linked-cohort difference is +13.13 percentage points (Newcombe 95% CI +2.59 to +23.14 pp). Fisher p=0.0177; Holm-adjusted p=0.1773. The family-wise result does not meet the 5% threshold.

The bounds are computed by assigning every unlinked deal either no activation (lower endpoint) or activation (upper endpoint). They are identification bounds, not confidence intervals. Paid and organic bounds overlap substantially.

## 2. Unlinked outcomes could change the comparison

For all mature deals, paid activation is `(79 + 57 × q_paid) / 144` and organic activation is `(80 + 101 × q_organic) / 204`, where each q is the unknown activation probability among unlinked sellers in that origin.

Sensitivity scenarios:
- If organic's unlinked activation is set equal to its observed linked rate (77.67%), paid's unlinked activation would need to be 57.62% for the paid all-mature rate to equal that organic observed benchmark.
- If paid's unlinked activation is set equal to its observed linked rate (90.80%), organic's unlinked activation would need to be 104.20% to equalize with that paid benchmark, which is impossible.
- If the same unknown activation probability is assumed for unlinked sellers in both channels, the equalizing rate is 157.61%, also impossible.

These are distinct, deliberately specified assumptions. They do not identify the true unknown rates. The first scenario is feasible, demonstrating that plausible unobserved paid outcomes can eliminate the observed linked-cohort difference.

## 3. Linkage is not confined to the outcome window

The linkage flag is based on whether a seller appears in order items at any observed date. Among linked mature sellers:
- 284/340 (83.53%) first sold within 90 days of `won_date`.
- 56/340 (16.47%) first sold after day 90 but before the exclusive data cutoff.
- No pre-win first sale was observed in this mature cohort.

This is material: a seller can enter the linked analysis group through a sale after the outcome window used to define 90-day activation. Treating the 82.94% linked-cohort rate as if linkage were pre-outcome selection would be inappropriate.

The mechanically calculated full-mature-cohort Kaplan–Meier median is 127.6 days and the 90-day restricted mean event-free time is 69.0 days. **These are assumption-dependent diagnostics, not defensible population estimates.** Kaplan–Meier requires independent/non-informative censoring. Here, the 316 no-event records are exactly the 316 unlinked sellers, while linkage is defined by appearing in order-item data at any observed date. The censoring mechanism is therefore likely informative, and the future-sale hazard of unlinked sellers cannot be assumed to match linked sellers. Do not use 127.6 days as an expected time-to-sale forecast or as a population median.

## 4. Unknown origin and GMV concentration require measurement attention

Unknown-origin sellers account for R$122,608.14 of delivered item-price GMV, from 73 linked mature sellers: **37.14%** of the cohort's R$330,080.56 delivered GMV. A seller-level bootstrap interval is 12.27%–60.43%, which is wide because of concentration and finite sample variation.

The top 10 sellers account for 48.43% of GMV; Gini is 0.793. This means acquisition-origin summaries are not only affected by incomplete linkage but also by concentrated value. An “unknown” origin group this large should be treated as an attribution-quality problem, not as a scalable marketing channel.

## 5. Operational data-quality checks

Payment totals were compared with item price plus freight for 98,665 comparable orders:
- 98,416 (99.75%) were within R$1.00.
- 98,284 (99.61%) were within R$0.01.

The 8 delivered-status orders missing a customer-delivery date affect 1 mature seller deal; the 6 non-delivered orders with a customer-delivery date affect 0 mature deals. The primary metric follows purchase-window order status; strict activation additionally requires a delivery date inside the window. No timestamps are imputed and order statuses are not recoded.

## What would change the decision

1. A validated, pre-outcome seller identity crosswalk that materially improves the 51.83% linkage coverage.
2. Campaign-level spend, source/medium, campaign IDs and stable attribution rules, enabling CAC and incremental efficiency calculations.
3. Seller registration and catalog-live timestamps, separating close date from go-live and first-sale time.
4. A randomized paid-search versus organic-search holdout or a defensible quasi-experimental design with a pre-registered activation definition and observation window.
5. A future cohort with linkage and outcomes measured consistently for all mature deals, including sellers with no orders.

## Decision

**Hold paid/organic budget reallocation.** Improve identity and spend instrumentation first, then run a controlled test. The present data support a descriptive funnel and seller-value diagnostic, not causal channel ROI.
