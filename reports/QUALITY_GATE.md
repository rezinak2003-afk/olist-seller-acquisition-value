# Quality gate — current build

## Executed evidence

| Check | Evidence | Result |
|---|---|---|
| Python pipeline | Executed locally against the supplied Olist snapshot | Passed: 8,000 qualified leads; 842 closed deals; 656 mature deals; 340 linked mature deals |
| Seller activation | `data/processed/` seller mart and summary outputs | 282 observed activated sellers; 82.94% among linked mature deals |
| Linkage coverage | 340 linked / 656 mature deals | 51.83%; activation among linked sellers must not be generalized to all mature deals |
| Conservative activation lower bound | 282 / 656 mature deals | 42.99% |
| Maturity cutoff | Exclusive `data_end=2018-08-28`; minimum 50 purchases/day | Implemented in Python and SQL; sparse-tail leakage validation included |
| Local tests | `python -m pytest -q` | 19 passed, 1 skipped; skipped test requires PostgreSQL configuration |
| PostgreSQL CI | PostgreSQL 16; pandas 2.2 and 3.0 matrix; run on commit `089f46e` | Passed against the committed synthetic fixture; this is not full raw-Olist PostgreSQL reconciliation |
| Statistical analysis | Fisher pairwise tests, Holm correction, Newcombe intervals, fixed-margin Monte Carlo omnibus tests | Generated; observational comparisons are not causal estimates |
| Linkage diagnostics | Linkage dimensions, propensity model and capped stabilized IPW sensitivity | Generated; outcome-dependent linkage remains a material limitation |
| GMV checks | `data/processed/gmv_and_payment_checks.csv` | All-status GMV R$336,683.90; delivered-only GMV R$330,080.56; difference R$6,603.34 |
| Excel | `excel/Origin_Pivot.xlsx` | Native PivotTable and dashboard workbook created; separate from the pipeline-generated validation workbook |
| Power BI | `powerbi/olist_seller_acquisition_value.pbix` | Native PBIX created with five report pages |
| PDF report | `reports/olist_seller_acquisition_value.pdf` | Five-page export created; visual refinements remain |
| GitHub Pages | `.github/workflows/pages.yml` | Deployment workflow has passed; published project page is available |

## Known data-quality and interpretation limitations

- Mature-deal linkage is outcome-dependent: a seller is linked when it appears in order-item data. The 82.94% activation rate is conditional on this linked cohort.
- Linkage coverage is 51.83%. The 42.99% figure is a conservative observed lower bound for the full mature cohort, not an adjusted estimate.
- The pipeline records 8 delivered orders without a delivery timestamp, 6 non-delivered orders with a delivery timestamp, and 1 negative close duration. These exceptions should be considered when interpreting results.
- Advertising spend is unavailable. Acquisition-origin comparisons are observational and do not establish causal channel performance.
- The logistic model has sparse non-events and unstable estimates; interpret its coefficients and confidence intervals cautiously.
- The payment reconciliation rates are blank because the supplementary payments CSV was not found. No payment reconciliation percentage is claimed.

## Deliverable review notes

- The Excel native PivotTable exists in `excel/Origin_Pivot.xlsx`. The PivotTable workbook is separate from the pipeline-generated workbook.
- The PBIX and PDF exist, but the PDF visual review identified layout issues requiring attention: the lead-conversion chart lacks a clear origin breakdown, the Wilson interval table is clipped, the statistical evidence table is difficult to read, and the GMV currency display needs correction.
- The Power BI report should not be described as fully presentation-ready until those visual issues are fixed and re-exported.
- `requirements.lock` remains a partial snapshot, not a complete canonical dependency lock.
- Raw source CSVs are not committed. Reproduction requires downloading the licensed Olist source data and placing the required files in the documented folders.

## Not yet evidenced

| Item | Status |
|---|---|
| Full raw-Olist PostgreSQL 16 reconciliation | Not yet evidenced; CI currently tests the committed synthetic fixture |
| Real-data SQL/Python reconciliation output | Do not claim complete parity until `data/processed/sql_python_reconciliation.csv` exists and every required check passes |
| Payment reconciliation | Not calculated; supplementary payments CSV was not found |
| Final Power BI visual QA | Outstanding; fix the layout and currency issues listed above |
| Complete dependency lock | Not generated |

## Release interpretation

The Python analysis has been executed locally, the local test suite passes with one PostgreSQL-dependent skip, and PostgreSQL CI has passed against a synthetic fixture. The Excel PivotTable, Power BI PBIX, PDF export and GitHub Pages deployment have been created.

The project still has material limitations around outcome-dependent seller linkage, unavailable payment reconciliation, full raw-data SQL parity and Power BI visual polish. Do not describe it as a fully verified 90+ deliverable or claim full raw-Olist PostgreSQL reconciliation until the outstanding evidence is produced.

