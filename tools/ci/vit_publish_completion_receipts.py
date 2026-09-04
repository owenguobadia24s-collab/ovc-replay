#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
from typing import Any, Callable, Mapping, Sequence


class RemoteReceiptPublishError(RuntimeError):
    pass


Run = Callable[..., subprocess.CompletedProcess[bytes]]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _normalise_prefix(prefix: str) -> str:
    value = str(prefix).strip().strip("/")
    if not value:
        raise RemoteReceiptPublishError("REMOTE_RECEIPT_PREFIX_EMPTY")
    parts = PurePosixPath(value).parts
    if any(part in {"", ".", ".."} for part in parts):
        raise RemoteReceiptPublishError("REMOTE_RECEIPT_PREFIX_INVALID")
    return "/".join(parts)


def _remote_ref(remote: str, prefix: str, relative: str) -> str:
    remote_name = str(remote).strip()
    if not remote_name or ":" in remote_name:
        raise RemoteReceiptPublishError("REMOTE_RECEIPT_REMOTE_INVALID")
    rel = PurePosixPath(relative)
    if rel.is_absolute() or any(part in {"", ".", ".."} for part in rel.parts):
        raise RemoteReceiptPublishError("REMOTE_RECEIPT_RELATIVE_PATH_INVALID")
    return f"{remote_name}:{prefix}/{rel.as_posix()}"


def _run_bytes(
    args: Sequence[str],
    *,
    runner: Run,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    return runner(
        list(args),
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _remote_stat(remote_ref: str, *, runner: Run) -> Mapping[str, Any] | None:
    proc = _run_bytes(
        ["rclone", "lsjson", "--stat", "--s3-no-check-bucket", remote_ref],
        runner=runner,
        check=False,
    )
    if proc.returncode == 3:
        return None
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RemoteReceiptPublishError(f"REMOTE_RECEIPT_STAT_FAILED:{proc.returncode}:{detail}")
    raw = proc.stdout.decode("utf-8", errors="strict").strip()
    if not raw:
        raise RemoteReceiptPublishError("REMOTE_RECEIPT_STAT_EMPTY_SUCCESS")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RemoteReceiptPublishError("REMOTE_RECEIPT_STAT_INVALID_JSON") from exc
    if not isinstance(value, Mapping):
        raise RemoteReceiptPublishError("REMOTE_RECEIPT_STAT_INVALID")
    if value.get("IsDir") is True:
        raise RemoteReceiptPublishError("REMOTE_RECEIPT_KEY_IS_DIRECTORY")
    return dict(value)


def _remote_bytes(remote_ref: str, *, runner: Run) -> bytes:
    proc = _run_bytes(
        ["rclone", "cat", "--s3-no-check-bucket", remote_ref],
        runner=runner,
    )
    return bytes(proc.stdout)


def _local_files(root: Path) -> tuple[Path, ...]:
    if not root.is_dir():
        raise RemoteReceiptPublishError("REMOTE_RECEIPT_LOCAL_ROOT_MISSING")
    files: list[Path] = []
    resolved_root = root.resolve()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise RemoteReceiptPublishError("REMOTE_RECEIPT_SYMLINK_FORBIDDEN")
        if path.is_dir():
            continue
        if not path.is_file():
            raise RemoteReceiptPublishError("REMOTE_RECEIPT_NONFILE_FORBIDDEN")
        resolved = path.resolve()
        try:
            resolved.relative_to(resolved_root)
        except ValueError as exc:
            raise RemoteReceiptPublishError("REMOTE_RECEIPT_PATH_ESCAPE") from exc
        files.append(path)
    if not files:
        raise RemoteReceiptPublishError("REMOTE_RECEIPT_LOCAL_ROOT_EMPTY")
    return tuple(files)


def publish_receipt_tree(
    *,
    local_root: str | Path,
    remote: str,
    prefix: str,
    runner: Run = subprocess.run,
) -> Mapping[str, Any]:
    root = Path(local_root).resolve()
    normalised_prefix = _normalise_prefix(prefix)
    objects: list[Mapping[str, Any]] = []

    for path in _local_files(root):
        relative = path.relative_to(root).as_posix()
        ref = _remote_ref(remote, normalised_prefix, relative)
        local_bytes = path.read_bytes()
        local_sha = _sha256(local_bytes)
        stat = _remote_stat(ref, runner=runner)
        if stat is not None:
            remote_bytes = _remote_bytes(ref, runner=runner)
            if remote_bytes != local_bytes:
                raise RemoteReceiptPublishError(
                    f"REMOTE_RECEIPT_COLLISION:{relative}:{local_sha}:{_sha256(remote_bytes)}"
                )
            mode = "EXISTING_IDENTICAL"
        else:
            _run_bytes(
                [
                    "rclone",
                    "copyto",
                    "--immutable",
                    "--s3-no-check-bucket",
                    str(path),
                    ref,
                ],
                runner=runner,
            )
            remote_bytes = _remote_bytes(ref, runner=runner)
            if remote_bytes != local_bytes:
                raise RemoteReceiptPublishError(
                    f"REMOTE_RECEIPT_READBACK_MISMATCH:{relative}:{local_sha}:{_sha256(remote_bytes)}"
                )
            mode = "UPLOADED_AND_VERIFIED"
        objects.append(
            {
                "relative_path": relative,
                "remote_ref": ref,
                "sha256": local_sha,
                "bytes": len(local_bytes),
                "mode": mode,
            }
        )

    report_core = {
        "schema": "ovc-vit-remote-receipt-publication-report/v1",
        "remote": str(remote),
        "prefix": normalised_prefix,
        "object_count": len(objects),
        "objects": objects,
        "overwrite": False,
        "delete": False,
        "readback_verified": True,
        "authority_effect": "NONE",
    }
    encoded = json.dumps(report_core, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {**report_core, "report_id": hashlib.sha256(encoded).hexdigest()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-root", required=True)
    parser.add_argument("--remote", default="ovc_r2")
    parser.add_argument(
        "--prefix",
        default="ovc-evidence/development/vit-completion-receipts/v1",
    )
    parser.add_argument("--report")
    args = parser.parse_args()
    try:
        report = publish_receipt_tree(
            local_root=args.local_root,
            remote=args.remote,
            prefix=args.prefix,
        )
        text = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.report:
            Path(args.report).write_text(text, encoding="utf-8")
        print("OVC_VIT_REMOTE_RECEIPT_PUBLICATION " + json.dumps(report, sort_keys=True), flush=True)
        return 0
    except (RemoteReceiptPublishError, OSError, UnicodeError, subprocess.SubprocessError) as exc:
        print(
            "::error title=DSAI3V remote receipt publication failed::"
            f"OVC_VIT_REMOTE_RECEIPT_PUBLICATION_FAILED: {exc}",
            flush=True,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
