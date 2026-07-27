from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

from . import dukascopy_intake as base
from . import dukascopy_intake_rps_g1a as profile
from .gapped_source_contract import (
    COVERAGE_STATE,
    END,
    EXPANDED_LIMIT,
    GATE,
    QUARANTINE_ID,
    SLICE_ID,
    START,
    RecoveryError,
    assert_operator_local,
    build_inventory,
    copy_pinned,
    decode_rows,
    inspect,
    load_inventory,
    preflight,
    resolve_paths,
    sha_file,
    utc,
    write_json,
)
from .gapped_source_qa import evaluate


def source_objects(staging: Path, rows) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for (clock, side), values in sorted(rows.items()):
        path, payload = profile._profile_write_csv(
            staging,
            clock=clock,
            side=side,
            rows=values,
        )
        result.append(
            {
                "object_id": profile._profile_source_object_id(
                    clock,
                    side,
                ),
                "clock": clock,
                "side": side,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
                "row_count": len(values),
                "first_timestamp_utc": utc(
                    values[0].timestamp_utc
                ),
                "last_timestamp_utc": utc(
                    values[-1].timestamp_utc
                ),
                "schema_fingerprint": base._schema_fingerprint(),
                "relative_path": path.relative_to(staging).as_posix(),
            }
        )
    return result


def manifest(
    objects: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    payload: dict[str, object] = {
        "slice_id": SLICE_ID,
        "instrument": "GBPUSD",
        "provider": "DUKASCOPY",
        "source_window_start_utc": utc(START),
        "source_window_end_utc": utc(END),
        "source_objects": [
            {
                "object_id": item["object_id"],
                "clock": item["clock"],
                "side": item["side"],
                "sha256": item["sha256"],
            }
            for item in sorted(
                objects,
                key=lambda item: (
                    str(item["clock"]),
                    str(item["side"]),
                ),
            )
        ],
        "coverage_state": COVERAGE_STATE,
        "frozen": True,
        "release_status": "NOT_A_RELEASE",
        "selector_eligibility": "NONE",
        "r2_publication": "DENIED",
    }
    logical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    payload["manifest_sha256"] = hashlib.sha256(
        logical
    ).hexdigest()
    return payload


def failure_quarantine(
    staging: Path,
    reason: str,
) -> Path | None:
    if not staging.exists():
        return None
    root = staging.parent / "quarantine"
    root.mkdir(parents=True, exist_ok=True)
    target = root / (
        f"{SLICE_ID}.rps-g1b-recovery."
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}."
        f"{uuid.uuid4().hex[:8]}"
    )
    try:
        write_json(
            staging / "incident.json",
            {
                "schema": "ovc-rps-g1b-recovery-incident/v1",
                "slice_id": SLICE_ID,
                "source_quarantine_id": QUARANTINE_ID,
                "reason": reason,
                "accepted_source_slice_created": False,
                "source_quarantine_mutated": False,
                "authority": "NONE",
            },
        )
    except Exception:
        pass
    staging.rename(target)
    return target


def freeze(
    repository_root: Path,
    gate: str,
    environ: Mapping[str, str] | None = None,
) -> dict[str, object]:
    values = os.environ if environ is None else environ
    if gate != GATE:
        raise RecoveryError(
            f"exact operator approval binding required: --gate {GATE}"
        )
    assert_operator_local(values)
    paths = resolve_paths(repository_root, values)
    if paths.final.exists():
        if any(paths.final.iterdir()):
            raise RecoveryError(
                "refusing to overwrite existing destination: "
                f"{paths.final}"
            )
        paths.final.rmdir()
    inventory = load_inventory(paths)
    before = inspect(paths)
    staging = paths.intake / (
        f".{SLICE_ID}.rps-g1b.staging.{uuid.uuid4().hex}"
    )
    staging.mkdir(parents=False, exist_ok=False)
    try:
        copy_pinned(paths, staging, inventory)
        rows = decode_rows(staging)
        # The historical G1A profile supplies the exact June clock
        # boundary to the reused H1 audit without mutating its identity.
        with profile._amended_profile():
            gap, pair, h1, coverage, accepted = evaluate(rows)
        receipts = staging / "receipts"
        # Evidence is materialised before the pass/fail branch so a
        # failed recovery remains diagnosable after its staging quarantine.
        write_json(
            receipts / "gap-and-duplicate-qa.json",
            gap,
        )
        write_json(
            receipts / "bid-ask-reconciliation.json",
            pair,
        )
        write_json(
            receipts / "native-h1-reconciliation.json",
            h1,
        )
        write_json(
            receipts / "downstream-coverage-propagation.json",
            coverage,
        )
        write_json(
            receipts / "quarantine-checksum-inventory.json",
            inventory,
        )
        if not accepted:
            raise RecoveryError(
                "RPS-G1B gapped-source acceptance conditions did not pass"
            )
        objects = source_objects(staging, rows)
        if base._workspace_size(staging) > EXPANDED_LIMIT:
            raise RecoveryError(
                "expanded-byte limit exceeded during recovery freeze"
            )
        write_json(
            receipts / "source-object-inventory.json",
            {
                "schema": "ovc-rps-g1b-source-object-inventory/v1",
                "slice_id": SLICE_ID,
                "coverage_state": COVERAGE_STATE,
                "source_object_count": len(objects),
                "source_objects": objects,
            },
        )
        files = inventory.get("files")
        if not isinstance(files, list):
            raise RecoveryError(
                "checksum inventory files are invalid"
            )
        transport = [
            item
            for item in files
            if isinstance(item, dict)
            and str(item.get("relative_path", "")).startswith(
                "transport/"
            )
        ]
        write_json(
            receipts / "provider-request-receipt.json",
            {
                "schema": (
                    "ovc-rps-g1b-provider-provenance-receipt/v1"
                ),
                "gate": GATE,
                "slice_id": SLICE_ID,
                "provider": "DUKASCOPY",
                "adapter": "OVC_DIRECT_BI5_CANDLE_ADAPTER",
                "adapter_version": "1.3.0-rps-g1b-recovery",
                "source_window_start_utc": utc(START),
                "source_window_end_utc": utc(END),
                "logical_streams": [
                    "M1_BID",
                    "M1_ASK",
                    "H1_BID",
                    "H1_ASK",
                ],
                "transport_objects": transport,
                "source_quarantine_id": QUARANTINE_ID,
                "quarantine_inventory_sha256": inventory[
                    "inventory_sha256"
                ],
                "provider_network_access_performed": False,
                "copy_on_verify": True,
                "source_quarantine_mutated": False,
            },
        )
        logical = manifest(objects)
        manifest_path = staging / "source-slice-manifest.json"
        write_json(manifest_path, logical)
        manifest_file_sha = sha_file(manifest_path)
        if before != inspect(paths):
            raise RecoveryError(
                "source quarantine changed during copy-on-verify freeze"
            )
        write_json(
            receipts / "freeze-receipt.json",
            {
                "schema": "ovc-rps-g1b-freeze-receipt/v1",
                "slice_id": SLICE_ID,
                "coverage_state": COVERAGE_STATE,
                "manifest_sha256": logical["manifest_sha256"],
                "manifest_file_sha256": manifest_file_sha,
                "source_object_count": 4,
                "quarantine_inventory_sha256": inventory[
                    "inventory_sha256"
                ],
                "source_quarantine_unchanged_after_copy": True,
                "frozen": True,
                "release_status": "NOT_A_RELEASE",
                "selector_eligibility": "NONE",
                "r2_publication": "DENIED",
                "validation_consumption": "DENIED",
                "live_prospective_append": "DENIED",
            },
        )
        if base._workspace_size(staging) > EXPANDED_LIMIT:
            raise RecoveryError(
                "expanded-byte limit exceeded after compact receipts"
            )
        staging.rename(paths.final)
        return {
            "status": "FROZEN_LOCAL_GAPPED_SOURCE_SLICE",
            "slice_id": SLICE_ID,
            "coverage_state": COVERAGE_STATE,
            "manifest_sha256": logical["manifest_sha256"],
            "manifest_file_sha256": manifest_file_sha,
            "quarantine_inventory_sha256": inventory[
                "inventory_sha256"
            ],
            "source_object_count": 4,
            "provider_network_access_performed": False,
            "source_quarantine_mutated": False,
            "release_status": "NOT_A_RELEASE",
            "selector_eligibility": "NONE",
            "r2_publication": "DENIED",
            "validation_consumption": "DENIED",
        }
    except Exception as exc:
        quarantined = failure_quarantine(staging, str(exc))
        suffix = (
            f"; recovery staging quarantined at {quarantined}"
            if quarantined
            else ""
        )
        if isinstance(exc, (RecoveryError, base.IntakeError)):
            raise RecoveryError(str(exc) + suffix) from exc
        raise RecoveryError(
            f"unexpected RPS-G1B recovery failure: {exc}{suffix}"
        ) from exc


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description=(
            "No-network checksum-pinned RPS-G1B June quarantine recovery."
        )
    )
    result.add_argument(
        "command",
        choices=("preflight", "inventory", "freeze"),
    )
    result.add_argument(
        "--repository-root",
        type=Path,
        default=Path.cwd(),
    )
    result.add_argument("--gate", default=None)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        repository = args.repository_root.resolve(strict=True)
        if args.command == "preflight":
            result = preflight(repository)
        elif args.command == "inventory":
            result = build_inventory(repository)
        else:
            result = freeze(repository, args.gate or "")
    except RecoveryError as exc:
        print(
            f"RPS-G1B recovery blocked: {exc}",
            file=sys.stderr,
        )
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
