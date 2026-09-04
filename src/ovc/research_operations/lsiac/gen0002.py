from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SOURCE_CENSUS_DIR = Path("docs/programmes/lsiac-v0-1/source-census")
PASSPORT_SUMMARY = SOURCE_CENSUS_DIR / "LSIAC_LABORATORY_SOURCE_PASSPORTS_v0_1.json"

GENERATION_ID = "OVC-LSIAC-ACCESSION-GEN-0002"
EXPECTED_PASSPORT_COUNT = 434
EXPECTED_SUBJECT_COUNT = 431
EXPECTED_FROZEN_PASSPORT_SET_SHA256 = "f97ba927944326864f1a5cc20ecc69a0a4623743231aa8479d713984bbe68019"
EXPECTED_COREFERENCE_GROUPS = {
    "OVC-MULTICLOCK-NONLINEAR-DYNAMICS-0005": 2,
    "OVC-MULTICLOCK-PERSISTENCE-DWELL-0006": 2,
    "OVC-OBSERVER-STATE-SUFFICIENCY-AND-GAMMA-ROBUSTNESS-FRONTIER": 2,
}


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _load_json(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"LSIAC_GEN0002_EXPECTED_OBJECT:{path}")
    return value


def audit_frozen_passport_subject_identity(root: str | Path) -> dict[str, Any]:
    """Audit GEN0001's exact frozen passport bytes without changing scientific evidence.

    The repair is accounting-only. It preserves every passport byte and asks how many
    exact subject identifiers those bytes actually encode. No subject is merged by
    title, semantics, similarity, programme family or scientific interpretation.
    """
    root = Path(root)
    summary = _load_json(root / PASSPORT_SUMMARY)
    if int(summary.get("passport_count", -1)) != EXPECTED_PASSPORT_COUNT:
        raise ValueError("LSIAC_GEN0002_PASSPORT_COUNT_DRIFT")
    if summary.get("full_passport_set_canonical_sha256") != EXPECTED_FROZEN_PASSPORT_SET_SHA256:
        raise ValueError("LSIAC_GEN0002_FROZEN_PASSPORT_SET_IDENTITY_DRIFT")

    passport_ids: list[str] = []
    subject_to_passports: dict[str, list[str]] = defaultdict(list)
    chunk_receipts: list[dict[str, Any]] = []

    for meta in summary.get("chunks", []):
        if not isinstance(meta, Mapping):
            raise ValueError("LSIAC_GEN0002_CHUNK_METADATA_INVALID")
        path = root / SOURCE_CENSUS_DIR / str(meta["file"])
        raw = path.read_bytes()
        raw_sha256 = hashlib.sha256(raw).hexdigest()
        if raw_sha256 != str(meta.get("file_sha256", "")):
            raise ValueError(f"LSIAC_GEN0002_CHUNK_BYTE_IDENTITY_DRIFT:{path.name}")
        chunk = json.loads(raw.decode("utf-8"))
        if not isinstance(chunk, Mapping):
            raise ValueError(f"LSIAC_GEN0002_CHUNK_INVALID:{path.name}")
        rows = chunk.get("rows")
        if not isinstance(rows, list):
            raise ValueError(f"LSIAC_GEN0002_CHUNK_ROWS_INVALID:{path.name}")
        if len(rows) != int(meta["count"]):
            raise ValueError(f"LSIAC_GEN0002_CHUNK_COUNT_MISMATCH:{path.name}")
        if int(chunk.get("start", -1)) != int(meta["start"]) or int(chunk.get("end", -1)) != int(meta["end"]):
            raise ValueError(f"LSIAC_GEN0002_CHUNK_RANGE_MISMATCH:{path.name}")
        embedded_identity = str(chunk.get("h", ""))
        if embedded_identity != str(meta.get("canonical_sha256", "")):
            raise ValueError(f"LSIAC_GEN0002_CHUNK_DECLARED_IDENTITY_MISMATCH:{path.name}")
        identity_payload = {key: value for key, value in chunk.items() if key != "h"}
        if _canonical_sha256(identity_payload) != embedded_identity:
            raise ValueError(f"LSIAC_GEN0002_CHUNK_CANONICAL_IDENTITY_MISMATCH:{path.name}")

        for row in rows:
            if not isinstance(row, list) or len(row) < 2:
                raise ValueError(f"LSIAC_GEN0002_PASSPORT_ROW_INVALID:{path.name}")
            passport_id = str(row[0]).strip()
            subject_id = str(row[1]).strip()
            if not passport_id or not subject_id:
                raise ValueError(f"LSIAC_GEN0002_PASSPORT_IDENTITY_EMPTY:{path.name}")
            passport_ids.append(passport_id)
            subject_to_passports[subject_id].append(passport_id)

        chunk_receipts.append(
            {
                "file": path.name,
                "file_sha256": raw_sha256,
                "canonical_sha256": embedded_identity,
                "count": len(rows),
            }
        )

    if len(passport_ids) != EXPECTED_PASSPORT_COUNT:
        raise ValueError(f"LSIAC_GEN0002_RECONSTRUCTED_PASSPORT_COUNT_MISMATCH:{len(passport_ids)}")
    if len(set(passport_ids)) != EXPECTED_PASSPORT_COUNT:
        duplicates = sorted(pid for pid, count in Counter(passport_ids).items() if count > 1)
        raise ValueError(f"LSIAC_GEN0002_DUPLICATE_PASSPORT_IDS:{duplicates}")

    subject_count = len(subject_to_passports)
    if subject_count != EXPECTED_SUBJECT_COUNT:
        raise ValueError(f"LSIAC_GEN0002_SUBJECT_COUNT_MISMATCH:{subject_count}")

    multiplicities = {
        subject: len(ids)
        for subject, ids in subject_to_passports.items()
        if len(ids) > 1
    }
    if multiplicities != EXPECTED_COREFERENCE_GROUPS:
        raise ValueError(
            "LSIAC_GEN0002_COREFERENCE_GROUP_MISMATCH:"
            + json.dumps(multiplicities, sort_keys=True, separators=(",", ":"))
        )

    accounting_rows = [
        {"subject_id": subject, "passport_ids": sorted(ids), "passport_count": len(ids)}
        for subject, ids in sorted(subject_to_passports.items())
    ]
    accounting_payload = {
        "schema": "ovc-lsiac-gen0002-subject-accounting/v0.1",
        "generation_id": GENERATION_ID,
        "frozen_source_passport_set_sha256": EXPECTED_FROZEN_PASSPORT_SET_SHA256,
        "passport_count": EXPECTED_PASSPORT_COUNT,
        "subject_count": EXPECTED_SUBJECT_COUNT,
        "subjects": accounting_rows,
    }
    accounting_sha256 = _canonical_sha256(accounting_payload)

    return {
        "schema": "ovc-lsiac-gen0002-frontier-accounting-audit/v0.1",
        "programme_id": "OVC-LSIAC-v0.1",
        "generation_id": GENERATION_ID,
        "source_generation": "OVC-LSIAC-ACCESSION-GEN-0001",
        "frozen_source_passport_set_sha256": EXPECTED_FROZEN_PASSPORT_SET_SHA256,
        "passport_count": EXPECTED_PASSPORT_COUNT,
        "subject_count": EXPECTED_SUBJECT_COUNT,
        "singleton_subject_count": EXPECTED_SUBJECT_COUNT - len(EXPECTED_COREFERENCE_GROUPS),
        "multi_passport_subject_count": len(EXPECTED_COREFERENCE_GROUPS),
        "co_reference_groups": [
            {
                "subject_id": subject,
                "passport_ids": sorted(subject_to_passports[subject]),
                "passport_count": len(subject_to_passports[subject]),
            }
            for subject in sorted(EXPECTED_COREFERENCE_GROUPS)
        ],
        "chunk_receipts": chunk_receipts,
        "subject_accounting_sha256": accounting_sha256,
        "source_bytes_changed": False,
        "scientific_disposition_changed": False,
        "scientific_accession_decisions": 0,
        "authority_effect": "NONE_ACCOUNTING_REPAIR_ONLY",
    }
