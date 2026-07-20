# Mission: us-water-usage

## Question

How much water does the United States use, how has that changed over prior
years, and where is it heading? The deliverable feeds a general-audience
research report, so the core need is a trustworthy, source-linked
**historical statistical record** (national totals and sector breakdowns,
as far back as systematic data exists) plus a **trend analysis** that
explains the shape of that record and what drives it.

"Use" means both withdrawals and consumptive use — the report must be
explicit about which is which, every time a number appears.

## What a great answer looks like

1. **The national time series.** Total US water withdrawals for every
   reporting year from 1950 to the most recent available (USGS published
   5-year estimates 1950–2015, then shifted toward annual/model-based
   releases — establish what exists post-2015 and use it). For each year:
   total withdrawals in Bgal/d (and thousand acre-ft/yr where published),
   split by freshwater vs saline and surface water vs groundwater.
2. **Sector breakdown per reporting year.** Public supply, domestic
   (self-supplied), irrigation, livestock, aquaculture, industrial, mining,
   thermoelectric power. Note category definitions and where the USGS
   changed methodology between reports (these breaks matter for trend
   claims — e.g. per-capita public-supply recalculations, thermoelectric
   fresh vs saline treatment).
3. **Per-capita trend.** Total and public-supply per-capita use over time;
   the decoupling of use from population growth.
4. **Trend narrative with drivers.** Withdrawals peaked around 1980 and
   have declined since — quantify that and attribute it: thermoelectric
   cooling shifts (once-through → recirculating, fuel mix), irrigation
   efficiency and acreage changes, industrial decline, appliance/plumbing
   efficiency, pricing and conservation programs. Every attribution needs
   a source, not lore.
5. **Regional breakdown — quantitative, not just texture.** The national
   trend hides divergent regional stories (e.g. the West's outsized
   withdrawals and its response to scarcity). Required:
   - A West-vs-Rest cut of the time series where data supports it (state
     totals from the USGS circulars/data releases; define the regional
     grouping explicitly — e.g. the 17 Western states convention or USGS
     water-resources regions — and state it in the report).
   - Sector-by-region contrast: irrigation's share of withdrawals in the
     West vs thermoelectric/public supply in the East; per-capita use by
     region.
   - Where the post-1980 national decline actually happened regionally,
     and where it didn't.
   - Top-withdrawal states and why; groundwater stress (High
     Plains/Ogallala, Central Valley, Colorado River basin).
   State-level data exists in every 5-year circular; county-level for
   recent years. A 50-state table is NOT required — aggregate to regions,
   plus spotlight states that explain the regional numbers.
6. **Consumptive use and forward look.** What is known about consumptive
   use (vs withdrawals), water availability assessments, and any credible
   projections of future US demand.

## Deliverable

`.research/us-water-usage/REPORT.md` —
a single markdown report with:

- a summary up top (10 lines max);
- the time-series tables (year × total, year × sector) with units on every
  column;
- the regional breakdown (West vs Rest time series where supportable,
  sector-by-region, per-capita by region);
- the trend narrative;
- a sources section listing every URL cited.

Every figure carries its source URL inline. Flag `[SINGLE-SOURCE]` where a
number rests on one source, `[INFERRED]` where you computed or interpolated
(and show the computation), and `[METHOD-BREAK]` where cross-year
comparability is compromised by methodology changes.

## Quality bars / stop conditions

- Exact figures with units, as published (Bgal/d, Mgal/d, thousand
  acre-ft/yr). Do not round silently; do not mix units in one column.
- Every claim carries a source URL. Prefer primary sources (USGS
  circulars/data releases) over secondary write-ups; use secondary sources
  for driver attribution where the primary record is silent.
- Where two credible sources disagree, report both and flag the conflict —
  never average or silently pick one.
- Coverage bar: the 1950–2015 five-year series must be complete (no
  skipped report years), and the post-2015 situation must be explicitly
  established (what annual data exists, from where).
- Stop when 2 consecutive search angles surface no new sources or entities.

## Notes discipline

Receipts only: `research summarize ... -o .research/us-water-usage/notes/`
(stdout carries path + RELEVANT LEADS only). Batch 3–8 URLs per summarize
call. When many note files accumulate on one subtopic, merge them with
`research ask --stdin` into a distillate instead of reading them all.
Searches and pages are cached on disk — never re-run a paid call with
`--fresh` unless a cached result is genuinely stale.

## Starting leads (verify, don't trust blindly)

- USGS "Water Use in the United States" landing page:
  https://www.usgs.gov/mission-areas/water-resources/science/water-use-united-states
  (already distilled — see notes/ for its leads list)
- USGS Circular 1441 (Dieter et al., 2015 estimates), Circular 1405
  (2010), 1268 (2005), and earlier circulars back to 1950 — pubs.usgs.gov
- USGS county-level and principal-aquifer data releases (2015),
  waterdata.usgs.gov / NWIS water use, ScienceBase data releases
- USGS National Water Availability Assessment / Water Availability and Use
  Science Program (post-2015 direction, consumptive use)
- EIA (thermoelectric water/cooling data), USDA Census of Agriculture
  (irrigation), EPA (public supply / drinking water)
- USGS Water Science School "Total Water Use" and "Trends in Water Use"
  topic pages for orientation (secondary; trace to primary)
