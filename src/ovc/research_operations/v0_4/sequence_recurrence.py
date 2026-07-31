from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .index_common import RO4IndexError
from .sequence_common import SequenceBuildResult, declared_distance, diversity_audit
from .sequence_finalize import finalize_sequence_evidence
from .sequence_validate import validate_sequence_evidence
from .sequence_workspace import build_sequence_partition, connect_workspace, workspace_inventory


def build_full_sequence_evidence(
    *, index_dir: Path, workspace_path: Path, output_dir: Path, benchmark_path: Path | None = None
) -> SequenceBuildResult:
    manifest_path = index_dir / "index-manifest.json"
    if not manifest_path.is_file():
        raise RO4IndexError("RO4_G1_INDEX_MANIFEST_MISSING")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in sorted(manifest["partitions"], key=lambda value: value["partition_id"]):
        build_sequence_partition(
            index_dir=index_dir, workspace_path=workspace_path, partition_id=item["partition_id"]
        )
    return finalize_sequence_evidence(
        index_dir=index_dir, workspace_path=workspace_path, output_dir=output_dir,
        benchmark_path=benchmark_path,
    )


__all__ = [
    "SequenceBuildResult", "build_full_sequence_evidence", "build_sequence_partition",
    "connect_workspace", "declared_distance", "diversity_audit", "finalize_sequence_evidence",
    "validate_sequence_evidence", "workspace_inventory",
]
