"""Synthetic-only C2E2-WP5 assurance orchestration.

The real-source replay entry point is intentionally absent. C2E2-G6-RUN-AUTH is
required before any source-run implementation can be invoked.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from .assurance_metrics import build_conflict_metric_receipt, build_conflict_metrics
from .checkpoint import create_checkpoint, verify_resume
from .persistence import build_stream_manifest
from .serialization import sha256_hex


def build_assurance_receipt(
    records: Sequence[Mapping[str, Any]],
    *, source_binding: Mapping[str, Any], boundary_pack_id: str,
    schema_ids: Sequence[str], code_hashes: Sequence[str],
    performance: Mapping[str, str], conflict_counts: Mapping[str, int],
    fixture_results: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    manifest = build_stream_manifest(records, source_binding=source_binding, boundary_pack_id=boundary_pack_id, schema_ids=schema_ids, code_hashes=code_hashes)
    reordered = build_stream_manifest(list(reversed(records)), source_binding=source_binding, boundary_pack_id=boundary_pack_id, schema_ids=schema_ids, code_hashes=code_hashes)
    layout_equivalent = manifest["ordered_record_ids"] == reordered["ordered_record_ids"] and manifest["ordered_record_hashes"] == reordered["ordered_record_hashes"]
    prefix_size = max(1, len(records) // 2)
    checkpoint = create_checkpoint(manifest, completed_partitions=["SYNTHETIC-P0"], logical_cursor=str(prefix_size), semantic_prefix_records=records[:prefix_size])
    restart = verify_resume(checkpoint, manifest, records[:prefix_size])
    metrics = build_conflict_metrics(**dict(conflict_counts))
    conflict_receipt = build_conflict_metric_receipt(run_id="C2E2.WP5.SYNTHETIC", boundary_pack_id=boundary_pack_id, metrics=metrics)
    fixture_rows = [dict(item) for item in fixture_results]
    all_fixtures_pass = bool(fixture_rows) and all(item.get("status") == "PASS" for item in fixture_rows)
    payload = {
        "schema": "c2e_assurance_receipt/v0_2",
        "run_id": "C2E2.WP5.SYNTHETIC",
        "mode": "SYNTHETIC_ADVERSARIAL_ONLY",
        "status": "PASS" if layout_equivalent and restart["status"] == "PASS" and all_fixtures_pass else "BLOCK",
        "boundary_pack_id": boundary_pack_id,
        "stream_manifest_id": manifest["stream_manifest_id"],
        "stream_logical_hash": manifest["logical_hash"],
        "layout_equivalence": "PASS" if layout_equivalent else "BLOCK",
        "restart_equivalence": restart["status"],
        "checkpoint_id": checkpoint["checkpoint_id"],
        "conflict_metric_receipt_hash": conflict_receipt["logical_sha256"],
        "fixture_count": len(fixture_rows),
        "fixture_pass_count": sum(item.get("status") == "PASS" for item in fixture_rows),
        "performance": dict(performance),
        "performance_threshold": None,
        "real_source_replay": False,
        "active_boundary_pack": "NONE",
        "selector_publication_validation": "DENIED",
        "authority_effect": "NONE",
    }
    payload["logical_sha256"] = sha256_hex(payload)
    return payload
