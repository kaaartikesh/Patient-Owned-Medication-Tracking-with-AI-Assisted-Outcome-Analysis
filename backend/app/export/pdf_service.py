import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable


def generate_patient_history_pdf(data: dict) -> bytes:
    """
    Generates a professional clinical PDF document summarizing patient medication history,
    active encounters, cross-doctor interaction alerts, and effectiveness logs.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Title"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1e293b"),
        alignment=0,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b"),
    )
    h2_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=14,
        spaceAfter=6,
    )
    cell_style = ParagraphStyle(
        "CellNormal",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1e293b"),
    )
    cell_bold = ParagraphStyle(
        "CellBold",
        parent=cell_style,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#0f172a"),
    )
    badge_high = ParagraphStyle(
        "BadgeHigh",
        parent=cell_style,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#dc2626"),
    )
    badge_critical = ParagraphStyle(
        "BadgeCrit",
        parent=cell_style,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#991b1b"),
    )

    story = []

    # Title & Header
    story.append(Paragraph("Patient Medication History & Interaction Report", title_style))
    story.append(
        Paragraph(
            f"Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} | Patient-Owned Healthcare System",
            subtitle_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3b82f6"), spaceBefore=8, spaceAfter=12))

    # Patient Details Block
    patient = data.get("patient", {})
    patient_info = [
        [
            Paragraph("<b>Full Name:</b>", cell_style),
            Paragraph(patient.get("full_name", "N/A"), cell_style),
            Paragraph("<b>Patient ID:</b>", cell_style),
            Paragraph(str(patient.get("id", "N/A")), cell_style),
        ],
        [
            Paragraph("<b>Email:</b>", cell_style),
            Paragraph(patient.get("email", "N/A"), cell_style),
            Paragraph("<b>Phone:</b>", cell_style),
            Paragraph(patient.get("phone_number") or "N/A", cell_style),
        ],
    ]
    p_table = Table(patient_info, colWidths=[70, 200, 70, 200])
    p_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(p_table)
    story.append(Spacer(1, 10))

    # Section 1: Cross-Doctor Drug Interaction Flags (Alert Box)
    flags = data.get("interaction_flags", [])
    if flags:
        story.append(Paragraph("⚠️ Clinical Drug-Drug Interaction Alerts", h2_style))
        flag_data = [
            [
                Paragraph("Severity", cell_bold),
                Paragraph("Medication A", cell_bold),
                Paragraph("Medication B", cell_bold),
                Paragraph("Clinical Description", cell_bold),
                Paragraph("Status", cell_bold),
            ]
        ]
        for f in flags:
            sev = f.get("severity", "FLAGGED")
            sev_style = badge_critical if sev in ("CRITICAL", "HIGH") else cell_bold
            flag_data.append(
                [
                    Paragraph(sev, sev_style),
                    Paragraph(f.get("medication_a_name", "N/A"), cell_style),
                    Paragraph(f.get("medication_b_name", "N/A"), cell_style),
                    Paragraph(f.get("description", ""), cell_style),
                    Paragraph(f.get("status", "FLAGGED"), cell_style),
                ]
            )
        f_table = Table(flag_data, colWidths=[65, 95, 95, 220, 65])
        f_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fee2e2")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#ef4444")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#fecaca")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(f_table)
        story.append(Spacer(1, 10))

    # Section 2: Medication History
    meds = data.get("medications", [])
    story.append(Paragraph("Medication Regimen & Prescription History", h2_style))
    if meds:
        med_data = [
            [
                Paragraph("Medication", cell_bold),
                Paragraph("Dosage", cell_bold),
                Paragraph("Frequency", cell_bold),
                Paragraph("Prescriber", cell_bold),
                Paragraph("Start Date", cell_bold),
                Paragraph("Status", cell_bold),
            ]
        ]
        for m in meds:
            status_text = "Active" if m.get("is_active") else "Discontinued"
            prescriber = m.get("doctor_name") or ("Patient Self-Log" if not m.get("doctor_id") else "Doctor")
            start_d = m.get("start_date")[:10] if m.get("start_date") else "N/A"
            med_data.append(
                [
                    Paragraph(m.get("medication_name", ""), cell_bold),
                    Paragraph(m.get("dosage") or "-", cell_style),
                    Paragraph(m.get("frequency") or "-", cell_style),
                    Paragraph(prescriber, cell_style),
                    Paragraph(start_d, cell_style),
                    Paragraph(status_text, cell_style),
                ]
            )
        m_table = Table(med_data, colWidths=[120, 75, 85, 120, 70, 70])
        m_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ]
            )
        )
        story.append(m_table)
    else:
        story.append(Paragraph("No medication records found.", cell_style))

    story.append(Spacer(1, 10))

    # Section 3: Clinical Encounters
    encounters = data.get("encounters", [])
    story.append(Paragraph("Doctor Encounters (Time-Limited Write Windows)", h2_style))
    if encounters:
        enc_data = [
            [
                Paragraph("Doctor", cell_bold),
                Paragraph("Started At", cell_bold),
                Paragraph("Expires At", cell_bold),
                Paragraph("Status", cell_bold),
                Paragraph("Notes", cell_bold),
            ]
        ]
        for e in encounters:
            start_s = e.get("started_at")[:16].replace("T", " ") if e.get("started_at") else "-"
            exp_s = e.get("expires_at")[:16].replace("T", " ") if e.get("expires_at") else "-"
            enc_data.append(
                [
                    Paragraph(e.get("doctor_name") or "Doctor", cell_style),
                    Paragraph(start_s, cell_style),
                    Paragraph(exp_s, cell_style),
                    Paragraph(e.get("status", ""), cell_style),
                    Paragraph(e.get("notes") or "-", cell_style),
                ]
            )
        e_table = Table(enc_data, colWidths=[120, 95, 95, 60, 170])
        e_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ]
            )
        )
        story.append(e_table)
    else:
        story.append(Paragraph("No encounter records recorded.", cell_style))

    story.append(Spacer(1, 10))

    # Section 4: Patient Effectiveness & Side Effects Logs
    logs = data.get("effectiveness_logs", [])
    story.append(Paragraph("Patient-Reported Outcomes & Effectiveness", h2_style))
    if logs:
        eff_data = [
            [
                Paragraph("Medication", cell_bold),
                Paragraph("Rating", cell_bold),
                Paragraph("Reported Side Effects", cell_bold),
                Paragraph("Logged Date", cell_bold),
            ]
        ]
        for l in logs:
            stars = "★" * int(l.get("rating", 0)) + "☆" * (5 - int(l.get("rating", 0)))
            eff_data.append(
                [
                    Paragraph(l.get("medication_name") or "Medication", cell_style),
                    Paragraph(f"{stars} ({l.get('rating')}/5)", cell_style),
                    Paragraph(l.get("side_effects") or "None reported", cell_style),
                    Paragraph(l.get("logged_at")[:10] if l.get("logged_at") else "-", cell_style),
                ]
            )
        eff_table = Table(eff_data, colWidths=[130, 80, 230, 100])
        eff_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ]
            )
        )
        story.append(eff_table)
    else:
        story.append(Paragraph("No patient outcome logs submitted yet.", cell_style))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
