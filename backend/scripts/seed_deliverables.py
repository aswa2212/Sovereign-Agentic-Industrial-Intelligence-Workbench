"""
SIH26117 — Seed baseline deliverable files for demo/testing.

Generates real DOCX + XLSX files using the DeliverablesFactory with
a canonical mock corrosion audit payload, then also copies them to
the deliverables/ folder under the baseline demo names.

Run from repo root:
    python -m backend.scripts.seed_deliverables
"""

import sys
import shutil
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from backend.app.services.deliverables.factory import DeliverablesFactory
from backend.app.services.deliverables.models import DeliverableFormat, ReportMetadata

# ── Canonical mock payload ────────────────────────────────────────────────────
from backend.app.services.validation.models import (
    CorrosionAuditResult,
    WallThicknessMeasurement,
    CorrosionCalculation,
    InspectionFinding,
    RecommendationCode,
    SourceCitation,
    MeasurementUnit,
)

# Construct a minimal valid CorrosionAuditResult payload
payload = CorrosionAuditResult(
    equipment_id="C-101",
    inspection_subject="Overhead Corrosion Audit",
    current_measurement=WallThicknessMeasurement(
        value_mm=8.4,
        unit=MeasurementUnit.MM,
        measurement_date="2026-03-20",
        location_tag="C-101",
    ),
    initial_measurement=WallThicknessMeasurement(
        value_mm=12.7,
        unit=MeasurementUnit.MM,
        measurement_date="2024-03-20",
        location_tag="C-101",
    ),
    minimum_required_thickness_mm=5.0,
    calculation=CorrosionCalculation(
        initial_thickness_mm=12.7,
        current_thickness_mm=8.4,
        inspection_interval_years=2.0,
        corrosion_rate_mm_per_year=0.38,
        remaining_life_years=8.9,
    ),
    findings=[
        InspectionFinding(
            description="Uniform thinning observed in the overhead section.",
            severity="LOW",
        )
    ],
    conclusion="Equipment is operating within acceptable limits.",
    recommendation=RecommendationCode.CONTINUE_SERVICE,
    citations=[],
    confidence=0.95,
)
MOCK_PAYLOAD = payload.dict()


DEMO_NAMES = {
    DeliverableFormat.DOCX: "MRPL_Corrosion_Audit_Memorandum_C101.docx",
    DeliverableFormat.XLSX: "C101_API570_Corrosion_Calculation_Sheet.xlsx",
    DeliverableFormat.PPTX: "MRPL_C101_Corrosion_Audit_Briefing.pptx",
}


def main() -> None:
    factory = DeliverablesFactory()
    meta = ReportMetadata(
        prepared_by="Er. Rajesh Kumar, MRPL NDT-0142",
        approved_by="Chief Inspection Engineer, MRPL",
        report_code="MRPL-INSP-C101-2026-003",
        revision="01",
    )

    print("Generating baseline deliverables …")
    result = factory.generate(
        payload=MOCK_PAYLOAD,
        formats=[DeliverableFormat.DOCX, DeliverableFormat.XLSX, DeliverableFormat.PPTX],
        metadata=meta,
        task_id="demo-seed-001",
    )

    deliv_dir = factory.base_output_dir / "deliverables"
    deliv_dir.mkdir(parents=True, exist_ok=True)

    for art in result.artifacts:
        src = factory.format_dirs[art.format] / art.filename
        if not src.exists():
            print(f"  WARNING: generated file not found at {src}")
            continue

        # Copy under canonical demo name into outputs/deliverables/
        dest_name = DEMO_NAMES.get(art.format, art.filename)
        dest = deliv_dir / dest_name
        shutil.copy2(src, dest)

        print(f"  [OK] {art.format.value.upper()}: {src.name}")
        print(f"    -> also seeded as {dest_name}")

    print(f"\nDone. {len(result.artifacts)} file(s) ready.")
    print(f"  Format dirs: {factory.base_output_dir}")


if __name__ == "__main__":
    main()
