# Power BI Desktop report — delivered PBIX and remaining QA

## Current deliverables

- Native five-page Power BI report: `powerbi/olist_seller_acquisition_value.pbix`.
- Five-page PDF export: `reports/olist_seller_acquisition_value.pdf`.
- Power Query source: `powerbi/PowerQuery_Load_Outputs.pq`.
- DAX reference library: `powerbi/DAX_MEASURES.dax`.

The PBIX was authored in Power BI Desktop. Recent desktop edits fixed the page-1 lead-to-deal conversion chart to break out by origin and changed the GMV currency formatting to Brazilian Real. The report has not yet passed final visual QA. The current PDF review still shows clipped/tiny confidence-interval tables, page-5 column clipping, under-used canvas space on pages 1–4, a stray `1.` text object on page 4, and a small page-2 chart.

## Model contract

1. Create `DimOrigin` from distinct values across the funnel and seller facts, as shown in `DAX_MEASURES.dax`. Relate `DimOrigin[origin]` one-to-many to both fact tables. Do not relate the two facts directly.
2. Create `DimDate` and relate `DimDate[Date]` one-to-many to `Seller_90d_Value[won_date_date]`. Mark it as the model date table.
3. Keep `Activation_Definition` disconnected; it switches between purchase-window and strict activation.
4. Keep validation, pairwise tests, linkage diagnostics and model outputs disconnected unless a visual requires a deliberate relationship.
5. Preserve NULLs for unlinked seller outcomes. Never turn unobserved outcomes into zero.

## Final visual remediation

### Page 1 — Acquisition funnel
- Retain the origin-level lead-to-deal conversion chart; the single overall bar was replaced with an origin axis.
- Display qualified-lead counts as full values (8,000, not 8K), label bars and sort descending by lead count.
- Keep `(missing)` and `unknown` visible as data-quality categories, not actionable channels.

### Page 2 — Cohort maturity and linkage
- Enlarge the linked-versus-unlinked chart to use the canvas.
- Show mature n, linked n, unlinked n and linkage rate for every origin.
- Keep the exclusive `data_end=2018-08-28` and 50-orders/day cutoff visible.

### Page 3 — Seller activation and linkage bounds
- Replace the two clipped/tiny confidence-interval tables with one readable table: origin, linked n, activated n, activation rate, Wilson lower, Wilson upper and `n<20` flag.
- Keep a single origin-level activation chart. Prefer an error-bar/forest display for Wilson intervals if supported by the visual.
- Add `All-Mature Activation Lower Bound %` and `All-Mature Activation Upper Bound %` from `DAX_MEASURES.dax`; use the lower-bound card next to the linked-cohort activation card.
- Add subtitle: `Linked cohort only; unlinked outcomes unobserved`.
- Label the linked sample size on bars/tooltips and flag groups with n<20.

### Page 4 — 90-day delivered item-price GMV
- BRL currency formatting is corrected to `R$`.
- Remove the stray `1.` text object.
- Expand the visuals to use available canvas while keeping the GMV definition visible: order-item price in BRL, not profit or platform revenue.
- Include unknown-origin GMV share and concentration context: 37.14% unknown-origin GMV share (73 sellers), top-10 share 48.43%.

### Page 5 — Quality and statistical evidence
- Give explicit widths to the `value` and `interpretation` columns; verify the right edge of every table in the exported PDF.
- Keep the pairwise evidence table to: origin A, origin B, n, rate difference, CI, raw p and Holm-adjusted p. Show omnibus rows separately.
- Include the bounds/tipping-point caveat and the 8/6 delivery-date anomaly impact.

## Global controls and small-group treatment

- Add a `DimDate[Date]` between slicer and use View → Sync slicers to synchronize the date and origin slicers across all five pages.
- Add the `Origin Sample Size Flag` measure to tooltip/table and show sample n on the charts.
- Any group with linked n<20 must be explicitly marked insufficient and not used for stable origin ranking.
- Verify slicers change the measures, Wilson intervals and n flags.

## Final release verification

1. Confirm the displayed 82.94% card is explicitly labelled as linked-cohort activation.
2. Confirm the 42.99% all-mature lower-bound card uses all 656 mature deals as denominator. The all-mature upper bound is 91.16%.
3. Confirm all five pages fit within the canvas and every table is readable at normal PDF zoom.
4. Export all five pages again to `reports/olist_seller_acquisition_value.pdf`.
5. Commit five page PNGs and a model-view screenshot under `powerbi/screenshots/` and `docs/`, respectively.
6. Confirm the DAX measures saved in the PBIX match `DAX_MEASURES.dax`; the PBIX binary has not been independently decoded in this audit.
