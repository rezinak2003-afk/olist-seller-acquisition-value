# QA and limitations

## Checks recorded in the current generated outputs
- `data_end` is the day after the last date with at least 50 orders; it is 2018-08-28 00:00 exclusive.
- There are 83 raw orders on/after that boundary; `mature_windows_ending_after_data_end` is zero.
- 656 deals have a complete 90-day purchase window; 340 have seller-ID linkage to order items and 316 do not.
- 282/340 linked mature deals have purchase-window delivered activation; 258/340 satisfy strict delivered-within-90-day activation.
- 8 delivered orders have no customer-delivery timestamp; 6 non-delivered orders carry a delivery timestamp.
- One closed deal has negative close duration; see `close_duration_exceptions.csv`.
- Payment reconciliation is 99.75% within R$1.00 and 99.61% within R$0.01 among 98,665 comparable orders.
- Unit/logic suite: 16 passed, 1 PostgreSQL-dependent test skipped locally. The synthetic-fixture end-to-end pipeline test passed; PostgreSQL/Python parity remains gated on PostgreSQL 16 execution.
- Headless browser validation of `dashboard/index.html`: origin filter, strict-definition toggle and minimum-n control all changed the KPI values; no browser JavaScript errors were recorded. Preview: `reports/charts/interactive_dashboard_preview.png`.

## Material interpretation risks
1. **Seller linkage:** 316/656 mature sellers are unlinked; marketplace outcomes for those deals are unknown, not zero.
2. **Selection:** the observed linked cohort may not represent the population. The linkage model/IPW output is a sensitivity check and depends on measured covariates.
3. **Maturity rule:** `data_end` is defined from daily order volume; 10/50/100 threshold sensitivity is provided.
4. **Channel inference:** origin is observational and there is no spend or randomized attribution. Multiple-comparison-adjusted evidence does not support reallocation.
5. **GMV interpretation:** values are item price in BRL; no freight, discounts, seller costs, refunds/settlements or platform economics are included.

## Not yet independently executed / unavailable native artifacts
- PostgreSQL 16 SQL execution and row-level reconciliation have not been run in this build container. `.github/workflows/ci.yml` provisions PostgreSQL 16 and executes the pipeline and SQL runner with synthetic fixture data. The local container has neither Docker nor PostgreSQL binaries.
- A native Power BI `.pbix`, the requested five page screenshots and PDF export require Power BI Desktop on Windows.
- A true Excel PivotTable must be inserted manually in Excel Desktop; the workbook includes the `PivotTable_Instructions` sheet.
- GitHub Pages deployment workflow is prepared but requires enabling Pages with GitHub Actions as the source in repository settings, then pushing/running the workflow.
- A canonical dependency lock could not be resolved because the environment could not reach PyPI; use the `uv pip compile` command documented in README on an internet-connected machine.
