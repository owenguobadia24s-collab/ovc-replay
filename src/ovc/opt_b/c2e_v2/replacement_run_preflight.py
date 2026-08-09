"""Fail-closed preflight for C2E2 replacement real-source run preparation.

This module does not build new C2 semantics. It only verifies whether accepted
C2 replay artifacts already materialise the observation-level identities and
structural/parent outputs required by the frozen C2 -> C2E handoff survey.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

REQUIRED_SURFACE_MARKERS = (
    "observation_id",
    "profile_output_id",
    "context_bundle_id",
)
REQUIRED_ID_PREFIX_MARKERS = (
    "C2.OBSERVATION",
    "C2.FORMULA.OUTPUT",
    "C2.PARENT.BUNDLE",
)


class ReplacementRunPreflightError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def count_lines(path: Path) -> int:
    with path.open("rb") as handle:
        return sum(1 for _ in handle)


def scan_markers(path: Path, markers: Iterable[str] = (*REQUIRED_SURFACE_MARKERS, *REQUIRED_ID_PREFIX_MARKERS)) -> dict[str, int]:
    wanted = tuple(str(item) for item in markers)
    counts = {marker: 0 for marker in wanted}
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            for marker in wanted:
                counts[marker] += raw.count(marker)
    return counts


def inspect_json_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ReplacementRunPreflightError("MANIFEST_OBJECT_REQUIRED")
    scope = value.get("scope", {})
    return {
        "sha256": sha256_file(path),
        "schema": value.get("schema"),
        "binding_id": value.get("binding_id"),
        "logical_population_sha256": value.get("logical_population_sha256"),
        "opportunity_types": list(scope.get("opportunity_types", [])),
        "object_families": list(scope.get("object_families", [])),
        "sequence_lengths": list(scope.get("sequence_lengths", [])),
        "counts": dict(value.get("counts", {})),
    }


def assess_accepted_surface(*, output_manifest: Path, replay_artifacts: Mapping[str, Path]) -> dict[str, Any]:
    manifest = inspect_json_manifest(output_manifest)
    artifact_rows = []
    all_marker_totals = {marker: 0 for marker in (*REQUIRED_SURFACE_MARKERS, *REQUIRED_ID_PREFIX_MARKERS)}
    for name, path in sorted(replay_artifacts.items()):
        counts = scan_markers(path)
        for marker, count in counts.items():
            all_marker_totals[marker] += count
        artifact_rows.append({
            "artifact": name,
            "sha256": sha256_file(path),
            "line_count": count_lines(path),
            "marker_counts": counts,
        })
    sequence_window_population = manifest["opportunity_types"] == ["REGISTERED_SEQUENCE_WINDOW"]
    required_surface_materialised = all(count > 0 for count in all_marker_totals.values())
    return {
        "schema": "c2e2_replacement_run_source_surface_preflight/v1",
        "manifest": manifest,
        "artifacts": artifact_rows,
        "marker_totals": all_marker_totals,
        "sequence_window_population": sequence_window_population,
        "required_observation_profile_parent_surface_materialised": required_surface_materialised,
        "disposition": "PASS" if (not sequence_window_population and required_surface_materialised) else "BLOCK",
    }
