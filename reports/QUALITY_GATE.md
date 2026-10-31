# Quality gate — current build

## Executed evidence

| Check | Evidence | Result |
|---|---|---|
| Python pipeline on supplied snapshot | `src/pipeline.py`; outputs under `data/processed/` | Executed |
| Maturity cutoff | Exclusive `data_end=2018-08-28`; 50 purchases/day; leakage count 0 | Pass |
| Snapshot / synthetic regression tests | `tests/test_snapshot_quality.py`, `tests/test_pipeline_logic.py` | 17 collected: 16 passed; 1 PostgreSQL integration test skipped locally |
| Pipeline end-to-end fixture | `tests/test_end_to_end.py` using committed synthetic inputs | Passed locally |
| Statistics | Fisher pairwise, Holm correction, Newcombe CIs, fixed-margin Monte Carlo omnibus, both definitions | Generated |
| Linkage diagnostics | Dimension tables, logistic propensity model and capped stabilized IPW sensitivity | Generated |
| Excel workbook | `tblSeller`, formula-based KPIs, dropdowns, reconciliation sheet, 11-origin charts | Recalculated/cached; one-cell edit test passed; manual PivotTable remains |
| HTML dashboard | Dynamic selectors and browser-side KPI calculations; origin/definition/minimum-n tested in headless Chromium; zero JS console errors | Generated and browser-tested |
| Dashboard preview | `reports/charts/interactive_dashboard_preview.png` | Captured from the generated HTML after initial-load rendering |
| GitHub Pages | `.github/workflows/pages.yml`; current official Pages actions | Workflow added; first deployment still requires repository Pages setting and a push |
| CI definition | PostgreSQL 16 service plus pandas 2.2 / 3.0 matrix; checkout/setup-python actions updated | Added; not executed from this offline build |

## Not claimed as executed

| Item | Current status | Requirement |
|---|---|---|
| PostgreSQL 16 execution | Not run in this container; no server or Docker | Run CI workflow or `scripts/run_postgres.py` locally; require every row in `sql_python_reconciliation.csv` to PASS |
| SQL parity result | Not claimed | Must compare all seller-mart/channel-summary columns plus reconciliation totals and close-day aggregates |
| Power BI `.pbix` | Not created | Author and validate in Power BI Desktop (Windows), then commit the PBIX, five screenshots and PDF export |
| Canonical dependency lock | Not generated | `uv pip compile` was attempted but PyPI DNS/network access failed; `requirements.lock` remains a partial local snapshot and is explicitly not a complete install lock |
| Excel PivotTable | Not created by openpyxl | Insert a native PivotTable in Excel Desktop using `tblSeller` |

## Release interpretation
The Python analysis and workbook/dashboard handoff are substantially improved, but the project is **not yet a verified 90+ PBIX deliverable**. Do not claim PostgreSQL 16 “8/8 PASS” until the committed reconciliation output verifies it. A native Power BI Desktop report and Excel PivotTable remain platform steps.
