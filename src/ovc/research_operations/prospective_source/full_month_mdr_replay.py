from __future__ import annotations

import errno
import os
import shutil
import stat
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from . import full_month_mdr_compute as implementation
from .full_month_mdr_compute import *  # noqa: F401,F403
from .models import ProspectiveBar, parse_utc


ACCEPTED_SOURCE_MANIFEST_EMBEDDED_LOGICAL_SHA256 = (
    implementation.SOURCE_MANIFEST_LOGICAL_SHA256
)
ACCEPTED_SOURCE_MANIFEST_CONTENT_LOGICAL_SHA256 = (
    "aee0006826b4a9703416a4f171306df02f85b081f7f515e701ac8b0b2b409669"
)
PRICE_SET_ID = "RPS.PRICESET.GBPUSD.PD-JUNE-FM.20260530_20260703.v1"
SOURCE_MANIFEST_ID = (
    "RPS.SOURCE-MANIFEST.PD-JUNE-FM."
    f"{implementation.SOURCE_MANIFEST_LOGICAL_SHA256[:24]}"
)
C1_SET_ID = "RPS.C1SET.GBPUSD.PD-JUNE-FM.20260530_20260703.v1"
C1_MANIFEST_ID = (
    "RPS.C1MANIFEST.PD-JUNE-FM."
    f"{implementation.canonical_hash({'source': implementation.SOURCE_MANIFEST_LOGICAL_SHA256, 'formula': implementation.FORMULA_REGISTRY_ID})[:24]}"
)
_ORIGINAL_PRICE_PAYLOAD = implementation.price_payload
_ORIGINAL_EXECUTE = implementation.execute
_ORIGINAL_SHUTIL = implementation.shutil
_ORIGINAL_RMTREE = shutil.rmtree
_CLEANUP_RETRY_DELAYS_SECONDS = (0.05, 0.10, 0.20, 0.40, 0.80, 1.00)
_RETRYABLE_CLEANUP_ERRNOS = {errno.EACCES, errno.EPERM, errno.EBUSY}
_RETRYABLE_WINDOWS_ERRORS = {5, 32, 145}


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


def price_payload(bar: ProspectiveBar, source_object_id: str) -> dict[str, Any]:
    """Emit the accepted prospective namespace required by frozen C1/C2 adapters."""

    payload = _ORIGINAL_PRICE_PAYLOAD(bar, source_object_id)
    payload["source_bar_id"] = (
        f"rps-price:{implementation.canonical_hash(bar.logical_dict())}"
    )
    return payload


def _retryable_cleanup_error(exc: OSError) -> bool:
    return (
        isinstance(exc, PermissionError)
        or getattr(exc, "errno", None) in _RETRYABLE_CLEANUP_ERRNOS
        or getattr(exc, "winerror", None) in _RETRYABLE_WINDOWS_ERRORS
    )


def _make_tree_writable(root: Path) -> None:
    """Best-effort removal of read-only attributes before a cleanup retry."""

    if not root.exists():
        return
    for current, directories, files in os.walk(root, topdown=False):
        current_path = Path(current)
        for name in files:
            try:
                os.chmod(current_path / name, stat.S_IREAD | stat.S_IWRITE)
            except OSError:
                pass
        for name in directories:
            try:
                os.chmod(
                    current_path / name,
                    stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC,
                )
            except OSError:
                pass
    try:
        os.chmod(root, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
    except OSError:
        pass


def _remove_tree_with_bounded_retry(
    path: Path,
    *,
    rmtree: Callable[[Path], None] = _ORIGINAL_RMTREE,
    sleeper: Callable[[float], None] = time.sleep,
) -> None:
    last_error: OSError | None = None
    for delay in (0.0, *_CLEANUP_RETRY_DELAYS_SECONDS):
        if delay:
            sleeper(delay)
        _make_tree_writable(path)
        try:
            rmtree(path)
            return
        except OSError as exc:
            if not path.exists():
                return
            if not _retryable_cleanup_error(exc):
                raise
            last_error = exc
    if last_error is not None:
        raise last_error


def _rename_with_bounded_retry(
    source: Path,
    target: Path,
    *,
    sleeper: Callable[[float], None] = time.sleep,
) -> None:
    last_error: OSError | None = None
    for delay in (0.0, *_CLEANUP_RETRY_DELAYS_SECONDS):
        if delay:
            sleeper(delay)
        try:
            source.rename(target)
            return
        except OSError as exc:
            if target.exists() and not source.exists():
                return
            if not _retryable_cleanup_error(exc):
                raise
            last_error = exc
    if last_error is not None:
        raise last_error


def dispose_determinism_workspace(
    path: Path,
    *,
    rmtree: Callable[[Path], None] = _ORIGINAL_RMTREE,
    sleeper: Callable[[float], None] = time.sleep,
) -> Path | None:
    """Remove pass B, or preserve it outside the candidate after bounded denial.

    A transient Windows scanner or filesystem handle must not invalidate an
    already byte-identical deterministic replay. If bounded retries cannot remove
    pass B, the duplicate workspace is moved to the compute quarantine with an
    explicit receipt. The candidate staging tree remains complete and contains
    only the manifest-bound payload and compact receipts.
    """

    try:
        _remove_tree_with_bounded_retry(path, rmtree=rmtree, sleeper=sleeper)
        return None
    except OSError as exc:
        if not _retryable_cleanup_error(exc):
            raise
        compute_root = path.parent.parent
        quarantine_root = compute_root / "quarantine"
        quarantine_root.mkdir(parents=True, exist_ok=True)
        target = quarantine_root / (
            "PD-JUNE-FM-WP2.DETERMINISM-CLEANUP."
            f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}."
            f"{uuid.uuid4().hex[:8]}"
        )
        implementation.common.write_json(
            path / "cleanup-receipt.json",
            {
                "schema": "ovc-pd-june-full-month-mdr-wp2-cleanup-quarantine/v1",
                "programme_id": implementation.PROGRAMME_ID,
                "packet_id": implementation.PACKET_ID,
                "slice_id": implementation.SLICE_ID,
                "workspace_role": "DETERMINISTIC_INDEPENDENT_RERUN_PASS_B",
                "reason": str(exc),
                "disposition": "QUARANTINED_AFTER_BOUNDED_WINDOWS_CLEANUP_DENIAL",
                "deterministic_inventory_comparison": "PASS_BYTE_IDENTICAL_BEFORE_CLEANUP",
                "candidate_payload_mutated": False,
                "provider_network_access_performed": False,
                "release_mutation_performed": False,
                "repair_performed": False,
                "r2_publication": "DENIED",
                "validation_consumption": "DENIED",
            },
        )
        _rename_with_bounded_retry(path, target, sleeper=sleeper)
        print(
            "PD-JUNE-FM-WP2 warning: pass-B cleanup remained access-denied "
            f"after bounded retries; duplicate workspace preserved at {target}",
            file=sys.stderr,
        )
        return target


class _ScopedShutilProxy:
    """Delegate shutil except for the pass-B cleanup operation."""

    def __getattr__(self, name: str) -> Any:
        return getattr(_ORIGINAL_SHUTIL, name)

    @staticmethod
    def rmtree(path: str | os.PathLike[str]) -> None:
        dispose_determinism_workspace(Path(path))


_SHUTIL_PROXY = _ScopedShutilProxy()


def execute(
    repository_root: Path,
    *,
    authority_gate: str,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Run the original replay with a scoped Windows-safe pass-B cleanup."""

    previous_shutil = implementation.shutil
    implementation.shutil = _SHUTIL_PROXY
    try:
        return _ORIGINAL_EXECUTE(
            repository_root,
            authority_gate=authority_gate,
            environ=environ,
        )
    finally:
        implementation.shutil = previous_shutil


# Functions defined in the implementation module resolve globals in that module.
# Bind the corrected, tested policies before exposing execute/main entrypoints.
implementation.PRICE_SET_ID = PRICE_SET_ID
implementation.SOURCE_MANIFEST_ID = SOURCE_MANIFEST_ID
implementation.C1_SET_ID = C1_SET_ID
implementation.C1_MANIFEST_ID = C1_MANIFEST_ID
implementation.verify_frozen_source = verify_frozen_source
implementation.complete_segments = complete_segments
implementation.price_payload = price_payload
implementation.execute = execute


if __name__ == "__main__":
    raise SystemExit(implementation.main())
