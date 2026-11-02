# Second-audit remediation changelog

**Base snapshot audited:** `844fe37`  
**Purpose:** distinguish analysis changes made in this remediation build from remaining desktop/database work.

## Implemented in this remediation build

### Analysis and code
- Added `src/sensitivity.py` with worst-case all-mature activation bounds, paid/organic tipping-point scenarios, first-sale timing, Kaplan–Meier time-to-first-sale with right censoring, delivery-date anomaly impact and seller-bootstrap unknown-origin GMV share.
- Added `tests/test_sensitivity.py` covering these functions, bounds arithmetic, right-censoring, anomaly impact and bootstrap reproducibility.
- Updated `src/analytics.py` to use a reduced L2-penalized binomial GLM for origin + lead type, pool rare category levels, and report event counts and events-per-parameter.
- Updated `src/pipeline.py` so maturity sensitivity includes activation and GMV outcomes at 10/50/100 purchases/day and writes the new sensitivity outputs.
- Updated `src/make_charts.py` with charts for all-mature activation bounds and unknown-origin GMV share.
- Re-ran the pipeline on the supplied real Olist snapshot and regenerated the processed aggregate CSV outputs.
- Re-ran tests: **26 passed, 1 skipped**. The skipped test requires PostgreSQL configuration.

### Current real-data findings
- Mature deals: 656; linked: 340; unlinked: 316.
- Observed linked-cohort purchase-window activation: 282/340 = 82.94%.
- Worst-case all-mature identification bounds: 42.99%–91.16%; not confidence intervals.
- First sale among linked sellers: 284/340 within 90 days, 56/340 after day 90 but before `data_end`.
- All-origin KM diagnostic median: 127.6 days; 90-day restricted mean event-free time: 69.0 days; 316 no-event deals are also unlinked, so independent censoring is doubtful and the median is not a population estimate.
- Paid/organic unlinked-outcome tipping scenarios are documented in `paid_organic_tipping_point.csv`.
- Delivery-date anomaly impact: 8 delivered/no-date orders affect 1 mature deal; 6 non-delivered/dated orders affect 0 mature deals.
- Payment checks were calculated using the optional source payments file: 99.75% within R$1.00 and 99.61% within R$0.01 across 98,665 comparable orders.
- Unknown origin: R$122,608.14 from 73 linked mature sellers (37.14% of delivered GMV); seller-bootstrap 95% interval 12.27%–60.43%.
- Logistic model now uses L2 regularisation; 58 non-events, 10 slope parameters, EPV 5.8; inference is still exploratory.

### Documentation
- Rewrote the README generated-results section from current processed CSVs and repaired UTF-8 encoding/BOM.
- Updated methodology, KPI definitions, cleaning log, executive summary, findings log, QA, quality gate and execution log.
- Added `reports/DECISION_MEMO.md`.
- Updated Power BI DAX reference and build guide with all-mature bounds and small-n flags; these reference measures are not independently verified as stored in the PBIX.

## Not completed / not to be claimed

- Full raw-Olist PostgreSQL 16 execution and `sql_python_reconciliation.csv` with all PASS rows. The known successful GitHub Actions run on `089f46e` is synthetic-fixture-only; the current code changes still require a new CI run after pushing.
- Excel median formula/cache repair. The current `Origin_Pivot.xlsx` still caches zero in the dashboard median cell instead of the expected R$215.70. The native PivotTable is left untouched; desktop helper formula instructions are in `reports/USER_FINISHING_STEPS.md`.
- Excel reconciliation `sql_value` population and consolidation of the PivotTable into the pipeline workbook.
- Complete Power BI final visual QA. The page-1 origin conversion chart and BRL formatting were fixed in the desktop PBIX before this remediation, but the PDF review still reports clipped CI tables/page-5 columns, whitespace, page-4 stray text, and missing date/synced slicers, small-n flags and lower-bound card.
- Five page PNGs and model-view screenshot.
- Canonical Python 3.12 dependency lock; the current lock remains a partial offline snapshot.
- Actual LICENSE copyright holder and genuine dataset retrieval date. These are not guessed.
- Raw CSVs are not included in this handoff archive; users must obtain them from the attributed Kaggle sources.
