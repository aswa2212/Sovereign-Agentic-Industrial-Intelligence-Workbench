"""
SIH26117 — Controlled Demonstration Industrial Knowledge Corpus Generator
Generates a controlled set of 10 multi-page synthetic industrial engineering PDF documents
with structured tables, section headings, and explicit synthetic demonstration disclaimers.

Corpus Target: data/raw/knowledge/
Source Type: synthetic_demo
"""

import sys
from pathlib import Path
from typing import List, Tuple

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
)

DISCLAIMER_TEXT = (
    "DEMONSTRATION SYNTHETIC CORPUS FOR SIH26117 — NOT OFFICIAL MRPL POLICY. "
    "FOR SOFTWARE PIPELINE VERIFICATION AND DEMONSTRATION PURPOSES ONLY."
)


def create_pdf(
    output_path: Path,
    title: str,
    doc_id: str,
    sections: List[Tuple[str, List[str]]],
    tables: List[Tuple[str, List[List[str]]]] = None,
    equipment_ids: List[str] = None,
):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#001440'),
        spaceAfter=6,
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#708090'),
        spaceAfter=10,
    )
    
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#C0392B'),
        spaceAfter=12,
    )
    
    heading_style = ParagraphStyle(
        'SecHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#001440'),
        spaceBefore=10,
        spaceAfter=4,
    )
    
    body_style = ParagraphStyle(
        'SecBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#2C3E50'),
        spaceAfter=6,
    )

    table_header_style = ParagraphStyle(
        'TblHdr',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white,
    )
    
    table_cell_style = ParagraphStyle(
        'TblCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#2C3E50'),
    )

    elements = []

    # Title & Metadata
    elements.append(Paragraph(title, title_style))
    eq_str = f" | Equipment Tag: {', '.join(equipment_ids)}" if equipment_ids else ""
    elements.append(Paragraph(f"Document Code: {doc_id} | Revision: 02 | Source Type: synthetic_demo{eq_str}", subtitle_style))
    elements.append(Paragraph(f"[{DISCLAIMER_TEXT}]", disclaimer_style))
    elements.append(Spacer(1, 8))

    # Add Sections
    for sec_title, paragraphs in sections:
        elements.append(Paragraph(sec_title, heading_style))
        for p in paragraphs:
            elements.append(Paragraph(p, body_style))
        elements.append(Spacer(1, 6))

    # Add Tables if any
    if tables:
        for tbl_title, raw_table_data in tables:
            elements.append(Paragraph(tbl_title, heading_style))
            
            formatted_data = []
            for r_idx, row in enumerate(raw_table_data):
                formatted_row = []
                for cell in row:
                    style = table_header_style if r_idx == 0 else table_cell_style
                    formatted_row.append(Paragraph(str(cell), style))
                formatted_data.append(formatted_row)

            col_widths = [110] + [(500 - 110) // (len(raw_table_data[0]) - 1)] * (len(raw_table_data[0]) - 1)
            t = Table(formatted_data, colWidths=col_widths)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#001440')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F8F9FA'), colors.white]),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 10))

    # Page 2 Footer Note & Signoff
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Controlled Demonstration Asset Integrity Record — Mangalore Demonstration Facility", subtitle_style))

    doc.build(elements)
    print(f"Generated: {output_path.name} ({doc_id})")


def generate_all_documents(target_dir: Path):
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. 01_C101_Inspection_Procedure.pdf
    create_pdf(
        target_dir / "01_C101_Inspection_Procedure.pdf",
        title="C-101 Atmospheric Distillation Column Ultrasonic Inspection Procedure",
        doc_id="DEMO-C101-PRO-001",
        equipment_ids=["C-101"],
        sections=[
            ("1.0 Purpose and Scope", [
                "This standard procedure specifies requirements for ultrasonic thickness gauging (UTG) of the Atmospheric Distillation Column C-101.",
                "It covers shell rings, nozzles, tray support rings, and critical vapor overhead piping junctions for crude distillation units.",
                "All examination protocols follow API 510 and ASME Section V non-destructive testing requirements.",
            ]),
            ("2.0 Inspection Methodology and Transducer Calibration", [
                "Ultrasonic thickness measurements must be performed using a calibrated dual-element 5.0 MHz transducer with an accuracy of +/- 0.05 mm.",
                "Calibration shall be verified against an ASTM A516 Grade 70 step wedge with verified thickness standards between 2.5 mm and 25.0 mm before and after each inspection shift.",
                "High-temperature couplant is required when surface skin temperatures exceed 60 degrees Celsius.",
            ]),
            ("3.0 CML Grid Allocation", [
                "Four mandatory Corrosion Monitoring Locations (CML) are permanently marked on Column C-101:",
                "CML-1 is situated at Shell Ring 1 Top Head Nozzle.",
                "CML-2 is positioned at the Reflux Inlet Nozzle transition.",
                "CML-3 covers Tray 12 Vapor Zone where localized organic acid attack is prevalent.",
                "CML-4 monitors the Overhead Condenser Vapor Line Elbow E-02, which experiences the highest recorded impingement velocity.",
            ]),
            ("4.0 Acceptance Standards and Signoff", [
                "Measured thicknesses must be checked against the demonstration engineering retirement threshold of 8.0 mm for C-101 shell components.",
                "Any thickness reading below 8.0 mm warrants immediate fail-closed notification, isolation tagging, and formal non-conformance review.",
            ]),
        ],
    )

    # 2. 02_Corrosion_Assessment_Guideline.pdf
    create_pdf(
        target_dir / "02_Corrosion_Assessment_Guideline.pdf",
        title="Refinery Process Equipment Corrosion Assessment & Monitoring Guideline",
        doc_id="DEMO-CORR-GDL-002",
        sections=[
            ("1.0 Corrosion Mechanisms in Crude Processing", [
                "Atmospheric distillation columns and overhead lines are susceptible to several active damage mechanisms including hydrochloric acid (HCl) dew-point corrosion, ammonium chloride salt deposition, and naphthenic acid attack at elevated temperatures.",
                "In crude column overhead condensers, water vapor condensation creates an acidic aqueous phase capable of producing localized thinning rates in excess of 0.35 mm per year if chemical neutralization is interrupted.",
            ]),
            ("2.0 Corrosion Allowance Monitoring", [
                "Design corrosion allowance must be tracked continuously across turnaround cycles.",
                "Equipment retirement criteria mandate that when accumulated metal loss consumes greater than 60 percent of the original corrosion allowance, the inspection frequency must be doubled.",
            ]),
            ("3.0 Chemical Neutralization & Wash Water Guidelines", [
                "Continuous injection of neutralizing amine and filming inhibitor must be maintained upstream of condenser inlets.",
                "Overhead accumulator boot water pH must be maintained strictly between 5.8 and 6.8 to mitigate acid attack.",
            ]),
        ],
    )

    # 3. 03_Thickness_Monitoring_Procedure.pdf
    create_pdf(
        target_dir / "03_Thickness_Monitoring_Procedure.pdf",
        title="Ultrasonic Thickness Gauging (UTG) & Continuous Monitoring Procedure",
        doc_id="DEMO-UTG-PRO-003",
        sections=[
            ("1.0 Ultrasonic Gauging Standards", [
                "This technical procedure outlines precise measurement requirements for digital ultrasonic thickness gauging on pressure vessels, piping, and distillation columns.",
                "The inspection Division Lead Engineer shall ensure all UTG data complies with ASME B31.3 and API 570 inspection standards.",
            ]),
            ("2.0 Instrument Precision & Surface Prep", [
                "Surface preparation must achieve SA 2.5 cleanliness using mechanical wire brushing to eliminate loose scale, paint blisters, and external rust.",
                "Acoustic velocity is standardized at 5900 meters per second for carbon steel components at ambient temperature.",
                "Measurement error tolerance is specified at +/- 0.1 mm. Three readings must be taken per CML point and the minimum thickness logged as the representative value.",
            ]),
        ],
    )

    # 4. 04_Inspection_Interval_Guideline.pdf
    create_pdf(
        target_dir / "04_Inspection_Interval_Guideline.pdf",
        title="Pressure Vessel and Column Inspection Interval Determination Guideline",
        doc_id="DEMO-INTV-GDL-004",
        sections=[
            ("1.0 Inspection Interval Calculation (Half-Life Principle)", [
                "Under API 510 and API 570 guidelines, the maximum allowable inspection interval for operating process equipment is determined as half the remaining service life (Remaining Life / 2.0).",
                "However, the demonstration guidance stipulates a maximum ceiling of 5.0 years between consecutive ultrasonic inspections for crude distillation units.",
            ]),
            ("2.0 Review Triggers and Accelerated Scheduling", [
                "When the calculated remaining service life of any CML drops below 4.0 years, the inspection interval is automatically reduced to annual review.",
                "If the calculated remaining service life falls below 2.0 years, mandatory engineering assessment for replacement or weld overlay must be initiated within 90 days.",
            ]),
        ],
    )

    # 5. 05_C101_Equipment_Record.pdf
    create_pdf(
        target_dir / "05_C101_Equipment_Record.pdf",
        title="Equipment Master Record: C-101 Atmospheric Distillation Column",
        doc_id="DEMO-C101-REC-005",
        equipment_ids=["C-101"],
        sections=[
            ("1.0 Equipment Identification", [
                "Equipment Tag: C-101",
                "Equipment Description: Atmospheric Crude Distillation Column",
                "Operating Unit: Crude Distillation Unit 1 (CDU-1)",
                "Commissioning Date: March 2011 | Design Life: 30 Years",
                "Service Fluid: Heavy Desalted Crude Oil and Vapor Distillates",
            ]),
            ("2.0 Mechanical Design Parameters", [
                "Shell Material of Construction: ASTM A516 Grade 70 Carbon Steel",
                "Nozzle Piping Material: ASTM A106 Grade B Seamless Carbon Steel",
                "Design Pressure: 3.5 bar(g) (350 kPa) | Operating Pressure: 1.8 bar(g)",
                "Design Temperature: 350 degrees C | Operating Overhead Temperature: 125 degrees C",
                "Column Dimensions: Height = 45.0 meters, Internal Diameter = 4200 mm",
            ]),
            ("3.0 Baseline Dimensions and Corrosion Allowance", [
                "Original Nominal Wall Thickness: 12.00 mm",
                "Design Corrosion Allowance: 3.00 mm",
                "Minimum Structural Thickness Requirement: 5.00 mm",
                "Configured Minimum Retirement Thickness (t_min): 8.00 mm",
            ]),
        ],
    )

    # 6. 06_C101_Thickness_History.pdf
    create_pdf(
        target_dir / "06_C101_Thickness_History.pdf",
        title="C-101 Historical Ultrasonic Thickness Survey & Gauging Log",
        doc_id="DEMO-C101-HIS-006",
        equipment_ids=["C-101"],
        sections=[
            ("1.0 Ultrasonic Survey Overview", [
                "This document provides historical ultrasonic thickness gauging survey results for Atmospheric Distillation Column C-101.",
                "Baseline baseline nominal thickness was established at 12.00 mm during commissioning in March 2021.",
                "The most recent comprehensive 5-year turnaround survey was conducted on March 15, 2026.",
            ]),
            ("2.0 Significant Findings", [
                "The lowest measured thickness across Column C-101 was recorded at CML-4 (Overhead Condenser Vapor Nozzle N1 / Elbow) at 10.10 mm.",
                "Over the 5.0-year elapsed operating interval, CML-4 experienced a total metal thickness loss of 1.90 mm (representing an average corrosion rate of 0.38 mm/year).",
                "All readings currently remain above the demonstration retirement limit of 8.00 mm.",
            ]),
        ],
        tables=[
            ("C-101 Ultrasonic Thickness Gauging Log (2021-2026)", [
                ["CML Tag", "Inspection Location", "Baseline (2021)", "Current (2026)", "Loss (mm)", "Rate (mm/yr)"],
                ["CML-1", "Shell Ring 1 (Top Head)", "12.00 mm", "11.45 mm", "0.55 mm", "0.11 mm/yr"],
                ["CML-2", "Reflux Inlet Nozzle", "12.00 mm", "10.90 mm", "1.10 mm", "0.22 mm/yr"],
                ["CML-3", "Tray 12 Vapor Zone", "12.00 mm", "10.40 mm", "1.60 mm", "0.32 mm/yr"],
                ["CML-4", "Overhead Condenser Nozzle N1", "12.00 mm", "10.10 mm", "1.90 mm", "0.38 mm/yr"],
            ]),
        ],
    )

    # 7. 07_Corrosion_Rate_Calculation_Guide.pdf
    create_pdf(
        target_dir / "07_Corrosion_Rate_Calculation_Guide.pdf",
        title="Corrosion Rate and Remaining Service Life Calculation Guide",
        doc_id="DEMO-CALC-GDL-007",
        sections=[
            ("1.0 Standard Corrosion Rate Calculation Formula", [
                "Corrosion rate is calculated deterministically as the difference between initial baseline thickness and current measured thickness divided by elapsed operational time:",
                "Formula: Corrosion Rate = (t_initial - t_actual) / Elapsed Time (years)",
                "Units: Corrosion rate must strictly be expressed in millimeters per year (mm/year).",
                "Example: With t_initial = 12.0 mm, t_actual = 10.1 mm, and elapsed time = 5.0 years: Corrosion Rate = (12.0 - 10.1) / 5.0 = 0.38 mm/year.",
            ]),
            ("2.0 Remaining Service Life Estimation Formula", [
                "Remaining service life is calculated by dividing remaining usable metal thickness above minimum allowable retirement limit by the corrosion rate:",
                "Formula: Remaining Life = (t_actual - t_min) / Corrosion Rate",
                "Units: Remaining life is expressed in years.",
                "Example: With t_actual = 10.1 mm, t_min = 8.0 mm, and Corrosion Rate = 0.38 mm/year: Remaining Life = (10.1 - 8.0) / 0.38 = 5.53 years.",
            ]),
            ("3.0 Validation and Quality Control", [
                "All calculations must undergo automated validation before inclusion in formal deliverables.",
                "A negative corrosion rate is considered physically impossible and indicates an instrument calibration error or data recording defect.",
            ]),
        ],
    )

    # 8. 08_Equipment_Retirement_Criteria.pdf
    create_pdf(
        target_dir / "08_Equipment_Retirement_Criteria.pdf",
        title="Process Vessel & Column Retirement Thresholds & Minimum Allowable Thickness Criteria",
        doc_id="DEMO-RETR-CRT-008",
        equipment_ids=["C-101"],
        sections=[
            ("1.0 Demonstration Minimum Thickness Criteria", [
                "This guideline specifies minimum allowable wall thickness retirement criteria for distillation equipment.",
                "For Column C-101 (Atmospheric Distillation Column overheads), the demonstration configuration threshold specifies a minimum allowable retirement thickness of 8.0 mm.",
                "For standard Class 150 process piping (ASTM A106 Grade B), the minimum allowable retirement threshold is 3.2 mm.",
            ]),
            ("2.0 Mandatory Fail-Closed Policy", [
                "Whenever measured ultrasonic thickness falls below the configured retirement threshold (t_actual < t_min):",
                "1. Immediate fail-closed lockout must occur with zero publication deliverables generated.",
                "2. The condition must be flagged as a CRITICAL non-conformance.",
                "3. Equipment isolation tagging and structural re-rating review are mandatory under refinery asset integrity protocols.",
            ]),
        ],
    )

    # 9. 09_Process_Equipment_Operating_Limits.pdf
    create_pdf(
        target_dir / "09_Process_Equipment_Operating_Limits.pdf",
        title="Operating Envelope and Integrity Limits for Distillation Columns",
        doc_id="DEMO-OPLM-GDL-009",
        equipment_ids=["C-101"],
        sections=[
            ("1.0 Integrity Operating Window (IOW)", [
                "Operating windows define parameter boundaries within which process equipment can operate without accelerated structural degradation.",
                "For Column C-101, operating pressure must remain between 1.2 and 2.2 bar(g). Overpressure relief valves are set at 3.5 bar(g).",
                "Overhead vapor temperature must be maintained between 115 degrees C and 135 degrees C.",
            ]),
            ("2.0 Velocity Limits and Erosion Control", [
                "Vapor velocities in the overhead vapor line leading to condenser E-02 must not exceed 22.0 meters per second.",
                "Velocities above 25.0 meters per second cause turbulent boundary layer stripping, multiplying corrosion rates by a factor of 3.0 or higher.",
            ]),
        ],
    )

    # 10. 10_Inspection_Finding_Classification.pdf
    create_pdf(
        target_dir / "10_Inspection_Finding_Classification.pdf",
        title="Non-Conformance & Inspection Finding Severity Classification Matrix",
        doc_id="DEMO-FIND-CLS-010",
        sections=[
            ("1.0 Severity Definitions", [
                "Inspection findings from ultrasonic surveys are classified into four severity tiers based on remaining thickness and remaining service life:",
                "CRITICAL: Current thickness is less than or equal to minimum required thickness (t_actual <= t_min) or remaining life is less than 1.0 year.",
                "HIGH: Current thickness is above t_min but calculated remaining life is between 1.0 and 2.0 years.",
                "MEDIUM: Current thickness is above t_min and remaining life is between 2.0 and 5.0 years (or localized thinning rate exceeds 0.30 mm/year). C-101 CML-4 is currently classified as MEDIUM.",
                "LOW: Current thickness is within normal parameters and remaining service life exceeds 5.0 years.",
            ]),
            ("2.0 Action Protocol", [
                "MEDIUM severity findings permit continued service under monitored conditions with mandatory re-inspection within the calculated half-life period.",
            ]),
        ],
    )

    print(f"\nSuccessfully generated all 10 demonstration documents in: {target_dir}")


if __name__ == "__main__":
    target = Path("data/raw/knowledge")
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
    generate_all_documents(target)
