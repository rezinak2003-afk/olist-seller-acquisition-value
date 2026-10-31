# Findings log — regenerated with 50-orders/day maturity cutoff

| ID | Finding | Current metric | Evidence | Caveat / implication |
|---|---|---|---|---|
| F-001 | Overall lead conversion | 842 / 8,000 = 10.53% | `acquisition_funnel.csv` | Distinct MQL; origin is observational |
| F-002 | Mature population and linkage | 656 mature; 340 linked / 656 = 51.83%; 316 remain unlinked | `seller_90d_value.csv`; `linkage_diagnostics.csv` | Unlinked marketplace outcomes remain NULL, not zero |
| F-003 | Purchase-window delivered activation | 282 / 340 = 82.94%; Wilson 95% CI 78.58%–86.57% | `statistics_summary.csv` | Order purchased inside window and source status says delivered |
| F-004 | Strict delivered-within-90-day activation | 258 / 340 = 75.88%; Wilson 95% CI 71.06%–80.12% | `statistics_summary.csv` | Both purchase and customer delivery must fall inside the window |
| F-005 | Delivered GMV is concentrated | R$330,080.56 total; top 10 sellers 48.43%; zero-GMV sellers 58 (17.06%); Gini 0.793 | `gmv_concentration.csv`; `gmv_lorenz_curve.csv` | Item-price GMV proxy, linked mature cohort only |
| F-006 | Paid search exceeds organic in the linked sample | 79/87 = 90.80% vs 80/103 = 77.67%; difference +13.13 pp; Newcombe CI +2.59 to +23.14 pp; Fisher p=0.0177; Holm p=0.1773 | `pairwise_comparisons.csv` | Not significant after Holm; observational; no budget shift supported |
| F-007 | GMV distributions across sufficiently sized origins | Kruskal-Wallis output in `inferential_tests.csv` | `inferential_tests.csv` | Descriptive rank comparison only; linked mature sellers |
| F-008 | Maturity depends on the volume rule | 665 deals at 10/day; 656 at 50/day; 654 at 100/day | `maturity_sensitivity.csv` | 50/day is primary and documented; cutoff is not absolute max timestamp |

## Business implication
Do not redirect spend based on the paid/organic gap. Secure origin-level spend, a validated seller-ID crosswalk and seller registration/go-live dates, then use a randomized holdout or another pre-registered design.
