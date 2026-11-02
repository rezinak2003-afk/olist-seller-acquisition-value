# Third-audit remediation changelog

## Implemented in this package

- Reduced the exploratory L2-penalty strength for the origin + lead-type activation model from alpha=0.5 to alpha=0.05 to avoid excessive shrinkage toward odds ratios of 1.0.
- Removed conventional Wald p-values from the penalized model output. The approximate penalized-Hessian intervals are explicitly labelled as non-frequentist; Fisher tests with Holm correction remain the source for group-level inference.
- Strengthened the Kaplan–Meier output with an explicit warning that independent/non-informative censoring is doubtful: all 316 no-event mature deals are also unlinked under the outcome-dependent seller/order-item linkage rule. The 127.6-day median is now labelled an assumption-dependent diagnostic, not a population estimate.
- Added automated tests for payment reconciliation at both R$1.00 and R$0.01 tolerances and for the missing-payments branch.
- Added a small synthetic payments CSV to the CI fixture so the payment reconciliation path executes during fixture pipeline runs. The fixture produces 20 comparable orders at 100% within both tolerances; this is test evidence only, not a statement about the Olist raw data.
- Added regression assertions for alpha=0.05, omitted penalized-model p-values, and the Kaplan–Meier censoring caveat.

## Verification

- Local test suite: **28 passed, 1 PostgreSQL-dependent test skipped**.
- Full pipeline executed against the committed synthetic fixture with payment reconciliation active. The workflow is configured to exercise this branch using the new payments fixture; rerun CI on the pushed commit before claiming hosted CI has passed.
- Synthetic fixture payment output: 20/20 comparable orders within R$1.00 and 20/20 within R$0.01. Do not confuse this with the full Olist result (98,416/98,665 within R$1.00 and 98,284/98,665 within R$0.01).

## Still outstanding

- PostgreSQL 16 parity on the full raw Olist CSVs is not run or claimed.
- PBIX visuals/layout and Excel workbook median/reconciliation require native Power BI / Excel Desktop implementation and verification.
- Canonical Python 3.12 dependency lock, final licence holder confirmation and user-recorded source retrieval date remain open.
