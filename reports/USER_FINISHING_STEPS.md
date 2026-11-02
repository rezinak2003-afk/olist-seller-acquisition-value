# Remaining release actions — only items requiring desktop, PostgreSQL or user-owned metadata

The analysis additions and local test suite have already been run in the working build. This file lists the remaining evidence that cannot be honestly manufactured by an offline build.

## 1. Real-data PostgreSQL 16 parity

On a Windows machine with Docker Desktop installed, from the repository root:

```powershell
docker compose -f compose.yaml up -d postgres
python -m src.pipeline
python scripts/run_postgres.py
```

Keep the four required source CSVs under `data/raw/`. The optional `olist_order_payments_dataset.csv` goes in `data/reference/` for the payment check. Do not commit raw CSVs.

Commit `data/processed/sql_python_reconciliation.csv` only after every reconciliation row is `PASS`. Update README and QUALITY_GATE to state the real-data check count. Keep the GitHub Actions pass on commit `089f46e` labelled synthetic-fixture-only.

## 2. Repair the Excel dashboard median

The existing `excel/Origin_Pivot.xlsx` has a native PivotTable, but `Executive_Dashboard!G10` currently caches zero instead of the expected linked-cohort median **R$215.70**. Keep a backup before editing.

In `Seller_Value`:
- Set `AB1` to `dashboard_selected_gmv_helper`.
- Set `AB2` to this formula and fill down through `AB843`:

```excel
=IF(AND($N2=1,$O2=1,OR(Executive_Dashboard!$B$3="All",$C2=Executive_Dashboard!$B$3)),IF(Executive_Dashboard!$E$3="Purchase-window",$X2,$Y2),"")
```

In `Executive_Dashboard!G10`, replace the broken formula with:

```excel
=IFERROR(MEDIAN(Seller_Value!$AB$2:$AB$843),NA())
```

Recalculate and save from Excel/WPS Desktop. With origin `All` and definition `Purchase-window`, confirm the displayed value is **R$215.70**. Do not replace the workbook with a programmatic export unless the native PivotTable cache and relationship parts are preserved.

After real PostgreSQL parity is available, fill the `sql_value` cells in the workbook's `Reconciliation` sheet from `sql_python_reconciliation.csv`. The current PivotTable workbook and pipeline workbook are separate; a unified workbook is still preferred.

## 3. Final Power BI visual QA

Open `powerbi/olist_seller_acquisition_value.pbix` and use `powerbi/POWER_BI_BUILD_GUIDE.md`. Highest priority:
- Replace the tiny/clipped confidence interval tables with one full-width table and one legible error-bar/forest chart.
- Fix page 5 column widths and clipped text.
- Remove the stray `1.` from page 4; expand pages 1–4 visuals to use the canvas.
- Add date and synchronized origin slicers; visibly flag linked n<20 groups.
- Add the 42.99% all-mature lower-bound card next to the explicitly labelled 82.94% linked-cohort card.
- Export the PDF again and inspect all five pages at normal zoom. Save five page PNGs and a model-view screenshot if the model is inspectable.

## 4. User-confirmed provenance and licence fields

- Replace `Project Contributors` in `LICENSE` only after the actual project-code copyright holder(s) are confirmed.
- Replace `not_recorded` in `DATA_SOURCES.md` / `source_manifest.csv` only with the actual date the raw datasets were downloaded.
- Generate a complete requirements lock on an internet-connected machine, aligned to CI's Python 3.12 environment; do not present the current partial snapshot as a full lock.
