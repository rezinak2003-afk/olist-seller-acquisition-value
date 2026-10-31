# Remaining user actions — desktop and account access

These steps cannot be completed honestly in this build environment because they require native Windows desktop applications, the live GitHub repository, or legal ownership information.

## 1. PostgreSQL 16 and SQL/Python parity

**Preferred route:** push the project to GitHub and open **Actions → data-pipeline-ci**. The workflow starts PostgreSQL 16, runs the source-fixture pipeline, executes `scripts/run_postgres.py`, and fails unless every reconciliation row is `PASS`. Download the CI artifacts/logs if the run fails and retain the generated `sql_python_reconciliation.csv` when all checks pass.

**Local alternative:** install Docker Desktop, open a terminal at the project root, then run:

```bash
docker compose -f compose.yaml up -d postgres
python -m pip install -r requirements.txt
python -m src.pipeline
python scripts/run_postgres.py
```

Do not put raw CSVs into Git. The runner reads the four required files from `data/raw/`; optional payments checks read from `data/reference/`.

## 2. Excel native PivotTable

1. Open `excel/olist_validation_workbook.xlsx` in Excel Desktop.
2. Read the `PivotTable_Instructions` sheet.
3. Insert a PivotTable using the `tblSeller` table as its source, preferably on a new worksheet named `Seller_Pivot`.
4. Use `origin` for Rows; add `mql_id` as Count in Values; add `mature_90d` and `seller_linked_to_order_items` as filters; add `activated_90d` as Sum in Values. Keep the filters visible so the pivot does not mix immature or unlinked sellers into activation denominators.
5. Save the workbook, close it, reopen it, and confirm the pivot and formula-driven dashboard remain intact.

The existing formula dashboard is not a substitute for the native PivotTable requested in the audit.

## 3. Power BI Desktop — five-page PBIX

1. Open Power BI Desktop on Windows and set a text parameter called `ProjectRoot` to the full path of this project folder (the folder containing `README.md`).
2. Create the queries from the named blocks in `powerbi/PowerQuery_Load_Outputs.pq`. The file uses forward-slash relative paths from `ProjectRoot`; it does not hard-code a user-specific Windows path.
3. Apply `powerbi/DAX_MEASURES.dax`; create the `DimDate` and `DimOrigin` tables and relationships described in `powerbi/POWER_BI_BUILD_GUIDE.md`.
4. Build the five pages and their origin, won-month, lead-type and activation-definition controls. Keep the denominator `n` visible beside each rate and label groups with `n<20` as insufficient data.
5. Validate the page totals against `data/processed/*.csv`, capture one screenshot per page, export a PDF, and save the PBIX under `powerbi/`.

## 4. GitHub Pages deployment

1. Push the repository and `.github/workflows/pages.yml` to the `main` branch.
2. In GitHub, open **Settings → Pages → Build and deployment → Source** and select **GitHub Actions**.
3. Open **Actions → Deploy interactive dashboard to GitHub Pages**. The deployment job displays the published URL.

If the repository's default branch is not `main`, change the branch filter in `pages.yml` before pushing.

## 5. Canonical dependency lock and licence holder

On an internet-connected machine, run:

```bash
uv pip compile requirements.in --python-version 3.12 --generate-hashes --output-file requirements.lock
```

Review the resolved versions and commit the generated lock. The existing `requirements.lock` is a partial offline snapshot, not a full install lock.

Replace `Project Contributors` in `LICENSE` with the actual copyright holder(s) for the project code before public release. Do not change the Olist dataset licence or imply that the MIT code licence covers the source data.
