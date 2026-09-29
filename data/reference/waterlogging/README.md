# Flood incident candidates (reference only)

This small CSV is a curated, source-linked copy of dated waterlogging entries from the user-provided candidate workbook, checked in part against the official Delhi Flood Control Order 2025. It is retained as an **incident-occurrence reference**, not as measured flood-depth ground truth.

- Primary source: [Delhi Flood Control Order 2025](https://ifc.delhi.gov.in/sites/default/files/ifc/circulars-orders/fco_2025.pdf).
- One row represents one source-listed date/location occurrence. `source_section_year` preserves the table heading; `event_date` preserves the date printed in that row. Some dates do not match the section heading year; these mismatches are intentionally retained and noted.
- Two workbook rows marked `NOT FOUND` were corrected using official section 2022 rows 119 and 120. The missing dates for 2023 row 223 were filled from the official PDF (4 and 9 July 2023).
- Workbook annotations and the non-event note row were not copied as incident records. The omitted FCO 2024 serial 161 was added as one explicitly multi-location candidate; it must be split/geocoded only after reviewing the original table.
- All coordinates and `depth_cm` are blank. Every row remains `not_checked` for the pilot boundary and must be geocoded and checked against the pilot polygon before map use.
- The current project boundary is `src/data/dwarka_catchment_bounds.geojson`: a manually defined rectangle spanning 77.015–77.050 E and 28.590–28.628 N (EPSG:4326). The source layer explicitly describes it as an approximate prototype boundary, not official coverage. Do not describe it as a surveyed hydrologic catchment. The incident workbook covers a wider area, and no row has been marked in/out based only on a locality name.
- The boundary metadata gives Dwarka Mor Metro Crossing (28.6186 N, 77.0319 E) as a pilot anchor. This is a manually set map anchor, not a verified coordinate for any incident or water-depth measurement.
- Do **not** use this file to train or validate depth prediction, infer dry conditions, or treat `frequency_count_from_candidate_workbook` as independent observations. The count is repeated per date and must not be summed across rows.
- This file is not wired into the application or model runtime.

An additional 2021 source extract is in [`delhi_traffic_police_2021_dwarka_najafgarh_candidates.csv`](delhi_traffic_police_2021_dwarka_najafgarh_candidates.csv). It contains 26 dated occurrences from 16 Dwarka/Najafgarh-area rows in the Delhi Traffic Police 2021 table. The official [waterlogging page](https://traffic.delhipolice.gov.in/water-logging-area) and [waterlogging circle map](https://traffic.delhipolice.gov.in/en/maps) provide historical occurrence/location context; the map is not a depth dataset. These 2021 entries are also un-geocoded and may include locations outside the current pilot rectangle. Check for duplicate date/location reports across sources before counting events.

## What is still needed before this can become ground truth

1. Resolve each occurrence to a point or defensible road segment from its source or an authoritative map, and record the geocoding source and confidence.
2. Check the resolved geometry against the pilot boundary. Keep outside and ambiguous locations out of the pilot evaluation set.
3. Obtain measured water depths (with timestamp, units, and method) and observed-dry controls. A reported waterlogging occurrence is not a depth label, and no report is not a dry observation.
4. Keep all observations from the same storm event in one evaluation split to avoid event leakage.

[`fco_2025_dwarka_najafgarh_2022_2023_attached_extract.csv`](fco_2025_dwarka_najafgarh_2022_2023_attached_extract.csv) preserves the user's filtered attachment as one row per listed date: 42 occurrence-date candidates from 33 source serial rows. The attachment's non-event note row was excluded. This separate filtered transcription overlaps the broader curated FCO candidate file above and must not be counted as an independent event source. It has no coordinates or depths and is not wired into the application or model runtime.

The FCO 2025 index says the 2024 section contains 194 locations, while the heading on the actual 2024 table says 165. The supplied summary uses 165; treat the count as an internal source inconsistency and verify the current official table before relying on it. The 2022/2023 filtered extract above does not resolve this 2024 discrepancy.
