# Data cleaning and validation log

This log records the actions applied to the supplied Olist snapshot. Counts below are generated from the current committed pipeline outputs.

## Structural and type handling
- Parsed lead contact dates, deal win dates and order timestamps as year-first dates/timestamps. The pipeline records parse failures in `validation_summary.csv`.
- Trimmed identifier strings and normalized empty identifiers to missing values before joins.
- Normalized blank categorical values to `(missing)` while leaving the source value `unknown` as its own category.
- Converted item `price`, `freight_value` and payment `payment_value` to numeric fields; no negative item price rows were found in this snapshot.
- Validated lead-to-deal and item-to-order joins; the generated validation file reports the match rate and primary-key/composite-key checks.

## Observation-window correction
- Replaced the old maximum-timestamp maturity boundary with a daily-volume rule: only calendar days with at least 50 purchases qualify; `data_end` is the following day at 00:00 and is exclusive.
- Last qualifying purchase day: **2018-08-27**. `data_end`: **2018-08-28 00:00:00**.
- There are **83** source orders on/after `data_end`; these sparse-tail rows do not extend the observation horizon.
- The current mature-deal population is **656**. The validation count `mature_windows_ending_after_data_end` is **0**.
- Sensitivity results at 10, 50 and 100 purchases/day are in `data/processed/maturity_sensitivity.csv`.

## Delivery and close-duration exceptions
- **8** orders have `order_status='delivered'` but no customer delivery timestamp. These can contribute to purchase-window delivered activation because the source status is delivered; they cannot satisfy the strict delivery-within-90-day definition.
- **6** non-delivered orders carry a customer delivery timestamp. These remain classified according to the source order status; the inconsistency is not silently recoded.
- **1** closed deal has negative close duration (win date precedes first contact). It is listed in `close_duration_exceptions.csv` and excluded from median/mean close-day calculations, but the underlying source dates are not overwritten.
- Null item-price rows: **0**. Missing freight/payment rows are handled as missing for payment reconciliation rather than zero-filled.

## Seller linkage and outcome handling
- The current mature set has **340 linked** and **316 unlinked** deal rows. Unlinked seller outcomes remain NULL, not zero.
- The linked mature cohort is not assumed representative of all mature sellers. `linkage_diagnostics.csv` reports linkage by origin, lead type, business segment and win month.
- `linkage_model.csv` and `ipw_activation_by_origin.csv` document an adjusted linkage-propensity sensitivity analysis. It cannot recover outcomes for unlinked records.

## Payments and GMV
- Purchase-window GMV across all order statuses is **R$336,683.90**; delivered-status GMV is **R$330,080.56**; gap is **R$6,603.34**.
- Among **98,665** comparable orders with item, freight and payment totals, **99.75%** reconcile within R$1.00 and **99.61%** within R$0.01. The tolerance is made explicit; the 99.75% figure is not an exact-match rate.
- Delivered GMV is item price in BRL, not seller profit or Olist-recognized revenue.

## Audit trail
- Every computed exception and control total is written to `data/processed/validation_summary.csv` or the related CSV diagnostics.
- `docs/METHODOLOGY.md` and `docs/KPI_DEFINITIONS.md` specify the denominators, cutoff and statistical procedures.
