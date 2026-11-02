# Executive decision brief — Olist seller acquisition

## Decision
**Do not reallocate acquisition budget based on this observational snapshot.** Paid search has a higher observed purchase-window activation rate than organic search among linked mature sellers, but Holm-adjusted evidence does not clear the family-wise 5% threshold and seller linkage is outcome-dependent. Run a controlled holdout or pre-registered paid-search versus organic-search experiment after spend and seller identity instrumentation are available.

## Channel comparison — linked cohort only
Paid-search activation is **90.80% (79/87)** versus **77.67% (80/103)** for organic search: an observed difference of **+13.13 percentage points** (Newcombe 95% CI **+2.59 to +23.14 pp**). The unadjusted Fisher exact p-value is **0.0177**, while the all-pairs Holm-adjusted p-value is **0.1773**. This is an observational comparison among linked sellers, not an estimated causal effect or evidence for a budget shift.

## Linkage changes the interpretation
Only **340 of 656 mature deals (51.83%)** link to order-item seller IDs; **316 outcomes are unobserved**, not zero. The linked-cohort activation rate is **282/340 = 82.94%**. Across all 656 mature deals, worst-case identification bounds are **42.99%–91.16%**:
- Lower endpoint: assume every unlinked seller did not activate (282/656).
- Upper endpoint: assume every unlinked seller activated ((282+316)/656).
These are identification bounds, not confidence intervals or an estimated population rate.

The linkage indicator is based on seller appearance in order items at any observed date, not solely within the first 90 post-win days. Among the 340 linked mature sellers, **284 (83.53%)** first sold within 90 days, while **56 (16.47%)** first sold after day 90 but before the exclusive data cutoff. This is direct evidence that some sellers enter the linked cohort through post-window activity.

## Tipping-point interpretation
The observed linked-cohort paid-minus-organic gap is +13.13 pp. Under the scenario that organic unlinked sellers are held at organic's observed linked rate, paid unlinked activation of **57.62%** would equalize paid's all-mature rate with that observed organic benchmark. Under the reverse scenario, organic unlinked activation would need to be **104.20%**; a common unlinked activation rate in both origins would need to be **157.61%**. Those last two scenarios are infeasible. These are assumption-specific sensitivity scenarios, not estimates of the unknown outcomes.

## Time to first observed sale
A mechanically calculated Kaplan–Meier diagnostic gives a 127.6-day median and 69.0-day restricted mean event-free time through day 90. **Do not interpret these as population estimates:** all 316 right-censored observations are also unlinked sellers, and linkage is defined by any observed order-item appearance. Independent/non-informative censoring is therefore doubtful; the figures are assumption-dependent and exploratory only.

## GMV and unknown attribution
Linked mature sellers contributed **R$330,080.56** in delivered item-price GMV. The top 10 sellers account for **48.43%** of that total; the Gini coefficient is **0.793**. Sellers with `unknown` origin account for **R$122,608.14 from 73 sellers (37.14%)**, with a seller-bootstrap 95% interval of **12.27%–60.43%**. The wide interval and concentrated GMV make attribution completeness a high-priority data-quality issue.

Payment reconciliation was calculated on **98,665 comparable orders**: **99.75%** are within R$1.00 and **99.61%** within R$0.01 of item price plus freight. These are tolerance-based checks, not exact reconciliation.

## What would change the conclusion
A validated seller-ID crosswalk that reduces outcome-dependent linkage, campaign spend and attribution data, and a randomized or well-designed quasi-experimental comparison could change the channel decision. The paid/organic result should also be revisited if plausible unlinked activation rates fall outside the sensitivity assumptions shown in `paid_organic_tipping_point.csv`.

## Required inputs before budget decisions
1. **Spend by origin and time period:** actual media costs, campaign IDs and attribution rules to estimate CAC/ROI.
2. **Seller identity crosswalk:** a validated seller-ID bridge between the marketing funnel and marketplace transactions, with unmatched/error rates.
3. **Seller registration / go-live date:** distinguish seller onboarding and catalog publication from first marketplace order; `won_date` is only the funnel close date.

## Observation rule
Maturity uses an exclusive `data_end` equal to the day after the last calendar day with at least 50 purchases. The last qualifying day is 27 August 2018; `data_end` is **28 August 2018 00:00**. The primary mature cohort is 656 deals. Strict delivered-within-90-day activation is **258/340 = 75.88%** (Wilson 95% CI 71.06%–80.12%).

## Interpretation guardrails
- The 50-orders/day cutoff is a modelling rule; `maturity_sensitivity.csv` shows 10/50/100 alternatives with activation and GMV.
- Groups with fewer than 20 linked deals are insufficient for stable origin-level interpretation.
- Delivered GMV is item price in BRL, not profit, recognized revenue, CAC or ROI. No spend data or randomized assignment is supplied.
