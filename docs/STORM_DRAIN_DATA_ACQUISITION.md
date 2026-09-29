# SIH 26085: request the Dwarka/Najafgarh storm-drain GIS

## What the supplied files establish

The current graph in `src/data/dwarka_drainage_graph.json` has six schematic
nodes and five assumed links. It is not a verified municipal pipe network.
The supplied drain table and Delhi's public PDFs can identify named drains and
some basin-level design figures. The map shows drain lines schematically, but
the files do not provide a machine-readable, georeferenced network with
connectivity, manholes/inlets, asset IDs, or invert/rim elevations. The
Flood Control Order 2025 tables transcribed in
[`data/reference/drainage/`](../data/reference/drainage/README.md) are useful
for identifying the Najafgarh block, not for building the pilot graph.

The supplied waterlogging extract has 33 source serial rows. Split across its
listed dates, it yields 42 occurrence-date candidates; one non-event note row
was excluded. The saved reference copy has blank coordinates and depths. These
are dated reports of waterlogging, not measured depth observations.

## Public planning documents

Use the official [I&FC Our Services page](https://ifc.delhi.gov.in/doit-content/our-services)
to locate the current copies of:

- [Delhi Drainage Map (PDF)](https://ifc.delhi.gov.in/sites/default/files/ifc/universal/delhi_map.pdf)
- [Drainage Master Plan (PDF)](https://ifc.delhi.gov.in/sites/default/files/inline-files/main_report_dmp_version51.pdf)
- [Flood Control Order 2025 (PDF)](https://ifc.delhi.gov.in/sites/default/files/ifc/circulars-orders/fco_2025.pdf)
- [I&FC natural-drain lists under MPD 1976](https://ifc.delhi.gov.in/ifc/natural-drains-mpd-1976)

For this project, start with the Najafgarh block entries in the Delhi Drainage
Map legend and Flood Control Order 2025 Annexure B (printed folio 30),
regulator/level entries on printed folios 37–38, and the dated incident
schedules for 2022–2024 (printed folios 52–79).
The Drainage Master Plan cover identifies it as the July 2018 Final Report
(the supplied summary's “2021” date is incorrect). Its institutional-jurisdiction
section says Delhi drainage responsibilities are spread across multiple
departments and civic bodies, and its data discussion lists 4-foot-and-larger
storm drains with inlet/manhole locations, sizes, and invert levels among the
GIS inputs the study expected. Its Najafgarh Basin chapter gives basin context
and modeled scenarios, not a downloadable pilot-area pipe GIS. The MPD 1976
page offers lists of 201 natural drains and 44 “untraceable” drains; these are
name/status references, not current machine-readable municipal asset geometry.
The Delhi Drainage Map is a city-scale indicative map and summary, not a
georeferenced asset inventory.

### Extracting what the public PDFs contain

1. Open the [I&FC Our Services page](https://ifc.delhi.gov.in/doit-content/our-services)
   and use its **Download** links. Keep the original PDFs so page numbers and
   source versions remain checkable.
2. In the Delhi Drainage Map PDF, find the legend table headed “Najafgarh
   Block-South West Delhi”. The extracted 13-row planning summary is already
   in `data/reference/drainage/delhi_drainage_map_najafgarh_block_summary.csv`.
   The same PDF explicitly labels the drawing indicative; do not treat its
   drawn lines as surveyed GIS geometry.
3. In the Flood Control Order 2025 PDF, search for “Najafgarh Block-South West
   Delhi” and check printed folio 30 for drain summary values. Search for
   “MAXIMUM WATER LEVEL” / “Najafgarh Drain” and check printed folios 37–38 for
   regulator/bund levels. Those table transcriptions are in
   `data/reference/drainage/`. The FCO table's catchment units are inferred
   from paired values, and its Najafgarh Pond Drain catchment pair is internally
   inconsistent; both caveats are recorded in the CSV/README.
4. In the same order, the printed 2022 and 2023 waterlogging schedules are on
   folios 52–73. The supplied filtered extract is saved as one row per date in
   `data/reference/waterlogging/fco_2025_dwarka_najafgarh_2022_2023_attached_extract.csv`.
   It records occurrences only: no depth or coordinates appear in those rows.
5. In the Master Plan, search for “Institutional Jurisdictions” and “4 feet and
   above storm drains”. Those passages explain the multiple data owners and
   the types of digital records the study expected; they do not supply the
   missing live asset files.

The source PDFs can identify and cross-check names and planning values. To get
the actual pilot-area GIS/CAD network, continue with the agency request sequence
below.

## Exact request sequence

1. **Attach the project boundary.** Use
   `src/data/dwarka_catchment_bounds.geojson` as an approximate prototype
   rectangle only. Label it “requested study area, approximate”, and include a
   PDF map with nearby roads/landmarks. Do not call this boundary an official
   drainage catchment.
2. **Identify the asset owner from the drain names.** The [I&FC organizational
   setup page](https://ifc.delhi.gov.in/ifc/organizational-setup) lists current
   division jurisdiction and reach/chainage for named drains. Check the entries
   for Palam, Palam Link, Nasirpur, Pankha Road, Bijwasan, and Najafgarh and
   address the request to the listed division, asking it to confirm the data
   custodian. The page currently lists, for example, Najafgarh Drain chainages
   RD 17,905–30,180 m (Dhoolsiras Bridge–Kakraula regulator) and RD
   30,180–45,316 m (Kakraula–Basaidarapur Bridge), Palam Drain RD 0–8,750 m,
   Palam Link RD 0–1,465 m, Pankha Road RD 0–3,600 m, and Bijwasan RD 0–4,200
   m. The project saves these reach references in
   `data/reference/drainage/ifc_jurisdiction_reach_index.csv`. On the [MCD
   site](https://mcdonline.nic.in/), also open “Drain Wise
   Nodal Officers for the purpose of desilting to address the water logging
   issues” and ask the relevant Najafgarh-zone officer to confirm which local
   drains/road assets MCD owns. The zone label alone does not prove ownership
   of a particular trunk drain.
3. **Send the boundary and named-drain list to the likely owners as separate
   requests.** Start with I&FC for the named large drains and MCD/PWD for local
   road drains; include DDA where it owns a development-area asset. Ask each
   recipient to identify and route any record held by another agency. Request
   an owner/agency field in the reply. Do not assume all drains in the area
   belong to one department.
4. **Request the existing digital files and their metadata.** Ask for
   GeoPackage, Shapefile, File Geodatabase, DWG/DXF, or another documented
   machine-readable format. Request the original CRS/projection, units,
   coordinate datum, schema/data dictionary, source/update date, coverage,
   accuracy, and an explicit surveyed/as-built/design/estimated status for
   each attribute. Ask for a PDF index map only as a fallback, not as a
   replacement for vector data.
5. **Keep sewer data separate.** If an agency redirects you to Delhi Jal Board,
   ask whether the records are stormwater drains or sanitary/combined sewers.
   Do not add sewer lines to the storm-drain graph without an explicit asset
   classification and verified hydraulic connection.
6. **Use RTI only for records the authority already holds.** First try the
   relevant agency's ordinary data/contact channel. If there is no response,
   open the [Delhi RTI Online portal](https://rtionline.delhi.gov.in/), choose
   **Submit Request**, select the correct Government of NCT of Delhi
   department/public authority, and submit a narrow request for copies of
   existing records. The portal says it is for Delhi Government authorities;
   it warns that requests for Central Government or other State authorities
   will be returned without the fee being refunded. Use its **PIO/Appellate
   Authority Details** page to confirm the authority before paying. The portal
   FAQ says an application text is limited to 3,000 characters and longer
   requests can be attached as PDF. An RTI request can ask for an existing
   survey/GIS or a written response that no such record is held; it cannot
   require the authority to conduct a new survey or create missing measurements.
7. **Only after receipt, review the data before using it.** Preserve the
   original files, written permissions/terms, metadata, and a checksum. Check
   CRS and topology, compare node/link references, and keep missing or estimated
   values missing/labelled. Then replace schematic graph features only where
   the municipal data supports them. Do not use the public schedule values as
   substitutes for absent geometry or elevations.

## Request text to adapt

**Subject:** Request for existing storm-drain GIS/CAD records — SIH 26085
Dwarka/Najafgarh pilot

> We are developing a student prototype for Smart India Hackathon problem
> 26085, “Urban Flood Nowcasting System (Drainage and Rainfall Coupling)”.
> Attached is the approximate Dwarka pilot study boundary and a list of nearby
> named drains from the Delhi Flood Control Order 2025. Please confirm whether
> your department owns or maintains stormwater assets within this area. If
> another agency holds any of the requested records, please identify the
> responsible department/division and the appropriate data custodian.
>
> If held, please provide the latest existing machine-readable storm-drain
> inventory for the boundary, in GeoPackage, Shapefile, File Geodatabase,
> DWG/DXF, or another documented format. We request channel/pipe geometry and
> connectivity; asset IDs and dimensions/material; manhole/inlet locations;
> rim and invert levels; inlet/outfall connections; catchments; pumps, gates,
> and operating levels; and roughness/design capacity, condition, blockage,
> maintenance/desilting, and survey date/status where recorded. Please retain
> the source's surveyed/as-built/design/estimated labels and leave unknown
> attributes blank rather than estimating them.
>
> Please include the coordinate reference system, units, vertical datum,
> schema/data dictionary, coverage, source/update date, positional/elevation
> accuracy, and any usage, attribution, fee, or public-demo restrictions. We
> are requesting records already held; we are not requesting a new survey.
> If no such digital network or attribute is held, please say which records
> exist in another format and identify the responsible custodian.
>
> Intended use: student research and SIH prototype demonstration. Contact:
> [name, institution, email, phone]. Approximate study boundary and map:
> [attach].

The existing general request draft is
[`docs/DATA_ACQUISITION_REQUEST_DRAFT.md`](DATA_ACQUISITION_REQUEST_DRAFT.md).
The attachment-derived event candidates are kept separately at
[`data/reference/waterlogging/fco_2025_dwarka_najafgarh_2022_2023_attached_extract.csv`](../data/reference/waterlogging/fco_2025_dwarka_najafgarh_2022_2023_attached_extract.csv)
and are not wired into the model.
