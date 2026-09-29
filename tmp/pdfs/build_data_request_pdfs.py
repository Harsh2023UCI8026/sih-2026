from __future__ import annotations

import json
import math
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "pdf"
OUT.mkdir(parents=True, exist_ok=True)

NAME = "Harsh Jha"
INSTITUTE = "NSUT, Delhi"
EMAIL = "harsh.jha.ug23@nsut.ac.in"
PHONE = "+91 70428 34496"
DATE = "29 September 2026"
BOUNDARY = "Approximate project rectangle: 77.015-77.050 E, 28.590-28.628 N (WGS 84 / EPSG:4326)."
PROJECT = "Smart India Hackathon problem statement 26085: Urban Flood Nowcasting System (Drainage and Rainfall Coupling)."

NAVY = colors.HexColor("#12304A")
BLUE = colors.HexColor("#1769AA")
TEAL = colors.HexColor("#138A83")
PALE = colors.HexColor("#EAF3F8")
MUTED = colors.HexColor("#506273")
INK = colors.HexColor("#1A2833")
RULE = colors.HexColor("#C8D5DE")
ORANGE = colors.HexColor("#B76A00")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="DocTitle", parent=styles["Title"], fontName="Helvetica-Bold",
    fontSize=17, leading=20, textColor=NAVY, alignment=TA_LEFT,
    spaceAfter=5,
))
styles.add(ParagraphStyle(
    name="SubTitle", parent=styles["Normal"], fontName="Helvetica",
    fontSize=8.4, leading=11, textColor=MUTED, spaceAfter=5,
))
styles.add(ParagraphStyle(
    name="BodySmall", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=9.1, leading=12, textColor=INK, spaceAfter=5,
))
styles.add(ParagraphStyle(
    name="BulletSmall", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=8.7, leading=11.2, textColor=INK, leftIndent=12,
    firstLineIndent=-8, bulletIndent=1, spaceAfter=2.5,
))
styles.add(ParagraphStyle(
    name="Meta", parent=styles["Normal"], fontName="Helvetica",
    fontSize=8.2, leading=10.5, textColor=MUTED, spaceAfter=3,
))
styles.add(ParagraphStyle(
    name="Notice", parent=styles["Normal"], fontName="Helvetica-Bold",
    fontSize=8.3, leading=10.5, textColor=ORANGE,
))
styles.add(ParagraphStyle(
    name="MapTitle", parent=styles["Title"], fontName="Helvetica-Bold",
    fontSize=21, leading=24, textColor=NAVY, alignment=TA_LEFT,
))
styles.add(ParagraphStyle(
    name="MapBody", parent=styles["Normal"], fontName="Helvetica",
    fontSize=9, leading=13, textColor=INK, spaceAfter=5,
))


def footer(c: canvas.Canvas, doc) -> None:
    c.saveState()
    w, _ = A4
    c.setStrokeColor(RULE)
    c.setLineWidth(0.5)
    c.line(18 * mm, 15 * mm, w - 18 * mm, 15 * mm)
    c.setFont("Helvetica", 7.3)
    c.setFillColor(MUTED)
    c.drawString(18 * mm, 10.5 * mm, f"{NAME} | {INSTITUTE} | {EMAIL} | {PHONE}")
    c.drawRightString(w - 18 * mm, 10.5 * mm, f"SIH 26085 | Page {doc.page}")
    c.restoreState()


def header(c: canvas.Canvas, doc) -> None:
    c.saveState()
    w, h = A4
    c.setFillColor(NAVY)
    c.rect(0, h - 12 * mm, w, 12 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(18 * mm, h - 8 * mm, "SIH 26085  |  DWARKA MOR / NAJAFGARH DATA REQUEST")
    c.setFillColor(TEAL)
    c.rect(0, h - 13.2 * mm, w, 1.2 * mm, stroke=0, fill=1)
    c.restoreState()
    footer(c, doc)


def bullet(text: str) -> Paragraph:
    return Paragraph(f"- {escape(text)}", styles["BulletSmall"])


def letter_pdf(filename: str, label: str, recipient: str, email_line: str, subject: str,
               greeting: str, paragraphs: list[str], requests: list[str], close: str,
               source_note: str, submission_note: str = "") -> None:
    doc = SimpleDocTemplate(
        str(OUT / filename), pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=21 * mm,
        title=label, author=NAME,
        subject="Student data availability request for SIH 26085",
    )
    story = [
        Paragraph(escape(label), styles["DocTitle"]),
        Paragraph(PROJECT, styles["SubTitle"]),
        HRFlowable(width="100%", thickness=0.7, color=RULE, spaceBefore=2, spaceAfter=8),
        Paragraph(f"<b>Date:</b> {DATE}", styles["Meta"]),
        Paragraph(f"<b>To:</b> {escape(recipient)}", styles["Meta"]),
        Paragraph(f"<b>Contact / submission route:</b> {escape(email_line)}", styles["Meta"]),
        Paragraph(f"<b>Subject:</b> {escape(subject)}", styles["BodySmall"]),
        Paragraph(escape(greeting), styles["BodySmall"]),
    ]
    story.extend(Paragraph(escape(p), styles["BodySmall"]) for p in paragraphs)
    if requests:
        story.append(Paragraph("Requested information", styles["Heading3"]))
        story.extend(bullet(x) for x in requests)
    story.extend([
        Spacer(1, 3),
        Paragraph(escape(close), styles["BodySmall"]),
        Spacer(1, 4),
        Paragraph("Sincerely,", styles["BodySmall"]),
        Spacer(1, 14),
        Paragraph(f"<b>{NAME}</b><br/>{INSTITUTE}<br/>{EMAIL}<br/>{PHONE}", styles["BodySmall"]),
        Paragraph("Signature: ____________________________________", styles["Meta"]),
        Spacer(1, 3),
        Table([[Paragraph(
            "Student-prepared request; this is not NSUT letterhead or an institutional endorsement. "
            "If a recipient requires an authorized institutional letter, obtain it before formal data supply.",
            styles["Notice"],
        )]], colWidths=[170 * mm], style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF5E5")),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#E7C58C")),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])),
        Spacer(1, 4),
        Paragraph(f"<b>Source / route:</b> {escape(source_note)}", styles["Meta"]),
    ])
    if submission_note:
        story.append(Paragraph(f"<b>Submission note:</b> {escape(submission_note)}", styles["Meta"]))
    doc.build(story, onFirstPage=header, onLaterPages=header)


def make_aoi_map() -> None:
    bounds_path = ROOT / "src" / "data" / "dwarka_catchment_bounds.geojson"
    roads_path = ROOT / "data" / "reference" / "roads" / "dwarka_roads.geojson"
    bounds_fc = json.loads(bounds_path.read_text(encoding="utf-8"))
    bounds_feature = bounds_fc["features"][0]
    ring = bounds_feature["geometry"]["coordinates"][0]
    props = bounds_feature.get("properties", {})
    road_fc = json.loads(roads_path.read_text(encoding="utf-8"))
    west = min(pt[0] for pt in ring)
    east = max(pt[0] for pt in ring)
    south = min(pt[1] for pt in ring)
    north = max(pt[1] for pt in ring)
    lat0 = (south + north) / 2
    lon0 = (west + east) / 2
    cos0 = math.cos(math.radians(lat0))
    km_lat = 111.32
    km_lon = 111.32 * cos0
    actual_w_km = (east - west) * km_lon
    actual_h_km = (north - south) * km_lat

    out_path = OUT / "06_Dwarka_Najafgarh_Approx_Pilot_AOI_Map.pdf"
    c = canvas.Canvas(str(out_path), pagesize=landscape(A4), pageCompression=1)
    page_w, page_h = landscape(A4)
    c.setTitle("Dwarka Mor and Najafgarh Approximate Project Pilot Boundary")
    c.setAuthor(NAME)
    c.setSubject("Approximate study area map for SIH 26085 data requests")
    c.setFillColor(colors.white)
    c.rect(0, 0, page_w, page_h, stroke=0, fill=1)
    c.setFillColor(NAVY)
    c.rect(0, page_h - 19 * mm, page_w, 19 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(17 * mm, page_h - 12 * mm, "DWARKA MOR / NAJAFGARH - APPROXIMATE PROJECT AOI")
    c.setFillColor(TEAL)
    c.rect(0, page_h - 20 * mm, page_w, 1.2 * mm, stroke=0, fill=1)

    map_x, map_y = 18 * mm, 24 * mm
    map_w, map_h = 175 * mm, page_h - 54 * mm
    scale = min(map_w / (actual_w_km * 1000), map_h / (actual_h_km * 1000))
    used_w = actual_w_km * 1000 * scale
    used_h = actual_h_km * 1000 * scale
    x0 = map_x + (map_w - used_w) / 2
    y0 = map_y + (map_h - used_h) / 2

    def project(lon: float, lat: float) -> tuple[float, float]:
        x = (lon - west) * km_lon * 1000 * scale + x0
        y = (lat - south) * km_lat * 1000 * scale + y0
        return x, y

    # Draw a restrained road context layer from the saved OSM extract.
    c.setFillColor(colors.HexColor("#FAFCFD"))
    c.rect(x0, y0, used_w, used_h, stroke=0, fill=1)
    highway_styles = {
        "motorway": (colors.HexColor("#7A4FA3"), 1.2),
        "trunk": (colors.HexColor("#B45B3C"), 1.15),
        "primary": (colors.HexColor("#D1812E"), 1.0),
        "secondary": (colors.HexColor("#7B8F9C"), 0.8),
        "tertiary": (colors.HexColor("#9AAAB3"), 0.55),
        "residential": (colors.HexColor("#B3C0C7"), 0.38),
        "unclassified": (colors.HexColor("#A9B8C1"), 0.35),
        "service": (colors.HexColor("#C7D0D6"), 0.25),
        "living_street": (colors.HexColor("#BBC8CE"), 0.3),
    }
    c.saveState()
    clip = c.beginPath()
    clip.rect(x0, y0, used_w, used_h)
    c.clipPath(clip, stroke=0, fill=0)
    for feature in road_fc.get("features", []):
        geom = feature.get("geometry") or {}
        props_r = feature.get("properties") or {}
        highway = props_r.get("highway")
        if highway not in highway_styles or geom.get("type") not in ("LineString", "MultiLineString"):
            continue
        color, width = highway_styles[highway]
        c.setStrokeColor(color)
        c.setLineWidth(width)
        line_groups = [geom.get("coordinates", [])] if geom.get("type") == "LineString" else geom.get("coordinates", [])
        for coords in line_groups:
            if len(coords) < 2:
                continue
            path = c.beginPath()
            start = True
            for lon, lat, *rest in coords:
                if west - 0.0005 <= lon <= east + 0.0005 and south - 0.0005 <= lat <= north + 0.0005:
                    px, py = project(lon, lat)
                    if start:
                        path.moveTo(px, py)
                        start = False
                    else:
                        path.lineTo(px, py)
                else:
                    start = True
            c.drawPath(path, stroke=1, fill=0)
    c.restoreState()

    # Pilot AOI outline.
    c.setStrokeColor(colors.HexColor("#C23B35"))
    c.setLineWidth(2.2)
    boundary_path = c.beginPath()
    for i, (lon, lat) in enumerate(ring):
        px, py = project(lon, lat)
        if i == 0:
            boundary_path.moveTo(px, py)
        else:
            boundary_path.lineTo(px, py)
    c.drawPath(boundary_path, stroke=1, fill=0)
    c.setStrokeColor(RULE)
    c.setLineWidth(0.7)
    c.rect(x0, y0, used_w, used_h, stroke=1, fill=0)

    # North arrow and approximate scale bar.
    ax = x0 + used_w - 10 * mm
    ay = y0 + used_h - 17 * mm
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(ax, ay + 10 * mm, "N")
    c.setStrokeColor(NAVY)
    c.setLineWidth(1.1)
    c.line(ax, ay, ax, ay + 8 * mm)
    c.line(ax, ay + 8 * mm, ax - 2 * mm, ay + 5 * mm)
    c.line(ax, ay + 8 * mm, ax + 2 * mm, ay + 5 * mm)
    scale_m = 500
    scale_len = scale_m * scale
    sbx, sby = x0 + 8 * mm, y0 + 8 * mm
    c.setStrokeColor(NAVY)
    c.setLineWidth(2)
    c.line(sbx, sby, sbx + scale_len, sby)
    c.line(sbx, sby - 2, sbx, sby + 2)
    c.line(sbx + scale_len, sby - 2, sbx + scale_len, sby + 2)
    c.setFillColor(NAVY)
    c.setFont("Helvetica", 7.4)
    c.drawString(sbx, sby + 3, "Approx. 500 m")

    # Right-side request context and legend.
    panel_x = 207 * mm
    panel_w = page_w - panel_x - 15 * mm
    c.setFillColor(PALE)
    c.roundRect(panel_x, 29 * mm, panel_w, page_h - 58 * mm, 3 * mm, stroke=0, fill=1)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(panel_x + 8 * mm, page_h - 31 * mm, "Study area reference")
    text_obj = c.beginText(panel_x + 8 * mm, page_h - 41 * mm)
    text_obj.setFont("Helvetica", 8.3)
    text_obj.setLeading(12)
    for line in [
        "Project: SIH 26085",
        "Dwarka Mor / Najafgarh pilot",
        "District: South West Delhi",
        "",
        "Approximate request bounds",
        f"West: {west:.3f} E",
        f"East: {east:.3f} E",
        f"South: {south:.3f} N",
        f"North: {north:.3f} N",
        "Coordinate system: WGS 84 / EPSG:4326",
        f"Approx. footprint: {actual_w_km:.1f} x {actual_h_km:.1f} km",
        "",
        "Map legend",
        "Red outline: request boundary",
        "Orange/red line: larger mapped road class",
        "Grey-blue line: other mapped road",
        "",
        "Data source",
        "Road context: project-supplied OpenStreetMap extract.",
        "Snapshot date is not recorded in source metadata.",
        "Map is not a drain survey, DEM, or flood-depth layer.",
    ]:
        text_obj.textLine(line)
    c.drawText(text_obj)
    c.setStrokeColor(colors.HexColor("#C23B35"))
    c.setLineWidth(2)
    c.line(panel_x + 8 * mm, 52 * mm, panel_x + 18 * mm, 52 * mm)
    c.setStrokeColor(colors.HexColor("#A9B8C1"))
    c.setLineWidth(1)
    c.line(panel_x + 8 * mm, 46 * mm, panel_x + 18 * mm, 46 * mm)

    c.setFillColor(colors.HexColor("#FFF5E5"))
    c.roundRect(panel_x + 6 * mm, 34 * mm, panel_w - 12 * mm, 20 * mm, 2 * mm, stroke=0, fill=1)
    c.setFillColor(ORANGE)
    c.setFont("Helvetica-Bold", 7.6)
    c.drawString(panel_x + 8 * mm, 47 * mm, "IMPORTANT")
    c.setFillColor(INK)
    c.setFont("Helvetica", 7.3)
    c.drawString(panel_x + 8 * mm, 42 * mm, "Approximate project rectangle only; not an official")
    c.drawString(panel_x + 8 * mm, 37 * mm, "hydrologic catchment or surveyed asset boundary.")

    c.setStrokeColor(RULE)
    c.line(18 * mm, 16 * mm, page_w - 18 * mm, 16 * mm)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7.1)
    c.drawString(18 * mm, 11 * mm, f"Prepared by {NAME}, {INSTITUTE} | {EMAIL} | {PHONE}")
    c.drawRightString(page_w - 18 * mm, 11 * mm, "OpenStreetMap contributors (ODbL) | SIH 26085")
    c.save()


letter_pdf(
    "01_IMD_DWR_Radar_Data_Request.pdf",
    "Delhi Doppler Radar Data Request",
    "India Meteorological Department (IMD), Radar Data Supply Portal - Data Request for Delhi-HQ coverage",
    "Submit through the signed-in Radar Data Supply Portal: https://radarapi.imd.gov.in/",
    "Availability and access process for machine-readable Delhi DWR rainfall grids for a student urban-flood prototype",
    "Dear Sir/Madam,",
    [
        f"I am a student at {INSTITUTE}, developing a prototype for {PROJECT}",
        f"Please confirm whether the Delhi-HQ Doppler Weather Radar archive or an official nowcast feed covers this approximate pilot area: {BOUNDARY} The attached AOI map is only a manually defined project rectangle, not a surveyed catchment.",
        "We are seeking an availability check and the official access, license, and fee process before requesting or using any records. Priority is native machine-readable radar rainfall/QPE, not a rendered image.",
    ],
    [
        "Archived Surface Rainfall Intensity (SRI) / quantitative precipitation estimate grids and, if available, official radar-nowcast grids for June-September 2022, 2023, and 2024; please prioritize candidate project dates 4 and 9 July 2023 with 6-12 hours of context on each side.",
        "For each product: native format, grid spacing and projection/CRS, units and accumulation interval, issue/valid timestamps and timezone, update interval, radar/site identifier, QC flags, missing-value codes, and processing/calibration notes.",
        "Coverage completeness, archive/live access, delivery latency, API or download method, fee estimate, attribution, and permission/restrictions for student research and a publicly accessible SIH demonstration.",
        "Please identify the nearest suitable radar and advise whether the proposed boundary should be expanded to include the surrounding rainfall field.",
    ],
    "If the archive is available, please advise the request fields and any required identity, institute, undertaking, or authorization documents. We will retain original metadata and will not present radar-image pixels as numeric rainfall grids.",
    "Submit this supporting request through the portal's Data Request option. Portal guide: https://radarapi.imd.gov.in/Received_data/dsp_userguide.pdf. Radar request queries listed by IMD: radarlab@gmail.com.",
    "Attach 06_Dwarka_Najafgarh_Approx_Pilot_AOI_Map.pdf in the portal request.",
)

letter_pdf(
    "02_RMC_Hourly_Rainfall_Availability_Request.pdf",
    "Historical Rain-Gauge Data Availability Request",
    "Technical Section (Data Supply Unit), Regional Meteorological Centre (RMC), New Delhi",
    "rmcnewdelhi.ts@gmail.com | 011-24652403",
    "Initial availability and estimate request: hourly rainfall observations for Dwarka/Najafgarh candidate stations, 2022-2024",
    "Dear Sir/Madam,",
    [
        f"I am a student at {INSTITUTE}, working on {PROJECT}",
        "Before submitting the formal Data Request Form, please confirm the available rain-gauge/AWS/ARG station inventory nearest to Dwarka Mor and Najafgarh and whether quality-controlled hourly records are available. The IMD procedure notes that hourly rainfall is available only for selected stations, so kindly confirm station IDs, coordinates, record coverage, and frequency first.",
        "Requested initial period: 1 June 2022 through 30 September 2024. Candidate heavy-rain event windows include 4 and 9 July 2023, but these are project-record dates for availability checking, not verified storm labels.",
    ],
    [
        "Station rainfall in mm with timestamp/timezone, units, quality flags, missing-value codes, station ID and coordinates; please include Palam and Najafgarh only if active/archived, plus the nearest suitable official stations you recommend.",
        "Available temporal resolution and archive years; digital delivery format; data charges and any student/research concession; and the Certificate of Undertaking or institutional authorization needed for supply.",
        "Written permission/terms for student research, model evaluation, and use in a publicly accessible SIH prototype demonstration, including attribution and any redistribution limits.",
    ],
    "This email is an initial availability inquiry. If records are available, please send the current official Data Request Form, undertaking format, and estimate process. We will review the station/date coverage and charges before accepting an estimate or making payment.",
    "RMC New Delhi data procedure: https://mausam.imd.gov.in/newdelhi/docs/data-procedure.pdf. Current official request form: https://mausam.imd.gov.in/newdelhi/docs/data-request.pdf.",
    "Attach 06_Dwarka_Najafgarh_Approx_Pilot_AOI_Map.pdf. For a formal paid data request, use the official RMC form and any institute-letterhead requirement supplied by RMC; this letter is not that official form.",
)

letter_pdf(
    "03_IFCD_Storm_Drain_Terrain_Records_Request.pdf",
    "Storm-Drain GIS and Terrain Records Request",
    "Chief Engineer / concerned Civil Division, Irrigation and Flood Control Department (I&FC), Government of NCT of Delhi",
    "ceifcd@gmail.com | copy: secretaryifcdgnctd@gmail.com",
    "Request for existing storm-drain GIS/CAD, terrain, and event records - SIH 26085 Dwarka/Najafgarh pilot",
    "Dear Sir/Madam,",
    [
        f"I am a student at {INSTITUTE}, developing {PROJECT} The attached map marks an approximate project request area. It is not an official drainage catchment, and we are requesting existing records only, not a new survey.",
        "The project has identified I&FC planning/jurisdiction references for the Najafgarh, Palam, Palam Link, Nasirpur, Pankha Road, Bijwasan, and related drain reaches. Please confirm which divisions and agencies own or maintain stormwater assets in the mapped area and forward this request to the appropriate record custodian if needed.",
    ],
    [
        "Latest existing machine-readable storm-drain GIS/CAD: node and pipe/channel geometries, connectivity, asset IDs, dimensions/material, inlets/manholes, outfalls, catchments, and ownership/status.",
        "Available surveyed/as-built/design values for invert and rim levels, slopes, roughness, design capacity, pumps/gates, regulator levels, and outfall conditions. Please preserve unknown fields and label surveyed, as-built, design, or estimated values.",
        "Existing terrain products suitable for surface-flow work (DTM/DEM/LiDAR if held), including road crowns, underpasses, barriers/breaklines, vertical datum, horizontal CRS, resolution, accuracy, and acquisition date.",
        "Event-linked waterlogging/flood observations or water-level records with coordinates, date/time, measured depth and units, method, uncertainty, and dry observations if held. Incident-only reports without depth should be identified as occurrence records.",
        "Preferred formats are GeoPackage, Shapefile, File Geodatabase, DWG/DXF, GeoTIFF, CSV, or another documented machine-readable format; please include schema/data dictionary, source date, fees, license, attribution, and public-demo permissions.",
    ],
    "If the department does not hold a requested record, please identify the responsible agency/division and the correct data contact. We will preserve the provided metadata and use records only under the terms you specify.",
    "I&FC contact and division directory: https://ifc.delhi.gov.in/ifc/organizational-setup. Department service/contact page: https://ifc.delhi.gov.in/ifc/citizen-charter.",
    "Attach 06_Dwarka_Najafgarh_Approx_Pilot_AOI_Map.pdf. Please confirm the correct division/record custodian before any wider public redistribution.",
)

letter_pdf(
    "04_MCD_Najafgarh_Local_Drain_Records_Request.pdf",
    "Local Storm-Drain and Waterlogging Records Request",
    "Deputy Commissioner / Executive Engineer (Storm-Water Drainage), Najafgarh Zone, Municipal Corporation of Delhi (MCD)",
    "dyancngz@mcd.org.in | MCD Citizen Call Centre: 155305",
    "Request for existing local storm-drain GIS, maintenance, and event records - Dwarka/Najafgarh pilot",
    "Dear Sir/Madam,",
    [
        f"I am a student at {INSTITUTE}, working on {PROJECT} The attached AOI map is an approximate project rectangle. Please confirm whether MCD owns or maintains local road drains, inlets, underpasses, or waterlogging assets within it. The MCD monsoon list includes Najafgarh Zone locations such as Nasirpur-Palam Road; it does not establish ownership for every asset in the AOI.",
        "We request copies of existing records only. If another department owns a trunk drain or road asset, please identify the responsible division and forward or redirect this request.",
    ],
    [
        "Existing local stormwater-drain/inlet/manhole GIS or CAD with geometry, connectivity, asset ID, dimensions, rim/invert levels, catchment links, outfall, and ownership where recorded.",
        "Available road-level terrain/underpass low-point surveys and maintenance records, including desilting dates, blockage/condition observations, pumps, and known drainage complaints.",
        "Historical waterlogging/flood reports or sensor records with exact location and date/time; include measured water depth, measurement method, units, uncertainty, and observed-dry records only where actually measured.",
        "Original coordinate reference system, vertical datum, units, resolution/accuracy, schema, record date/status, access costs, attribution, and permission for student research and public SIH demonstration.",
    ],
    "Please advise the correct MCD email/inward channel and the zone/division data custodian for submitting or collecting the records. We will not convert incident-only complaints into measured depth labels.",
    "Najafgarh Zone listing: https://dmsouthwest.delhi.gov.in/about-district/administrative-setup/south-delhi-municipal-corporation/. MCD monsoon waterlogging/nodal-area list: https://mcdonline.nic.in/portal/downloadFile/drain_wise_nodal_officers_for_the_purpose_of_desilting_to_address_the_water_logging_issues_26031801270838.pdf.",
    "Attach 06_Dwarka_Najafgarh_Approx_Pilot_AOI_Map.pdf. The zonal mailbox is listed by the Government of Delhi district portal; ask the zone to confirm the correct engineering/data custodian for the requested assets.",
)

letter_pdf(
    "05_PWD_Drain_Road_And_Underpass_Records_Request.pdf",
    "PWD Road-Drain and Underpass Records Request",
    "Superintending Engineer, C&ND / concerned PWD division, Public Works Department, Government of NCT of Delhi",
    "sepwddelhicnd@gmail.com | PWD contact: complaint@pwd.delhi.com",
    "Request for existing PWD road-drain, underpass, terrain, and waterlogging records - SIH 26085",
    "Dear Sir/Madam,",
    [
        f"I am a student at {INSTITUTE}, developing {PROJECT} Please confirm whether PWD maintains roads, drains, subways/underpasses, or flood-vulnerable points within the attached approximate Dwarka Mor/Najafgarh request area. We are seeking existing records for student research and model evaluation, not a new survey or a live operational feed.",
        "The current PWD nodal directory assigns monsoon preparedness, drain desilting, and waterlogging coordination to the C&ND Superintending Engineer. Please route the request to the correct division and identify asset ownership where it is held by another department.",
    ],
    [
        "Existing road and storm-drain GIS/CAD: road centerlines/edges, drain and inlet geometry, connectivity, dimensions, outfalls, asset IDs, and ownership.",
        "Available surveyed/as-built road elevations, road crowns, subway/underpass low points, barriers, DTM/LiDAR, vertical datum, CRS, resolution, accuracy, and acquisition date.",
        "Historical road-waterlogging/underpass records and any sensor or measured-depth observations with location, timestamp, depth/units, method, uncertainty, and closure status where recorded.",
        "Drain desilting/maintenance dates, blockage/condition logs, pump or gate status, source date, data dictionary, access cost, attribution, and permission for research and a public SIH demonstration.",
    ],
    "Please confirm the correct PWD division/contact for the coordinates shown on the map and advise availability, formats, access terms, and any formal request or institute authorization required.",
    "PWD nodal officers (monsoon/drain desilting/waterlogging): https://www.pwddelhi.gov.in/new-nodal-officers. PWD Monsoon Order 2025: https://pwddelhi.gov.in/writeread/Circular/PWDFloodControl2025.pdf.",
    "Attach 06_Dwarka_Najafgarh_Approx_Pilot_AOI_Map.pdf. Verify that C&ND is the correct division for the particular roads before sending.",
)

make_aoi_map()
print("Created 6 request PDFs:")
for path in sorted(OUT.glob("*.pdf")):
    print(f"{path.name}\t{path.stat().st_size} bytes")
