# Rainfall data fetch guide for SIH 26085

## Status from the team's RMC New Delhi reply

The team sent an initial hourly-rainfall availability inquiry for Dwarka/Najafgarh. RMC replied that its meteorological data request must specify either **Safdarjung or Palam**, use the prescribed Data Request Form, and include a valid college ID. The reply is a request-process response, not rainfall data or approval; the formal request and dataset are pending. Narrow the form to one of those stations before submitting.

This guide separates the rainfall sources by what they actually provide. The
priority input for street-level rainfall forcing is an authorized,
machine-readable Delhi Doppler radar grid. The IMD public radar page is only a
visual product page. Gauge observations, public APIs, NASA IMERG, and IMD's
daily 0.25-degree grid are supporting sources with different spatial and
temporal coverage.

## 1. Confirm the radar display (visual check only)

1. Open the official [IMD Radar Services page for Delhi-HQ](https://mausam.imd.gov.in/responsive/radar.php?id=Delhi).
2. Confirm the header says **RADAR - Delhi-HQ**.
3. Inspect **Surface Rainfall Intensity** and **Precipitation Accumulation**;
   open an image to zoom, or use the page's 3-hour animation link.
4. Record the product name and timestamp if useful for a request. The displayed
   image is not a downloadable rainfall grid and must not be used as numeric
   model input.

## 2. Request digital Delhi radar archive/live access

**Direct links**

- [Radar Data Supply Portal guide (PDF)](https://radarapi.imd.gov.in/Received_data/dsp_userguide.pdf)
- [IMD Data Service Portal](https://dsp.imdpune.gov.in/)
- [Registration page](https://dsp.imdpune.gov.in/home_registration_form.php)
- [Radar portal sign-in](https://radarapi.imd.gov.in/)
- [Delhi-HQ radar page and historical-data contact](https://mausam.imd.gov.in/responsive/radar.php?id=Delhi)

**Portal steps from the guide**

1. If the team does not already have an IMD Data Service Portal account, open
   the registration page, choose the applicable user category, and complete
   the required fields.
2. Verify the email and upload the requested PDF identity/undertaking
   documents for that category. The current DSP categories and forms are
   listed at [Categories](https://dsp.imdpune.gov.in/home_categories.php) and
   [Certificate Formats](https://dsp.imdpune.gov.in/home_certificateformats.php).
3. Open the Radar Data Supply Portal and sign in with the DSP credentials, as
   described in the radar guide.
4. Select **Data Request**, complete the form shown after sign-in, and submit.
   The publicly viewable guide says to submit through this menu; exact request
   fields are only visible in the signed-in form.
5. Save the confirmation/request number and follow the portal status or the
   instructions sent by IMD. Do not pay until IMD confirms product availability,
   terms, and the applicable amount. The general DSP payment page explicitly
   says its standard payment instructions do not apply to radar data.

In the request, attach the pilot GeoJSON or a coordinate file. The current
project rectangle is approximately **77.015–77.050°E, 28.590–28.628°N**; it is
a manually defined prototype boundary, not a surveyed hydrologic catchment.
Ask IMD to confirm the best coverage/AOI and radar identifier. Request the
native machine-readable SRI/QPE or radar-nowcast grids for selected event
windows, preferably 2022–2024 monsoons if available. For each product ask for:

- native file format (for example NetCDF/HDF5/BUFR), projection/CRS, grid
  spacing, units, accumulation interval, and native update interval;
- valid/issue timestamps and timezone, missing-value codes, original QC/quality
  flags, and metadata/readme;
- coverage dates, archive completeness, live/near-real-time access, delivery
  latency, and public SIH demo/republication permissions and fees.

Use the project waterlogging dates only as **candidate event windows**. For
example, the existing source extract includes 4 and 9 July 2023; those entries
record incident dates, not proof of a particular rainfall intensity. Request a
buffer around each event (for example, 6–12 hours on either side), or ask IMD
to identify the largest archived rainfall events inside the seasons. A full
three-season request may cost more, so first request availability and an
estimate.

If the signed-in request form is unavailable or the team needs a human contact,
the IMD radar page lists a historical-data contact (Ranjan Phukan,
`ranjan.phukan@imd.gov.in`, +91 9435669264). The DSP home page also lists the
Radar Data contact (`radarlab@gmail.com`, +91 11 2434 4281). Use one of these
only to clarify the official request route or product availability; the
`/dsp/frontend/contact` page is not the online **Data Request** form.

## 3. Request nearby gauge/AWS/ARG rainfall separately

The supplied `data-request-form.pdf` and `data-supply-procedure.pdf` are the
RMC New Delhi route for station observations. They cover surface meteorological
data such as rainfall; they do not substitute for the radar-grid request.
The RMC procedure says hourly rainfall is available only for selected
stations, so ask IMD to confirm station inventory and historical coverage.

### Option A — RMC New Delhi form/email route (matches the supplied PDFs)

1. Fill the 13-field form. Suggested entries:
   - **1–3:** requesting student/team lead, school/institute, contact address,
     phone, and email;
   - **4:** Research (if applicable); **5:** Research;
   - **6:** Surface; **7:** Rainfall (RF);
   - **8:** `Hourly or finer quality-controlled rainfall; please confirm active
     station IDs/coordinates and availability for Palam, Najafgarh, and the
     nearest operating AWS/ARG. Include quality flags, units, timezone, and
     permission for the SIH research/public demo.`
   - **9:** Hourly;
   - **10:** `Palam; Najafgarh if active/archived; otherwise nearest IMD
     rain-gauge/AWS/ARG to Dwarka. Please confirm official station names,
     station IDs, coordinates, and available years.` The Google My Maps images
     supplied with the request are a third-party lead from 2023, not an
     authoritative station inventory.
   - **11:** use the chosen event dates or June–September 2022, 2023, and 2024;
   - **12:** CD (the form's listed digital medium); in **13** also request email
     delivery if permitted. Ask for the original digital file format.
2. Attach a short formal request letter on the school/institute letterhead,
   signed by an authorized school/institute representative, plus the pilot
   boundary and event-date list. The RMC terms describe the letterhead request
   as a way to establish the user's identity.
3. Send the request by email to **rmcnewdelhi.ts@gmail.com**. The supplied
   procedure also lists post/in-person submission to Head, RMC New Delhi,
   Lodhi Road, New Delhi 110003, phone **011-24652403**. Its terms allow initial
   availability questions by email.
4. Wait for the written availability/cost estimate and Certificate of
   Undertaking. Check stations, frequency, date coverage, use terms, and total
   amount before proceeding; the procedure says paid amounts are not
   refundable.
5. If accepting the estimate, return the signed form and undertaking, and
   receipts using the payment instructions RMC sends. The attached RMC
   procedure describes BharatKosh for the data cost plus a separate GST
   receipt. RMC says delivery may be by post, CD, or email.

### Option B — IMD online Data Service Portal for historical observations

1. Open the [DSP home page](https://dsp.imdpune.gov.in/). Before registering,
   check [List of Stations](https://dsp.imdpune.gov.in/home_station_list.php)
   and [Data Formats & Cost Estimate](https://dsp.imdpune.gov.in/home_sampledata_costestimate.php).
2. Read the [user categories](https://dsp.imdpune.gov.in/home_categories.php).
   Register at the page above using the category that actually fits the
   requester. The site says registration requires email verification and a
   one-time PDF identity card and/or Certificate of Undertaking. Its **Students
   (S)** category lists 100% waiver for qualifying students and requires student
   ID plus an institute/school/college letterhead undertaking; do not select it
   unless the team meets the posted definition.
3. Sign in. Submit a historical observation request for **Surface → Rainfall**,
   select the stations the portal confirms, choose hourly frequency and the
   event period, and state research/SIH use. Save the enquiry/request number.
4. Follow the estimate and payment steps shown inside this portal. Its payment
   page says Indian-user data charges use BharatKosh/NTRP with GST added during
   payment; it also says those standard instructions do not apply to radar,
   satellite, or astronomical data. Do not mix this online flow with the
   separate RMC email flow above.
5. Download the supplied records from the request/dashboard when the portal
   marks them ready. The DSP page says the download remains available for one
   month; save it and its metadata promptly.

The screenshot of the AWS/ARG username/password page indicates that the
real-time observation portal is access-controlled. Do not treat the login as
open historical data or try guessed credentials. Ask RMC/DSP or the listed
AWS/ARG helpdesk to confirm whether separate live credentials are available.

## 4. Public IMD APIs for dashboard context (not a rainfall grid)

IMD's published API list includes these direct endpoints:

- [District nowcast](https://mausam.imd.gov.in/api/nowcast_district_api.php)
- [Station nowcast](https://mausam.imd.gov.in/api/nowcastapi.php)
- [District-wise rainfall](https://mausam.imd.gov.in/api/districtwise_rainfall_api.php)
- [District-wise warnings](https://mausam.imd.gov.in/api/warnings_district_api.php)
- [AWS/ARG data](https://city.imd.gov.in/api/aws_data_api.php)
- [District nowcast RSS](https://mausam.imd.gov.in/imd_latest/contents/dist_nowcast_rss.php)

Open an endpoint in a browser and save the returned structured response (or
fetch it in the application only after checking the live response, update time,
field meanings, and permitted use). For station nowcast, use the official
station name/identifier; do not copy the Jaipur example from the old API
document as a Delhi ID. The API-document PDF
(`https://mausam.imd.gov.in/imd_latest/contents/api.pdf`) returned 404 when
checked on 2026-09-27, so verify endpoints and schemas before integrating them.
These endpoints provide official context/alerts or station/district
observations, not a high-resolution gridded DWR input.

## 5. Download NASA GPM IMERG as a satellite fallback

**Direct links:** [Earthdata account registration](https://urs.earthdata.nasa.gov/users/new)
and [GPM IMERG Final half-hourly 0.1° V07 collection](https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGHH_07/summary).

1. Create/verify an Earthdata Login account.
2. Open the GPM IMERG Final half-hourly V07 dataset page and choose **Data
   Access** or **Subset / Get Data**.
3. Sign in when prompted. Set the period (for a three-monsoon retrospective,
   June 1, 2022 through September 30, 2024; or use the selected event windows).
4. Set a spatial bounding box or draw the pilot area on the map. The current
   project rectangle is 77.015–77.050°E, 28.590–28.628°N; use a buffer if the
   analysis needs storm context beyond the prototype boundary.
5. Keep the precipitation estimate and available quality/error variables;
   retain the provider README and metadata. Submit the subset, download all
   returned file links, and retain the original granules/filenames.

The collection page describes V07 at 0.1° and 30-minute resolution. IMERG is a
multi-satellite estimate, not Delhi Doppler radar. Use Final Run for retrospective
analysis; label satellite data clearly in the project and do not count it as an
IMD radar feed.

## 6. Download IMD daily 0.25° rainfall for broad historical checks

**Direct link:** [IMD 0.25° daily rainfall NetCDF archive](https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html).
If that page is unavailable, try the [binary archive and sample readers](https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_Bin.html).

1. Open the NetCDF archive and scroll to **Yearly Gridded Rainfall (0.25 x
   0.25) data NetCDF File**.
2. Select a year in the yearly-file selector and click **Input/submit** to
   request that annual file; repeat for 2022, 2023, and 2024 as needed.
3. Save the file and the page's metadata/readme. The archive page currently
   describes daily millimetres on a 0.25° grid, 135 × 129 points, with its
   long-period series listed through 2024. Ask IMD about newer years if needed.
4. Read the NetCDF with a geospatial tool, check coordinates/units/missing
   values, then extract the cells intersecting Dwarka. Do not interpret one
   coarse daily grid cell as a neighborhood-scale rainfall measurement.

This is daily, roughly 25–28 km grid spacing: useful for historical/regional
checks, not street-level nowcasting or a substitute for radar/gauges.

## 7. Put files into SIH only with provenance and permission

- Keep original downloads and provider metadata. Record provider, product,
  request/receipt ID, station/radar ID, dates, original format, timezone,
  coordinate system, quality flags, and access/demo terms.
- Store radar grids under `data/operational_bundle/rainfall/` only after IMD
  supplies them and public-demo use is permitted. Populate the project
  `rainfall/manifest.json` from the actual metadata; never invent timestep,
  CRS, resolution, or QC fields.
- Store IMERG and the IMD daily grid under `data/reference/` as labelled
  fallbacks until the model explicitly supports their products. They do not
  meet the operational radar-grid requirement in
  [`SIH26085_DATA_READINESS.md`](SIH26085_DATA_READINESS.md).
- Keep gauge series separate from gridded radar data, preserve station IDs and
  coordinates, and use gauges for checks/bias correction only when time windows
  and quality flags align.
