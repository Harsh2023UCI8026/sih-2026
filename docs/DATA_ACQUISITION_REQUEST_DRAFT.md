# SIH 26085 data acquisition request draft

This formal request draft is still pending submission. The team has already
sent an initial hourly-rainfall availability inquiry to RMC New Delhi and
received a reply asking for a choice of Safdarjung or Palam, the prescribed
Data Request Form, and a valid college ID. The dataset has not been supplied.
Review this draft through the relevant agency's official process. Replace
bracketed fields and confirm the pilot boundary before submitting. Ask each data owner about
availability, access conditions, cost, permitted research/demo use, and whether
the data may be used by a publicly deployed SIH prototype.

## 1. India Meteorological Department: radar rainfall and gauge data

**Subject:** Request for digital Doppler radar rainfall data and gauge observations for a Dwarka urban-flood nowcasting prototype

> We are developing a student prototype for Smart India Hackathon problem
> statement 26085, “Urban Flood Nowcasting System (Drainage and Rainfall
> Coupling).” We request information on the availability and access process for
> digital Doppler Weather Radar rainfall products covering Dwarka/Najafgarh,
> Delhi, for research, model development, and a publicly accessible competition
> demonstration.
>
> If available, we request machine-readable Surface Rainfall Intensity (SRI)
> or quantitative precipitation grids, with the native update interval and
> spatial resolution, for historical heavy-rain event windows between
> [start date] and [end date], and details of any live or near-real-time radar
> feed or official radar-nowcast product. The pilot boundary/coordinates will
> be attached. A rendered radar image alone is not sufficient for the
> catchment-routing calculations.
>
> For each product, please advise the available format (for example NetCDF,
> HDF5, or BUFR), grid projection/CRS, units and accumulation interval,
> issue/valid timestamps and time zone, quality-control flags, missing-data
> codes, radar/site identifier, processing/calibration documentation, archive
> coverage, delivery latency, API or download mechanism, license/attribution
> requirements, and any fees or restrictions on public demonstration.
>
> We also request the access process and availability for quality-controlled
> hourly rainfall observations from the nearest AWS/ARG or rain-gauge stations
> (including Palam/Najafgarh or other stations you consider relevant) for the
> same event windows. These observations would be used for rainfall quality
> checks and bias correction, not represented as street-level rain readings.
>
> Team/contact: [name, institution/school, email, phone]
> Project/pilot boundary: [attach map or verified coordinates]
> Intended use: student research, model evaluation, and SIH prototype demo
> Requested event windows: [attach list after confirming event dates]

Use the [IMD Radar Data Supply Portal guide](https://radarapi.imd.gov.in/Received_data/dsp_userguide.pdf):
register through the IMD Data Service Portal, then sign in to the Radar Data
Supply Portal and submit through its **Data Request** option. The portal's
`/dsp/frontend/contact` page is not the request form. See
[`IMD_RAINFALL_DATA_FETCH_GUIDE.md`](IMD_RAINFALL_DATA_FETCH_GUIDE.md) for the
separate radar, gauge, API, and fallback procedures. Actual Dwarka archive
coverage, formats, and access conditions still need confirmation from IMD.

## 2. Delhi drainage, terrain, and flood-observation data owners

Submit a separate request to the relevant owners (for example, Irrigation &
Flood Control Department, PWD, DJB, MCD, and/or Delhi Traffic Police) and ask
them to identify which agency holds each dataset. Request:

- Latest surveyed storm-drain GIS/CAD inventory for the confirmed pilot area:
  node and pipe/channel geometries, connectivity, asset IDs, dimensions, invert
  and rim elevations, material/roughness, inlet/outfall details, design
  capacity, and documented unknown/estimated attributes.
- Catchments and operating context: contributing area, inlet/catchment links,
  outfall water levels, pumps/gates, maintenance/desilting dates, known
  blockages, and asset condition where recorded.
- Terrain suitable for surface-flow routing: recent DEM/DTM or LiDAR-derived
  elevation data, horizontal/vertical CRS and datum, resolution, vertical
  accuracy, acquisition date, nodata/quality flags, and any available road
  crown, underpass, barrier, or building-breakline layers.
- Event-linked flood observations: exact location, date and time, measured
  water depth (with units), measurement method, observation duration, source
  ID, uncertainty, and whether a location was observed dry. Request water-level
  sensor records or surveyed post-event marks where available; a reported
  waterlogging incident without a measured depth should remain an occurrence
  label only.
- Usage terms: permission to use these records in a student research prototype
  and publicly deployed competition demo, attribution, redaction/privacy
  conditions, fees, and the required citation format.

Ask for digital files with their original metadata (GeoPackage, Shapefile,
CSV, GeoTIFF, or another documented format). Do not request or publish private
resident details; location and water-depth evidence is sufficient.

## Submission checklist

- [ ] Confirm the pilot boundary and intended public-demo use.
- [ ] Attach a short event-date list and map; ask for the closest radar site and
      gauge stations rather than assuming coverage.
- [ ] Keep the agency response, access/license terms, source metadata, and
      original files together.
- [ ] Do not label incident-only records as measured depth or dry outcomes.
- [ ] Run `python -B src/sih_data_bundle.py` after arranging authorized files
      in the documented bundle layout.
