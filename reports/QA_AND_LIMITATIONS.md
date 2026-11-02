# QA and limitations — current analysis build

## Re-executed local evidence
- Real Olist pipeline: `python -m src.pipeline` completed with 8,000 qualified leads, 842 closed deals, 656 mature deals and 340 linked mature deals.
- Local tests: `python -m pytest -q` returned **28 passed, 1 skipped**. The skipped test requires PostgreSQL; this environment has no Docker or PostgreSQL client/server binaries.
- Charts: `python -m src.make_charts` completed, including the new activation-bounds and unknown-origin GMV charts.
- Payment input was available under `data/reference/` for this local run. `gmv_and_payment_checks.csv` reports 98,665 comparable orders, 99.75% within R$1.00 and 99.61% within R$0.01.
- The code and documentation now include worst-case activation bounds, paid/organic tipping scenarios, first-sale timing, right-censored time-to-first-sale, anomaly impact and extended 10/50/100 maturity sensitivity.
- Dashboard browser validation from the prior build remains recorded: origin filter, definition toggle and minimum-n control recalculated KPIs without JavaScript console errors.

## Core interpretation risks
1. **Outcome-dependent seller linkage:** the linked flag is based on seller ID appearing in any order-item row, including after the first 90 post-win days. Of 340 linked mature sellers, 56 first sold after day 90. This makes 82.94% a linked-cohort outcome, not an unbiased estimate for all mature deals.
2. **Unobserved outcomes:** 316 of 656 mature deals are unlinked. Worst-case all-mature identification bounds are 42.99%–91.16%; these are not confidence intervals.
3. **Tipping-point assumptions:** the paid/organic scenarios are sensitivity calculations, not observed or estimated unlinked activation rates.
4. **Censoring:** time-to-first-sale mechanically right-censors no-sale records at `data_end`. All 316 no-event records are also unlinked sellers, so independent/non-informative censoring is doubtful. The KM median is assumption-dependent and must not be presented as a population estimate.
5. **Channel inference:** origin is observational, there is no media spend or randomized attribution, and all-pairs Holm adjustment does not support a paid/organic reallocation.
6. **Model stability:** the reduced L2 model now uses alpha=0.05, with 58 non-events, 10 slope parameters and EPV 5.8. Approximate penalized-Hessian intervals are not frequentist confidence intervals; conventional p-values are omitted for penalized coefficients.
7. **GMV interpretation:** item price in BRL is not seller profit, platform revenue, CAC or ROI. Top-10 concentration is 48.43%; unknown origin contributes 37.14% of observed linked mature seller GMV, with a wide seller-bootstrap interval.

## Evidence still missing
- PostgreSQL 16 full-data execution against the real four required CSVs and a committed `sql_python_reconciliation.csv` with every row PASS. The successful GitHub Actions run on `089f46e` used the committed synthetic fixture only.
- Excel median formula cache repair and a single reconciled workbook. The current `Origin_Pivot.xlsx` median dashboard cell caches 0 instead of R$215.70; its `Reconciliation.sql_value` remains NOT RUN.
- Final Power BI visual QA: the page-1 origin conversion chart and BRL currency have been corrected, but the PDF still shows clipped/tiny confidence-interval visuals, page-5 clipped columns, unused canvas, a stray page-4 `1.`, missing date/synced slicers, missing small-n labels and no companion 42.99% lower-bound card.
- Five page screenshots and model-view screenshot are not committed.
- `requirements.lock` is still a partial environment snapshot; a canonical lock could not be generated offline.
- `LICENSE` still says `Project Contributors`; actual code copyright holder must be confirmed.
- Source retrieval date remains `not_recorded`; do not invent it.

## Release stance
The analysis is more complete and transparent, but this build is not yet a verified 95/100 release. Full raw-data SQL parity, Excel repair and final Power BI visual QA remain the primary blocking items.
