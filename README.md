# BBMED Packaging Operations Intelligence

Dependency-free analysis dashboard for the BBMED Production Data Challenge. It combines the supplied 2026 MES production periods, stoppages, staffing links, manual Excel production, ERP product data, rejects, and the KM1 energy pilot into a responsive browser dashboard.

## What is included

- **Management Overview** — output, target achievement, availability, non-production time, labor productivity, reconciliation and the top five capacity-review orders.
- **MES vs Excel** — all matched and MES-only orders, global Excel-only records, quantities, timestamps, elapsed durations and exception status (±5% quantity / 60-minute time thresholds).
- **Production Delays** — target-rate runtime versus usage time, overrun proxies and monthly, daily and recorded-shift non-production trends.
- **Stoppage Causes** — filtered reason Pareto and disturbance counts; technical/organizational period totals; separate operator-reported setup, cleaning and changeover totals.
- **Staffing** — weighted actual headcount, units per labor hour, recorded-shift productivity and order investigation signals.
- **Production Efficiency** — ordered/produced quantities, recorded rejects, cycles, targets and small/medium/large batch comparisons.
- **Packaging Cost** — available pack-size attributes and explicit missing-cost inputs. No invented packaging costs or cost rankings.
- **Energy Monitoring** — consecutive meter deltas, sampling-rate-adjusted trends, component contribution, candidate peaks and estimated time-overlap order allocation.
- **Data Quality / Sources & Model** — coverage controls, source inventory, relationships and KPI definitions.

## Architecture

This repository deliberately uses **static HTML + CSS + JavaScript** for the deployed dashboard. There is no runtime database and no npm dependency. The browser reads `data/dashboard.json` (~1.5 MB), which contains order-level and aggregate data built from the Excel source files.

The original cleaned workbooks remain in `source-data/` for auditability and reproducibility. They are excluded from Vercel deployment with `.vercelignore`, so the deployed website stays small.

`reference/` contains the supplied dashboard prototypes, KPI Python script and research report for traceability. It is also excluded from Vercel.

## Data build / reproducibility

To rebuild the compact dashboard dataset after replacing or updating the workbooks:

```bash
python scripts/build_dashboard_data.py
```

The ETL uses Python's standard library only. It aggregates 2026 production periods to order grain, joins stoppages and rejects by `WorkRecordID`, reconciles manual Excel production after order-level aggregation, enriches product attributes from ERP, and calculates the KM1 meter deltas from cumulative readings.

Important definitions:

- Gross rate = Produced units / Usage minutes.
- Availability proxy = Production time / Usage time.
- Performance = Produced units / theoretical output from target rate × production time.
- Quality proxy = Produced / (Produced + recorded rejects). Reject coverage is sparse, so this is explicitly provisional.
- OEE proxy = Availability × Performance × Quality.
- Disturbance minutes = MES type-1 stoppage time joined by WorkRecordID.
- MES↔Excel quantity variance = (MES quantity − Excel quantity) / Excel quantity.
- Energy = sum of valid consecutive reading differences per meter. Negative differences are treated as resets; invalid readings and conflicting duplicate timestamps break the chain and are counted. Identical duplicate readings are deduplicated. The source does **not** document the physical unit, so the deployed UI calls these "meter units", not kWh.

## Local preview

Because the dashboard loads JSON with `fetch()`, serve it through a local HTTP server rather than opening `index.html` directly:

```bash
python -m http.server 8080
```

Then open `http://localhost:8080`.

## Deploy to Vercel

1. Create a GitHub repository and push this folder.
2. In Vercel choose **Add New → Project** and import the GitHub repository.
3. Framework preset: **Other** (static site).
4. Build command: leave empty.
5. Output directory: leave empty / repository root.
6. Deploy.

`vercel.json` adds basic security headers and caching for the compact JSON dataset.

## Repository structure

```text
index.html                 Static application shell
styles.css                 Responsive desktop/mobile design
app.js                     Navigation, filters and shared rendering
analytics.js               Eight management workstream views
data/dashboard.json        Precomputed real dashboard dataset
scripts/build_dashboard_data.py
source-data/*.xlsx         Original 20 cleaned source workbooks
reference/                 Supplied prototypes/report/script
vercel.json
.vercelignore
README.md
```

## Validation snapshot

The generated data currently resolves to:

- 430 MES 2026 orders
- 398 manual Excel orders
- 263 matched MES↔Excel orders
- 11,632,839 produced units
- 16,280.2 usage hours
- median gross rate 14.19 units/min
- median availability proxy 42.4%
- median performance 90.7%
- median OEE proxy 38.6%
- 59.7% of matched orders within ±1% quantity
- 87.1% within ±5%
- energy window 3.49 hours across five KM1 meters
- total cumulative meter delta 11.22696 raw meter units

These values are produced by `scripts/build_dashboard_data.py` from the committed Excel files; they are not hard-coded dashboard samples.

## Known limitations

The repository preserves the limitations found in the supplied research: incomplete shift data, unresolved personnel IDs, sparse product density, sparse reject capture, mixed stoppage taxonomy, and an energy pilot whose physical unit is not documented. The dashboard avoids converting these limitations into unsupported precision or savings claims.

## Interpretation and filter scope

Filters select full orders by their primary machine/product and dominant recorded shift. Period charts additionally restrict the selected periods to the chosen machine/product/shift. They do not reconstruct full-order totals for a single shift. Excel-only records, Energy Monitoring, Data Quality and Sources use explicit global scopes.

Expected runtime is `TargetQuantity / TargetProductionRatePerMinute`, available for 275 of the supplied 430 MES orders. It is a **target-rate proxy**, not a validated production plan or due-date adherence metric. Non-production hours use positive period-level usage minus production differences. These hours overlap stoppage losses and must not be added to them. Stoppage events use the source `stoppage_count`; reason records may overlap in time.

Manual Excel end times earlier than the same row's start time roll into the next day. Reconciliation duration is first start to last end, including gaps; it is not summed labor or running time. Order normalization trims whitespace, normalizes case and canonicalizes integral numeric keys.

Energy allocation divides each valid meter interval among uniquely overlapping KM1 orders, assuming constant consumption within that interval. Gaps or competing orders remain unallocated. Full production-period output cannot be divided into the shorter pilot window without another assumption, so energy per unit and output/energy scatter remain unavailable. kWh and energy cost require verified meter units and a tariff; idle energy requires validated machine-state intervals. The pilot is not a product-efficiency ranking.

Packaging costs, planned staffing, complete good/scrap quantities and schedule adherence remain unavailable where inputs are absent. Manual setup/cleaning/changeover totals are separate from MES losses, with blanks treated as no recorded time. No causal staffing or financial savings claim is made.

## Checks

```bash
python -m unittest discover -s tests -v
node --check app.js
node --check analytics.js
```

The tests cover meter resets, invalid and duplicate samples, normalized order IDs, ambiguous/gapped allocation, allocation conservation and the supplied reconciliation totals. Browser verification covers all tabs, machine filtering, reset, empty states and desktop/mobile overflow.
