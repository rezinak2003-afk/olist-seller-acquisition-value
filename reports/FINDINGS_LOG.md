# Findings log — regenerated with 50-orders/day maturity cutoff

| ID | Finding | Current metric | Evidence | Caveat / implication |
|---|---|---|---|---|
| F-001 | Overall lead conversion | 842 / 8,000 = 10.53% | `acquisition_funnel.csv` | Distinct MQL; origin is observational |
| F-002 | Mature population and linkage | 656 mature; 340 linked / 656 = 51.83%; 316 remain unlinked | `seller_90d_value.csv`; `linkage_diagnostics.csv` | Unlinked marketplace outcomes remain NULL, not zero |
| F-003 | Purchase-window delivered activation | 282 / 340 = 82.94%; Wilson 95% CI 78.58%–86.57% | `statistics_summary.csv` | Conditional on linked mature sellers |
| F-004 | Strict delivered-within-90-day activation | 258 / 340 = 75.88%; Wilson 95% CI 71.06%–80.12% | `statistics_summary.csv` | Both purchase and customer delivery must fall inside the window |
| F-005 | Delivered GMV is concentrated | R$330,080.56 total; top 10 sellers 48.43%; zero-GMV sellers 58 (17.06%); Gini 0.793 | `gmv_concentration.csv`; `gmv_lorenz_curve.csv` | Item-price GMV proxy, linked mature cohort only |
| F-006 | Paid search exceeds organic in the linked sample | 79/87 = 90.80% vs 80/103 = 77.67%; difference +13.13 pp; Newcombe CI +2.59 to +23.14 pp; Fisher p=0.0177; Holm p=0.1773 | `pairwise_comparisons.csv` | Not significant after Holm; observational; no budget shift supported |
| F-007 | GMV distributions across sufficiently sized origins | Kruskal-Wallis output in `inferential_tests.csv` | `inferential_tests.csv` | Descriptive rank comparison only; linked mature sellers |
| F-008 | Maturity depends on the volume rule | 665 deals at 10/day; 656 at 50/day; 654 at 100/day | `maturity_sensitivity.csv` | 50/day is primary and documented; cutoff is not absolute max timestamp |
| F-009 | Linkage creates wide full-cohort uncertainty | 42.99%–91.16% worst-case activation bounds for 656 mature deals | `activation_bounds_by_origin.csv` | Identification bounds, not confidence intervals or point estimates |
| F-010 | Linkage is partly determined by post-window selling | 284/340 first sold within 90 days; 56/340 first sold after day 90 but before `data_end` | `linkage_first_sale_timing.csv` | The `linked` flag is defined by any observed item sale, not a 90-day-only window |
| F-011 | Time to first sale is delayed and censored | All-origin KM diagnostic median 127.6 days; 90-day RMST 69.0 days; 316 right-censored and also unlinked; non-informative censoring doubtful | `time_to_first_sale_by_origin.csv` | Kaplan–Meier estimates require independent censoring and are descriptive |
| F-012 | Delivery-date inconsistencies have limited mature-cohort impact | 8 delivered/no-date orders affect 1 mature seller deal; 6 non-delivered/dated orders affect 0 mature deals | `delivery_date_anomaly_impact.csv` | Primary status policy retained; no timestamps imputed |
| F-013 | Payment checks are calculated | 98,416/98,665 (99.75%) within R$1; 98,284/98,665 (99.61%) within R$0.01 | `gmv_and_payment_checks.csv` | Comparable orders only; tolerances are not exact matches |
| F-014 | Unknown origin represents a material share of GMV | 73 sellers; R$122,608.14; 37.14% of delivered GMV; seller-bootstrap 95% interval 12.27%–60.43% | `unknown_origin_gmv_bootstrap.csv` | Wide bootstrap interval; unknown attribution is not a channel recommendation |
| F-015 | Activation model has been regularized but remains exploratory | L2 alpha 0.05; 58 non-events; 10 slope parameters; EPV 5.8; approximate penalized-Hessian intervals; penalized-model p-values omitted | `activation_logistic_regression.csv` | Approximate penalized-Hessian CIs and low EPV; not causal |

## Business implication

Do not redirect spend based on the paid/organic gap. The observed difference is linked-cohort-only, and full-cohort bounds are wide. Secure origin-level spend, a validated seller-ID crosswalk and seller registration/go-live dates, then use a randomized holdout or another pre-registered design.
