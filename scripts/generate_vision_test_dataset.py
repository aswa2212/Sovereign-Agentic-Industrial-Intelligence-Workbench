"""
SIH26117 — Vision Model Evaluation Dataset Generator
Generates synthetic, project-safe industrial test images for evaluating local VLM (qwen2.5vl:3b).
Does NOT use or invent real production MRPL data.
Categories:
  - pid/
  - equipment/
  - gauges/
  - nameplates/
  - tables/
"""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

DATASET_ROOT = Path("data/vision_test")


def get_font(size=14):
    try:
        # Standard Windows fonts
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        try:
            return ImageFont.truetype("calibri.ttf", size)
        except Exception:
            return ImageFont.load_default()


def create_pid_samples():
    out_dir = DATASET_ROOT / "pid"
    out_dir.mkdir(parents=True, exist_ok=True)
    font_lg = get_font(18)
    font_md = get_font(13)
    font_sm = get_font(10)

    # 1. P&ID Standard Fractionation Column
    img1 = Image.new("RGB", (900, 650), color=(255, 255, 255))
    draw1 = ImageDraw.Draw(img1)

    # Border & Title block
    draw1.rectangle([20, 20, 880, 630], outline=(40, 40, 40), width=2)
    draw1.rectangle([600, 550, 880, 630], outline=(40, 40, 40), width=1)
    draw1.text((610, 555), "SYNTHETIC BENCHMARK P&ID", fill=(0, 0, 0), font=font_md)
    draw1.text((610, 575), "DWG: PID-BENCH-001 REV 0", fill=(50, 50, 50), font=font_sm)
    draw1.text((610, 595), "UNIT: CDU BENCHMARK LOOP", fill=(50, 50, 50), font=font_sm)
    draw1.text((610, 610), "NOT FOR PRODUCTION USE", fill=(180, 0, 0), font=font_sm)

    # Distillation Column Vessel C-201
    draw1.rectangle([350, 120, 450, 480], outline=(0, 0, 0), width=3)
    draw1.arc([350, 90, 450, 150], start=180, end=0, fill=(0, 0, 0), width=3)
    draw1.arc([350, 450, 450, 510], start=0, end=180, fill=(0, 0, 0), width=3)
    draw1.text((370, 280), "C-201", fill=(0, 0, 0), font=font_lg)
    draw1.text((360, 310), "BENCHMARK", fill=(70, 70, 70), font=font_sm)
    draw1.text((365, 325), "COLUMN", fill=(70, 70, 70), font=font_sm)

    # Feed Line
    draw1.line([(100, 300), (350, 300)], fill=(0, 0, 0), width=2)
    draw1.polygon([(340, 296), (350, 300), (340, 304)], fill=(0, 0, 0))
    draw1.text((120, 280), '6"-CRU-2001-CS150', fill=(0, 0, 150), font=font_md)

    # Overhead Vapor Line
    draw1.line([(400, 105), (400, 60), (700, 60), (700, 180)], fill=(0, 0, 0), width=2)
    draw1.text((450, 40), '10"-VAP-2002-CS300', fill=(0, 0, 150), font=font_md)

    # Overhead Condenser E-205
    draw1.ellipse([670, 180, 730, 260], outline=(0, 0, 0), width=2)
    draw1.text((680, 215), "E-205", fill=(0, 0, 0), font=font_md)

    # Instrument Bubbles
    # PT-201 on overhead
    draw1.ellipse([480, 80, 520, 120], outline=(0, 0, 0), width=2)
    draw1.line([(500, 60), (500, 80)], fill=(0, 0, 0), width=1)
    draw1.line([(480, 100), (520, 100)], fill=(0, 0, 0), width=1)
    draw1.text((486, 84), "PT", fill=(0, 0, 0), font=font_sm)
    draw1.text((486, 104), "201", fill=(0, 0, 0), font=font_sm)

    # TT-201 on column top
    draw1.ellipse([270, 140, 310, 180], outline=(0, 0, 0), width=2)
    draw1.line([(310, 160), (350, 160)], fill=(0, 0, 0), width=1)
    draw1.line([(270, 160), (310, 160)], fill=(0, 0, 0), width=1)
    draw1.text((276, 144), "TT", fill=(0, 0, 0), font=font_sm)
    draw1.text((276, 164), "201", fill=(0, 0, 0), font=font_sm)

    # Control Valve on feed line
    draw1.polygon([(230, 290), (250, 300), (230, 310)], outline=(0, 0, 0), fill=(255, 255, 255))
    draw1.polygon([(270, 290), (250, 300), (270, 310)], outline=(0, 0, 0), fill=(255, 255, 255))
    draw1.text((240, 315), "FCV-201", fill=(0, 0, 0), font=font_sm)

    img1.save(out_dir / "pid_distillation_column.png")

    # 2. P&ID Partial / Ambiguous Drawing
    img2 = Image.new("RGB", (700, 500), color=(245, 245, 245))
    draw2 = ImageDraw.Draw(img2)
    draw2.rectangle([10, 10, 690, 490], outline=(120, 120, 120), width=1)
    draw2.text((20, 20), "PARTIAL SCHEMATIC - UNCERTAIN EXTRACTION BENCHMARK", fill=(100, 100, 100), font=font_md)

    # Broken / Partial lines
    draw2.line([(50, 150), (280, 150)], fill=(50, 50, 50), width=2)
    draw2.line([(280, 150), (280, 250)], fill=(50, 50, 50), width=2)
    draw2.line([(350, 250), (550, 250)], fill=(150, 150, 150), width=1)  # faint line

    # Incomplete instrument tag bubble
    draw2.ellipse([260, 70, 300, 110], outline=(0, 0, 0), width=1)
    draw2.line([(280, 110), (280, 150)], fill=(0, 0, 0), width=1)
    draw2.text((268, 85), "P?-??", fill=(100, 0, 0), font=font_sm)

    # Blurred / degraded tag annotation
    draw2.text((80, 130), 'LINE: 4"-???-CS???', fill=(120, 120, 120), font=font_sm)
    draw2.text((320, 380), "NOTE: PARTIAL DRAWING — FIELD VERIFICATION REQUIRED", fill=(150, 50, 50), font=font_md)
    draw2.text((320, 405), "DO NOT INFER MISSING TAG IDENTIFIERS", fill=(180, 0, 0), font=font_sm)

    img2.save(out_dir / "pid_partial_ambiguous.png")


def create_equipment_samples():
    out_dir = DATASET_ROOT / "equipment"
    out_dir.mkdir(parents=True, exist_ok=True)
    font_lg = get_font(18)
    font_md = get_font(14)
    font_sm = get_font(11)

    # 1. Centrifugal Pump P-102A Schematic
    img1 = Image.new("RGB", (750, 500), color=(255, 255, 255))
    draw1 = ImageDraw.Draw(img1)
    draw1.rectangle([10, 10, 740, 490], outline=(0, 0, 0), width=2)

    draw1.text((30, 25), "EQUIPMENT ISOLATION BENCHMARK: CENTRIFUGAL PUMP", fill=(0, 0, 0), font=font_md)
    draw1.text((30, 45), "SYNTHETIC DATASET SAMPLE — NOT PRODUCTION MRPL ASSET", fill=(160, 0, 0), font=font_sm)

    # Volute Casing
    draw1.ellipse([250, 180, 450, 380], outline=(0, 0, 0), width=3)
    draw1.ellipse([310, 240, 390, 320], outline=(80, 80, 80), width=2)
    draw1.text((320, 272), "IMPELLER", fill=(100, 100, 100), font=font_sm)

    # Suction Flange (left)
    draw1.rectangle([150, 260, 250, 300], outline=(0, 0, 0), width=2)
    draw1.rectangle([140, 250, 150, 310], outline=(0, 0, 0), fill=(180, 180, 180), width=2)
    draw1.text((160, 240), 'SUCTION 6" FLANGE', fill=(0, 0, 120), font=font_sm)

    # Discharge Flange (top)
    draw1.rectangle([330, 90, 370, 180], outline=(0, 0, 0), width=2)
    draw1.rectangle([320, 80, 380, 90], outline=(0, 0, 0), fill=(180, 180, 180), width=2)
    draw1.text((390, 110), 'DISCHARGE 4" FLANGE', fill=(0, 0, 120), font=font_sm)

    # Motor coupling (right)
    draw1.rectangle([450, 250, 520, 310], outline=(0, 0, 0), width=2)
    draw1.rectangle([520, 210, 680, 350], outline=(0, 0, 0), width=3)
    draw1.text((545, 270), "ELECTRIC MOTOR", fill=(0, 0, 0), font=font_md)
    draw1.text((560, 295), "30 kW / 2950 RPM", fill=(60, 60, 60), font=font_sm)

    # Tag callouts
    draw1.rectangle([270, 410, 430, 455], fill=(240, 240, 240), outline=(0, 0, 0), width=2)
    draw1.text((290, 420), "TAG: P-102A", fill=(0, 0, 180), font=font_lg)

    img1.save(out_dir / "equipment_centrifugal_pump.png")

    # 2. Shell & Tube Heat Exchanger E-104
    img2 = Image.new("RGB", (800, 480), color=(255, 255, 255))
    draw2 = ImageDraw.Draw(img2)
    draw2.rectangle([10, 10, 790, 470], outline=(0, 0, 0), width=2)

    draw2.text((30, 25), "EQUIPMENT ISOLATION BENCHMARK: SHELL & TUBE HEAT EXCHANGER", fill=(0, 0, 0), font=font_md)
    draw2.text((30, 45), "SYNTHETIC DATASET SAMPLE — NOT PRODUCTION MRPL ASSET", fill=(160, 0, 0), font=font_sm)

    # Exchanger Body
    draw2.rectangle([200, 160, 600, 320], outline=(0, 0, 0), width=3)
    draw2.arc([140, 160, 260, 320], start=90, end=270, fill=(0, 0, 0), width=3)
    draw2.arc([540, 160, 660, 320], start=270, end=90, fill=(0, 0, 0), width=3)

    # Shell Nozzles
    draw2.rectangle([280, 100, 320, 160], outline=(0, 0, 0), width=2)
    draw2.text((285, 80), 'N1 (IN)', fill=(0, 0, 140), font=font_sm)
    draw2.rectangle([480, 320, 520, 380], outline=(0, 0, 0), width=2)
    draw2.text((485, 385), 'N2 (OUT)', fill=(0, 0, 140), font=font_sm)

    # Tube side connections
    draw2.rectangle([120, 220, 170, 260], outline=(0, 0, 0), width=2)
    draw2.text((50, 230), 'TUBE IN', fill=(0, 100, 0), font=font_sm)

    draw2.rectangle([630, 220, 680, 260], outline=(0, 0, 0), width=2)
    draw2.text((690, 230), 'TUBE OUT', fill=(0, 100, 0), font=font_sm)

    # Tag Badge
    draw2.rectangle([330, 220, 470, 265], fill=(235, 245, 255), outline=(0, 0, 180), width=2)
    draw2.text((350, 230), "TAG: E-104", fill=(0, 0, 180), font=font_lg)

    img2.save(out_dir / "equipment_heat_exchanger.png")


def create_gauge_samples():
    out_dir = DATASET_ROOT / "gauges"
    out_dir.mkdir(parents=True, exist_ok=True)
    font_lg = get_font(18)
    font_md = get_font(14)
    font_sm = get_font(11)

    # 1. Analog Pressure Gauge PG-302 (14.2 bar)
    img1 = Image.new("RGB", (600, 600), color=(240, 240, 240))
    draw1 = ImageDraw.Draw(img1)

    # Dial bezel
    draw1.ellipse([50, 50, 550, 550], fill=(255, 255, 255), outline=(50, 50, 50), width=6)
    draw1.ellipse([70, 70, 530, 530], outline=(150, 150, 150), width=2)

    # Dial markings (0 to 25 bar)
    draw1.text((270, 130), "bar", fill=(0, 0, 0), font=font_md)
    draw1.text((245, 160), "EN 837-1", fill=(100, 100, 100), font=font_sm)
    draw1.text((240, 360), "TAG: PI-302", fill=(0, 0, 140), font=font_lg)
    draw1.text((250, 390), "WIKA CL. 1.0", fill=(120, 120, 120), font=font_sm)

    # Numbers around face
    draw1.text((140, 380), "0", fill=(0, 0, 0), font=font_md)
    draw1.text((110, 260), "5", fill=(0, 0, 0), font=font_md)
    draw1.text((170, 160), "10", fill=(0, 0, 0), font=font_md)
    draw1.text((290, 110), "15", fill=(0, 0, 0), font=font_md)
    draw1.text((410, 160), "20", fill=(0, 0, 0), font=font_md)
    draw1.text((460, 260), "25", fill=(0, 0, 0), font=font_md)

    # Needle pointing towards ~14.2 bar (angle near top center-right)
    # Pivot at (300, 300)
    draw1.ellipse([285, 285, 315, 315], fill=(30, 30, 30))
    draw1.line([(300, 300), (280, 140)], fill=(200, 0, 0), width=4)

    # Reading note below
    draw1.text((160, 565), "EXPECTED VALUE: ~14.2 bar (INDICATOR PI-302)", fill=(80, 80, 80), font=font_sm)

    img1.save(out_dir / "gauge_pressure_analog.png")

    # 2. Temperature Gauge Dial TI-108 (245 °C)
    img2 = Image.new("RGB", (600, 600), color=(240, 240, 240))
    draw2 = ImageDraw.Draw(img2)

    draw2.ellipse([50, 50, 550, 550], fill=(255, 255, 255), outline=(50, 50, 50), width=6)
    draw2.ellipse([70, 70, 530, 530], outline=(150, 150, 150), width=2)

    draw2.text((275, 130), "°C", fill=(0, 0, 0), font=font_md)
    draw2.text((240, 360), "TAG: TI-108", fill=(0, 0, 140), font=font_lg)
    draw2.text((230, 390), "BIMETAL THERMOMETER", fill=(120, 120, 120), font=font_sm)

    draw2.text((140, 380), "0", fill=(0, 0, 0), font=font_md)
    draw2.text((110, 260), "100", fill=(0, 0, 0), font=font_md)
    draw2.text((210, 130), "200", fill=(0, 0, 0), font=font_md)
    draw2.text((360, 130), "300", fill=(0, 0, 0), font=font_md)
    draw2.text((460, 260), "400", fill=(0, 0, 0), font=font_md)

    # Needle pointing towards 245 °C
    draw2.ellipse([285, 285, 315, 315], fill=(30, 30, 30))
    draw2.line([(300, 300), (285, 135)], fill=(200, 0, 0), width=4)

    draw2.text((160, 565), "EXPECTED VALUE: ~245 °C (INDICATOR TI-108)", fill=(80, 80, 80), font=font_sm)

    img2.save(out_dir / "gauge_temperature_dial.png")


def create_nameplate_samples():
    out_dir = DATASET_ROOT / "nameplates"
    out_dir.mkdir(parents=True, exist_ok=True)
    font_xl = get_font(18)
    font_md = get_font(13)
    font_sm = get_font(11)

    # 1. Metallic Pressure Vessel Nameplate V-301
    img1 = Image.new("RGB", (700, 420), color=(220, 225, 230))
    draw1 = ImageDraw.Draw(img1)

    # Outer stamped border
    draw1.rectangle([15, 15, 685, 405], outline=(80, 90, 100), width=3)
    draw1.rectangle([25, 25, 675, 395], outline=(150, 160, 170), width=1)

    # Screw holes
    for cx, cy in [(35, 35), (665, 35), (35, 385), (665, 385)]:
        draw1.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=(70, 70, 70), outline=(40, 40, 40))

    draw1.text((160, 40), "SYNTHETIC PRESSURE VESSEL NAMEPLATE", fill=(30, 40, 50), font=font_xl)
    draw1.text((220, 68), "ASME SECTION VIII DIVISION 1 — U STAMP", fill=(60, 70, 80), font=font_md)

    # Stamped Data Fields
    fields = [
        ("EQUIPMENT TAG:", "V-301 (LP FLASH DRUM)"),
        ("MANUFACTURER:", "BHARAT FABRICATORS LTD."),
        ("SERIAL NO / YEAR:", "BF-2019-9482 / 2019"),
        ("DESIGN PRESSURE (MAWP):", "25.5 BAR (G) @ 300 °C"),
        ("DESIGN TEMPERATURE:", "-20 °C TO 350 °C"),
        ("SHELL MATERIAL:", "SA-516 GRADE 70"),
        ("NOMINAL SHELL THICKNESS:", "14.50 MM"),
        ("CORROSION ALLOWANCE:", "3.00 MM"),
        ("HYDROSTATIC TEST PRESS:", "38.25 BAR (G)"),
    ]

    y_pos = 105
    for label, val in fields:
        draw1.text((45, y_pos), label, fill=(50, 60, 70), font=font_md)
        draw1.text((310, y_pos), val, fill=(0, 0, 100), font=font_md)
        y_pos += 29

    img1.save(out_dir / "nameplate_pressure_vessel.png")

    # 2. Process Pump Nameplate P-204B
    img2 = Image.new("RGB", (650, 380), color=(210, 215, 215))
    draw2 = ImageDraw.Draw(img2)
    draw2.rectangle([15, 15, 635, 365], outline=(60, 60, 60), width=3)

    draw2.text((140, 35), "CENTRIFUGAL PROCESS PUMP", fill=(20, 20, 20), font=font_xl)
    draw2.text((200, 65), "API 610 11TH EDITION / ISO 13709", fill=(70, 70, 70), font=font_md)

    pump_fields = [
        ("TAG NO:", "P-204B"),
        ("SERVICE:", "CDU HEAVY GAS OIL BOOSTER"),
        ("MODEL:", "OH2 100-250"),
        ("RATED CAPACITY:", "145 M3/HR"),
        ("DIFFERENTIAL HEAD:", "92 M"),
        ("RATED SPEED:", "2950 RPM"),
        ("CASING MAWP:", "35.0 BAR @ 220 °C"),
        ("CASING MATERIAL:", "ASTM A216 GR WCB"),
    ]

    y_pos = 105
    for label, val in pump_fields:
        draw2.text((45, y_pos), label, fill=(50, 50, 50), font=font_md)
        draw2.text((260, y_pos), val, fill=(0, 0, 120), font=font_md)
        y_pos += 28

    img2.save(out_dir / "nameplate_process_pump.png")


def create_table_samples():
    out_dir = DATASET_ROOT / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    font_xl = get_font(16)
    font_md = get_font(12)
    font_sm = get_font(10)

    # 1. Ultrasonic Thickness Survey Tabular Scan
    img1 = Image.new("RGB", (850, 480), color=(255, 255, 255))
    draw1 = ImageDraw.Draw(img1)

    draw1.text((30, 25), "NDT ULTRASONIC THICKNESS SURVEY LOG — BENCHMARK SCAN", fill=(0, 0, 0), font=font_xl)
    draw1.text((30, 50), "EQUIPMENT: COLUMN V-401 OVERHEAD PIPING • DATE: 2026-02-18", fill=(80, 80, 80), font=font_md)

    # Table Grid Coordinates
    x_start = 30
    y_start = 85
    col_widths = [90, 260, 110, 110, 110, 110]
    total_w = sum(col_widths)
    row_h = 32

    headers = ["CML TAG", "INSPECTION POINT LOCATION", "NOMINAL", "MEASURED", "LOSS (Δt)", "DATE"]
    rows = [
        ["CML-01", "Top Head Elbow Centerline", "12.70 mm", "11.85 mm", "0.85 mm", "2026-02-18"],
        ["CML-02", "Overhead Vapor Line Flange Spool", "12.70 mm", "11.20 mm", "1.50 mm", "2026-02-18"],
        ["CML-03", "Reflux Inlet Tee Extrados", "12.70 mm", "10.65 mm", "2.05 mm", "2026-02-18"],
        ["CML-04", "Vapor Condenser Reducer N1", "12.70 mm", "10.30 mm", "2.40 mm", "2026-02-18"],
        ["CML-05", "Reflux Return Line Spool 3", "9.52 mm", "8.90 mm", "0.62 mm", "2026-02-18"],
    ]

    # Draw Header Row
    draw1.rectangle([x_start, y_start, x_start + total_w, y_start + row_h], fill=(230, 235, 245), outline=(50, 50, 50), width=1)
    curr_x = x_start
    for i, h in enumerate(headers):
        draw1.text((curr_x + 8, y_start + 8), h, fill=(0, 0, 0), font=font_md)
        curr_x += col_widths[i]

    # Draw Data Rows
    for r_idx, r_data in enumerate(rows):
        y = y_start + (r_idx + 1) * row_h
        bg_fill = (250, 250, 250) if r_idx % 2 == 0 else (255, 255, 255)
        draw1.rectangle([x_start, y, x_start + total_w, y + row_h], fill=bg_fill, outline=(180, 180, 180), width=1)
        curr_x = x_start
        for c_idx, val in enumerate(r_data):
            draw1.text((curr_x + 8, y + 8), val, fill=(30, 30, 30), font=font_md)
            curr_x += col_widths[c_idx]

    # Footnote
    draw1.text((30, y_start + 7 * row_h + 10), "CALIBRATION: VELOCITY 5920 m/s (CARBON STEEL), PROBE 5.0 MHz DUAL ELEMENT.", fill=(100, 100, 100), font=font_sm)
    draw1.text((30, y_start + 7 * row_h + 30), "BENCHMARK SYNTHETIC DATASET — NOT REAL REFINERY INSPECTION LOG.", fill=(180, 0, 0), font=font_sm)

    img1.save(out_dir / "table_thickness_survey_scan.png")

    # 2. NDT Calibration Step Wedge Log
    img2 = Image.new("RGB", (750, 420), color=(255, 255, 255))
    draw2 = ImageDraw.Draw(img2)

    draw2.text((30, 25), "ULTRASONIC INSTRUMENT DAILY CALIBRATION RECORD", fill=(0, 0, 0), font=font_xl)
    draw2.text((30, 50), "EQUIPMENT: OLYMPUS 38DL PLUS • PROBE: D790-SM (5 MHz)", fill=(70, 70, 70), font=font_md)

    col_widths2 = [130, 130, 130, 130, 150]
    total_w2 = sum(col_widths2)
    headers2 = ["STEP (MM)", "NOMINAL", "MEASURED", "ERROR", "RESULT"]
    rows2 = [
        ["Step 1", "2.50 mm", "2.51 mm", "+0.01 mm", "PASS"],
        ["Step 2", "5.00 mm", "5.00 mm", "0.00 mm", "PASS"],
        ["Step 3", "7.50 mm", "7.49 mm", "-0.01 mm", "PASS"],
        ["Step 4", "10.00 mm", "10.02 mm", "+0.02 mm", "PASS"],
        ["Step 5", "12.50 mm", "12.50 mm", "0.00 mm", "PASS"],
    ]

    draw2.rectangle([x_start, y_start, x_start + total_w2, y_start + row_h], fill=(230, 240, 230), outline=(50, 50, 50), width=1)
    curr_x = x_start
    for i, h in enumerate(headers2):
        draw2.text((curr_x + 8, y_start + 8), h, fill=(0, 0, 0), font=font_md)
        curr_x += col_widths2[i]

    for r_idx, r_data in enumerate(rows2):
        y = y_start + (r_idx + 1) * row_h
        draw2.rectangle([x_start, y, x_start + total_w2, y + row_h], fill=(255, 255, 255), outline=(180, 180, 180), width=1)
        curr_x = x_start
        for c_idx, val in enumerate(r_data):
            color = (0, 140, 0) if val == "PASS" else (30, 30, 30)
            draw2.text((curr_x + 8, y + 8), val, fill=color, font=font_md)
            curr_x += col_widths2[c_idx]

    img2.save(out_dir / "table_ndt_calibration_log.png")


def main():
    print("Generating Vision Model Evaluation Dataset in data/vision_test/...")
    create_pid_samples()
    create_equipment_samples()
    create_gauge_samples()
    create_nameplate_samples()
    create_table_samples()
    print("Generation complete.")


if __name__ == "__main__":
    main()
