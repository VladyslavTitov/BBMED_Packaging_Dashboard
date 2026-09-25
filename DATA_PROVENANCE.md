# Active dashboard data provenance

The active UI comes from the user-supplied `BBMED_Final_Dynamic_Insight_Dashboard.html`. Its unchanged original is retained in `reference/BBMED_Final_Dynamic_Insight_Dashboard.html`.

`scripts/build_dashboard_data.py` imports its embedded operations (`D`) and expanded energy (`EN`) datasets into `data/dashboard.json`, schema 3. Metadata records the original filename and SHA-256. Import validates the relationships and totals; it does not reproduce the raw-workbook transformations independently.

## Operations model

The supplied data contains 430 MES orders, 398 operator Excel orders, 263 matches and a union of 565 orders. Normalized `order` keys link:

- `operations.union` → nested MES and Excel order facts;
- `operations.comparisons` → matched quantity/time differences;
- `operations.mes_reason_events` → type-1 reason minutes;
- `operations.manual_events` → cleaning, changeover, packaging handling and disturbance minutes;
- `energy.orders` → allocated KM1 energy and per-meter contributions.

The underlying workbook relationships remain OrderNo / OrderNumber / Auftragskarte Nr. for orders, WorkRecordID for stoppage/personnel/reject links, and ProductID / ArticleNo / ItemCode for products. Supplied diagrams are available in the Calculation / Validation / Model page.

## Expanded energy model

The new snapshot declares 1,417,704 rows from the updated energy source, five canonical meters, confirmed kWh and a January–September 2026 timeline. `source-data/21.update_energy_data.xlsx` is retained in the repository. The original short pilot workbook remains separate and is not used by the active UI.

The supplied snapshot describes energy as consecutive cumulative-reading differences per canonical meter, with negative differences excluded. It describes order allocation through timestamp overlap and disturbance allocation through clipped type-1 stoppage intervals. These methods and the unit confirmation are imported claims from the supplied dashboard. The integration validates aggregate consistency and referential integrity; it does not independently validate every raw interval.

Daily whole-line energy, daily per-meter energy and whole-order energy are distinct grains. Whole-line state percentages cannot be divided by single-meter consumption. Order-date selections retain the complete order allocation and output, whereas daily trends select calendar-day totals. The UI labels these differences.

Electricity tariff and line cost are scenario inputs. Packaging handling exposure is not packaging material cost. The supplied workbooks lack material price/BOM inputs for actual packaging costs.

## Legacy build

`scripts/build_legacy_dashboard_data.py` and `reference/legacy-dashboard.json` preserve the earlier workbook model and unconfirmed-unit pilot for audit only. They are not connected to the active application. Original workbook hashes remain in `source-data/SHA256SUMS.txt`.
