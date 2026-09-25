# make_kpi_pdf.py
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Preformatted, PageBreak
)
from reportlab.lib.enums import TA_LEFT

# ------------------------------------------------------------
# Styles
# ------------------------------------------------------------
styles = getSampleStyleSheet()
title_style = ParagraphStyle(
    'CustomTitle',
    parent=styles['Heading1'],
    fontSize=20,
    leading=24,
    spaceAfter=12,
    textColor=colors.HexColor('#1a1a1a'),
    alignment=TA_LEFT
)
h1 = ParagraphStyle(
    'H1',
    parent=styles['Heading1'],
    fontSize=16,
    leading=20,
    spaceBefore=16,
    spaceAfter=8,
    textColor=colors.HexColor('#003366')
)
h2 = ParagraphStyle(
    'H2',
    parent=styles['Heading2'],
    fontSize=13,
    leading=16,
    spaceBefore=12,
    spaceAfter=6,
    textColor=colors.HexColor('#005599')
)
body = ParagraphStyle(
    'Body',
    parent=styles['BodyText'],
    fontSize=10,
    leading=14,
    spaceAfter=6
)
code_style = ParagraphStyle(
    'Code',
    parent=styles['Code'],
    fontName='Courier',
    fontSize=8,
    leading=10,
    backColor=colors.HexColor('#f5f5f5'),
    borderColor=colors.HexColor('#cccccc'),
    borderWidth=0.5,
    borderPadding=4,
    spaceAfter=8
)

# ------------------------------------------------------------
# Document
# ------------------------------------------------------------
doc = SimpleDocTemplate(
    "KPI_Pack.pdf",
    pagesize=A4,
    rightMargin=2*cm,
    leftMargin=2*cm,
    topMargin=2*cm,
    bottomMargin=2*cm,
    title="KPI Pack – Energy, Production, MES",
    author="Data Engineering"
)

story = []

# ------------------------------------------------------------
# Title
# ------------------------------------------------------------
story.append(Paragraph("KPI Pack – Energy, Production, MES", title_style))
story.append(Paragraph(
    "Derived from cleaned Power Query tables: "
    "<i>dw_energy_readers_data_clean</i>, "
    "<i>excl_production_data_2026_clean</i>, "
    "<i>mes_cycle_data_clean</i>, "
    "<i>erp_product_info_clean</i>, "
    "<i>dw_energy_meter_x_machine_clean</i>.",
    body
))
story.append(Spacer(1, 0.5*cm))

# ------------------------------------------------------------
# 1. KPI Catalog
# ------------------------------------------------------------
story.append(Paragraph("1. KPI Catalog", h1))
story.append(Paragraph(
    "Assumption: <b>total_energy_passed</b> is in kWh. "
    "If it is in Wh, divide by 1000. "
    "<b>Solltakt</b> is assumed to be seconds per unit.",
    body
))
story.append(Spacer(1, 0.2*cm))

catalog_data = [
    ["Domain", "KPI", "Formula", "Source"],
    ["Energy", "Total Energy", "SUM(delta_energy)", "energy readers"],
    ["Energy", "Average Power kW", "SUM(delta_energy) / SUM(duration_hours)", "energy readers"],
    ["Energy", "Energy by Machine", "SUM(delta_energy) grouped by connected_machine", "energy + mapping"],
    ["Energy", "Negative Delta Count", "COUNT(delta_energy < 0)", "energy readers"],
    ["Energy", "Data Gap Count > 5 min", "COUNT(duration_seconds > 300)", "energy readers"],
    ["Energy", "Energy per Unit", "Total Energy / Total Produced", "energy + production"],
    ["Production", "Total Produced", "SUM(Stueckzahl)", "production"],
    ["Production", "Total Scrap", "SUM(Ausschuss)", "production"],
    ["Production", "Scrap Rate", "SUM(Ausschuss) / SUM(Stueckzahl)", "production"],
    ["Production", "Good Rate", "(SUM(Stueckzahl) - SUM(Ausschuss)) / SUM(Stueckzahl)", "production"],
    ["Production", "Runtime Hours", "SUM(end_datetime - start_datetime)", "production"],
    ["Production", "Downtime Hours", "SUM(downtime_min) / 60", "production"],
    ["Production", "Net Runtime Hours", "Runtime Hours - Downtime Hours", "production"],
    ["Production", "Availability", "Net Runtime Hours / Runtime Hours", "production"],
    ["Production", "Throughput", "SUM(Stueckzahl) / Net Runtime Hours", "production"],
    ["Production", "Labor Productivity", "SUM(Stueckzahl) / SUM(MA * Runtime Hours)", "production"],
    ["Production", "Setup / Changeover Ratio", "SUM(setup_min) / Runtime Hours", "production"],
    ["MES", "Total Menge2", "SUM(Menge2)", "MES"],
    ["MES", "Cycle Count", "COUNTROWS(mes_cycle_data_clean)", "MES"],
    ["MES", "Actual Takt", "Duration / Total Menge2", "MES"],
    ["MES", "Performance", "Solltakt / Actual Takt", "MES"],
    ["MES", "OEE", "Availability * Performance * Quality", "production + MES"],
    ["ERP", "Item Count", "COUNTROWS(erp_product_info_clean)", "ERP"],
    ["ERP", "Density Parsed %", "non-null density / total items", "ERP"],
    ["ERP", "Fill Volume Parsed %", "non-null fill volume / total items", "ERP"],
    ["ERP", "Avg Units per Pallet", "AVERAGE(UnitsOnPallet)", "ERP"],
    ["Cross", "Energy Cost", "Total Energy * price_per_kWh", "energy"],
    ["Cross", "CO2 Emissions", "Total Energy * CO2_factor", "energy"],
    ["Cross", "Scrap Cost", "Total Scrap * unit_cost", "production"],
]
t = Table(catalog_data, colWidths=[2.2*cm, 3.5*cm, 6.5*cm, 3.8*cm])
t.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003366')),
    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ('FONTSIZE', (0,0), (-1,-1), 8),
    ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f0f4f8')]),
]))
story.append(t)
story.append(PageBreak())

# ------------------------------------------------------------
# 2. Sample Energy KPIs
# ------------------------------------------------------------
story.append(Paragraph("2. Sample Energy KPIs", h1))
story.append(Paragraph(
    "Calculated from the provided excerpt: "
    "<b>2026-09-23 14:26:40.233</b> to <b>2026-09-23 17:56:18.283</b> "
    "(duration ≈ 3.4937 h).",
    body
))
story.append(Spacer(1, 0.2*cm))

sample_data = [
    ["Meter", "Machine", "Total Energy (kWh)", "Avg Power (kW)", "Share"],
    ["IFD001", "falschacht", "3.02295", "0.8652", "26.9%"],
    ["IFD002", "etikket", "0.42899", "0.1228", "3.8%"],
    ["IFD003", "verschr", "3.88110", "1.1109", "34.6%"],
    ["IFD004", "abf", "2.58594", "0.7402", "23.0%"],
    ["IFD005", "Flaschenbeschicker", "1.30798", "0.3744", "11.7%"],
    ["Total", "", "11.22696", "3.2135", "100%"],
]
t2 = Table(sample_data, colWidths=[2.5*cm, 3.5*cm, 3.5*cm, 3.0*cm, 2.5*cm])
t2.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#005599')),
    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ('FONTSIZE', (0,0), (-1,-1), 9),
    ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#e8f0fe')]),
]))
story.append(t2)
story.append(Spacer(1, 0.5*cm))
story.append(Paragraph(
    "<i>Note: The full file will recalculate these values exactly. "
    "These numbers are based only on the excerpt provided.</i>",
    body
))
story.append(PageBreak())

# ------------------------------------------------------------
# 3. Power Query M Code
# ------------------------------------------------------------
story.append(Paragraph("3. Power Query M Code", h1))
story.append(Paragraph(
    "Create each as a Blank Query in Excel: "
    "<b>Data &gt; Get Data &gt; From Other Sources &gt; Blank Query &gt; Advanced Editor</b>. "
    "Replace <b>C:\\Path\\...</b> with your actual file paths.",
    body
))
story.append(Spacer(1, 0.3*cm))

m_codes = {
    "3.1 Energy_By_Meter_KPI": '''let
    Source = dw_energy_readers_data_clean,
    Group = Table.Group(
        Source,
        {"energy_meter_device_asset_tag", "name_old", "connected_machine", "prod_line"},
        {
            {"first_timestamp", each List.Min([timestamp]), type datetime},
            {"last_timestamp", each List.Max([timestamp]), type datetime},
            {"first_energy", each List.First(List.Sort([total_energy_passed])), type number},
            {"last_energy", each List.Last(List.Sort([total_energy_passed])), type number},
            {"readings", each Table.RowCount(_), Int64.Type},
            {"total_energy", each List.Sum([delta_energy]), type number},
            {"avg_power", each List.Average([power_kw]), type number},
            {"min_delta", each List.Min([delta_energy]), type number},
            {"max_delta", each List.Max([delta_energy]), type number},
            {"negative_delta_count", each List.Count(List.Select([delta_energy], each _ < 0)), Int64.Type},
            {"gap_count_gt_5min", each List.Count(List.Select([duration_seconds], each _ > 300)), Int64.Type}
        }
    ),
    AddShare = Table.AddColumn(
        Group,
        "share",
        each if List.Sum(Group[total_energy]) = 0 then null
             else [total_energy] / List.Sum(Group[total_energy]),
        type number
    )
in
    AddShare''',

    "3.2 Energy_By_Hour_KPI": '''let
    Source = dw_energy_readers_data_clean,
    AddDateHour = Table.AddColumn(
        Source,
        "date_hour",
        each #datetime(
            Date.Year([timestamp]),
            Date.Month([timestamp]),
            Date.Day([timestamp]),
            Time.Hour([timestamp]),
            0,
            0
        ),
        type datetime
    ),
    Group = Table.Group(
        AddDateHour,
        {"date_hour", "energy_meter_device_asset_tag", "connected_machine", "prod_line"},
        {
            {"total_energy", each List.Sum([delta_energy]), type number},
            {"avg_power", each List.Average([power_kw]), type number},
            {"readings", each Table.RowCount(_), Int64.Type}
        }
    )
in
    Group''',

    "3.3 Production_By_Order_KPI": '''let
    Source = excl_production_data_2026_clean,
    AddRuntime = Table.AddColumn(
        Source,
        "runtime_hours",
        each Duration.TotalHours([end_datetime] - [start_datetime]),
        type number
    ),
    AddDowntime = Table.AddColumn(
        AddRuntime,
        "downtime_min",
        each List.Sum({
            [Stoerung1_Min],
            [Stoerung2_Min],
            [Pause_pro_Person],
            [Reinigung],
            [Maschine_einrichten],
            [Maschine_umruesten],
            [Wechsel1_Min],
            [Wechsel2_Min],
            [Wechsel3_Min]
        }),
        type number
    ),
    AddNetRuntime = Table.AddColumn(
        AddDowntime,
        "net_runtime_hours",
        each [runtime_hours] - ([downtime_min] / 60),
        type number
    ),
    AddMAHours = Table.AddColumn(
        AddNetRuntime,
        "ma_hours",
        each [MA] * [runtime_hours],
        type number
    ),
    Group = Table.Group(
        AddMAHours,
        {"Auftragskarte_Nr", "Artikelnummer"},
        {
            {"total_stueck", each List.Sum([Stueckzahl]), type number},
            {"total_ausschuss", each List.Sum([Ausschuss]), type number},
            {"runtime_hours", each List.Sum([runtime_hours]), type number},
            {"net_runtime_hours", each List.Sum([net_runtime_hours]), type number},
            {"ma_hours", each List.Sum([ma_hours]), type number},
            {"downtime_min", each List.Sum([downtime_min]), type number}
        }
    ),
    AddGoodUnits = Table.AddColumn(
        Group,
        "good_units",
        each [total_stueck] - [total_ausschuss],
        type number
    ),
    AddScrapRate = Table.AddColumn(
        AddGoodUnits,
        "scrap_rate",
        each if [total_stueck] = 0 then null
             else [total_ausschuss] / [total_stueck],
        type number
    ),
    AddAvailability = Table.AddColumn(
        AddScrapRate,
        "availability",
        each if [runtime_hours] = 0 then null
             else [net_runtime_hours] / [runtime_hours],
        type number
    ),
    AddThroughput = Table.AddColumn(
        AddAvailability,
        "units_per_hour",
        each if [net_runtime_hours] = 0 then null
             else [total_stueck] / [net_runtime_hours],
        type number
    ),
    AddLaborProd = Table.AddColumn(
        AddThroughput,
        "units_per_labor_hour",
        each if [ma_hours] = 0 then null
             else [total_stueck] / [ma_hours],
        type number
    )
in
    AddLaborProd''',

    "3.4 MES_By_Machine_KPI": '''let
    Source = mes_cycle_data_clean,
    Group = Table.Group(
        Source,
        {"Maschine", "Auftrag", "Artikel"},
        {
            {"total_menge2", each List.Sum([Menge2]), type number},
            {"cycles", each Table.RowCount(_), Int64.Type},
            {"avg_solltakt", each List.Average([Solltakt]), type number},
            {"start_time", each List.Min([datetime]), type datetime},
            {"end_time", each List.Max([datetime]), type datetime}
        }
    ),
    AddDurationSec = Table.AddColumn(
        Group,
        "duration_sec",
        each Duration.TotalSeconds([end_time] - [start_time]),
        type number
    ),
    AddActualTakt = Table.AddColumn(
        AddDurationSec,
        "actual_takt_sec",
        each if [total_menge2] = 0 then null
             else [duration_sec] / [total_menge2],
        type number
    ),
    AddPerformance = Table.AddColumn(
        AddActualTakt,
        "performance",
        each if [actual_takt_sec] = 0 then null
             else [avg_solltakt] / [actual_takt_sec],
        type number
    )
in
    AddPerformance''',

    "3.5 ERP_Data_Quality_KPI": '''let
    Source = erp_product_info_clean,
    Total = Table.RowCount(Source),
    KPI = Table.FromRecords({
        [KPI = "Total Items", Value = Total],
        [KPI = "Items with density", Value = List.Count(List.Select(Source[FilledLiquideDensity_num], each _ <> null))],
        [KPI = "Items with fill volume", Value = List.Count(List.Select(Source[fill_value_num], each _ <> null))],
        [KPI = "Items with units per pallet", Value = List.Count(List.Select(Source[UnitsOnPallet], each _ <> null))]
    })
in
    KPI''',

    "3.6 Cross_Energy_Per_Unit_Daily": '''let
    EnergyDaily = Table.Group(
        dw_energy_readers_data_clean,
        {"Datum"},
        {{"total_energy", each List.Sum([delta_energy]), type number}}
    ),
    ProductionDaily = Table.Group(
        excl_production_data_2026_clean,
        {"Datum"},
        {{"total_units", each List.Sum([Stueckzahl]), type number}}
    ),
    Join = Table.NestedJoin(
        EnergyDaily,
        {"Datum"},
        ProductionDaily,
        {"Datum"},
        "prod",
        JoinKind.LeftOuter
    ),
    Expand = Table.ExpandTableColumn(Join, "prod", {"total_units"}),
    AddKPI = Table.AddColumn(
        Expand,
        "energy_per_unit",
        each if [total_units] = 0 or [total_units] = null then null
             else [total_energy] / [total_units],
        type number
    )
in
    AddKPI'''
}

for title, code in m_codes.items():
    story.append(Paragraph(title, h2))
    story.append(Preformatted(code, code_style))
    story.append(Spacer(1, 0.2*cm))

story.append(PageBreak())

# ------------------------------------------------------------
# 4. DAX Measures
# ------------------------------------------------------------
story.append(Paragraph("4. DAX Measures", h1))
story.append(Paragraph(
    "Load the cleaned queries into the Data Model and create these measures.",
    body
))
story.append(Spacer(1, 0.2*cm))

dax_code = '''Total Energy :=
SUM(dw_energy_readers_data_clean[delta_energy])

Avg Power kW :=
DIVIDE(
    [Total Energy],
    SUM(dw_energy_readers_data_clean[duration_seconds]) / 3600
)

Negative Delta Count :=
COUNTROWS(
    FILTER(dw_energy_readers_data_clean, dw_energy_readers_data_clean[delta_energy] < 0)
)

Total Produced :=
SUM(excl_production_data_2026_clean[Stueckzahl])

Total Scrap :=
SUM(excl_production_data_2026_clean[Ausschuss])

Scrap Rate :=
DIVIDE([Total Scrap], [Total Produced])

Good Rate :=
DIVIDE([Total Produced] - [Total Scrap], [Total Produced])

Runtime Hours :=
SUMX(
    excl_production_data_2026_clean,
    DATEDIFF(
        excl_production_data_2026_clean[start_datetime],
        excl_production_data_2026_clean[end_datetime],
        SECOND
    ) / 3600
)

Downtime Hours :=
SUM(excl_production_data_2026_clean[downtime_min]) / 60

Net Runtime Hours :=
[Runtime Hours] - [Downtime Hours]

Availability :=
DIVIDE([Net Runtime Hours], [Runtime Hours])

Throughput :=
DIVIDE([Total Produced], [Net Runtime Hours])

Labor Productivity :=
DIVIDE(
    [Total Produced],
    SUMX(
        excl_production_data_2026_clean,
        excl_production_data_2026_clean[MA] *
        DATEDIFF(
            excl_production_data_2026_clean[start_datetime],
            excl_production_data_2026_clean[end_datetime],
            SECOND
        ) / 3600
    )
)

MES Total Menge2 :=
SUM(mes_cycle_data_clean[Menge2])

MES Cycles :=
COUNTROWS(mes_cycle_data_clean)

MES Actual Takt :=
DIVIDE(
    DATEDIFF(
        MIN(mes_cycle_data_clean[datetime]),
        MAX(mes_cycle_data_clean[datetime]),
        SECOND
    ),
    [MES Total Menge2]
)

MES Performance :=
DIVIDE(
    AVERAGE(mes_cycle_data_clean[Solltakt]),
    [MES Actual Takt]
)

Energy per Unit :=
DIVIDE([Total Energy], [Total Produced])'''

story.append(Preformatted(dax_code, code_style))
story.append(PageBreak())

# ------------------------------------------------------------
# 5. Dashboard Layout
# ------------------------------------------------------------
story.append(Paragraph("5. Recommended Dashboard Layout", h1))

layout = [
    ["Page", "Visuals"],
    ["Page 1 – Energy",
     "Cards: Total Energy, Avg Power, Negative Delta Count\n"
     "Bar chart: Energy by Machine\n"
     "Line chart: Energy by Hour\n"
     "Table: Energy_By_Meter_KPI"],
    ["Page 2 – Production",
     "Cards: Total Produced, Scrap Rate, Availability, Throughput\n"
     "Bar chart: Top orders by Throughput\n"
     "Matrix: Order × Article with Scrap Rate\n"
     "Table: Production_By_Order_KPI"],
    ["Page 3 – MES",
     "Cards: Total Menge2, Cycles, Performance\n"
     "Bar chart: Performance by Machine\n"
     "Table: MES_By_Machine_KPI"],
    ["Page 4 – Cross / Management",
     "Cards: Energy per Unit, Energy Cost, CO2, Scrap Cost\n"
     "Line chart: Energy per Unit over time\n"
     "Table: Cross_Energy_Per_Unit_Daily"],
]
t3 = Table(layout, colWidths=[4*cm, 12*cm])
t3.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003366')),
    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ('FONTSIZE', (0,0), (-1,-1), 9),
    ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f0f4f8')]),
]))
story.append(t3)
story.append(Spacer(1, 0.5*cm))
story.append(Paragraph(
    "<b>How to load into Excel:</b><br/>"
    "1. Create all cleaned queries from the previous step.<br/>"
    "2. Create each KPI query using the M code above.<br/>"
    "3. For each query: <i>Close &amp; Load To… &gt; PivotTable Report</i> or <i>Only Create Connection</i>.<br/>"
    "4. Add to Data Model if you want DAX measures.<br/>"
    "5. Build PivotTables / charts from the KPI tables.",
    body
))

# ------------------------------------------------------------
# Build
# ------------------------------------------------------------
doc.build(story)
print("PDF created: KPI_Pack.pdf")