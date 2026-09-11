"""Integrity verification for the tamper-evident audit hash chain."""

from typing import List, Optional
from app.services.audit.hash_chain import GENESIS_HASH, calculate_event_hash
from app.services.audit.models import AuditEvent, AuditVerificationResult


class AuditIntegrityVerifier:
    """Verifies chronological continuity and cryptographic hash integrity of the audit chain."""

    @staticmethod
    def verify_chain(events: List[AuditEvent]) -> AuditVerificationResult:
        """
        Verify that all events form an unbroken, un-tampered hash chain starting from GENESIS_HASH.
        Detects:
        - Content modifications (event_hash mismatch)
        - Deletions / omissions (hash discontinuity)
        - Reordering (previous_hash mismatch)
        - Invalid genesis linkages
        """
        if not events:
            return AuditVerificationResult(
                valid=True,
                events_checked=0,
                first_invalid_event=None,
                first_invalid_index=None,
                error_detail="Empty audit ledger: no events to verify."
            )

        expected_prev = GENESIS_HASH

        for idx, event in enumerate(events):
            # 1. Verify previous_hash linkage
            if event.previous_hash != expected_prev:
                return AuditVerificationResult(
                    valid=False,
                    events_checked=idx,
                    first_invalid_event=event.event_id,
                    first_invalid_index=idx,
                    error_detail=(
                        f"Hash link mismatch at event {event.event_id} (index {idx}). "
                        f"Expected previous_hash '{expected_prev}', got '{event.previous_hash}'."
                    )
                )

            # 2. Recompute and verify event_hash
            computed_hash = calculate_event_hash(event, expected_prev)
            if event.event_hash != computed_hash:
                return AuditVerificationResult(
                    valid=False,
                    events_checked=idx,
                    first_invalid_event=event.event_id,
                    first_invalid_index=idx,
                    error_detail=(
                        f"Cryptographic digest mismatch at event {event.event_id} (index {idx}). "
                        f"Recorded event_hash '{event.event_hash}', calculated '{computed_hash}'."
                    )
                )

            # Advance chain pointer
            expected_prev = event.event_hash

        return AuditVerificationResult(
            valid=True,
            events_checked=len(events),
            first_invalid_event=None,
            first_invalid_index=None,
            error_detail=None
        )
