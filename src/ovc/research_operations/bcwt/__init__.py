"""BCWT mechanical B->C Research Operations surface. Authority effect: NONE."""

from .assurance import assert_mechanical_only
from .mechanical import (
    BCWTValidationError,
    MEASUREMENTS,
    TERMINAL_STATUSES,
    assert_r2_origin,
    compile_ledger,
    compile_mechanical_origins,
    logical_id,
    make_consequence_pack,
    make_join_manifest,
    make_run_receipt,
    replay_digest,
)
from .records import (
    BCWT_PAYLOAD_REQUIRED,
    BCWT_RECORD_DIRECTORIES,
    BCWT_RECORD_TYPES,
    validate_bcwt_payload,
)

__all__ = [
    "BCWTValidationError",
    "MEASUREMENTS",
    "TERMINAL_STATUSES",
    "assert_r2_origin",
    "compile_ledger",
    "compile_mechanical_origins",
    "logical_id",
    "make_consequence_pack",
    "make_join_manifest",
    "make_run_receipt",
    "replay_digest",
    "assert_mechanical_only",
    "BCWT_PAYLOAD_REQUIRED",
    "BCWT_RECORD_DIRECTORIES",
    "BCWT_RECORD_TYPES",
    "validate_bcwt_payload",
]
