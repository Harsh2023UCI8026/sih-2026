# SIH 26085 peer data-source review and Dwarka collection plan

Review date: 2026-10-15. This note summarizes source descriptions published in
the linked repositories. Repository descriptions are team-reported; they are
not independent proof that a feed is live, that access is authorized, or that a
model is accurate.

## What the reviewed teams say they used

| Project | Sources / collection approach described by its repository | What that means for our project |
| --- | --- | --- |
| [Andheri SIH](https://github.com/akansal307/SIH) | Says its road graph and static road features come from OpenStreetMap. Its README distinguishes those features from illustrative rain/tide inputs and says depth/onset are placeholder calculations, not outputs of its classifier. | Useful pattern: use OSM for real road geometry, keep flood-depth truth separate, and document every derived/assumed field. Do not borrow its placeholder depths as Delhi observations. |
| [Siddhesh SIH 26085](https://github.com/siddhesh-narwade/sih26085-urban-flood) | Its [data-source matrix](https://github.com/siddhesh-narwade/sih26085-urban-flood/blob/main/docs/DATA_SOURCES.md) classifies layers as public, API, derived, or simulated. It documents OSM/Geofabrik roads, Copernicus GLO-30/SRTM terrain, and MOSDAC rainfall access; its municipal storm-drain conduits are explicitly synthetic. Its [validation note](https://github.com/siddhesh-narwade/sih26085-urban-flood/blob/main/docs/VALIDATION.md) says local field-depth validation is unavailable. | Best transferable method: preserve a source/status label per layer and run physical sanity checks. Its synthetic conduits can support a labelled demo, but they are not a replacement for Delhi asset data. |
| [FlowState](https://github.com/Mobi45651/SiH-FlowState) | Its README describes Open-Meteo forecast input, synthetic flood training rows, and no real drain sensors. It explicitly says any training score is not real-world forecast skill. | Shows how a demo can operate without paid data, while keeping the synthetic training limitation visible. It does not solve the need for measured Dwarka flood depths. |
| [U-RNN research code](https://github.com/holmescao/U-RNN) | Provides research datasets and pretrained flood-nowcasting models built around particular study areas and benchmark cases. | A research baseline for later experimentation, not a Delhi incidents/depth/drainage dataset. Its reported benchmark numbers must not be presented as Dwarka accuracy. |
| [UFNS v4 SIH repository](https://github.com/Vinamra-Mishra/SIH26085-Urban-Flood-Nowcasting-System) | Its README describes DWR/NASA inputs and a coupled 1D/2D solver. The public description alone does not establish that the feed credentials, downloaded local event files, or measured street-depth truth are available to our team. | Treat it as an architecture reference. Ask for reproducible inputs and provenance before copying its data claims or performance figures. |

## What we already have in this repository

Do not spend time downloading these layers again:

- [`data/reference/roads/dwarka_roads.geojson`](../data/reference/roads/dwarka_roads.geojson): OSM road geometry for map context and route geometry. It is not a flood-depth layer or a verified drain network.
- [`data/reference/terrain/copernicus_glo30_dwarka_pilot.tif`](../data/reference/terrain/copernicus_glo30_dwarka_pilot.tif): Copernicus GLO-30 terrain reference. Its roughly 30 m surface resolution cannot show curbs, road crowns, or underpass-scale depressions reliably.
- [`data/reference/landcover/esa_worldcover2021_dwarka_pilot.tif`](../data/reference/landcover/esa_worldcover2021_dwarka_pilot.tif): clipped ESA WorldCover 2021, 10 m land-cover classes. Built-up class is not measured impervious percentage.
- [`data/reference/drainage/`](../data/reference/drainage/README.md): selected Najafgarh planning-table extracts from Delhi documents. They help identify drain names and basin context; they are not a connected, surveyed pipe GIS.
- [`data/reference/waterlogging/`](../data/reference/waterlogging/README.md): incident-occurrence records/candidates. They do not supply measured centimetre depths.
- [`src/data/vashu.csv`](../src/data/vashu.csv): older project-entered rows include numeric depth claims. Their sources and whether any number is actually a measured depth have not been independently verified; the new `depth_verification_status` field marks each claim `UNVERIFIED_PROJECT_ENTRY`. The claims are not training truth. Two older rows were found misaligned against the CSV header and have been corrected in this working copy.

## Use the peer teams' collection method, not their assumed values

1. **Keep the pilot boundary fixed and label its status.** Our current Dwarka
   polygon is an approximate study boundary; do not call it an official
   hydrologic catchment unless an authority verifies it.
2. **Use openly licensed map/land-cover data for context.** The OSM roads and
   ESA WorldCover clip already in this repository are appropriate for the
   interface and broad spatial covariates. Keep OSM attribution and each
   product's date/license in metadata.
3. **For rainfall, separate forecast from historical observation.** Open-Meteo
   is the current forecast input. For research calibration, use the pending
   IMD request for quality-controlled station/radar records if granted. Save
   source, station/radar, valid time, interval, units, quality flags, license,
   and retrieval date. Do not rename interpolated forecast values as radar or
   gauge measurements.
4. **For storm drains, request the existing municipal files.** Keep following
   [`STORM_DRAIN_DATA_ACQUISITION.md`](STORM_DRAIN_DATA_ACQUISITION.md) for
   I&FC/MCD/PWD ownership and GIS/CAD requests. Public basin maps and simulated
   CPHEEO-sized pipes can support a clearly labelled demonstration only; they
   cannot verify node connectivity or local capacity.
5. **For flood observations, treat reports as occurrence labels.** Preserve
   the date and cited location from the Traffic Police/FCO lists. Geocode vague
   place names as candidate coordinates and manually check them; retain the
   original wording and a coordinate-confidence field. Do not create a depth
   value from an incident report. Request measured depth/time records or
   collect gauge observations, including observed-dry controls.
6. **Use explicit provenance values for every record:**
   `OBSERVED`, `FORECAST`, `DERIVED`, `ESTIMATED`, or `SIMULATED`; include
   `source_id`, source URL/file, event ID, observation/forecast time, units,
   CRS, resolution, license/permission, and validation status. Keep raw files
   unchanged and save processed copies separately.
7. **Validate by complete storm event.** Keep all records from one storm in
   the same train/validation/test split. Report measured-depth error only after
   actual depth labels exist; incident-only data can evaluate occurrence or
   hotspot recall, not depth error.

## Recommended next data tasks for Dwarka/Najafgarh

1. Finish provenance/metadata checks for the existing road, terrain, and
   WorldCover files.
2. Continue the existing IMD and drainage-record requests; do not invent
   replacement values if an agency cannot provide the files.
3. Geocode the saved waterlogging occurrence rows into a separate review
   spreadsheet with `candidate_lat`, `candidate_lon`, `coordinate_method`,
   `coordinate_confidence`, and `manual_verified` fields.
4. Start a measured-observation CSV with event ID, UTC timestamp, lat/lon,
   depth in cm, wet/dry state, method, source, and validation status. Leave
   depth blank until it is measured or comes from an authoritative record.
5. Use synthetic rainfall/drainage cases only to demonstrate repeatable
   interface behavior. Keep them visibly labelled `SIMULATED`; do not mix them
   into model-accuracy claims.

## First practical collection step

Start with [`data/reference/waterlogging/measured_observations_template.csv`](../data/reference/waterlogging/measured_observations_template.csv).
Keep depth blank for Traffic Police/FCO locations unless the cited source
actually states a measured or explicitly quantified depth. For the first
usable local truth, ask I&FC/PWD/MCD for event-time water-level logs or
post-event gauge/survey records for Dwarka Mor, Kakrola, and nearby pilot
locations, plus dry readings from the same storms. The request checklist is in
[`DATA_ACQUISITION_REQUEST_DRAFT.md`](DATA_ACQUISITION_REQUEST_DRAFT.md); the
existing measured-depth file stays empty until observations with provenance
are received or collected.

Related project files: [`DATA_ACQUISITION_REQUEST_DRAFT.md`](DATA_ACQUISITION_REQUEST_DRAFT.md),
[`SIH26085_DATA_READINESS.md`](SIH26085_DATA_READINESS.md), and
[`DATA_PROVENANCE_AUDIT.md`](../DATA_PROVENANCE_AUDIT.md).
