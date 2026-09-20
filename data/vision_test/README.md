# Vision Model Evaluation Dataset

> **Classification:** Synthetic / Project-Safe Benchmark Dataset  
> **Target Evaluation Model:** `qwen2.5vl:3b` (via ModelManager `vision` role)  
> **Status:** Completely Isolated from Workbench Initial State & Production MRPL Data

---

## 1. Purpose

This controlled dataset evaluates what local multimodal Vision-Language Models (specifically `qwen2.5vl:3b` executing within the 8 GB VRAM hardware profile) can actually extract from industrial refinery imagery.

It serves as a repeatable testbed for:
- Symbol recognition on piping and instrumentation diagrams (P&ID)
- Equipment tag identification and spatial localization
- Dial reading and unit recognition on field gauges
- Stamped parameter extraction from mechanical nameplates
- Tabular digit parsing from ultrasonic non-destructive testing (NDT) scans
- Graceful handling of ambiguous, low-contrast, or partial drawings

This dataset is **NOT** production MRPL operational data. All tags, dimensions, serial numbers, and readings are synthetic benchmarks designed to prevent contamination of production engineering baselines.

---

## 2. Directory Structure & Inventory

```
data/vision_test/
├── README.md                          # This documentation file
├── eval_results.json                  # Automated test evaluation results
├── pid/
│   ├── pid_distillation_column.png    # Standard P&ID: Column C-201, lines, instruments
│   └── pid_partial_ambiguous.png      # Degraded/partial P&ID with missing tags & noise
├── equipment/
│   ├── equipment_centrifugal_pump.png # Centrifugal Pump P-102A mechanical schematic
│   └── equipment_heat_exchanger.png   # Shell & Tube Exchanger E-104 nozzle callout
├── gauges/
│   ├── gauge_pressure_analog.png      # Analog Bourdon pressure gauge PI-302 (~14.2 bar)
│   └── gauge_temperature_dial.png     # Analog bimetal temperature dial TI-108 (~245 °C)
├── nameplates/
│   ├── nameplate_pressure_vessel.png  # ASME Sec VIII Div 1 vessel nameplate (V-301)
│   └── nameplate_process_pump.png     # API 610 centrifugal process pump stamped plate (P-204B)
└── tables/
    ├── table_thickness_survey_scan.png # Tabular NDT thickness survey grid (5 CMLs)
    └── table_ndt_calibration_log.png   # Step wedge ultrasonic calibration log
```

---

## 3. Test Cases & Ground-Truth Expectations

### A. P&ID Schematics (`pid/`)

#### 1. `pid_distillation_column.png`
- **Expected Vision Task:** Parse process flow, vessel symbol, line annotations, and instrument bubbles.
- **What should be extracted:**
  - Equipment tags: `C-201` (Distillation Column), `E-205` (Overhead Condenser).
  - Instrument tags: `PT-201` (Pressure Transmitter on overhead line), `TT-201` (Temperature Transmitter on top shell), `FCV-201` (Flow Control Valve on feed).
  - Line IDs: `6"-CRU-2001-CS150`, `10"-VAP-2002-CS300`.
- **What should NOT be inferred:**
  - Do NOT infer internal tray corrosion rates or wall thickness measurements. P&ID drawings do not contain thickness survey data.

#### 2. `pid_partial_ambiguous.png`
- **Expected Vision Task:** Evaluate uncertainty handling and confidence scoring on incomplete drawings.
- **What should be extracted:**
  - Notice note: `PARTIAL DRAWING — FIELD VERIFICATION REQUIRED`.
  - Confidence should drop below `0.70` on obscured bubbles (`P?-??`) and lines (`4"-???-CS???`).
- **What should NOT be inferred:**
  - The model must NOT hallucinate `C-101` or invent complete tag IDs for blurred or damaged sections.

---

### B. Equipment Schematics (`equipment/`)

#### 1. `equipment_centrifugal_pump.png`
- **Expected Vision Task:** Extract equipment identity, subcomponents, and flange connection sizes.
- **What should be extracted:**
  - Equipment Tag: `P-102A`.
  - Equipment Type: Centrifugal pump with electric motor.
  - Flanges / Sizes: Suction 6" flange, Discharge 4" flange.
  - Motor rating: `30 kW / 2950 RPM`.
- **What should NOT be inferred:**
  - Do NOT infer remaining life or impeller wear without gauging evidence.

#### 2. `equipment_heat_exchanger.png`
- **Expected Vision Task:** Identify shell and tube connections and equipment tag.
- **What should be extracted:**
  - Equipment Tag: `E-104`.
  - Connections: `N1 (IN)`, `N2 (OUT)`, `TUBE IN`, `TUBE OUT`.
- **What should NOT be inferred:**
  - Do NOT infer bundle metallurgy unless explicitly printed on a nameplate.

---

### C. Gauges & Dial Indicators (`gauges/`)

#### 1. `gauge_pressure_analog.png`
- **Expected Vision Task:** Needle angle interpretation, scale detection, and instrument tag extraction.
- **What should be extracted:**
  - Instrument Tag: `PI-302`.
  - Unit of Measurement: `bar`.
  - Scale Range: `0 to 25 bar`.
  - Needle Value: `~14.2 bar` (acceptable range: 13.5 to 14.8 bar).
  - Standard / Class: `EN 837-1`, `WIKA CL. 1.0`.
- **What should NOT be inferred:**
  - Do NOT infer operating pressure safety limits unless indicated by color bands.

#### 2. `gauge_temperature_dial.png`
- **Expected Vision Task:** Temperature scale and dial position extraction.
- **What should be extracted:**
  - Instrument Tag: `TI-108`.
  - Unit of Measurement: `°C`.
  - Scale Range: `0 to 400 °C`.
  - Needle Value: `~245 °C` (acceptable range: 240 to 250 °C).
- **What should NOT be inferred:**
  - Do NOT confuse Celsius with Fahrenheit.

---

### D. Industrial Equipment Nameplates (`nameplates/`)

#### 1. `nameplate_pressure_vessel.png`
- **Expected Vision Task:** Dense OCR of stamped metal plate fields.
- **What should be extracted:**
  - Equipment Tag: `V-301` (`LP FLASH DRUM`).
  - Standard: `ASME SECTION VIII DIVISION 1`.
  - Manufacturer: `BHARAT FABRICATORS LTD.`
  - Serial / Year: `BF-2019-9482 / 2019`.
  - MAWP: `25.5 BAR (G) @ 300 °C`.
  - Material: `SA-516 GRADE 70`.
  - Nominal Thickness: `14.50 MM`.
  - Corrosion Allowance: `3.00 MM`.
- **What should NOT be inferred:**
  - Do NOT infer current measured thickness from nominal stamped thickness. The nameplate provides design baseline only ($t_{\text{initial}}$), not inspection thickness ($t_{\text{actual}}$).

#### 2. `nameplate_process_pump.png`
- **Expected Vision Task:** Industrial pump specification extraction.
- **What should be extracted:**
  - Equipment Tag: `P-204B`.
  - Standard: `API 610 11TH EDITION / ISO 13709`.
  - Service: `CDU HEAVY GAS OIL BOOSTER`.
  - Rated Capacity: `145 M3/HR`.
  - Head: `92 M` at `2950 RPM`.
  - Material: `ASTM A216 GR WCB`.

---

### E. Tabular NDT Inspection Scans (`tables/`)

#### 1. `table_thickness_survey_scan.png`
- **Expected Vision Task:** High-accuracy tabular OCR digit alignment and CML extraction.
- **What should be extracted:**
  - Component / Vessel: `COLUMN V-401 OVERHEAD PIPING`.
  - Date: `2026-02-18`.
  - CML readings table:
    - `CML-01`: Nominal `12.70 mm`, Measured `11.85 mm`, Loss `0.85 mm`.
    - `CML-02`: Nominal `12.70 mm`, Measured `11.20 mm`, Loss `1.50 mm`.
    - `CML-03`: Nominal `12.70 mm`, Measured `10.65 mm`, Loss `2.05 mm`.
    - `CML-04`: Nominal `12.70 mm`, Measured `10.30 mm`, Loss `2.40 mm` (Governing / Minimum).
    - `CML-05`: Nominal `9.52 mm`, Measured `8.90 mm`, Loss `0.62 mm`.
- **What should NOT be inferred:**
  - Elapsed time is not in the table; do NOT invent an inspection interval unless provided.

#### 2. `table_ndt_calibration_log.png`
- **Expected Vision Task:** Calibration step wedge validation.
- **What should be extracted:**
  - Instrument: `OLYMPUS 38DL PLUS`, Probe `5 MHz`.
  - Calibration Steps: 2.50 mm, 5.00 mm, 7.50 mm, 10.00 mm, 12.50 mm.
  - Calibration Status: `PASS` across all 5 steps.

---

## 4. Execution & Automated Testing

To run the automated vision evaluation suite against this dataset:

```bash
# Run against the vision provider abstraction (mock/deterministic or live Ollama)
python scripts/test_vision_dataset.py

# Run explicitly with live Ollama (if running locally):
python scripts/test_vision_dataset.py --live
```

The script records:
- Input filename & category
- Extraction latency (ms)
- Identified equipment and instrument tags
- Structured visual findings conforming to `SchematicAnalysisResult`
- Detection confidence scores
- Output JSON report in `data/vision_test/eval_results.json`
