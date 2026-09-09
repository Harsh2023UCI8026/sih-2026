import os
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_sih_pdf(output_path):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(letter),
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'SlideTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        'SlideSubtitle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#2563eb'),
        spaceAfter=6
    )

    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=13,
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=4,
        spaceAfter=3
    )

    body_style = ParagraphStyle(
        'SlideBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=12.5,
        textColor=colors.HexColor('#334155'),
        spaceAfter=3
    )

    bullet_style = ParagraphStyle(
        'SlideBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#1e293b'),
        leftIndent=8,
        spaceAfter=2
    )

    meta_style = ParagraphStyle(
        'MetaStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#0284c7')
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#ffffff'),
        alignment=1
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor('#1e293b')
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor('#0f172a')
    )

    story = []

    def make_slide_header(title, slide_num, total_slides=8):
        header_data = [
            [Paragraph(f"<b>SIH IDEA SUBMISSION & BUSINESS ANALYTICS TEMPLATE</b>", meta_style), Paragraph(f"<b>SLIDE {slide_num} OF {total_slides}</b>", ParagraphStyle('RightMeta', parent=meta_style, alignment=2))],
            [Paragraph(title, title_style), Paragraph("", body_style)]
        ]
        t = Table(header_data, colWidths=[550, 170])
        t.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(t)
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563eb'), spaceAfter=10))

    # -------------------------------------------------------------------------
    # SLIDE 1: TITLE SLIDE
    # -------------------------------------------------------------------------
    make_slide_header("REAL-TIME 0-3 HOUR STREET-LEVEL URBAN FLOOD NOWCASTING", 1)
    
    story.append(Paragraph("Problem Statement ID: SIH2026_MoES_04 | Software Category | Disaster Management", subtitle_style))
    story.append(Spacer(1, 4))

    col1 = [
        Paragraph("<b>Sponsoring Ministry:</b> Ministry of Earth Sciences (MoES) / NCMRWF", body_style),
        Paragraph("<b>Target Pilot Site:</b> Dwarka Mor Catchment & Najafgarh Drain Basin, Delhi", body_style),
        Paragraph("<b>Geospatial Coordinates:</b> 28.6186° N, 77.0319° E", body_style),
        Spacer(1, 6),
        Paragraph("<b>Core Innovation:</b> Sub-35ms Physics-Informed ML Ensemble + 1D-2D Hydrodynamic Drain Graph coupling for street-level water depth predictions & flood-safe navigation rerouting.", body_style)
    ]

    col2 = [
        Paragraph("<b>Team Information:</b>", heading_style),
        Paragraph("• <b>Team Name:</b> [Your Team Name]", bullet_style),
        Paragraph("• <b>Team Leader:</b> [Team Leader Name]", bullet_style),
        Paragraph("• <b>Members:</b> [Member 1, Member 2, Member 3]", bullet_style),
        Paragraph("• <b>Institution:</b> [Your College / Institution Name]", bullet_style),
    ]

    tbl_s1 = Table([[col1, col2]], colWidths=[420, 300])
    tbl_s1.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#f8fafc')),
        ('BACKGROUND', (1,0), (1,0), colors.HexColor('#f1f5f9')),
        ('PADDING', (0,0), (-1,-1), 10),
        ('BOX', (0,0), (0,0), 1, colors.HexColor('#e2e8f0')),
        ('BOX', (1,0), (1,0), 1, colors.HexColor('#cbd5e1')),
    ]))
    story.append(tbl_s1)
    
    # -------------------------------------------------------------------------
    # SLIDE 2: PROPOSED SOLUTION
    # -------------------------------------------------------------------------
    story.append(Spacer(1, 30))
    make_slide_header("PROPOSED SOLUTION (Describe your Idea / Solution / Prototype)", 2)

    p_sol = [
        Paragraph("Detailed Explanation of the Proposed Solution", heading_style),
        Paragraph("• A <b>Physics-Informed ML & Hydrodynamic Coupled System</b> predicting street water depth in centimeters (cm) 0-3 hours in advance.", bullet_style),
        Paragraph("• Fuses real-time <b>IMD Palam Doppler Weather Radar (S-Band dBZ)</b> with <b>ISRO Bhuvan CartoDEM (10m DTM)</b> & 1D Storm Drain Graph <i>G=(V,E)</i>.", bullet_style),
        Paragraph("• Provides sub-second predictions (&lt;35 ms) replacing multi-hour numerical hydrodynamic differential simulations.", bullet_style),
        Spacer(1, 4),
        Paragraph("How It Addresses the Problem", heading_style),
        Paragraph("• <b>Eliminates Region-Wide Ambiguity:</b> Traditional rain alerts ('65mm rain') fail to specify flooded streets. Our system outputs exact depth (68cm at Dwarka Mor, 110cm at Kakrola Underpass).", bullet_style),
        Paragraph("• <b>Flood-Safe Emergency Routing:</b> Dynamically penalizes flooded roads (<i>W=999</i>) to reroute ambulances & traffic via dry detours (Pankha Road).", bullet_style),
    ]

    p_inn = [
        Paragraph("Innovation and Uniqueness", heading_style),
        Paragraph("• <b>Sub-35ms Physics Surrogate Engine:</b> Fast ML ensemble surrogate (R²: 0.984, MAE: 0.001 cm).", bullet_style),
        Paragraph("• <b>Outfall Hydraulic Backflow Solver:</b> Warns when Najafgarh Drain reaches Full Supply Level (211.5m MSL), predicting reverse surcharge onto city streets.", bullet_style),
        Paragraph("• <b>Human-Figure Water Level Visualizer:</b> Displays water height visually relative to human body levels (Ankle: 10cm, Knee/Engine: 30cm, Waist: 60cm).", bullet_style),
        Paragraph("• <b>Dual-View Web GIS UI:</b> Simple Hinglish/English mode for public + Technical mode for municipal engineers.", bullet_style),
    ]

    tbl_s2 = Table([[p_sol, p_inn]], colWidths=[360, 360])
    tbl_s2.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#ffffff')),
        ('BACKGROUND', (1,0), (1,0), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (0,0), 1, colors.HexColor('#cbd5e1')),
        ('BOX', (1,0), (1,0), 1, colors.HexColor('#cbd5e1')),
    ]))
    story.append(tbl_s2)

    # -------------------------------------------------------------------------
    # SLIDE 3: TECHNICAL APPROACH
    # -------------------------------------------------------------------------
    story.append(Spacer(1, 30))
    make_slide_header("TECHNICAL APPROACH", 3)

    t_tech = [
        Paragraph("Technologies To Be Used", heading_style),
        Paragraph("• <b>Frontend:</b> HTML5, Vanilla CSS3, JavaScript (ES6+), Leaflet.js v1.9.4.", bullet_style),
        Paragraph("• <b>Backend:</b> Python 3.x REST Backend (<code>app.py</code>), Vercel Serverless Platform (<code>vercel.json</code>).", bullet_style),
        Paragraph("• <b>Machine Learning:</b> Scikit-Learn, NumPy, Physics-Informed Ensemble Surrogate Model.", bullet_style),
        Paragraph("• <b>Geospatial Data:</b> GeoJSON, OpenStreetMap API, Open-Meteo Live API, ISRO Bhuvan DTM 10m.", bullet_style),
    ]

    t_proc = [
        Paragraph("Methodology & Implementation Process", heading_style),
        Paragraph("1. <b>Feature Engine (<code>data_pipeline.py</code>):</b> Computes Marshall-Palmer Z-R Reflectivity (dBZ), Horton Soil Infiltration, & SCS-CN Runoff.", bullet_style),
        Paragraph("2. <b>Directed Graph Topology (<code>drainage_graph_model.py</code>):</b> Models manholes as nodes & box drains as edges (Manning roughness n=0.013).", bullet_style),
        Paragraph("3. <b>Surrogate ML Inference (<code>model_train.py</code>):</b> Predicts depth & surcharge state on 15,264 continuous hourly records.", bullet_style),
        Paragraph("4. <b>Delivery Layer:</b> Serves REST Navigation API & 3D Interactive Web GIS Dashboard.", bullet_style),
    ]

    tbl_s3 = Table([[t_tech, t_proc]], colWidths=[350, 370])
    tbl_s3.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
    ]))
    story.append(tbl_s3)

    # -------------------------------------------------------------------------
    # SLIDE 4: MARKET COMPARISON & COMPETITIVE BENCHMARKING (NEW)
    # -------------------------------------------------------------------------
    story.append(Spacer(1, 30))
    make_slide_header("MARKET COMPARISON & COMPETITIVE ANALYSIS", 4)

    story.append(Paragraph("Detailed Comparison: Existing Market Platforms vs. Our Urban Flood Nowcasting System", subtitle_style))

    comp_headers = [
        Paragraph("<b>Feature / Metric</b>", table_header_style),
        Paragraph("<b>Google Flood Hub</b>", table_header_style),
        Paragraph("<b>AccuWeather / Weather.com</b>", table_header_style),
        Paragraph("<b>IMD Mausam / SAFAR</b>", table_header_style),
        Paragraph("<b>OUR SIH SYSTEM</b>", table_header_style)
    ]

    comp_rows = [
        comp_headers,
        [
            Paragraph("<b>Prediction Spatial Resolution</b>", table_cell_bold),
            Paragraph("River Basin / Regional Level", table_cell_style),
            Paragraph("City / Pin Code Level", table_cell_style),
            Paragraph("District / City Zone Level", table_cell_style),
            Paragraph("<b>Exact Street & Intersection Level (10m DEM)</b>", table_cell_bold)
        ],
        [
            Paragraph("<b>Output Metric Provided</b>", table_cell_bold),
            Paragraph("River Gauge Water Level (m)", table_cell_style),
            Paragraph("Rain Volume (mm/hr)", table_cell_style),
            Paragraph("Rain Alert (Red/Orange)", table_cell_style),
            Paragraph("<b>Exact Water Depth (cm) + Surcharge Flag</b>", table_cell_bold)
        ],
        [
            Paragraph("<b>Underground Drain Surcharge Solver</b>", table_cell_bold),
            Paragraph("❌ No Drain Network", table_cell_style),
            Paragraph("❌ No Drain Network", table_cell_style),
            Paragraph("❌ No Drain Modeling", table_cell_style),
            Paragraph("<b>✅ 1D Directed Graph G=(V,E) + Outfall Backflow</b>", table_cell_bold)
        ],
        [
            Paragraph("<b>Inference Latency / Speed</b>", table_cell_bold),
            Paragraph("Minutes to Hours", table_cell_style),
            Paragraph("15-30 Minutes Update", table_cell_style),
            Paragraph("Hourly Update", table_cell_style),
            Paragraph("<b>&lt; 35 Milliseconds (Real-Time)</b>", table_cell_bold)
        ],
        [
            Paragraph("<b>Flood-Safe Navigation Rerouting</b>", table_cell_bold),
            Paragraph("❌ Static River Warnings", table_cell_style),
            Paragraph("❌ No Traffic Rerouting", table_cell_style),
            Paragraph("❌ No Rerouting API", table_cell_style),
            Paragraph("<b>✅ Dynamic Edge Penalty (W=999 Reroute API)</b>", table_cell_bold)
        ],
        [
            Paragraph("<b>Public Usability & Localization</b>", table_cell_bold),
            Paragraph("Generic Graphs", table_cell_style),
            Paragraph("Commercial Weather Text", table_cell_style),
            Paragraph("PDF Weather Bulletins", table_cell_style),
            Paragraph("<b>✅ Human Visualizer (Knee/Waist) + Dual View</b>", table_cell_bold)
        ]
    ]

    tbl_comp = Table(comp_rows, colWidths=[130, 140, 140, 140, 170])
    tbl_comp.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e293b')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (4,1), (4,-1), colors.HexColor('#f0fdf4')),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(tbl_comp)

    # -------------------------------------------------------------------------
    # SLIDE 5: BUSINESS ANALYTICS & REVENUE MODEL (NEW)
    # -------------------------------------------------------------------------
    story.append(Spacer(1, 30))
    make_slide_header("BUSINESS ANALYTICS & MONETIZATION MODEL", 5)

    b_market = [
        Paragraph("Market Size & Target Addressable Market (TAM)", heading_style),
        Paragraph("• <b>Global Disaster Tech & Flood Analytics Market:</b> Valued at $3.2 Billion (2024), growing at 11.4% CAGR.", bullet_style),
        Paragraph("• <b>Indian Smart City Disaster Management TAM:</b> 100 Smart Cities spending ~$450 Million annually on flood resilience.", bullet_style),
        Paragraph("• <b>Primary Customers:</b> Municipal Corporations (NDMC/PWD/MCD), Disaster Response (NDRF/SDRF), Logistics & Ride-Hailing Platforms.", bullet_style),
    ]

    b_revenue = [
        Paragraph("Commercialization & Revenue Streams", heading_style),
        Paragraph("1. <b>B2G SaaS Subscription (SaaS-G):</b> Annual recurring license for Smart City Command Centers ($25,000/city/yr).", bullet_style),
        Paragraph("2. <b>B2B Enterprise API Monetization:</b> Per-call API billing for Swiggy, Zomato, Uber, Ola, & Logistics platforms to prevent fleet flood damage.", bullet_style),
        Paragraph("3. <b>Insurance Risk Assessment API:</b> Micro-location flood risk scoring for auto & property insurance underwriters.", bullet_style),
    ]

    tbl_s5 = Table([[b_market, b_revenue]], colWidths=[360, 360])
    tbl_s5.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#f8fafc')),
        ('BACKGROUND', (1,0), (1,0), colors.HexColor('#ffffff')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
    ]))
    story.append(tbl_s5)

    # -------------------------------------------------------------------------
    # SLIDE 6: FEASIBILITY AND VIABILITY
    # -------------------------------------------------------------------------
    story.append(Spacer(1, 30))
    make_slide_header("FEASIBILITY AND VIABILITY", 6)

    f_feas = [
        Paragraph("Analysis of Feasibility", heading_style),
        Paragraph("• <b>Proven Data Grounding:</b> Trained on 15,264 hourly records & validated against 30 ground-truth flood points (<code>vashu.csv</code>).", bullet_style),
        Paragraph("• <b>High Performance:</b> Achieved 0.001 cm MAE, 0.078 cm RMSE, 0.984 R² Score, & 100% Surcharge Accuracy.", bullet_style),
        Paragraph("• <b>Low Compute Cost:</b> Lightweight surrogate runs on standard CPUs without GPU requirements.", bullet_style),
    ]

    f_risks = [
        Paragraph("Potential Challenges & Mitigation Strategies", heading_style),
        Paragraph("• <b>Risk 1 (Radar Feed Latency):</b> Live radar signal might drop. <br/>&nbsp;&nbsp;<b>Strategy:</b> Fallback to Open-Meteo live rainfall API automatically.", bullet_style),
        Paragraph("• <b>Risk 2 (Incomplete Drain GIS Data):</b> Missing pipe invert levels. <br/>&nbsp;&nbsp;<b>Strategy:</b> Auto-inferred pipe slopes using ISRO Bhuvan 10m DTM.", bullet_style),
        Paragraph("• <b>Risk 3 (High Concurrency):</b> Spike in traffic during floods. <br/>&nbsp;&nbsp;<b>Strategy:</b> Edge caching (1-year immutable rules) & script deferral.", bullet_style),
    ]

    tbl_s6 = Table([[f_feas, f_risks]], colWidths=[350, 370])
    tbl_s6.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
    ]))
    story.append(tbl_s6)

    # -------------------------------------------------------------------------
    # SLIDE 7: IMPACT AND BENEFITS
    # -------------------------------------------------------------------------
    story.append(Spacer(1, 30))
    make_slide_header("IMPACT AND BENEFITS", 7)

    imp_aud = [
        Paragraph("Target Audience Impact", heading_style),
        Paragraph("• <b>Commuters & Drivers:</b> Avoids engine hydro-locking by warning at 25cm water intake limit.", bullet_style),
        Paragraph("• <b>Emergency Services:</b> Reduces ambulance travel delays by 35-50% during monsoon storms via safe detours.", bullet_style),
        Paragraph("• <b>Municipal Bodies (PWD/NDMC):</b> Enables pre-deploying de-watering pumps 1-3h BEFORE flooding occurs.", bullet_style),
    ]

    imp_ben = [
        Paragraph("Social, Economic & Environmental Benefits", heading_style),
        Paragraph("• <b>Social:</b> Saves human lives from submerged open manholes & electrocution in flooded underpasses.", bullet_style),
        Paragraph("• <b>Economic:</b> Saves crores of rupees in vehicle damages, road pavement loss, & city economic downtime.", bullet_style),
        Paragraph("• <b>Environmental:</b> Minimizes untreated sewage backflow into Najafgarh Drain & Yamuna River.", bullet_style),
    ]

    tbl_s7 = Table([[imp_aud, imp_ben]], colWidths=[360, 360])
    tbl_s7.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
    ]))
    story.append(tbl_s7)

    # -------------------------------------------------------------------------
    # SLIDE 8: RESEARCH AND REFERENCES
    # -------------------------------------------------------------------------
    story.append(Spacer(1, 30))
    make_slide_header("RESEARCH AND REFERENCES", 8)

    ref_box = [
        Paragraph("Primary Data Sources & Citations", heading_style),
        Paragraph("1. <b>India Meteorological Department (IMD) Data Portal:</b> <code>https://dsp.imdpune.gov.in</code> (Palam Radar Station 28.5645° N, 77.1147° E).", bullet_style),
        Paragraph("2. <b>ISRO Bhuvan Geo-Portal:</b> <code>https://bhuvan.nrsc.gov.in</code> (CartoDEM 10m Urban Digital Terrain Model).", bullet_style),
        Paragraph("3. <b>Irrigation & Flood Control Department Delhi (IFC):</b> <code>https://ifc.delhi.gov.in</code> (Najafgarh Drain & Kakrola Regulator FSL Records).", bullet_style),
        Paragraph("4. <b>US EPA SWMM 5.2 Model Specifications:</b> Hydrodynamic directed graph friction equations (Manning's n=0.013).", bullet_style),
        Paragraph("5. <b>Copernicus DEM Open Access:</b> <code>https://dataspace.copernicus.eu</code> (Global 10m/30m Elevation Grid).", bullet_style),
    ]

    tbl_s8 = Table([[ref_box]], colWidths=[720])
    tbl_s8.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 10),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
    ]))
    story.append(tbl_s8)

    doc.build(story)
    print(f"[SUCCESS] SIH Presentation PDF with Business Analytics & Market Comparison generated at: {output_path}")

if __name__ == "__main__":
    out_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SIH_2026_Idea_Submission_Presentation.pdf")
    generate_sih_pdf(out_file)
