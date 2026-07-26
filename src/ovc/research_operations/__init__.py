"""Deterministic Research Operations evidence and operator services.

RO-WP2 adds governed append-only record writes, audit emission, queues and a
read/verify/report-only artifact catalogue. It performs no Git, R2, selector,
threshold, market-classification, probability, exposure or execution action.
"""
from .availability import derive_reproducibility_state
from .canonical import canonical_json_bytes, canonical_sha256
from .catalogue import (
    ArtifactCatalogue,
    ArtifactCatalogueBuilder,
    ArtifactNode,
    CatalogueIssue,
    catalogue_report,
    read_catalogue,
    write_catalogue,
)
from .config import ConfigurationError, ResearchOperationsConfig
from .identity import DuplicateRecordIdError, RecordIdRegistry, deterministic_record_id
from .lifecycle import FrozenRecordMutationError, freeze_record, supersede_record, verify_frozen_record
from .operations import ResearchOperationsService
from .paths import ApprovedPathRegistry, PathPolicyError, UnsafePathError
from .queues import ResearchQueueService
from .storage import AppendOnlyViolationError, DraftStore, FrozenRecordStore, ResearchWriteService
from .validation import RecordValidationError, validate_record

__all__ = [
    "canonical_json_bytes", "canonical_sha256", "deterministic_record_id",
    "DuplicateRecordIdError", "RecordIdRegistry", "FrozenRecordMutationError",
    "freeze_record", "supersede_record", "verify_frozen_record",
    "RecordValidationError", "validate_record", "derive_reproducibility_state",
    "ConfigurationError", "ResearchOperationsConfig", "ApprovedPathRegistry",
    "PathPolicyError", "UnsafePathError", "AppendOnlyViolationError", "DraftStore",
    "FrozenRecordStore", "ResearchWriteService", "ResearchOperationsService",
    "ArtifactNode", "CatalogueIssue", "ArtifactCatalogue", "ArtifactCatalogueBuilder",
    "write_catalogue", "read_catalogue", "catalogue_report", "ResearchQueueService",
]
