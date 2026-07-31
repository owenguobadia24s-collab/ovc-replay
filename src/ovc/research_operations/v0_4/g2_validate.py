from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .g2_common import _iter_gzip_jsonl, _stream_hash, _validate_record_hash
from .index_common import AXES, RO4IndexError, canonical_bytes, logical_hash, sha256_file


def validate_g2_evidence(output_dir: Path, expected_g1_hash: str) -> dict[str, Any]:
    manifest_path = output_dir / "g2-manifest.json"
    if not manifest_path.is_file():
        raise RO4IndexError("RO4_G2_MANIFEST_MISSING")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("source_g1_logical_hash") != expected_g1_hash:
        raise RO4IndexError("RO4_G2_PARENT_HASH_MISMATCH")
    if manifest.get("validation_consumption") != "LOCKED_UNCONSUMED":
        raise RO4IndexError("VALIDATION_DENIAL_NOT_PRESERVED")
    artifact_map = {item["artifact_type"]: item for item in manifest.get("artifacts", [])}
    if set(artifact_map) != {"matrices", "persistence", "conflicts", "cross_scale"}:
        raise RO4IndexError("RO4_G2_ARTIFACT_SET_MISMATCH")
    for item in artifact_map.values():
        path = output_dir / item["file"]
        if not path.is_file() or sha256_file(path) != item["sha256"]:
            raise RO4IndexError(f"RO4_G2_ARTIFACT_HASH_MISMATCH:{item['artifact_type']}")

    matrices = json.loads((output_dir / artifact_map["matrices"]["file"]).read_text(encoding="utf-8"))
    if matrices.get("source_g1_logical_hash") != expected_g1_hash:
        raise RO4IndexError("MATRIX_PARENT_HASH_MISMATCH")
    if _stream_hash(matrices["records"]) != matrices["record_stream_sha256"]:
        raise RO4IndexError("MATRIX_STREAM_HASH_MISMATCH")
    matrix_wrapper_core = dict(matrices)
    matrix_declared = matrix_wrapper_core.pop("logical_hash", None)
    if logical_hash(matrix_wrapper_core) != matrix_declared:
        raise RO4IndexError("MATRIX_WRAPPER_HASH_MISMATCH")
    for record in matrices["records"]:
        _validate_record_hash(record, record.get("matrix_id", "matrix"))
        if record["eligible_denominator"] + record.get("missing_count", 0) + record.get("excluded_count", 0) != record["total_transition_count"]:
            raise RO4IndexError("MATRIX_COUNT_CONSERVATION_FAILURE")
        for cell in record["cells"]:
            if cell["display_text"] != f"{cell['count']} of {cell['eligible_denominator']} eligible records":
                raise RO4IndexError("COUNT_PRESENTATION_MISMATCH")
            if any(key in cell for key in ("percentage", "ratio", "probability", "rank", "colour_intensity", "bar_length")):
                raise RO4IndexError("PROBABILITY_SHAPED_MATRIX_FIELD")

    conflicts = json.loads((output_dir / artifact_map["conflicts"]["file"]).read_text(encoding="utf-8"))
    if _stream_hash(conflicts["records"]) != conflicts["record_stream_sha256"]:
        raise RO4IndexError("CONFLICT_STREAM_HASH_MISMATCH")
    conflict_wrapper_core = dict(conflicts)
    conflict_declared = conflict_wrapper_core.pop("logical_hash", None)
    if logical_hash(conflict_wrapper_core) != conflict_declared:
        raise RO4IndexError("CONFLICT_WRAPPER_HASH_MISMATCH")
    for record in conflicts["records"]:
        _validate_record_hash(record, record.get("conflict_run_id", "conflict"))
        if len(record["participating_axes"]) < 2 or not record["matched_control_ids"]:
            raise RO4IndexError("INVALID_CONFLICT_VECTOR_OR_CONTROL")
        if any(key in record for key in ("winner", "composite_score", "severity_rank", "threshold_recommendation")):
            raise RO4IndexError("CONFLICT_COMPOSITE_OR_RECOMMENDATION_FIELD")

    persistence_count = 0
    persistence_digest = hashlib.sha256()
    for record in _iter_gzip_jsonl(output_dir / artifact_map["persistence"]["file"]):
        line = canonical_bytes(record)
        persistence_digest.update(line)
        if not record.get("run_id", "").startswith("RO4.RUN.") or not isinstance(record.get("logical_hash"), str):
            raise RO4IndexError("INVALID_PERSISTENCE_IDENTITY")
        if record["duration_records"] != len(record["member_state_ids"]) or record["duration_records"] < 1:
            raise RO4IndexError("INVALID_PERSISTENCE_PARTITION")
        persistence_count += 1
    if persistence_count != artifact_map["persistence"]["record_count"] or persistence_digest.hexdigest() != artifact_map["persistence"]["record_stream_sha256"]:
        raise RO4IndexError("PERSISTENCE_STREAM_RECONCILIATION_FAILURE")

    cross_count = 0
    cross_digest = hashlib.sha256()
    seen_projection_ids: set[str] = set()
    for record in _iter_gzip_jsonl(output_dir / artifact_map["cross_scale"]["file"]):
        line = canonical_bytes(record)
        cross_digest.update(line)
        projection_id = record["projection_id"]
        if not projection_id.startswith("RO4.XSCALE.") or not isinstance(record.get("logical_hash"), str):
            raise RO4IndexError("INVALID_CROSS_SCALE_IDENTITY")
        if projection_id in seen_projection_ids:
            raise RO4IndexError("DUPLICATE_CROSS_SCALE_PROJECTION")
        seen_projection_ids.add(projection_id)
        if record["parent_state_id"] is None and any(
            value["relation"] != "MISSING" for value in record["axis_relations"].values()
        ):
            raise RO4IndexError("UNKNOWN_PARENT_BRIDGED")
        if set(record["axis_relations"]) != set(AXES):
            raise RO4IndexError("CROSS_SCALE_FIVE_AXIS_SET_MISMATCH")
        cross_count += 1
    if cross_count != artifact_map["cross_scale"]["record_count"] or cross_digest.hexdigest() != artifact_map["cross_scale"]["record_stream_sha256"]:
        raise RO4IndexError("CROSS_SCALE_STREAM_RECONCILIATION_FAILURE")

    core = dict(manifest)
    declared = core.pop("logical_hash", None)
    if logical_hash(core) != declared:
        raise RO4IndexError("RO4_G2_MANIFEST_LOGICAL_HASH_MISMATCH")
    return {
        "status": "PASS",
        **manifest["counts"],
        "logical_hash": declared,
        "matched_real_controls": manifest["matched_real_controls"],
    }

