# Najafgarh storm-drain planning references

These files are transcriptions of planning summary tables published by the
Government of NCT of Delhi:

- `delhi_drainage_map_najafgarh_block_summary.csv`: 13 Najafgarh-block drain
  rows from the legend table in the [Delhi Drainage Map](https://ifc.delhi.gov.in/sites/default/files/ifc/universal/delhi_map.pdf).
  The map itself says it is indicative and should not be used for any other
  purpose. This table's listed lengths, catchment areas, and design discharges
  are useful for identifying drains to ask about; they do not constitute
  machine-readable, georeferenced asset geometry or surveyed attributes.
- `fco2025_najafgarh_block_drain_summary.csv`: 11 named drains and the published
  length, catchment, and design-discharge summary in Annexure B of the [Flood
  Control Order 2025](https://ifc.delhi.gov.in/sites/default/files/ifc/circulars-orders/fco_2025.pdf),
  printed folio 30. The table's extracted headings are incomplete; the paired
  catchment and discharge columns are interpreted as square miles/hectares and
  cumec/cusecs from the matching unit conversions. Confirm those headings with
  I&FC before engineering use.

- `fco2025_najafgarh_block_drain_summary.csv`: 11 named drains and the published
  length, catchment, and design-discharge summary in Annexure B, printed folio
  30. The table's extracted headings are incomplete; the paired catchment and
  discharge columns are interpreted as square miles/hectares and cumec/cusecs
  from the matching unit conversions. Confirm those headings with I&FC before
  engineering use.
- `fco2025_najafgarh_regulator_levels.csv`: regulator/bund level and capacity
  entries for the Najafgarh Drain system, printed folios 37–38.
- `ifc_jurisdiction_reach_index.csv`: drain reach/chainage listings from the
  current I&FC [organizational setup page](https://ifc.delhi.gov.in/ifc/organizational-setup).
  These help route the request to I&FC but still contain no GIS geometry.

These are **planning schedule values, not the municipal asset GIS**. The map
depicts drain lines schematically, but neither table supplies machine-readable,
georeferenced centerlines, node coordinates, network connectivity, asset IDs,
manholes/inlets, rim/invert levels, material, or survey status. Blank
coordinates and `not_stated` survey/vertical-datum fields are intentionally
left blank; do not create map points from place names or feed these values into
the prototype graph as if they described its six nodes and five links.

The attached `drain_network.csv` matches the map's Najafgarh summary values.
Map and FCO schedules differ for some entries (for example, Najafgarh Drain
length 57.40 vs 57.11 km; Palam Link Drain 1.65 vs 1.47 km; Pankha Road Drain
5.30 vs 3.60 km; Najafgarh Pond Drain catchment/discharge 51.80 ha / 60 cusecs
vs 176 ha / 31 cusecs). Preserve these as separate source versions and ask
I&FC which current schedule/as-built record applies. Do not average or silently
overwrite the discrepancies.

The FCO table itself contains a catchment-area inconsistency for Najafgarh
Pond Drain: it lists 0.02 square miles and 176 hectares, which do not convert
to one another. Both values are preserved as published in the CSV and flagged;
confirm the correct value with I&FC before using it.

I&FC's [organizational setup page](https://ifc.delhi.gov.in/ifc/organizational-setup)
also lists division jurisdiction by drain and chainage, including Palam,
Nasirpur, Pankha Road, Bijwasan, and Najafgarh reaches. Use its current division
listing to route the request, then ask the division to confirm the GIS custodian
and current asset ownership.

The SIH prototype has not loaded these summaries into the live model. See
[`docs/STORM_DRAIN_DATA_ACQUISITION.md`](../../../docs/STORM_DRAIN_DATA_ACQUISITION.md)
for the exact request process for the missing digital network.
