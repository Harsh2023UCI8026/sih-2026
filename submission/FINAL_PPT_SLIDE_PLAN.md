# SIH 26085 final presentation: slide-by-slide revision plan

The current `SIH_2026_Idea_Submission_Presentation.pdf` is a one-page idea submission, not a full final deck. Use this outline for the final 8–10 slide presentation. Keep claims consistent with the live demo and show each data source as **live**, **reference**, **assumed**, **synthetic**, or **requested**.

| Slide | Content to show | Edit needed / evidence boundary |
| --- | --- | --- |
| 1. Title and challenge | Urban Flood Nowcasting System · SIH 26085 · Dwarka Mor/Najafgarh prototype | Replace broad “all Delhi / operational warning” phrasing with the actual pilot. Add team, institution, and date. |
| 2. Why street flooding is hard | Local rain + terrain depressions + inlet/drain capacity + surcharge + downstream/pump effects | Use a simple rainfall → surface → inlet/drain → surcharge diagram. Explain that a city-wide rainfall number alone cannot resolve the street location. |
| 3. Data sources and request status | Open-Meteo point forecast; OSM road geometry; Copernicus GLO-30 and ESA WorldCover context rasters; IIT Delhi/IFCD 2018 Najafgarh plan; IMD/RMC correspondence | Separate runtime inputs from contextual references. RMC New Delhi replied that data requests must specify Safdarjung or Palam and include its Data Request Form plus a valid college ID. The formal application and dataset are still pending. Do not call the reply a data delivery. |
| 4. Current prototype architecture | Forecast-model point input → six-node/five-edge pilot graph → local RandomForest surrogate or lightweight formula path → depth bands and GIS map | State which backend produced the shown result. The forest is a formula/synthetic-target surrogate; geometry/capacity are assumed and no independent observed-depth validation exists. No 2D shallow-water solver is implemented. |
| 5. Research and design choice | 2023 radar + 2D shallow-water nowcasting; 2020 RF surrogate trained on high-fidelity 1D/2D model; SWMM + raster 2D coupling | Explain the intended next architecture. Explicitly distinguish the paper's calibrated physics labels from this project's formula-generated labels. Put citations in slide footer and full references at the end. |
| 6. Mumbai/IIT Bombay precedent | 2014–17 Mithi catchment research project: sensor/weather (WRF-UCM)/tide/integrated flash-tidal flood components; C-DAC reported a preliminary PARAM Yuva-II real-time experiment compared with observations | Cite the government ISTI record and C-DAC 2017–18 report. Say “past research/experiment”; do not imply that project is the current live service or that its data are available to this team. |
| 7. Dashboard and route demo | Use current Simple/Technical views, a forecast lead time, a route request, actual OSM road geometry, distance/ETA, and nearby model context | Replace “Dry forecast” with the current “No rain forecast · street depth unverified” state. Route options are road directions, not flood-safe certificates; show route-source attribution and no-traffic/no-closure caveat. |
| 8. Model, latency, and deployment | Local 1.53 GB RF artifact; Vercel lightweight path; private HF Model repository; proposed Render FastAPI inference service | The pasted HF CLI log shows the private model upload succeeded, while the HF Docker Space creation returned 402. Render `/healthz` has not been confirmed: the supplied check used a placeholder URL and returned 404. Do not present remote inference as live until `/healthz` reports `model_loaded: true` and Vercel returns `depth_model_backend=random_forest_huggingface`. |
| 9. Current gaps and request status | Sparse pilot graph; no measured-depth validation; initial IMD/RMC inquiry sent and answered | Say **RMC replied with the required application steps**: choose Safdarjung or Palam, submit the prescribed Data Request Form, and provide a valid college ID. State **formal request and rainfall dataset pending**. |
| 10. Validation plan and ask | Request data-owner support; collect gauge/radar, surveyed DEM and network, event wet/dry depths; calibrate 1D/2D and compare held-out storms; then train compact surrogate and route impact layer | End with concrete acceptance metrics and the agency/team action needed. Mark every future capability as “next step” until completed. |

## Suggested demo narration

1. Set Dwarka Mor and select `+60 min`; name the forecast source and its point scale.
2. Open Technical View and point to the assumed 6-node/5-edge graph, formula pipeline, and readiness panel.
3. Show a route option. Explain its OSM road geometry/ETA and that nearby point bands are unvalidated and not measured along that street.
4. Open the Najafgarh 2018 reference card and explain that it helps frame agency/data requests; it is basin-wide context, not a Dwarka input.
5. Finish with the data-request and validation plan. Do not present a synthetic demo scenario as a live forecast.

## References to put in the deck

- [IIT Bombay/MoES Mithi-catchment project record (ISTI Portal)](https://www.indiascienceandtechnology.gov.in/research/near-real-time-urban-flood-forecasting-system?language=en)
- [C-DAC Annual Report 2017–18](https://cdac.in/index.aspx?id=pdf_annual_report_17-18)
- Costabile et al. (2023), [radar-driven street-level flood nowcasting](https://doi.org/10.1029/2023WR034599)
- Zahura et al. (2020), [RF surrogate of a high-fidelity 1D/2D flood model](https://doi.org/10.1029/2019WR027038)
- Wu et al. (2022), [SWMM and 2D surface-flow coupling](https://www.mdpi.com/2073-4441/14/11/1760)

## Paste-ready text for the two revised slides

### Data sources and request status

**Runtime inputs:** Open-Meteo point precipitation forecast (forecast-model output, not radar); OpenStreetMap road geometry for map and route context; a six-node/five-link Dwarka pilot graph.

**Context references:** Copernicus GLO-30 elevation and ESA WorldCover land cover (context rasters, not a surveyed street DTM); IIT Delhi/IFCD *Najafgarh Drainage Master Plan* (2018; basin-scale context); US EPA SWMM 5.2 documentation (method reference only—the current dashboard does not run SWMM).

**IMD/RMC data request:** RMC New Delhi replied to our initial inquiry. It asked us to choose Safdarjung or Palam, submit the prescribed Data Request Form, and provide a valid college ID. **Formal application and station rainfall data are pending.**

### Technical approach and deployment status

**Dashboard:** HTML/CSS/JavaScript + Leaflet GIS map  
**Rainfall input:** Open-Meteo forecast-model precipitation when reachable  
**Pilot network:** 6 nodes · 5 schematic drainage links · assumed dimensions/capacity  
**Depth model:** RandomForest surrogate trained with formula-derived targets and synthetic rainfall/geometry examples; no independent observed-depth validation  
**Serving design:** Vercel dashboard/API → Render FastAPI (`/predict`, `/healthz`) → private Hugging Face Model repository  
**Status:** The 1.53 GB model artifact upload to the private HF Model repository succeeded. Render inference is **not yet verified**; connect Vercel only after `/healthz` reports `model_loaded: true`. The current Vercel path uses the lightweight formula unless a healthy RandomForest endpoint is configured.

**Route layer:** OpenStreetMap/OSRM road directions; nearby pilot estimates do not verify street-water depth or route safety.
