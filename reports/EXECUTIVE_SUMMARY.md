# Executive decision brief — Olist seller acquisition

## Decision
**Do not shift acquisition budget toward paid search based on this snapshot.** Run a controlled holdout or a pre-registered paid-search versus organic-search experiment, and instrument spend and seller identity before using activation to allocate budget.

## One decision number
Paid-search purchase-window activation was **90.8% (79/87)** versus **77.7% (80/103)** for organic search: a **+13.1 percentage-point** observed difference (Newcombe 95% CI **+2.6 to +23.1 pp**). The unadjusted Fisher exact p-value is **0.0177**, but the all-pairs Holm-adjusted p-value is **0.1773**. The primary comparison therefore does not clear the family-wise 5% threshold. It is an observational cohort difference, not an estimated causal effect.

## One material risk
Only **340 of 656 mature deals (51.8%)** link to seller transaction rows. The other **316** have unknown marketplace outcomes and stay NULL, not zero. Linkage rates vary by origin and deal attributes; propensity weighting is a useful sensitivity check but cannot recover outcomes for sellers who remain unlinked.

## Observation rule and current cohort
Maturity uses an exclusive `data_end` equal to the day after the last calendar day with at least 50 purchases. The last qualifying day is 27 August 2018; `data_end` is **28 August 2018 00:00**. The resulting mature cohort is 656 deals. Among the 340 linked mature sellers, observed purchase-window activation is 282/340 (**82.9%**, Wilson 95% CI 78.6%–86.6%); 282/656 (**43.0%**) is a conservative lower bound using all mature deals as denominator, not an estimate of true activation. Strict delivered-within-90-day activation is 258/340 (**75.9%**, Wilson 95% CI 71.1%–80.1%).

## Required data before budget decisions
1. **Spend by origin and time period:** actual media costs, campaign IDs and attribution rules to estimate CAC/ROI.
2. **Seller identity crosswalk:** a validated seller-ID bridge between the marketing funnel and marketplace transactions, with unmatched/error rates.
3. **Seller registration / go-live date:** distinguish seller onboarding and catalog publication from first marketplace order; `won_date` is only the funnel close date.

## Interpretation guardrails
- The 50-orders/day maturity cutoff is a modelling rule; see 10/50/100 thresholds in `maturity_sensitivity.csv`.
- The paid/organic comparison is selected on successful seller linkage and is not randomized. Holm correction covers all eligible origin pairs.
- Delivered item-price GMV is not profit, recognized revenue, CAC or ROI. The linked mature cohort's total delivered item-price GMV is R$330,080.56; the top 10 sellers account for 48.4%, and the Gini coefficient is 0.793.

## Next step
Run the paid/organic holdout only after spend and identity instrumentation are available; pre-specify the primary outcome, observation window and sample size. Until then, treat the channel ranking as a hypothesis for testing, not a budget recommendation.
