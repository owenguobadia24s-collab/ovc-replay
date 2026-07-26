"""Deterministic Research Operations evidence and operator services.

RO-WP3 adds a no-mutation QA runner, replaceable typed read model and local
read-only console projection. These surfaces perform no Git, R2, selector,
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
from .console import ConsoleWriteDenied, ResearchConsole
from .identity import DuplicateRecordIdError, RecordIdRegistry, deterministic_record_id
from .lifecycle import FrozenRecordMutationError, freeze_record, supersede_record, verify_frozen_record
from .operations import ResearchOperationsService
from .paths import ApprovedPathRegistry, PathPolicyError, UnsafePathError
from .qa import QAAssertion, QARun, QARunner, required_fields_check
from .queues import ResearchQueueService
from .read_model import ReadModelBuilder, ReadModelNode, ResearchReadModel, query_nodes
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
    "QAAssertion", "QARun", "QARunner", "required_fields_check",
    "ReadModelNode", "ResearchReadModel", "ReadModelBuilder", "query_nodes",
    "ConsoleWriteDenied", "ResearchConsole",
]
