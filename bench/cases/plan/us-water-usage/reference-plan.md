# Plan: us-water-usage

## Mission
Build a source-linked historical statistical record of US water use
(withdrawals + consumptive use) 1950→most-recent, with sector breakdowns,
per-capita trend, driver attribution, regional texture, and forward look.

## Six answer areas (from brief) → source targets

1. **National time series 1950→present** (total, fresh/saline, SW/GW)
   - USGS Circular 1441 (2015) — has the canonical 1950–2015 trend table
   - USGS "Trends in Water Use" topic page (table)
   - National Water Availability Assessment 2025 (post-2015 / 2020 / 2025 nos)
   - Earlier circulars: 1405 (2010), 1268 (2005), 1344 (1950–2005 trends)
2. **Sector breakdown per year** (8 categories) + method breaks
   - Circular 1441 (2015 full sector table), 1405 (2010), 1268 (2005)
   - Document method changes (thermoelectric fresh/saline, public-supply per-capita recalc)
3. **Per-capita trend**
   - Circular 1441 per-capita figure; "Trends in Water Use" page
   - Public-supply per-capita reanalysis data release (2000–2020)
4. **Trend narrative + drivers** (peak ~1980, decline)
   - Primary: Circular 1441, 1405 narrative
   - Secondary: USGS Water Science School, academic/EIA/EPRI on thermoelectric cooling shift
   - Irrigation efficiency: USDA Census of Ag + USGS
5. **Regional/state texture**
   - Circular 1441 top states; Ogallala/High Plains; Central Valley; Colorado River
   - USGS groundwater depletion studies (Konikow)
6. **Consumptive use + forward look**
   - NWAA 2025; USGS consumptive use methodology; NWAA projections

## Execution order
- S1: searches for primary circulars + trends table + post-2015 situation (parallel)
- D1: dispatch summarize on 2015 Circular, 2010 Circular, 2005 Circular, trends page
- S2: searches for per-capita, drivers, thermoelectric, irrigation, regions
- D2: dispatch summarize on driver/region/consumptive sources
- S3: gap-fill (1980 peak detail, per-capita series, post-2015 specifics)
- Merge notes per subtopic via `research ask --stdin`
- Write REPORT.md

## Stop condition
2 consecutive search angles yield no new sources/entities.
