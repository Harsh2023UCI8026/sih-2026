"""Generate an accurate overview of the Dwarka flood-dashboard prototype."""

import os
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)


def generate_sih_pdf(output_path):
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=24, leading=29, textColor=colors.HexColor("#10233f"),
        alignment=TA_CENTER, spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name="Deck", parent=styles["Normal"], fontSize=12, leading=18,
        textColor=colors.HexColor("#475569"), alignment=TA_CENTER,
        spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name="Section", parent=styles["Heading2"], fontSize=15,
        leading=19, textColor=colors.HexColor("#145c73"), spaceBefore=8,
        spaceAfter=7,
    ))
    styles.add(ParagraphStyle(
        name="BodySmall", parent=styles["BodyText"], fontSize=10,
        leading=15, textColor=colors.HexColor("#243449"), spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="Cell", parent=styles["BodyText"], fontSize=9,
        leading=13, textColor=colors.HexColor("#243449"),
    ))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#d5e2e8"))
        canvas.line(0.65 * inch, 0.55 * inch, 7.85 * inch, 0.55 * inch)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(0.68 * inch, 0.36 * inch, "Dwarka pilot prototype - for demonstration only")
        canvas.drawRightString(7.82 * inch, 0.36 * inch, f"Page {doc.page}")
        canvas.restoreState()

    story = [
        Spacer(1, 0.14 * inch),
        Paragraph("Urban Flood Dashboard Prototype", styles["CoverTitle"]),
        Paragraph("SIH 2026 | Dwarka pilot concept", styles["Deck"]),
        Spacer(1, 0.1 * inch),
        Paragraph(
            "A map-first interface for exploring forecast-model precipitation, a prototype "
            "drainage graph, and clearly labelled model estimates. This build is not an "
            "operational flood-warning service.", styles["BodySmall"]),
        Spacer(1, 0.2 * inch),
        Paragraph("What the prototype does", styles["Section"]),
        Paragraph(
            "The dashboard presents a Simple View for public-facing status and a Technical "
            "View for model inputs and limitations. An OpenStreetMap base map provides "
            "geographic context. Forecast mode requests precipitation forecast-model output "
            "from Open-Meteo for the Dwarka pilot coordinate. Demo mode uses fixed synthetic "
            "scenarios for interface demonstration.", styles["BodySmall"]),
        Paragraph(
            "When valid forecast input is available, a RandomForest surrogate estimates "
            "depth using a deterministic hydraulic formula and assumed or estimated drainage "
            "geometry. These values are unvalidated model estimates, not measured street "
            "water levels. The prototype does not connect to local radar, rain gauges, or "
            "water-level sensors.", styles["BodySmall"]),
        Paragraph("Data quality and system boundaries", styles["Section"]),
    ]

    rows = [
        [Paragraph("Component", styles["Cell"]), Paragraph("Current status", styles["Cell"])],
        [Paragraph("Weather input", styles["Cell"]), Paragraph("Open-Meteo forecast-model precipitation; not a local observation. Fifteen-minute values may be interpolated in this region.", styles["Cell"])],
        [Paragraph("Street depth", styles["Cell"]), Paragraph("Unvalidated model estimate. No independent local measured-depth validation set is available.", styles["Cell"])],
        [Paragraph("Map", styles["Cell"]), Paragraph("OpenStreetMap base map. It is not a flood or live-radar layer.", styles["Cell"])],
        [Paragraph("Historical reports", styles["Cell"]), Paragraph("Citation-listed records with mixed coordinate precision and source confidence; not verified sensor measurements.", styles["Cell"])],
        [Paragraph("Routes and alerts", styles["Cell"]), Paragraph("Route geometry may be shown with unverified nearby estimates. Routes are not safety-certified. Alert actions are local previews; no agency messages are sent.", styles["Cell"])],
    ]
    table = Table(rows, colWidths=[1.35 * inch, 5.75 * inch], repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dceef2")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#10233f")),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6fafb")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([
        table,
        Spacer(1, 0.12 * inch),
        Paragraph("Conditions for operational use", styles["Section"]),
        Paragraph(
            "Operational use would require authenticated local rainfall or radar feeds, "
            "water-level observations, a surveyed drainage inventory, independent event "
            "validation, and reviewed warning and routing procedures. Until those are "
            "available, check official local advisories and do not use this prototype to "
            "decide whether a road is safe.", styles["BodySmall"]),
        Paragraph("References", styles["Section"]),
        Paragraph(
            "Open-Meteo Forecast API documentation: https://open-meteo.com/en/docs<br/>"
            "OpenStreetMap attribution: https://www.openstreetmap.org/copyright<br/>"
            "Project data findings: DATA_PROVENANCE_AUDIT.md", styles["BodySmall"]),
    ])

    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        leftMargin=0.7 * inch, rightMargin=0.7 * inch,
        topMargin=0.65 * inch, bottomMargin=0.75 * inch,
        title="Urban Flood Dashboard Prototype - Dwarka Pilot",
        author="SIH 2026 project team",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    output = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "submission", "SIH_2026_Idea_Submission_Presentation.pdf",
    )
    generate_sih_pdf(output)
    print(f"Updated presentation: {output}")
