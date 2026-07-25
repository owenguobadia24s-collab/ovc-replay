from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class PopulationIntegrityError(RuntimeError):
    """Raised when accepted provider evidence cannot prove byte identity and lineage."""


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_year_workspace(root: Path, expected_year: int) -> dict[str, Any]:
    """Verify one WP4 yearly workspace without granting release authority."""
    root = root.resolve(strict=True)
    intake_dir = root / "records" / "intake"
    identity_dir = root / "records" / "source_identity"
    downloader_dir = root / "records" / "downloader"
    summary_dir = root / "summaries"

    intake = {_read_json(p)["source_object_id"]: _read_json(p) for p in intake_dir.glob("*.json")}
    identities = {_read_json(p)["source_object_id"]: _read_json(p) for p in identity_dir.glob("*.json")}
    downloader_files = sorted(downloader_dir.glob(f"{expected_year}-*.json"))
    summaries = sorted(summary_dir.glob(f"{expected_year}-*.json"))
    violations: list[str] = []
    source_ids: set[str] = set()
    rows = csv_bytes = transport_chunks = not_present = 0

    if len(downloader_files) != 12 or len(summaries) != 12:
        violations.append("year must contain exactly twelve downloader receipts and summaries")

    for receipt_path in downloader_files:
        receipt = _read_json(receipt_path)
        year_month = receipt.get("year_month", "")
        if not year_month.startswith(f"{expected_year}-"):
            violations.append(f"unexpected receipt partition: {year_month}")
        if receipt.get("market_authority") != "NONE":
            violations.append(f"{year_month}: market authority must remain NONE")

        for obj in receipt.get("objects", []):
            source_id = obj["source_object_id"]
            source_ids.add(source_id)
            csv_path = root / obj["output_path"]
            if not csv_path.is_file():
                violations.append(f"{source_id}: missing accepted CSV")
                continue
            observed_hash = _sha256(csv_path)
            observed_size = csv_path.stat().st_size
            if observed_hash != obj.get("output_sha256"):
                violations.append(f"{source_id}: downloader CSV hash mismatch")
            if observed_size != obj.get("output_size_bytes"):
                violations.append(f"{source_id}: downloader CSV size mismatch")

            intake_record = intake.get(source_id)
            identity = identities.get(source_id)
            if intake_record is None:
                violations.append(f"{source_id}: missing intake record")
                continue
            if identity is None:
                violations.append(f"{source_id}: missing source identity")
                continue

            request = intake_record.get("request", {})
            required_request_fields = {
                "interval_start", "interval_end", "provider_instrument",
                "timeframe", "price_side", "parameters_sha256",
            }
            missing = sorted(required_request_fields - request.keys())
            if missing:
                violations.append(f"{source_id}: request lineage missing {','.join(missing)}")
            if intake_record.get("response", {}).get("sha256") != observed_hash:
                violations.append(f"{source_id}: intake response hash mismatch")
            if identity.get("response_sha256") != observed_hash:
                violations.append(f"{source_id}: identity hash mismatch")
            if intake_record.get("response", {}).get("size_bytes") != observed_size:
                violations.append(f"{source_id}: intake response size mismatch")
            if identity.get("size_bytes") != observed_size:
                violations.append(f"{source_id}: identity size mismatch")
            if intake_record.get("qa_state") != "PASS" or identity.get("quality_state") != "PASS":
                violations.append(f"{source_id}: accepted object is not QA PASS")

            rows += int(obj["row_count"])
            csv_bytes += observed_size
            for chunk in obj.get("transport_chunks", []):
                transport_chunks += 1
                status = chunk.get("status")
                if status == "NOT_PRESENT":
                    not_present += 1
                    continue
                if status != "DOWNLOADED":
                    violations.append(f"{source_id}: unknown transport status {status}")
                    continue
                cached_path = root / chunk["cached_path"]
                if not cached_path.is_file():
                    violations.append(f"{source_id}: missing transport object {chunk['relative_provider_path']}")
                    continue
                if _sha256(cached_path) != chunk.get("sha256"):
                    violations.append(f"{source_id}: transport hash mismatch {chunk['relative_provider_path']}")
                if cached_path.stat().st_size != chunk.get("size_bytes"):
                    violations.append(f"{source_id}: transport size mismatch {chunk['relative_provider_path']}")
                if not chunk.get("url"):
                    violations.append(f"{source_id}: transport request URL missing")

    result = {
        "year": expected_year,
        "month_count": len(downloader_files),
        "source_object_count": len(source_ids),
        "row_count": rows,
        "csv_size_bytes": csv_bytes,
        "transport_chunk_count": transport_chunks,
        "not_present_transport_chunk_count": not_present,
        "violation_count": len(violations),
        "violations": violations,
        "result": "PASS" if not violations and len(source_ids) == 48 else "FAIL",
        "authority": {
            "workspace_entry": "AUTHORISED" if not violations and len(source_ids) == 48 else "DENIED",
            "release_freeze": "DENIED",
            "selector_activation": "DENIED",
            "market": "NONE",
        },
    }
    if result["result"] != "PASS":
        raise PopulationIntegrityError(json.dumps(result, sort_keys=True))
    return result
