#!/usr/bin/env python3
"""Build compact production dashboard data from the supplied BBMED Excel sources.

Runtime dashboard does NOT require Python. This script exists so the JSON can be
reproduced from the original source workbooks committed under source-data/.
Uses only Python standard library to avoid adding ETL dependencies.
"""
from __future__ import annotations
import json, math, os, re, statistics, zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from pathlib import Path
from dashboard_metrics import normalize_order, meter_intervals, allocate_energy

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "source-data"
OUT = ROOT / "data" / "dashboard.json"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

FILES = {
    "meter_map": "1.dw_energy_meter_x_machine.xlsx",
    "energy": "2.dw_energy_readers_data .xlsx",
    "erp": "3.erp_product_info_cleaned.xlsx",
    "excel_prod": "4.excl_production_data_2026_cleaned.xlsx",
    "cycle": "5.mes_cycle_data_cleaned.xlsx",
    "stoppages": "6.mes_stoppages_cleaned.xlsx",
    "stoppage_types": "7.mes_stoppage_types_cleaned.xlsx",
    "reasons": "8.mes_stopage_reason_per_machine_group_cleaned.xlsx",
    "categories": "9.mes_stopage_categories_cleaned.xlsx",
    "shifts": "10.mes_shift_info_cleaned.xlsx",
    "temp": "11.mes_temp_stoppages_cleaned.xlsx",
    "rejects": "12.mes_rejections_ids_x_work_ids_cleaned.xlsx",
    "machine_groups": "13.mes_machine_groups_cleaned.xlsx",
    "periods_2025": "14.mes_production_periods_2025_cleaned.xlsx",
    "periods_2026": "15.mes_production_periods_2026_cleaned.xlsx",
    "person_bridge": "16.mes_person_x_work_record_cleaned.xlsx",
    "rates": "17.mes_item_prod_rate_cleaned.xlsx",
    "orders": "18.mes_production_orders_cleaned.xlsx",
    "order_audit": "19.mes_prod_order_data_cleaned.xlsx",
    "personnel": "20.mes_personel_cleaned.xlsx",
}

ROLES = {
    "meter_map": "Energy meter dimension / component map",
    "energy": "Raw cumulative energy readings",
    "erp": "Product dimension; density / pack attributes",
    "excel_prod": "Manual production fact / comparison source",
    "cycle": "Raw cycle/event log; drill-through source",
    "stoppages": "Stoppage fact by WorkRecordID",
    "stoppage_types": "Stoppage type dimension",
    "reasons": "Stoppage reason dimension; composite key",
    "categories": "Reference stoppage taxonomy",
    "shifts": "Shift dimension",
    "temp": "Raw status/event log; energy-state/audit layer",
    "rejects": "Reject fact",
    "machine_groups": "Machine-group dimension",
    "periods_2025": "Production-period fact (historical)",
    "periods_2026": "Production-period fact (2026 core)",
    "person_bridge": "WorkRecord↔Person bridge",
    "rates": "Product target-rate enrichment",
    "orders": "Order dimension / planned attributes",
    "order_audit": "Order audit snapshot / validation source",
    "personnel": "Personnel dimension",
}


def shared_strings(z: zipfile.ZipFile):
    try:
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return ["".join(t.text or "" for t in si.iter(NS + "t")) for si in root.findall(NS + "si")]


def col_index(ref: str) -> int:
    m = re.match(r"([A-Z]+)", ref)
    n = 0
    for ch in m.group(1):
        n = n * 26 + ord(ch) - 64
    return n - 1


def iter_xlsx(path: Path):
    with zipfile.ZipFile(path) as z:
        ss = shared_strings(z)
        with z.open("xl/worksheets/sheet1.xml") as f:
            header = None
            for _, elem in ET.iterparse(f, events=("end",)):
                if elem.tag != NS + "row":
                    continue
                vals = {}
                for c in elem.findall(NS + "c"):
                    ref = c.get("r", "A1")
                    typ = c.get("t")
                    v = c.find(NS + "v")
                    if typ == "inlineStr":
                        isel = c.find(NS + "is")
                        val = "".join(t.text or "" for t in isel.iter(NS + "t")) if isel is not None else ""
                    elif v is None:
                        val = ""
                    elif typ == "s":
                        val = ss[int(v.text)] if v.text else ""
                    else:
                        val = v.text or ""
                    vals[col_index(ref)] = val
                mx = max(vals) if vals else -1
                row = [vals.get(i, "") for i in range(mx + 1)]
                elem.clear()
                if header is None:
                    header = row
                    continue
                if not any(str(x).strip() for x in row):
                    continue
                if len(row) < len(header):
                    row += [""] * (len(header)-len(row))
                yield {header[i]: row[i] if i < len(row) else "" for i in range(len(header))}


def sheet_dimension(path: Path):
    with zipfile.ZipFile(path) as z:
        with z.open("xl/worksheets/sheet1.xml") as f:
            chunk = f.read(16384).decode("utf-8", "ignore")
    m = re.search(r'<dimension ref="([A-Z]+)(\d+):([A-Z]+)(\d+)"', chunk)
    if m:
        return int(m.group(4)) - 1
    # fallback count rows
    return sum(1 for _ in iter_xlsx(path))


def fnum(v, default=0.0):
    try:
        if v is None or str(v).strip() == "": return default
        return float(v)
    except Exception:
        return default


def txt(v):
    s = str(v or "").strip()
    if s.endswith(".0") and s[:-2].isdigit(): s = s[:-2]
    return s


def excel_dt(serial):
    if serial is None or str(serial).strip()=="": return None
    try:
        return datetime(1899, 12, 30) + timedelta(days=float(serial))
    except Exception:
        try: return datetime.fromisoformat(str(serial).replace(".000", ""))
        except Exception: return None


def iso(dt): return dt.isoformat(timespec="seconds") if dt else None

def median(vals):
    vals=[v for v in vals if v is not None and math.isfinite(v)]
    return statistics.median(vals) if vals else None

def mean(vals):
    vals=[v for v in vals if v is not None and math.isfinite(v)]
    return sum(vals)/len(vals) if vals else None

def pct(n,d): return 100*n/d if d else None

def pearson(xs, ys):
    pairs=[(x,y) for x,y in zip(xs,ys) if x is not None and y is not None and math.isfinite(x) and math.isfinite(y)]
    if len(pairs)<3:return None
    xs=[p[0] for p in pairs]; ys=[p[1] for p in pairs]
    mx=sum(xs)/len(xs); my=sum(ys)/len(ys)
    a=sum((x-mx)*(y-my) for x,y in pairs)
    b=math.sqrt(sum((x-mx)**2 for x in xs)*sum((y-my)**2 for y in ys))
    return a/b if b else None

# -------- dimensions / lookup data --------
reason_lookup={}
for r in iter_xlsx(SRC/FILES["reasons"]):
    reason_lookup[f"{txt(r['machine_group_id'])}|{txt(r['disruption_number'])}"] = r.get("short_text") or r.get("long_text") or "Unknown"

meter_map={r["name_new"]: {"component":r["connected_machine"],"line":r["prod_line"],"legacy":r["name_old"]} for r in iter_xlsx(SRC/FILES["meter_map"])}

# ERP density / fill
products={}
for r in iter_xlsx(SRC/FILES["erp"]):
    code=txt(r["ItemCode"])
    density=fnum(r.get("FilledLiquideDensity"), None)
    if density is None or density==0: density=fnum(r.get("U_AbfDichte"), None)
    products[code]={"density":density,"fill":r.get("FillUpVolume") or "","unitsBox":fnum(r.get("UnitsInBox"),None),"unitsPallet":fnum(r.get("UnitsOnPallet"),None)}

# -------- 2026 production periods aggregated to order --------
planned={normalize_order(r["OrderNumber"]): r for r in iter_xlsx(SRC/FILES["orders"])}
km1_periods=[]
period_groups=defaultdict(lambda: {"usageHours":0, "productionHours":0, "produced":0, "employeeHours":0, "technicalMin":0, "organizationalMin":0})
orders=defaultdict(lambda:{"workRecords":set(),"machineSec":defaultdict(float),"productSec":defaultdict(float),"shifts":Counter(),"usageSec":0.0,"prodSec":0.0,"produced":0.0,"theoretical":0.0,"employeeHours":0.0,"starts":[],"ends":[]})
wr_to_order={}
wr_machine={}
for r in iter_xlsx(SRC/FILES["periods_2026"]):
    order=normalize_order(r.get("OrderNo")); wr=txt(r.get("WorkRecordID")); machine=txt(r.get("MachineID")); product=txt(r.get("ProductID")); shift=txt(r.get("Shift"))
    if not order: continue
    usage=fnum(r.get("CalcUsageTime")); prod=fnum(r.get("CalcProductionTime")); produced=fnum(r.get("ProducedDuringThePeriod")); target=fnum(r.get("TargetUnitsPerMinute")); workers=fnum(r.get("WorkerCount"))
    o=orders[order]; o["workRecords"].add(wr); o["usageSec"]+=usage; o["prodSec"]+=prod; o["produced"]+=produced; o["theoretical"]+=target*prod/60; o["employeeHours"]+=workers*usage/3600
    o["machineSec"][machine]+=usage; o["productSec"][product]+=usage
    if shift:o["shifts"][shift]+=usage
    try: st=datetime.fromisoformat(str(r.get("PointStart")).replace(".000","")); o["starts"].append(st)
    except: pass
    try: en=datetime.fromisoformat(str(r.get("PointEnd")).replace(".000","")); o["ends"].append(en)
    except: pass
    if machine=="KM1":
        period_start=excel_dt(r.get("PointStart")); period_end=excel_dt(r.get("PointEnd"))
        if period_start and period_end and period_end>period_start: km1_periods.append((period_start,period_end,order))
    day=str(r.get("PointStart", ""))[:10]
    pg=period_groups[(order,machine,product,shift or "Unknown",day)]
    for key,value in {"usageHours":usage/3600,"productionHours":prod/3600,"produced":produced,"employeeHours":workers*usage/3600,"technicalMin":fnum(r.get("StoppageTimeTechnic"))/60,"organizationalMin":fnum(r.get("StoppageTimeOrganiz"))/60}.items(): pg[key]+=value
    wr_to_order[wr]=order; wr_machine[wr]=machine

# rejects by order
reject_by_order=defaultdict(float); reject_wr=set()
for r in iter_xlsx(SRC/FILES["rejects"]):
    wr=txt(r.get("WorkRecordId")); q=fnum(r.get("RejectQTY")); reject_wr.add(wr)
    if wr in wr_to_order: reject_by_order[wr_to_order[wr]] += q

# type-1 stoppage by order/reason
stop_details=[]
stop_by_order=defaultdict(float); stop_reason_order=defaultdict(lambda:defaultdict(float)); stop_reason_total=defaultdict(float); stop_reason_count=defaultdict(int)
for r in iter_xlsx(SRC/FILES["stoppages"]):
    wr=txt(r.get("work_record_id")); order=wr_to_order.get(wr)
    if not order or txt(r.get("stoppage_type_code")) != "1": continue
    secs=fnum(r.get("stoppage_time")); no=txt(r.get("stoppage_no")); machine=wr_machine.get(wr,"")
    group="2" if machine.startswith("AXO") else "1"
    label=reason_lookup.get(f"{group}|{no}", f"Reason {no}")
    stop_details.append({"order":order,"reason":label,"minutes":round(secs/60,4),"events":fnum(r.get("stoppage_count"),None),"machine":machine})
    stop_by_order[order]+=secs; stop_reason_order[order][label]+=secs; stop_reason_total[label]+=secs; stop_reason_count[label]+=1

# Excel manual production aggregated by order
excel_orders=defaultdict(lambda:{"qty":0.0,"scrap":0.0,"starts":[],"ends":[],"rows":0,"products":Counter(),"cleaningMin":0,"setupMin":0,"changeoverMin":0})
for r in iter_xlsx(SRC/FILES["excel_prod"]):
    order=normalize_order(r.get("Auftragskarte Nr."));
    if not order: continue
    x=excel_orders[order]; x["rows"]+=1; x["qty"]+=fnum(r.get("Stückzahl")); x["scrap"]+=fnum(r.get("Ausschuss (Stück)")); x["products"][txt(r.get("Artikelnummer"))]+=1
    x["cleaningMin"]+=fnum(r.get("Reinigung (Min.)"))
    x["setupMin"]+=fnum(r.get("Maschine einrichten (Min.)"))
    x["changeoverMin"]+=fnum(r.get("Maschine umrüsten (Min.)"))+sum(fnum(r.get(f"Wechsel {i} (Min.)")) for i in [1,2,3])
    d=excel_dt(r.get("Datum")); bt=excel_dt(r.get("Beginn")); et=excel_dt(r.get("Ende"))
    if d and bt:
        st=datetime(d.year,d.month,d.day)+timedelta(days=(bt-datetime(1899,12,30)).total_seconds()/86400 % 1); x["starts"].append(st)
    if d and et:
        en=datetime(d.year,d.month,d.day)+timedelta(days=(et-datetime(1899,12,30)).total_seconds()/86400 % 1)
        if bt and en < st: en += timedelta(days=1)
        x["ends"].append(en)

# finalize order records
records=[]
for order,o in orders.items():
    machine=max(o["machineSec"], key=o["machineSec"].get) if o["machineSec"] else "Unknown"
    product=max(o["productSec"], key=o["productSec"].get) if o["productSec"] else "Unknown"
    usage_h=o["usageSec"]/3600; prod_h=o["prodSec"]/3600
    rate=o["produced"]/(o["usageSec"]/60) if o["usageSec"] else None
    net_rate=o["produced"]/(o["prodSec"]/60) if o["prodSec"] else None
    availability=o["prodSec"]/o["usageSec"] if o["usageSec"] else None
    performance=o["produced"]/o["theoretical"] if o["theoretical"] else None
    rejects=reject_by_order.get(order,0)
    quality=o["produced"]/(o["produced"]+rejects) if (o["produced"]+rejects)>0 else None
    oee=(availability*performance*quality) if None not in (availability,performance,quality) else None
    stop_min=stop_by_order.get(order,0)/60
    intensity=stop_min/usage_h if usage_h else None
    avg_workers=o["employeeHours"]/usage_h if usage_h else None
    units_emp=o["produced"]/o["employeeHours"] if o["employeeHours"] else None
    xo=excel_orders.get(order)
    xqty=xo["qty"] if xo else None
    delta=((o["produced"]-xqty)/xqty*100) if xqty not in (None,0) else None
    start=min(o["starts"]) if o["starts"] else None; end=max(o["ends"]) if o["ends"] else None
    xstart=min(xo["starts"]) if xo and xo["starts"] else None; xend=max(xo["ends"]) if xo and xo["ends"] else None
    start_gap=abs((start-xstart).total_seconds())/60 if start and xstart else None
    duration_min=(end-start).total_seconds()/60 if start and end else None
    xduration_min=(xend-xstart).total_seconds()/60 if xstart and xend else None
    dens=products.get(product,{}).get("density")
    fill=products.get(product,{}).get("fill") or "Unknown"
    top_reason=None
    if stop_reason_order.get(order):
        top_reason=max(stop_reason_order[order], key=stop_reason_order[order].get)
    plan=planned.get(order,{})
    target_qty=fnum(plan.get("TargetQuantity"),None)
    target_rate=fnum(plan.get("TargetProductionRatePerMinute"),None)
    planned_min=target_qty/target_rate if target_qty and target_rate and target_rate>0 else None
    records.append({
        "orderedQty":target_qty,"targetRate":target_rate,"plannedRunMin":planned_min,
        "excelStart":iso(xstart),"excelEnd":iso(xend),
        "manualCleaningMin":xo["cleaningMin"] if xo else None,"manualSetupMin":xo["setupMin"] if xo else None,"manualChangeoverMin":xo["changeoverMin"] if xo else None,
        "endGapMin":abs((end-xend).total_seconds())/60 if end and xend else None,
        "unitsBox":products.get(product,{}).get("unitsBox"),
        "order":order,"machine":machine,"product":product,"shift":o["shifts"].most_common(1)[0][0] if o["shifts"] else "Unknown",
        "start":iso(start),"end":iso(end),"usageHours":round(usage_h,4),"productionHours":round(prod_h,4),"produced":round(o["produced"]),
        "grossRate":round(rate,3) if rate is not None else None,"netRunRate":round(net_rate,3) if net_rate is not None else None,
        "availability":round(availability*100,2) if availability is not None else None,"performance":round(performance*100,2) if performance is not None else None,
        "quality":round(quality*100,2) if quality is not None else None,"oee":round(oee*100,2) if oee is not None else None,
        "rejectQty":round(rejects,2),"hasRejectRecord":any(w in reject_wr for w in o["workRecords"]),
        "disturbanceMin":round(stop_min,2),"disturbanceIntensity":round(intensity,3) if intensity is not None else None,"topReason":top_reason,
        "employeeHours":round(o["employeeHours"],3),"avgWorkers":round(avg_workers,3) if avg_workers is not None else None,"unitsPerEmployeeHour":round(units_emp,2) if units_emp is not None else None,
        "excelQty":round(xqty,2) if xqty is not None else None,"qtyDeltaPct":round(delta,3) if delta is not None else None,"startGapMin":round(start_gap,2) if start_gap is not None else None,
        "mesDurationMin":round(duration_min,2) if duration_min is not None else None,"excelDurationMin":round(xduration_min,2) if xduration_min is not None else None,
        "density":density if (density:=dens) is not None else None,"fillVolume":fill,"workRecordCount":len(o["workRecords"]),
    })

# quartiles by produced count among positive-production orders
positive=sorted([r for r in records if r["produced"]>0], key=lambda r:r["produced"])
for i,r in enumerate(positive):
    q=min(4, int(i*4/len(positive))+1); r["sizeQuartile"]=f"Q{q}"
for r in records:
    if "sizeQuartile" not in r:r["sizeQuartile"]="Q1"
    if r["excelQty"] is None:r["matchStatus"]="UNMATCHED"
    elif r["qtyDeltaPct"] is None:r["matchStatus"]="UNDEFINED"
    elif r["qtyDeltaPct"] is not None and abs(r["qtyDeltaPct"])<=1:r["matchStatus"]="LE1"
    elif r["qtyDeltaPct"] is not None and abs(r["qtyDeltaPct"])<=5:r["matchStatus"]="LE5"
    else:r["matchStatus"]="GT5"

records.sort(key=lambda r:(r["machine"],r["order"]))
matched=[r for r in records if r["excelQty"] is not None]
valid=[r for r in records if r["produced"]>0 and r["usageHours"]>0]

# size group summaries
size_summary=[]
for q in ["Q1","Q2","Q3","Q4"]:
    rr=[r for r in valid if r["sizeQuartile"]==q]
    size_summary.append({"group":q,"orders":len(rr),"medianRate":round(median([r["grossRate"] for r in rr]),2),"medianDisturbanceIntensity":round(median([r["disturbanceIntensity"] for r in rr]),2),"medianUnits":round(median([r["produced"] for r in rr]))})

machine_summary=[]
for m in sorted(set(r["machine"] for r in valid)):
    rr=[r for r in valid if r["machine"]==m]; mm=[r for r in rr if r["excelQty"] is not None]
    machine_summary.append({
        "machine":m,"orders":len(rr),"produced":round(sum(r["produced"] for r in rr)),"medianRate":round(median([r["grossRate"] for r in rr]),2),"medianAvailability":round(median([r["availability"] for r in rr]),2),"medianOee":round(median([r["oee"] for r in rr]),2),
        "matched":len(mm),"within1Pct":round(pct(sum(r["qtyDeltaPct"] is not None and abs(r["qtyDeltaPct"])<=1 for r in mm),len(mm)),1) if mm else None,"within5Pct":round(pct(sum(r["qtyDeltaPct"] is not None and abs(r["qtyDeltaPct"])<=5 for r in mm),len(mm)),1) if mm else None,
    })

# stoppage pareto
reasons=[]
tot_stop=sum(stop_reason_total.values())
running=0
for label,secs in sorted(stop_reason_total.items(), key=lambda kv:kv[1], reverse=True):
    running+=secs
    reasons.append({"reason":label,"minutes":round(secs/60,1),"events":stop_reason_count[label],"cumulativePct":round(100*running/tot_stop,1) if tot_stop else 0})

# energy
energy_by_meter=defaultdict(list)
for r in iter_xlsx(SRC/FILES["energy"]):
    meter=r["Energy Meter Device Asset Tag"]
    d=excel_dt(r["Timestamp (Date)"]); t=excel_dt(r["Timestamp (Time)"])
    if not d or not t: continue
    dt=datetime(d.year,d.month,d.day)+timedelta(days=(t-datetime(1899,12,30)).total_seconds()/86400 % 1)
    energy_by_meter[meter].append((dt,fnum(r["Total Energy Passed (unit unspecified)"],None)))
energy_components=[]; all_ts=[]; energy_intervals=[]; energy_issues=0
for meter,arr in energy_by_meter.items():
    arr.sort(); all_ts += [x[0] for x in arr]
    intervals,issues=meter_intervals(arr)
    energy_issues+=issues
    energy_intervals.extend(dict(x,meter=meter) for x in intervals)
    delta=sum(x["delta"] for x in intervals)
    mm=meter_map.get(meter,{})
    energy_components.append({"meter":meter,"component":mm.get("component",meter),"line":mm.get("line","KM1"),"readings":len(arr),"first":iso(arr[0][0]),"last":iso(arr[-1][0]),"delta":round(delta,5)})
energy_components.sort(key=lambda x:x["delta"],reverse=True)
total_energy=sum(x["delta"] for x in energy_components)
for x in energy_components:x["sharePct"]=round(100*x["delta"]/total_energy,1) if total_energy else 0
allocated_energy,unallocated_energy=allocate_energy(energy_intervals,km1_periods)
energy_window_hours=(max(all_ts)-min(all_ts)).total_seconds()/3600 if all_ts else 0

# source inventory with dimensions and columns (skip parsing full large files)
source_inventory=[]
for key,fn in FILES.items():
    path=SRC/fn
    # get header via one-row manual parse
    first=next(iter_xlsx(path),{})
    # This loses headers when no data? all sources have data. derive header from keys.
    source_inventory.append({"id":key,"file":fn,"rows":sheet_dimension(path),"columns":list(first.keys()),"role":ROLES[key]})

# quality metrics / relationships
bridge_rows=list(iter_xlsx(SRC/FILES["person_bridge"]))
personnel_ids={txt(r["PersNr"]) for r in iter_xlsx(SRC/FILES["personnel"])}
bridge_ids={txt(r["PersNo"]) for r in bridge_rows}
resolved_bridge_ids=bridge_ids & personnel_ids
wr_2026={wr for o in orders.values() for wr in o["workRecords"]}
bridge_wr={txt(r["WorkRecordId"]) for r in bridge_rows}
shift_filled=sum(1 for r in iter_xlsx(SRC/FILES["periods_2026"]) if txt(r.get("Shift")))
period_rows=sheet_dimension(SRC/FILES["periods_2026"])
active_products={r["product"] for r in records if r["product"] and r["product"]!="Unknown"}
density_covered=sum(1 for p in active_products if products.get(p,{}).get("density") is not None)

summary={
    "mesOrders":len(records),"excelOrders":len(excel_orders),"matchedOrders":len(matched),
    "totalProduced":round(sum(r["produced"] for r in valid)),"usageHours":round(sum(r["usageHours"] for r in valid),1),"productionHours":round(sum(r["productionHours"] for r in valid),1),
    "medianGrossRate":round(median([r["grossRate"] for r in valid]),2),"medianAvailability":round(median([r["availability"] for r in valid]),1),"medianPerformance":round(median([r["performance"] for r in valid]),1),"medianOee":round(median([r["oee"] for r in valid]),1),
    "within1Pct":round(pct(sum(r["qtyDeltaPct"] is not None and abs(r["qtyDeltaPct"])<=1 for r in matched),len(matched)),1),"within5Pct":round(pct(sum(r["qtyDeltaPct"] is not None and abs(r["qtyDeltaPct"])<=5 for r in matched),len(matched)),1),
    "medianAbsQtyGap":round(median([abs(r["qtyDeltaPct"]) for r in matched if r["qtyDeltaPct"] is not None]),2),"medianStartGapMin":round(median([r["startGapMin"] for r in matched]),1),
    "corrDisturbanceRate":round(pearson([r["disturbanceIntensity"] for r in valid],[r["grossRate"] for r in valid]),3),"corrWorkersRate":round(pearson([r["avgWorkers"] for r in valid],[r["grossRate"] for r in valid]),3),
    "energyWindowHours":round(energy_window_hours,2),"energyMeters":len(energy_components),"energyDelta":round(total_energy,5),
}

quality={
    "shiftCompletenessPct":round(100*shift_filled/period_rows,1) if period_rows else None,
    "staffMasterResolvedIds":len(resolved_bridge_ids),"staffBridgeDistinctIds":len(bridge_ids),"staffIdResolutionPct":round(100*len(resolved_bridge_ids)/len(bridge_ids),1) if bridge_ids else None,
    "workRecordStaffCoveragePct":round(100*len(wr_2026 & bridge_wr)/len(wr_2026),1) if wr_2026 else None,
    "densityActiveProducts":density_covered,"activeProducts":len(active_products),"densityCoveragePct":round(100*density_covered/len(active_products),1) if active_products else None,
    "energyUnitConfirmed":False,"energyWindowHours":round(energy_window_hours,2),"energyMeters":len(energy_components),
}

payload={
    "meta":{"schemaVersion":2,"title":"BBMED Packaging Operations Intelligence","generatedAt":datetime.now().isoformat(timespec="seconds"),"scope":"2026 production operations + KM1 energy pilot","method":"Precomputed from supplied cleaned Excel workbooks. Dashboard runtime uses this compact JSON; original workbooks are retained in source-data/."},
    "periods":[dict(v,order=k[0],machine=k[1],product=k[2],shift=k[3],day=k[4]) for k,v in period_groups.items()],
    "stoppages":stop_details,
    "excelOnly":[{"order":k,"produced":v["qty"],"product":v["products"].most_common(1)[0][0],"start":iso(min(v["starts"])) if v["starts"] else None,"end":iso(max(v["ends"])) if v["ends"] else None} for k,v in excel_orders.items() if k not in orders],
    "summary":summary,"orders":records,"machineSummary":machine_summary,"sizeSummary":size_summary,"stoppageReasons":reasons,"energy":{"orderAllocation":[{"order":k,"delta":round(v,8)} for k,v in allocated_energy.items()],"unallocatedDelta":round(unallocated_energy,8),"intervals":energy_intervals,"invalidIntervals":energy_issues,"components":energy_components,"totalDelta":round(total_energy,5),"windowHours":round(energy_window_hours,3),"unit":"raw meter units (unit metadata not supplied)"},"quality":quality,"sources":source_inventory,
    "definitions":{
        "expectedRuntime":"Ordered quantity / order-master target rate; not a validated schedule. Runtime overrun = max(usage minutes − expected runtime, 0)","lostHours":"Sum of max(period usage hours − period production hours, 0); overlaps stoppage measures", "laborProductivity":"Produced units / sum(WorkerCount × usage hours); staffing coverage incomplete", "matchRate":"Matched orders / selected MES orders; Excel-only counts remain global", "energyAllocation":"Consecutive meter deltas distributed to unique order timestamp overlaps, assuming constant consumption inside each meter interval; gaps and ambiguous overlaps remain unallocated", "packagingCost":"Unavailable: requires packaging consumption and effective unit prices", "grossRate":"Produced units / usage minutes","availability":"Production seconds / usage seconds (proxy)","performance":"Produced units / sum(TargetUnitsPerMinute × production minutes)","quality":"Produced / (Produced + recorded rejects); sparse reject records mean this is a proxy","oee":"Availability × Performance × Quality (proxy)","disturbance":"Type-1 MES stoppages joined by WorkRecordID","reconciliation":"MES order totals vs manual Excel order totals","energy":"Sum of valid consecutive deltas per meter; negative resets and conflicting/invalid samples excluded and counted. Raw unit unspecified"
    }
}
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
print(json.dumps(summary,indent=2))
print(json.dumps(quality,indent=2))
print(f"wrote {OUT} ({OUT.stat().st_size/1024:.1f} KB)")
