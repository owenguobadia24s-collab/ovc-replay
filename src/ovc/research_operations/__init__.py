"""Deterministic Research Operations evidence-kernel helpers.

RO-WP1 exposes pure functions only. It performs no durable writes, Git/R2
operations, Validation payload access or market classification.
"""
from .availability import derive_reproducibility_state
from .canonical import canonical_json_bytes, canonical_sha256
from .identity import DuplicateRecordIdError, RecordIdRegistry, deterministic_record_id
from .lifecycle import FrozenRecordMutationError, freeze_record, supersede_record, verify_frozen_record
from .validation import RecordValidationError, validate_record

__all__ = [
    "canonical_json_bytes", "canonical_sha256", "deterministic_record_id",
    "DuplicateRecordIdError", "RecordIdRegistry", "FrozenRecordMutationError",
    "freeze_record", "supersede_record", "verify_frozen_record",
    "RecordValidationError", "validate_record", "derive_reproducibility_state",
]
