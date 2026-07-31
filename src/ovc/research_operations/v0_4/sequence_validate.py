from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .index_common import RO4IndexError, logical_hash, sha256_file
from .sequence_common import CANDIDATE_AUTHORITY, DENIED_PD_FIELDS, iter_gzip_jsonl
from .sequence_workspace import workspace_inventory

EXPECTED_G2_HASH = "eb5435443be26e956334c4aedd12c2a5280fc815f014f24bd74b064bf4e6eaeb"


def validate_sequence_evidence(output_dir: Path, expected_g1_hash: str) -> dict[str, Any]:
    manifest_path = output_dir / "g3-manifest.json"
    if not manifest_path.is_file():
        raise RO4IndexError("RO4_G3_MANIFEST_MISSING")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    core = dict(manifest); declared = core.pop("logical_hash", None)
    if logical_hash(core) != declared:
        raise RO4IndexError("RO4_G3_MANIFEST_LOGICAL_HASH_MISMATCH")
    if manifest.get("authority") != CANDIDATE_AUTHORITY:
        raise RO4IndexError("RO4_G3_AUTHORITY_MISMATCH")
    if manifest.get("source_g1_logical_hash") != expected_g1_hash:
        raise RO4IndexError("RO4_G3_PARENT_G1_HASH_MISMATCH")
    if manifest.get("source_g2_logical_hash") != EXPECTED_G2_HASH:
        raise RO4IndexError("RO4_G3_PARENT_G2_HASH_MISMATCH")
    if manifest.get("validation_consumption") != "LOCKED_UNCONSUMED":
        raise RO4IndexError("VALIDATION_DENIAL_NOT_PRESERVED")
    if manifest.get("sample_state") != "FULL_POPULATION_NO_SAMPLING":
        raise RO4IndexError("SILENT_OR_UNAUTHORISED_SEQUENCE_SAMPLING")
    if manifest.get("semantic_authority") != "NONE" or manifest.get("promotion_path") != "DENIED":
        raise RO4IndexError("SEMANTIC_OR_PROMOTION_PATH_PRESENT")
    if manifest.get("pd_population_merge") != "DENIED":
        raise RO4IndexError("PD_POPULATION_ISOLATION_FAILURE")
    if manifest.get("synthetic_controls_operator_facing") != 0:
        raise RO4IndexError("SYNTHETIC_CONTROL_OPERATOR_LEAK")

    artifacts = {item["artifact_type"]: item for item in manifest.get("artifacts", [])}
    required = {
        "candidates", "real_controls", "blinded_batch", "sealed_answer_key", "diversity_audit",
        "review_signatures", "machine_ablation_assurance", "pd_isolation_assurance",
        "vocabulary_assurance", "operation_mode_assurance", "population_inventory",
        "sequence_population_workspace",
    }
    if set(artifacts) != required:
        raise RO4IndexError("RO4_G3_ARTIFACT_SET_MISMATCH")
    for item in artifacts.values():
        path = output_dir / item["file"]
        if not path.is_file():
            raise RO4IndexError(f"RO4_G3_ARTIFACT_MISSING:{item['artifact_type']}")
        if item["artifact_type"] == "sequence_population_workspace":
            if item.get("byte_identity") != "LOGICAL_ONLY_REPLACEABLE_SQLITE":
                raise RO4IndexError("RO4_G3_WORKSPACE_BYTE_IDENTITY_SCOPE_MISMATCH")
        elif sha256_file(path) != item["sha256"]:
            raise RO4IndexError(f"RO4_G3_ARTIFACT_HASH_MISMATCH:{item['artifact_type']}")

    workspace_path = output_dir / artifacts["sequence_population_workspace"]["file"]
    inventory = workspace_inventory(workspace_path)
    if inventory["logical_hash"] != artifacts["sequence_population_workspace"]["logical_hash"]:
        raise RO4IndexError("RO4_G3_WORKSPACE_LOGICAL_HASH_MISMATCH")
    if inventory["window_count"] != manifest["window_count"]:
        raise RO4IndexError("RO4_G3_WINDOW_COUNT_MISMATCH")
    if max((item["max_calendar_partition_count"] for item in inventory["partitions"]), default=0) > 100_000:
        raise RO4IndexError("RO4_G3_WINDOW_CAP_FAILURE")

    candidate_count = 0
    candidate_ids: set[str] = set()
    control_ids_required = 0
    for record in iter_gzip_jsonl(output_dir / artifacts["candidates"]["file"]):
        candidate_count += 1
        candidate_id = record.get("candidate_id", "")
        if not candidate_id.startswith("RO4.RECURRENCE.") or candidate_id in candidate_ids:
            raise RO4IndexError("INVALID_OR_DUPLICATE_RECURRENCE_ID")
        candidate_ids.add(candidate_id)
        if record.get("authority") != CANDIDATE_AUTHORITY or record.get("semantic_label") != "PROHIBITED":
            raise RO4IndexError("CANDIDATE_AUTHORITY_OR_SEMANTIC_FAILURE")
        if record.get("signature_type") not in {"EXACT", "DECLARED_DISTANCE"}:
            raise RO4IndexError("INVALID_SIGNATURE_TYPE")
        if record.get("full_member_count", 0) < 2 or len(record.get("member_sequence_ids", [])) < 2:
            raise RO4IndexError("RECURRENCE_MEMBER_CARDINALITY_FAILURE")
        if not record.get("matched_control_ids") or not record.get("population_control_ids"):
            raise RO4IndexError("REAL_CONTROL_REQUIREMENT_FAILURE")
        control_ids_required += len(record["matched_control_ids"]) + len(record["population_control_ids"])
        leaked = DENIED_PD_FIELDS.intersection(record)
        if leaked or any(key.startswith("pd_") for key in record):
            raise RO4IndexError("RO4_PD_FIELD_LEAK:" + ",".join(sorted(leaked)))
    if candidate_count != manifest["recurrence_candidate_count"]:
        raise RO4IndexError("RECURRENCE_CANDIDATE_COUNT_MISMATCH")

    control_count = 0
    for record in iter_gzip_jsonl(output_dir / artifacts["real_controls"]["file"]):
        control_count += 1
        if record.get("candidate_id") not in candidate_ids:
            raise RO4IndexError("CONTROL_UNKNOWN_CANDIDATE")
        controls = record.get("real_controls", [])
        if not controls or any(item.get("synthetic") is not False for item in controls):
            raise RO4IndexError("SYNTHETIC_OR_MISSING_REAL_CONTROL")
        if record.get("synthetic_controls_operator_facing") != "DENIED":
            raise RO4IndexError("MACHINE_CONTROL_PRESENTATION_DENIAL_MISSING")
    if control_count != candidate_count:
        raise RO4IndexError("CANDIDATE_CONTROL_LEDGER_COUNT_MISMATCH")

    answer_path = output_dir / artifacts["sealed_answer_key"]["file"]
    batch = json.loads((output_dir / artifacts["blinded_batch"]["file"]).read_text(encoding="utf-8"))
    if batch.get("answer_key_sha256") != sha256_file(answer_path):
        raise RO4IndexError("SEALED_ANSWER_KEY_HASH_MISMATCH")
    if batch.get("answer_key_access_state") != "SEALED_SEPARATE" or not batch.get("blinded"):
        raise RO4IndexError("BLINDING_OR_ANSWER_KEY_SEPARATION_FAILURE")
    if any("true_class" in card or "control_type" in card for card in batch.get("cards", [])):
        raise RO4IndexError("BLINDED_BATCH_ANSWER_LEAK")
    if batch.get("composition", {}).get("synthetic_controls") != 0:
        raise RO4IndexError("SYNTHETIC_CONTROL_IN_REVIEW_BATCH")

    diversity = json.loads((output_dir / artifacts["diversity_audit"]["file"]).read_text(encoding="utf-8"))
    if diversity["full_population"]["status"] not in {"PASS", "SIGNATURE_CONCENTRATION_WARNING"}:
        raise RO4IndexError("FULL_POPULATION_DIVERSITY_NOT_EVALUABLE")
    if diversity["operator_batch"]["status"] == "SIGNATURE_CONCENTRATION_WARNING":
        raise RO4IndexError("OPERATOR_BATCH_SIGNATURE_CAP_FAILURE")
    if diversity["ro4_g4_acknowledgement_required"] != (diversity["full_population"]["status"] == "SIGNATURE_CONCENTRATION_WARNING"):
        raise RO4IndexError("DIVERSITY_ACKNOWLEDGEMENT_STATE_MISMATCH")

    machine = json.loads((output_dir / artifacts["machine_ablation_assurance"]["file"]).read_text(encoding="utf-8"))
    if machine.get("result") != "PASS" or machine.get("operator_surface_state") != "DENIED" or machine.get("operator_facing_artifacts"):
        raise RO4IndexError("MACHINE_ABLATION_PRESENTATION_FAILURE")
    pd = json.loads((output_dir / artifacts["pd_isolation_assurance"]["file"]).read_text(encoding="utf-8"))
    if pd.get("result") != "PASS" or pd.get("population_merge") != "DENIED" or pd.get("evidence_bridge") != "DENIED":
        raise RO4IndexError("RO4_PD_ISOLATION_FAILURE")
    vocab = json.loads((output_dir / artifacts["vocabulary_assurance"]["file"]).read_text(encoding="utf-8"))
    if vocab.get("result") != "PASS" or vocab.get("forbidden_field_hits"):
        raise RO4IndexError("SEMANTIC_VOCABULARY_ASSURANCE_FAILURE")
    mode = json.loads((output_dir / artifacts["operation_mode_assurance"]["file"]).read_text(encoding="utf-8"))
    if (
        mode.get("result") != "PASS"
        or mode.get("replay_to_prospective_translation") != "DENIED"
        or mode.get("post_cutoff_identifier_access") != "ABSENT_NOT_HIDDEN"
        or mode.get("validation_consumption") != "LOCKED_UNCONSUMED"
    ):
        raise RO4IndexError("OPERATION_MODE_OR_CUTOFF_ASSURANCE_FAILURE")
    return {
        "status": "PASS",
        "window_count": manifest["window_count"],
        "recurrence_candidate_count": candidate_count,
        "real_control_ledgers": control_count,
        "operator_batch_count": len(batch["cards"]),
        "diversity_status": diversity["full_population"]["status"],
        "logical_hash": declared,
    }
