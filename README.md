# BBMED Packaging Operations Intelligence

Production-ready, dependency-free dashboard for the BBMED Production Data Challenge. It combines the supplied 2026 MES production periods, stoppages, staffing links, manual Excel production, ERP product data, rejects, and the KM1 energy pilot into a responsive browser dashboard.

## What is included

- **Executive Overview** — produced units, gross rate, availability/performance/OEE proxies, MES↔Excel consistency, order-size pattern and stoppage signal.
- **Operations** — staffing, disturbance intensity, OEE proxy, top disturbance orders and reconciliation detail.
- **Energy Pilot** — exact cumulative meter deltas from the supplied five KM1 meters, with explicit limitations because the energy unit is not documented and the observation window is only ~3.49 hours.
- **Data Quality** — shift, personnel, density, energy-metadata and reconciliation controls.
- **Sources & Model** — all 20 source tables, row counts, main columns, role, relationships and KPI definitions.

## Architecture

This repository deliberately uses **static HTML + CSS + JavaScript** for the deployed dashboard. There is no runtime database and no npm dependency. The browser reads `data/dashboard.json` (~300 KB), which contains order-level and aggregate data built from the Excel source files.

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
- Energy = last cumulative meter reading − first cumulative meter reading in the supplied window. The source does **not** document the physical unit, so the deployed UI calls these "meter units", not kWh.

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
app.js                     Filters, KPIs, SVG charts and tables
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
