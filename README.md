# BBMED Final Dynamic Insight Dashboard

The main page at `/` is the supplied **BBMED_Final_Dynamic_Insight_Dashboard** design, integrated into this static project. The previous dashboard UI has been replaced.

## Active application

- `index.html` — the new three-page dashboard: Operations & Data Reliability, Energy & Processing Cost, and Calculation / Validation / Model.
- `app.js` — the new dashboard's filters, SVG charts, scenario inputs, order traces and asynchronous data loading.
- `styles.css` — the supplied design with accessibility and mobile containment fixes.
- `data/dashboard.json` — schema 3: `operations`, `energy`, and import provenance metadata.
- `public/semantic-model.png`, `public/data-workflow.png` — the supplied relationship/workflow diagrams, extracted from embedded images.
- `reference/BBMED_Final_Dynamic_Insight_Dashboard.html` — unchanged supplied original, retained as the auditable data snapshot.

There are no npm dependencies, external chart services or runtime database connections. The browser loads the local JSON dataset and PNG assets.

## Preview

```bash
python -m http.server 8080 --bind 127.0.0.1
```

Open `http://127.0.0.1:8080/`. Use an HTTP server, since the application fetches JSON; opening `index.html` directly as a local file will show a loading error.

## Data build

```bash
python scripts/build_dashboard_data.py
```

The default build imports the embedded `D` and `EN` data from the preserved final dashboard snapshot. It validates normalized order uniqueness, reconciliation and meter relationships, and energy totals, then writes the current JSON schema. This preserves the supplied expanded energy dataset (1,417,704 source rows; 8,426.286 kWh; 80 allocated KM1 orders).

**This command imports the supplied dashboard calculations; it does not independently reprocess the 1.42M raw meter readings.** The updated workbook is retained at `source-data/21.update_energy_data.xlsx`. Editing a workbook alone does not refresh this snapshot. To import a newer compatible dashboard export, run:

```bash
python scripts/build_dashboard_data.py --source /path/to/new-dashboard-export.html
```

The supplied export remains the authority for the calculations, canonical meter aliases, timestamp allocations and kWh confirmation. `meta.sourceSha256` identifies the exact imported HTML file. Raw workbooks and source hashes remain available for audit.

## Relationships and filter scope

- Normalized order keys link the 565-order MES/Excel union, 263 comparisons, manual loss records and MES reason records.
- 80 KM1 energy orders link to the order union; their `meter_kwh` keys link to the five canonical energy meters.
- `daily_meter` supports calendar-date/meter consumption charts; `daily` supports whole-line allocation/disturbance/idle percentages.
- Operations date filters select complete orders by `order_date`; machine/product/shift are order-level attributes.
- Energy product and size filters select allocated orders. Their date filter selects complete orders by order date; it does not clip their energy or output to midnight boundaries.
- Energy daily charts use calendar dates and meter selection, retaining all products. State percentages always use **all five meters** and the selected calendar dates because meter-level state breakdowns are not supplied.
- Processing costs use manual minutes for selected whole orders. Meter selection does not change those minutes. Electricity tariff and line-hour cost are user-entered scenarios, not booked financial costs.

The UI makes these differing scopes explicit. Pareto totals and cumulative shares use all selected reasons, even when only the top eight are drawn. Missing percentages/correlations are not converted into zero observations.

## Legacy analysis

The earlier workbook ETL is retained as `scripts/build_legacy_dashboard_data.py`; it writes **only** `reference/legacy-dashboard.json`. It cannot overwrite the live dashboard schema. Its helper functions and regression tests remain available for auditing the previous short energy pilot. The old `analytics.js` has been removed, and neither the old UI nor the pilot dataset is loaded by the current page.

## Checks

```bash
python -m unittest discover -s tests -v
node --check app.js
```

Tests cover snapshot reproducibility, active asset references, order/meter relationships and energy totals, plus the legacy meter-delta/allocation checks. Browser checks cover tabs, filters, resets, tariff changes, order traces, diagrams and mobile layout.

## Vercel

Deploy as a static project (Framework: Other; project root output; no build command required since the generated JSON is committed). `index.html` is the entry point. `vercel.json` retains security headers, requires data revalidation, and redirects both forms of the old long dashboard URL to `/`. `.vercelignore` excludes source workbooks, reference snapshots, scripts and tests from deployment. No deployment is performed by the integration or data-build scripts.
