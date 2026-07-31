from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from . import full_month_mdr_compute as implementation
from .full_month_mdr_compute import *  # noqa: F401,F403
from .models import ProspectiveBar, parse_utc


ACCEPTED_SOURCE_MANIFEST_EMBEDDED_LOGICAL_SHA256 = (
    implementation.SOURCE_MANIFEST_LOGICAL_SHA256
)
ACCEPTED_SOURCE_MANIFEST_CONTENT_LOGICAL_SHA256 = (
    "aee0006826b4a9703416a4f171306df02f85b081f7f515e701ac8b0b2b409669"
)


def validate_source_manifest_hashes(
    manifest: Mapping[str, Any],
) -> tuple[str, str]:
    """Validate the exact accepted A2 manifest without rewriting frozen bytes.

    The A2 acceptance amendment changed authority and censoring fields after the
    intake manifest's self-hash had been generated. The frozen file hash and the
    canonical hash of the accepted logical content are therefore validated
    independently, while the preserved embedded value remains an audited field.
    """

    logical = dict(manifest)
    claimed = logical.pop("manifest_sha256", None)
    if claimed != ACCEPTED_SOURCE_MANIFEST_EMBEDDED_LOGICAL_SHA256:
        raise implementation.ComputeError(
            "source manifest embedded logical SHA-256 mismatch"
        )
    observed = implementation.common.logical_sha(logical)
    if observed != ACCEPTED_SOURCE_MANIFEST_CONTENT_LOGICAL_SHA256:
        raise implementation.ComputeError(
            "source manifest accepted-content logical SHA-256 mismatch"
        )
    return str(claimed), observed


def verify_frozen_source(
    repository_root: Path,
    environ: Mapping[str, str],
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    """Verify the exact frozen source and corrected A2 manifest hash semantics."""

    index = implementation.load_source_acceptance_index(repository_root)
    root = (
        implementation.common.external_root(repository_root, environ)
        / "prospective-source"
        / "intake"
        / implementation.SLICE_ID
    )
    if not root.is_dir():
        raise implementation.ComputeError(
            f"accepted frozen source slice unavailable: {root}"
        )

    compact = {
        str(item["name"]): item for item in index.get("compact_files", [])
    }
    if len(compact) != 8:
        raise implementation.ComputeError(
            "compact source evidence inventory mismatch"
        )
    for name, item in compact.items():
        relative = (
            name if name == "source-slice-manifest.json"
            else f"receipts/{name}"
        )
        path = implementation.common.safe_file(root, relative)
        if path.stat().st_size != int(item["size_bytes"]):
            raise implementation.ComputeError(
                f"compact evidence size mismatch:{name}"
            )
        if implementation.common.sha_file(path) != item["sha256"]:
            raise implementation.ComputeError(
                f"compact evidence SHA-256 mismatch:{name}"
            )

    manifest_path = implementation.common.safe_file(
        root, "source-slice-manifest.json"
    )
    manifest = implementation.common.load_json(
        manifest_path,
        "INVALID_FULL_MONTH_SOURCE_MANIFEST",
    )
    validate_source_manifest_hashes(manifest)
    if (
        implementation.common.sha_file(manifest_path)
        != implementation.SOURCE_MANIFEST_FILE_SHA256
    ):
        raise implementation.ComputeError(
            "source manifest file SHA-256 mismatch"
        )

    manifest_required = {
        "slice_id": implementation.SLICE_ID,
        "source_window_start_utc": implementation.SOURCE_START,
        "source_window_end_exclusive_utc": implementation.SOURCE_END,
        "target_start_utc": implementation.TARGET_START,
        "target_end_exclusive_utc": implementation.TARGET_END,
        "target_eligibility": "TARGET_JUNE_ONLY",
        "coverage_state": (
            "ACCEPTED_WITH_EXPLICIT_PAIRED_PROVIDER_ABSENCE_AND_CENSORING"
        ),
        "frozen": True,
        "release_status": "NOT_A_RELEASE",
        "selector_eligibility": "NONE",
        "r2_publication": "DENIED",
        "validation_consumption": "DENIED",
    }
    for key, expected in manifest_required.items():
        if manifest.get(key) != expected:
            raise implementation.ComputeError(
                f"source manifest authority mismatch:{key}"
            )

    inventory = implementation.common.load_json(
        implementation.common.safe_file(
            root, "receipts/source-object-inventory.json"
        ),
        "INVALID_FULL_MONTH_SOURCE_OBJECT_INVENTORY",
    )
    if (
        inventory.get("slice_id") != implementation.SLICE_ID
        or inventory.get("source_object_count") != 4
    ):
        raise implementation.ComputeError(
            "source-object inventory identity mismatch"
        )
    expected = {
        str(item["object_id"]): item
        for item in index.get("source_objects", [])
    }
    observed = {
        str(item["object_id"]): item
        for item in inventory.get("source_objects", [])
    }
    if set(observed) != set(expected) or len(expected) != 4:
        raise implementation.ComputeError(
            "source-object identity inventory mismatch"
        )
    for object_id, item in expected.items():
        actual = observed[object_id]
        for field in (
            "clock",
            "side",
            "relative_path",
            "row_count",
            "size_bytes",
            "sha256",
            "schema_fingerprint",
            "first_timestamp_utc",
            "last_timestamp_utc",
        ):
            if actual.get(field) != item.get(field):
                raise implementation.ComputeError(
                    f"source-object metadata mismatch:{object_id}:{field}"
                )
        path = implementation.common.safe_file(
            root, str(item["relative_path"])
        )
        if path.stat().st_size != int(item["size_bytes"]):
            raise implementation.ComputeError(
                f"source-object size mismatch:{object_id}"
            )
        if implementation.common.sha_file(path) != item["sha256"]:
            raise implementation.ComputeError(
                f"source-object SHA-256 mismatch:{object_id}"
            )
    return root, index, inventory


def complete_segments(
    bars: Sequence[ProspectiveBar],
) -> list[list[ProspectiveBar]]:
    """Return every complete contiguous segment without dropping boundary bars."""

    ordered = sorted(bars, key=lambda item: item.start_utc)
    segments: list[list[ProspectiveBar]] = []
    current: list[ProspectiveBar] = []
    expected_seconds = implementation.CLOCK_SECONDS[ordered[0].clock] if ordered else 0
    previous_end: str | None = None

    for bar in ordered:
        if bar.quality_state != "COMPLETE":
            if current:
                segments.append(current)
                current = []
            previous_end = None
            continue

        duration = int(
            (parse_utc(bar.end_utc) - parse_utc(bar.start_utc)).total_seconds()
        )
        if duration != expected_seconds:
            raise implementation.ComputeError(
                f"unexpected bar duration:{bar.clock}:{bar.start_utc}"
            )

        if (
            previous_end is not None
            and parse_utc(bar.start_utc) != parse_utc(previous_end)
        ):
            if current:
                segments.append(current)
            current = []

        current.append(bar)
        previous_end = bar.end_utc

    if current:
        segments.append(current)
    return segments


# Functions defined in the implementation module resolve globals in that module.
# Bind the corrected, tested policies before exposing execute/main entrypoints.
implementation.verify_frozen_source = verify_frozen_source
implementation.complete_segments = complete_segments


if __name__ == "__main__":
    raise SystemExit(implementation.main())
