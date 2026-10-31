"""Build a refreshable Excel dashboard with a live Seller_Value table."""
from __future__ import annotations
from pathlib import Path
import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.chart import BarChart, Reference
from openpyxl.workbook.defined_name import DefinedName

NAVY = "17365D"
BLUE = "D9EAF7"
PALE = "F5F8FC"
GOLD = "FFF2CC"
INK = "29445F"
GREEN = "E2F0D9"
RED = "FCE4D6"


def _excel_value(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    return value


def _write_csv_sheet(wb, out_dir: Path, sheet_name: str, csv_name: str | None,
                     table_name: str | None = None):
    ws = wb.create_sheet(sheet_name)
    ws.sheet_view.showGridLines = False
    if csv_name and (out_dir/csv_name).exists():
        df = pd.read_csv(out_dir/csv_name)
        # Excel tables and structured references behave best when the first row
        # contains unique, non-empty column names.
        cols = [str(c) for c in df.columns]
        ws.append(cols)
        boolean_cols = {"mature_90d", "seller_linked_to_order_items", "activated_90d",
                        "activated_90d_any_status", "activated_delivered_within_90d"}
        for row in df.itertuples(index=False, name=None):
            vals = []
            for col, value in zip(cols, row):
                if col in boolean_cols and pd.notna(value):
                    value = int(str(value).lower() in {"true", "1", "1.0"})
                vals.append(_excel_value(value))
            ws.append(vals)
        if table_name and ws.max_row >= 2:
            ref = f"A1:{get_column_letter(ws.max_column)}{ws.max_row}"
            tab = Table(displayName=table_name, ref=ref)
            tab.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showFirstColumn=False,
                                                showLastColumn=False, showRowStripes=True,
                                                showColumnStripes=False)
            ws.add_table(tab)
    else:
        ws.append([f"Run python -m src.pipeline to populate {csv_name or sheet_name}"])
    ws.freeze_panes = "A2"
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=NAVY)
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[1].height = 28
    if not table_name:
        ws.auto_filter.ref = ws.dimensions
    for col in ws.columns:
        letter = get_column_letter(col[0].column)
        max_len = max((len(str(c.value or "")) for c in list(col)[:300]), default=10)
        ws.column_dimensions[letter].width = min(max(max_len+2, 12), 42)
    return ws


def _get_metric_values(out_dir: Path) -> tuple[dict, dict]:
    funnel = pd.read_csv(out_dir/"acquisition_funnel.csv")
    seller = pd.read_csv(out_dir/"seller_90d_value.csv")
    mature = seller.mature_90d.astype(bool)
    linked = mature & seller.seller_linked_to_order_items.astype(bool)
    linked_df = seller.loc[linked]
    python_values = {
        "qualified_leads": float(funnel.qualified_leads.sum()),
        "closed_deals": float(funnel.closed_leads.sum()),
        "mature_deals": float(mature.sum()),
        "linked_mature_deals": float(linked.sum()),
        "activated_purchase_window": float(pd.to_numeric(linked_df.activated_90d).sum()),
        "activated_strict": float(pd.to_numeric(linked_df.activated_delivered_within_90d).sum()),
        "delivered_gmv": float(pd.to_numeric(linked_df.gmv_90d_delivered_only).sum()),
        "strict_delivered_gmv": float(pd.to_numeric(linked_df.gmv_90d_delivered_within_90d).sum()),
        "close_days_sum": float(pd.to_numeric(seller.close_days, errors="coerce").sum()),
        "close_days_n": float(pd.to_numeric(seller.close_days, errors="coerce").notna().sum()),
    }
    sql_values = {}
    path = out_dir/"sql_reconciliation_source.csv"
    if path.exists():
        source = pd.read_csv(path)
        values = dict(zip(source.metric.astype(str), pd.to_numeric(source.value, errors="coerce")))
        sql_values = {
            "qualified_leads": values.get("qualified_leads"),
            "closed_deals": values.get("closed_deals"),
            "mature_deals": values.get("mature_deals"),
            "linked_mature_deals": values.get("linked_mature_deals"),
            "activated_purchase_window": values.get("activated_linked_mature_deals"),
            "activated_strict": values.get("strict_activated_linked_mature_deals"),
            "delivered_gmv": values.get("delivered_gmv_90d"),
            "strict_delivered_gmv": values.get("strict_delivered_gmv_90d"),
            "close_days_sum": values.get("close_days_sum"),
            "close_days_n": values.get("close_days_n"),
        }
    return python_values, sql_values


def _build_dashboard(wb, out_dir: Path, origin_values: list[str]):
    ws = wb.create_sheet("Executive_Dashboard", 0)
    ws.sheet_view.showGridLines = False
    ws.merge_cells("A1:H1")
    ws["A1"] = "OLIST SELLER ACQUISITION & 90-DAY VALUE"
    ws["A1"].font = Font(name="Aptos Display", size=16, bold=True, color="FFFFFF")
    ws["A1"].fill = PatternFill("solid", fgColor=NAVY)
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 32
    ws.merge_cells("A2:H2")
    ws["A2"] = "Live formula dashboard | edit the selectors or Seller_Value table to refresh the KPIs"
    ws["A2"].font = Font(italic=True, color=NAVY, size=10)
    ws["A2"].fill = PatternFill("solid", fgColor=BLUE)
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")

    ws["A3"] = "Origin filter"
    ws["B3"] = "All"
    ws["D3"] = "Activation definition"
    ws["E3"] = "Purchase-window"
    ws["A3"].font = ws["D3"].font = Font(bold=True, color=INK)
    ws["B3"].fill = ws["E3"].fill = PatternFill("solid", fgColor=GOLD)
    ws["B3"].font = ws["E3"].font = Font(bold=True, color=NAVY)

    cards = [
        ("A5:B5", "A6:B7", "Mature deals", '=IF($B$3="All",COUNTIFS(tblSeller[mature_90d],1),COUNTIFS(tblSeller[mature_90d],1,tblSeller[origin],$B$3))', "#,##0"),
        ("C5:D5", "C6:D7", "Linked mature deals", '=IF($B$3="All",COUNTIFS(tblSeller[mature_90d],1,tblSeller[seller_linked_to_order_items],1),COUNTIFS(tblSeller[mature_90d],1,tblSeller[seller_linked_to_order_items],1,tblSeller[origin],$B$3))', "#,##0"),
        ("E5:F5", "E6:F7", "Unlinked / unobserved", "=A6-C6", "#,##0"),
        ("G5:H5", "G6:H7", "Observed activation", '=IF($E$3="Purchase-window",IF($B$3="All",SUMIFS(tblSeller[activated_90d],tblSeller[mature_90d],1,tblSeller[seller_linked_to_order_items],1),SUMIFS(tblSeller[activated_90d],tblSeller[mature_90d],1,tblSeller[seller_linked_to_order_items],1,tblSeller[origin],$B$3)),IF($B$3="All",SUMIFS(tblSeller[activated_delivered_within_90d],tblSeller[mature_90d],1,tblSeller[seller_linked_to_order_items],1),SUMIFS(tblSeller[activated_delivered_within_90d],tblSeller[mature_90d],1,tblSeller[seller_linked_to_order_items],1,tblSeller[origin],$B$3)))', "#,##0"),
        ("A9:B9", "A10:B11", "Activation rate", "=IFERROR(G6/C6,0)", "0.00%"),
        ("C9:D9", "C10:D11", "Delivered GMV (BRL)", '=IF($E$3="Purchase-window",IF($B$3="All",SUMIFS(tblSeller[gmv_90d_delivered_only],tblSeller[mature_90d],1,tblSeller[seller_linked_to_order_items],1),SUMIFS(tblSeller[gmv_90d_delivered_only],tblSeller[mature_90d],1,tblSeller[seller_linked_to_order_items],1,tblSeller[origin],$B$3)),IF($B$3="All",SUMIFS(tblSeller[gmv_90d_delivered_within_90d],tblSeller[mature_90d],1,tblSeller[seller_linked_to_order_items],1),SUMIFS(tblSeller[gmv_90d_delivered_within_90d],tblSeller[mature_90d],1,tblSeller[seller_linked_to_order_items],1,tblSeller[origin],$B$3)))', '"R$" #,##0.00'),
        ("E9:F9", "E10:F11", "Average delivered GMV", '=IF($E$3="Purchase-window",IF($B$3="All",AVERAGEIFS(tblSeller[gmv_90d_delivered_only],tblSeller[mature_90d],1,tblSeller[seller_linked_to_order_items],1),AVERAGEIFS(tblSeller[gmv_90d_delivered_only],tblSeller[mature_90d],1,tblSeller[seller_linked_to_order_items],1,tblSeller[origin],$B$3)),IF($B$3="All",AVERAGEIFS(tblSeller[gmv_90d_delivered_within_90d],tblSeller[mature_90d],1,tblSeller[seller_linked_to_order_items],1),AVERAGEIFS(tblSeller[gmv_90d_delivered_within_90d],tblSeller[mature_90d],1,tblSeller[seller_linked_to_order_items],1,tblSeller[origin],$B$3)))', '"R$" #,##0.00'),
        ("G9:H9", "G10:H11", "Median delivered GMV", '=IFERROR(MEDIAN(IF((tblSeller[mature_90d]=1)*(tblSeller[seller_linked_to_order_items]=1)*IF($B$3="All",1,tblSeller[origin]=$B$3),IF($E$3="Purchase-window",tblSeller[gmv_90d_delivered_only],tblSeller[gmv_90d_delivered_within_90d]))),0)', '"R$" #,##0.00'),
    ]
    for label_range, value_range, label, formula, fmt in cards:
        ws.merge_cells(label_range)
        ws.merge_cells(value_range)
        label_cell = label_range.split(":")[0]
        value_cell = value_range.split(":")[0]
        ws[label_cell] = label
        ws[value_cell] = formula
        for row in ws[label_range]:
            for cell in row:
                cell.fill = PatternFill("solid", fgColor="EAF1F8")
                cell.font = Font(bold=True, color=INK, size=10)
                cell.alignment = Alignment(horizontal="center", vertical="center")
        for row in ws[value_range]:
            for cell in row:
                cell.fill = PatternFill("solid", fgColor=PALE)
                cell.font = Font(bold=True, color=NAVY, size=18)
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.number_format = fmt

    ws.merge_cells("A13:H14")
    ws["A13"] = ("Unlinked seller outcomes are unobserved, not zero. Purchase-window activation means a seller has at least one "
                 "order purchased in the first 90 days and marked delivered in the source snapshot; strict activation requires "
                 "both purchase and delivery inside the first 90 days. GMV is item price in BRL, not seller profit or platform revenue.")
    ws["A13"].fill = PatternFill("solid", fgColor=GOLD)
    ws["A13"].font = Font(color="7F6000", size=10)
    ws["A13"].alignment = Alignment(wrap_text=True, vertical="center")

    for col, width in {"A":22, "B":18, "C":22, "D":18, "E":22, "F":18, "G":22, "H":18}.items():
        ws.column_dimensions[col].width = width
    ws.row_dimensions[13].height = 31
    ws.row_dimensions[14].height = 31
    ws.freeze_panes = "A3"

    origins_ws = wb["_Lists"]
    origin_dv = DataValidation(type="list", formula1="=OriginOptions", allow_blank=False)
    definition_dv = DataValidation(type="list", formula1="=DefinitionOptions", allow_blank=False)
    ws.add_data_validation(origin_dv)
    ws.add_data_validation(definition_dv)
    origin_dv.add(ws["B3"])
    definition_dv.add(ws["E3"])


def _build_origin_summary(wb, origins: list[str]):
    ws = wb.create_sheet("Origin_Summary")
    ws.sheet_view.showGridLines = False
    headers = ["origin", "mature_deals", "linked_mature_n", "activated_n", "activation_rate_pct", "wilson_low_pct", "wilson_high_pct", "linkage_rate_pct"]
    ws.append(headers)
    for idx, origin in enumerate(origins, start=2):
        ws.cell(idx, 1, origin)
        ws.cell(idx, 2, f'=COUNTIFS(tblSeller[origin],A{idx},tblSeller[mature_90d],1)')
        ws.cell(idx, 3, f'=COUNTIFS(tblSeller[origin],A{idx},tblSeller[mature_90d],1,tblSeller[seller_linked_to_order_items],1)')
        ws.cell(idx, 4, f'=IF(Executive_Dashboard!$E$3="Purchase-window",SUMIFS(tblSeller[activated_90d],tblSeller[origin],A{idx},tblSeller[mature_90d],1,tblSeller[seller_linked_to_order_items],1),SUMIFS(tblSeller[activated_delivered_within_90d],tblSeller[origin],A{idx},tblSeller[mature_90d],1,tblSeller[seller_linked_to_order_items],1))')
        ws.cell(idx, 5, f'=IFERROR(100*D{idx}/C{idx},0)')
        ws.cell(idx, 6, f'=IF(C{idx}=0,0,100*((D{idx}/C{idx}+1.95996398454^2/(2*C{idx}))/(1+1.95996398454^2/C{idx})-1.95996398454*SQRT(((D{idx}/C{idx})*(1-D{idx}/C{idx})+1.95996398454^2/(4*C{idx}))/C{idx})/(1+1.95996398454^2/C{idx})))')
        ws.cell(idx, 7, f'=IF(C{idx}=0,0,100*((D{idx}/C{idx}+1.95996398454^2/(2*C{idx}))/(1+1.95996398454^2/C{idx})+1.95996398454*SQRT(((D{idx}/C{idx})*(1-D{idx}/C{idx})+1.95996398454^2/(4*C{idx}))/C{idx})/(1+1.95996398454^2/C{idx})))')
        ws.cell(idx, 8, f'=IFERROR(100*C{idx}/B{idx},0)')
    end = len(origins)+1
    tab = Table(displayName="tblOriginSummary", ref=f"A1:H{end}")
    tab.tableStyleInfo = TableStyleInfo(name="TableStyleMedium4", showRowStripes=True, showColumnStripes=False)
    ws.add_table(tab)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=NAVY)
    ws.freeze_panes = "A2"
    for col, width in {"A":25, "B":16, "C":18, "D":15, "E":19, "F":17, "G":17, "H":17}.items():
        ws.column_dimensions[col].width = width
    return ws


def _build_reconciliation(wb, out_dir: Path):
    ws = wb.create_sheet("Reconciliation")
    ws.sheet_view.showGridLines = False
    ws.append(["metric", "python_value", "workbook_value", "sql_value", "absolute_difference", "tolerance", "status"])
    python_values, sql_values = _get_metric_values(out_dir)
    rows = [
        ("qualified_leads", "=SUM(tblLeads[qualified_leads])", 0),
        ("closed_deals", "=SUM(tblLeads[closed_leads])", 0),
        ("mature_deals", "=COUNTIFS(tblSeller[mature_90d],1)", 0),
        ("linked_mature_deals", "=COUNTIFS(tblSeller[mature_90d],1,tblSeller[seller_linked_to_order_items],1)", 0),
        ("activated_purchase_window", "=SUMIFS(tblSeller[activated_90d],tblSeller[mature_90d],1,tblSeller[seller_linked_to_order_items],1)", 0),
        ("activated_strict", "=SUMIFS(tblSeller[activated_delivered_within_90d],tblSeller[mature_90d],1,tblSeller[seller_linked_to_order_items],1)", 0),
        ("delivered_gmv", "=SUMIFS(tblSeller[gmv_90d_delivered_only],tblSeller[mature_90d],1,tblSeller[seller_linked_to_order_items],1)", 0.01),
        ("strict_delivered_gmv", "=SUMIFS(tblSeller[gmv_90d_delivered_within_90d],tblSeller[mature_90d],1,tblSeller[seller_linked_to_order_items],1)", 0.01),
        ("close_days_sum", "=SUM(tblSeller[close_days])", 0),
        ("close_days_n", "=COUNT(tblSeller[close_days])", 0),
    ]
    for idx, (metric, formula, tolerance) in enumerate(rows, start=2):
        ws.cell(idx, 1, metric)
        ws.cell(idx, 2, python_values.get(metric))
        ws.cell(idx, 3, formula)
        val = sql_values.get(metric)
        ws.cell(idx, 4, _excel_value(val) if val is not None and pd.notna(val) else None)
        ws.cell(idx, 5, f'=IF(OR(C{idx}="",D{idx}=""),"",ABS(C{idx}-D{idx}))')
        ws.cell(idx, 6, tolerance)
        ws.cell(idx, 7, f'=IF(D{idx}="","NOT RUN",IF(E{idx}<=F{idx},"PASS","FAIL"))')
    tab = Table(displayName="tblReconciliation", ref=f"A1:G{len(rows)+1}")
    tab.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    ws.add_table(tab)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=NAVY)
    for col, width in {"A":31, "B":18, "C":18, "D":18, "E":20, "F":14, "G":15}.items():
        ws.column_dimensions[col].width = width
    ws.freeze_panes = "A2"
    return ws


def build_workbook(out_dir: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    wb.remove(wb.active)

    readme = wb.create_sheet("Read_Me")
    readme.sheet_view.showGridLines = False
    notes = [
        ["Olist Seller Acquisition & 90-Day Value — live workbook"],
        ["Purpose", "Review qualified leads, deal maturity, seller linkage and observed post-win marketplace outcomes."],
        ["Live table", "Seller_Value is tblSeller. Edit a value in tblSeller and the formula-driven dashboard KPIs recalculate."],
        ["Selectors", "Executive_Dashboard B3 selects origin; E3 selects purchase-window or strict activation definition."],
        ["Booleans", "Boolean indicators are stored as 1/0 so Excel formulas and filters behave predictably."],
        ["Nulls", "Unlinked seller outcomes remain blank (unobserved), not zero. Mature/linked filters define the denominators."],
        ["Reconciliation", "Python and workbook values are populated. SQL values remain blank until scripts/run_postgres.py has run successfully."],
        ["PivotTable", "Excel PivotTables are not authorable with openpyxl. Follow PivotTable_Instructions in desktop Excel to insert the manual PivotTable."],
        ["Refresh", "Run python -m src.pipeline to regenerate source tabs and formulas, then open in Excel to calculate formulas."],
    ]
    for row in notes: readme.append(row)
    for cell in readme[1]:
        cell.font = Font(bold=True, color="FFFFFF", size=14)
        cell.fill = PatternFill("solid", fgColor=NAVY)
    for row in readme.iter_rows(min_row=2):
        row[0].font = Font(bold=True, color=INK)
        row[0].fill = PatternFill("solid", fgColor=BLUE)
        row[1].alignment = Alignment(wrap_text=True, vertical="top")
    readme.column_dimensions["A"].width = 23
    readme.column_dimensions["B"].width = 110
    readme.freeze_panes = "A2"

    tabs = [
        ("Lead_Pivots", "acquisition_funnel.csv", "tblLeads"),
        ("Seller_Value", "seller_90d_value.csv", "tblSeller"),
        ("Channel_Summary", "channel_90d_summary.csv", "tblChannel"),
        ("Validation_Exceptions", "validation_summary.csv", "tblValidation"),
        ("Close_Exceptions", "close_duration_exceptions.csv", "tblCloseExceptions"),
        ("Statistics", "statistics_summary.csv", "tblStatistics"),
        ("Inferential_Tests", "inferential_tests.csv", "tblInferentialTests"),
        ("Source_Manifest", "source_manifest.csv", "tblSourceManifest"),
        ("Linkage_Diagnostics", "linkage_diagnostics.csv", "tblLinkageDiagnostics"),
        ("IPW_Activation", "ipw_activation_by_origin.csv", "tblIPWActivation"),
        ("Window_Sensitivity", "window_sensitivity.csv", "tblWindowSensitivity"),
        ("Conversion_Lead_Type", "conversion_by_lead_type.csv", "tblLeadTypeConversion"),
        ("Conversion_Segment", "conversion_by_business_segment.csv", "tblSegmentConversion"),
        ("GMV_Concentration", "gmv_concentration.csv", "tblGMVConcentration"),
    ]
    for name, filename, table_name in tabs:
        _write_csv_sheet(wb, out_dir, name, filename, table_name)

    funnel = pd.read_csv(out_dir/"acquisition_funnel.csv")
    seller = pd.read_csv(out_dir/"seller_90d_value.csv")
    origins = sorted(set(funnel.origin.astype(str)) | set(seller.origin.astype(str)))
    lists = wb.create_sheet("_Lists")
    lists.sheet_state = "hidden"
    lists["A1"] = "Origin options"
    lists["A2"] = "All"
    for idx, origin in enumerate(origins, start=3): lists.cell(idx, 1, origin)
    lists["B1"] = "Definition options"
    lists["B2"] = "Purchase-window"
    lists["B3"] = "Strict"
    wb.defined_names.add(DefinedName("OriginOptions", attr_text=f"'_Lists'!$A$2:$A${len(origins)+2}"))
    wb.defined_names.add(DefinedName("DefinitionOptions", attr_text="'_Lists'!$B$2:$B$3"))

    _build_origin_summary(wb, origins)
    _build_dashboard(wb, out_dir, origins)
    _build_reconciliation(wb, out_dir)

    pivot = wb.create_sheet("PivotTable_Instructions")
    pivot.append(["Create the manual Excel PivotTable"])
    pivot.append(["1", "Select any populated cell in Seller_Value (tblSeller)."])
    pivot.append(["2", "Insert → PivotTable → From Table/Range. Keep tblSeller as the source."])
    pivot.append(["3", "Place origin in Rows; mature_90d and seller_linked_to_order_items in Filters."])
    pivot.append(["4", "Place mql_id in Values as Count; add activated_90d as Sum and gmv_90d_delivered_only as Sum."])
    pivot.append(["5", "Rename the sheet Origin_Pivot and format values. Refresh after editing Seller_Value."])
    pivot.append(["Status", "This workbook contains formula summaries and charts; the native PivotTable still must be inserted in desktop Excel."])
    for cell in pivot[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=NAVY)
    pivot.column_dimensions["A"].width = 15
    pivot.column_dimensions["B"].width = 110

    # All 11 origin categories are used in the two dashboard charts.
    dash = wb["Executive_Dashboard"]
    chart1 = BarChart()
    chart1.type = "bar"
    chart1.style = 10
    chart1.title = "Qualified leads by origin (all categories)"
    chart1.y_axis.title = "Origin"
    chart1.x_axis.title = "Qualified leads"
    source = wb["Lead_Pivots"]
    chart1.add_data(Reference(source, min_col=2, min_row=1, max_row=source.max_row), titles_from_data=True)
    chart1.set_categories(Reference(source, min_col=1, min_row=2, max_row=source.max_row))
    chart1.height = 8.2
    chart1.width = 15
    chart1.legend = None
    dash.add_chart(chart1, "A16")

    chart2 = BarChart()
    chart2.type = "bar"
    chart2.style = 11
    chart2.title = "Linkage and activation by origin (all 11 categories)"
    chart2.y_axis.title = "Origin"
    chart2.x_axis.title = "Rate (%)"
    origin_ws = wb["Origin_Summary"]
    chart2.add_data(Reference(origin_ws, min_col=8, max_col=8, min_row=1, max_row=origin_ws.max_row), titles_from_data=True)
    chart2.add_data(Reference(origin_ws, min_col=5, max_col=5, min_row=1, max_row=origin_ws.max_row), titles_from_data=True)
    chart2.set_categories(Reference(origin_ws, min_col=1, min_row=2, max_row=origin_ws.max_row))
    chart2.height = 8.2
    chart2.width = 15
    chart2.legend.position = "b"
    dash.add_chart(chart2, "J16")

    # Reconciliation formulas should recalculate on open in Excel.
    wb.calculation.fullCalcOnLoad = True
    wb.calculation.forceFullCalc = True
    wb.calculation.calcMode = "auto"
    wb.save(target)

