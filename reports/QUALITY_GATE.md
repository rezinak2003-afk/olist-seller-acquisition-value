# Quality gate — current build

## Executed evidence

| Check | Evidence | Result |
|---|---|---|
| Python pipeline on supplied Olist snapshot | `src/pipeline.py`; outputs under `data/processed/` | Executed locally: 8,000 qualified leads; 842 closed deals; 656 mature deals; 340 linked mature deals |
| Purchase-window activation | `seller_90d_value.csv`, `statistics_summary.csv` | 282/340 = 82.94%; conditional on linked mature sellers |
| All-mature activation bounds | `activation_bounds_by_origin.csv` | 42.99%–91.16% overall worst-case identification interval; not a confidence interval |
| Linkage timing | `linkage_first_sale_timing.csv` | 284/340 first sold within 90 days; 56/340 first sold after day 90 before `data_end` |
| Time-to-first-sale | `time_to_first_sale_by_origin.csv` | KM diagnostic median 127.6 days; 316 no-event sellers are also unlinked, so non-informative censoring is doubtful; not a population estimate |
| Maturity sensitivity | `maturity_sensitivity.csv` | Activation, worst-case bounds and delivered GMV included at 10/50/100 orders/day |
| Data-quality impact | `delivery_date_anomaly_impact.csv` | 8 delivered/no-date orders impact 1 mature seller deal; 6 non-delivered/dated orders impact 0 mature deals |
| Payment reconciliation | `gmv_and_payment_checks.csv`; `tests/test_payment_reconciliation.py`; synthetic payments fixture | Real Olist aggregate: 98,416/98,665 (99.75%) within R$1.00; 98,284/98,665 (99.61%) within R$0.01. The optional code path is now unit-tested and exercised by fixture CI after push. |
| Activation model | `activation_logistic_regression.csv` | L2 alpha=0.05; 58 non-events; 10 slope parameters; EPV 5.8; penalized-Hessian intervals only; no penalized-model p-values |
| Local tests | `python -m pytest -q` | 28 passed, 1 skipped; includes payment tolerance tests and the censoring/model regression checks; skipped PostgreSQL integration requires PostgreSQL configuration |
| PostgreSQL CI | PostgreSQL 16; pandas 2.2 and 3.0 matrix; successful run recorded on commit `089f46e` | Passed against committed synthetic fixture only; not full raw-Olist reconciliation |
| Excel | `excel/Origin_Pivot.xlsx` | Native PivotTable exists, but dashboard median cache remains 0 instead of expected R$215.70; separate from pipeline workbook |
| Power BI | `powerbi/olist_seller_acquisition_value.pbix` | Native five-page PBIX exists; currency and page-1 origin conversion chart were improved |
| PDF report | `reports/olist_seller_acquisition_value.pdf` | Five-page export exists; visual QA still identifies clipping and layout defects |

## Key analytical limitations

- Seller linkage is defined by seller ID appearing in order items at any observed date. This is outcome-dependent and includes 56 linked mature sellers whose first observed sale was after day 90.
- Observed 82.94% activation is conditional on 340 linked sellers. The 42.99%–91.16% interval is a worst-case identification bound for all 656 mature deals, not a confidence interval or adjusted point estimate.
- Paid/organic tipping scenarios are assumption-dependent; no scenario estimates the actual unlinked activation rate.
- Advertising spend is unavailable, and acquisition-origin comparisons are observational.
- The L2 activation model uses alpha=0.05 and has 58 non-events and 10 slope parameters (EPV 5.8). Penalized-Hessian intervals are approximate and not frequentist CIs; no p-values are reported for penalized coefficients.
- Delivered GMV is order-item price in BRL, not seller profit, recognized platform revenue or ROI.
- Raw payment rows are not committed. The payment result is based on the optional supplementary payment input and is committed only as an aggregate reconciliation output.

## Power BI visual QA still outstanding

The latest desktop report includes the page-1 conversion-by-origin chart and BRL currency formatting. The latest PDF review still found:
- Wilson confidence-interval tables are clipped/tiny and should be replaced by one readable table and an error-bar/forest visual.
- Page 5 value and interpretation columns need explicit widths; some content remains clipped.
- Pages 1–4 under-use the canvas, page 4 has a stray `1.` text object, and page 2's chart is too small.
- A date slicer and synchronized origin/date slicers are not yet evidenced.
- Small-n (`n<20`) chart labels/flags and the 42.99% all-mature lower-bound companion card are not yet evidenced.
- The PBIX model relationships and stored DAX have not been independently inspected from the model binary.

## Remaining evidence gaps

| Item | Status |
|---|---|
| Full raw-Olist PostgreSQL 16 reconciliation | Not yet executed; CI evidence is synthetic-fixture-only |
| `sql_python_reconciliation.csv` on real Olist data | Missing; do not claim full-data parity |
| Excel dashboard median | Formula/cache defect remains in current native-PivotTable workbook; expected linked-cohort median is R$215.70 |
| Unified Excel workbook with SQL reconciliation results | Not complete; PivotTable is separate, and `sql_value` remains NOT RUN |
| Complete dependency lock | `requirements.lock` remains a partial environment snapshot, not a canonical lock |
| Copyright holder in LICENSE | Still says `Project Contributors`; requires owner confirmation |
| Source retrieval date | `not_recorded`; must be supplied from actual retrieval records |
| Power BI final visual QA | Outstanding as listed above |
| Five report page PNGs and model view screenshot | Not committed |

## Release interpretation

The project now contains stronger real-data sensitivity analysis: worst-case linkage bounds, explicit tipping scenarios, first-sale timing, Kaplan–Meier time-to-first-sale, anomaly impact, maturity activation/GMV sensitivity, a regularized exploratory model, and payment reconciliation. The local test suite is 28 passed and 1 PostgreSQL-dependent skip.

This is materially stronger than the 80.5/100 audit snapshot, but it is not a fully verified 95-point deliverable. The largest remaining score gaps are Power BI layout/visual validation, raw-data PostgreSQL parity, Excel median/reconciliation, and completion of provenance/reproducibility metadata.
