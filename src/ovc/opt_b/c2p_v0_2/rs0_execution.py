from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

MANIFEST_SCHEMA = "ovc-c2p2-rs0-source-locator/v1"
ROW_SCHEMA = "ovc-c2p2-rs0-source-row/v1"
ALLOWED_ROLES = {"C2_VNEXT", "C2E_V0_2"}
FORBIDDEN_FIELDS = {
    "opt_c", "opt_d", "outcome", "future_information", "validation",
    "probability", "risk", "exposure", "trade_signal", "execution",
    "family_label", "c3_semantics",
}

class RS0ExecutionError(RuntimeError):
    pass

@dataclass(frozen=True)
class VerifiedSource:
    role: str
    relative_path: str
    sha256: str
    size_bytes: int
    row_count: int

def _safe_path(root: Path, relative_path: str) -> Path:
    root = root.resolve()
    candidate = (root / relative_path).resolve()
    if candidate == root or root not in candidate.parents:
        raise RS0ExecutionError(f"RS0_SOURCE_PATH_ESCAPE:{relative_path}")
    return candidate

def _sha_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def validate_locator(locator: Mapping[str, Any], external_root: Path) -> tuple[VerifiedSource, ...]:
    if locator.get("schema") != MANIFEST_SCHEMA:
        raise RS0ExecutionError("RS0_SOURCE_LOCATOR_SCHEMA_MISMATCH")
    if locator.get("instrument") != "GBPUSD":
        raise RS0ExecutionError("RS0_SOURCE_INSTRUMENT_MISMATCH")
    if sorted(locator.get("sides", [])) != ["ASK", "BID"]:
        raise RS0ExecutionError("RS0_SOURCE_SIDE_SCOPE_MISMATCH")
    if sorted(locator.get("clocks", [])) != ["15M", "2H_A_L"]:
        raise RS0ExecutionError("RS0_SOURCE_CLOCK_SCOPE_MISMATCH")
    if locator.get("interval") != "[2021-01-01T00:00:00Z,2024-01-01T00:00:00Z)":
        raise RS0ExecutionError("RS0_SOURCE_INTERVAL_MISMATCH")
    sources = locator.get("sources")
    if not isinstance(sources, list) or not sources:
        raise RS0ExecutionError("RS0_SOURCE_LOCATOR_EMPTY")
    verified=[]
    for item in sources:
        if not isinstance(item, Mapping):
            raise RS0ExecutionError("RS0_SOURCE_LOCATOR_ENTRY_INVALID")
        role=str(item.get("role",""))
        if role not in ALLOWED_ROLES:
            raise RS0ExecutionError(f"RS0_SOURCE_ROLE_FORBIDDEN:{role}")
        rel=str(item.get("relative_path",""))
        path=_safe_path(external_root, rel)
        if not path.is_file():
            raise RS0ExecutionError(f"RS0_SOURCE_FILE_MISSING:{rel}")
        expected_size=int(item.get("size_bytes",-1))
        expected_sha=str(item.get("sha256",""))
        if path.stat().st_size != expected_size:
            raise RS0ExecutionError(f"RS0_SOURCE_SIZE_MISMATCH:{rel}")
        if _sha_file(path) != expected_sha:
            raise RS0ExecutionError(f"RS0_SOURCE_SHA256_MISMATCH:{rel}")
        verified.append(VerifiedSource(role, rel, expected_sha, expected_size, int(item.get("row_count",-1))))
    return tuple(verified)

def iter_verified_rows(path: Path, *, expected_role: str) -> Iterable[dict[str, Any]]:
    count=0
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, start=1):
            if not raw.strip():
                continue
            try:
                row=json.loads(raw)
            except json.JSONDecodeError as exc:
                raise RS0ExecutionError(f"RS0_SOURCE_JSON_INVALID:{path}:{line_no}") from exc
            if not isinstance(row, dict) or row.get("schema") != ROW_SCHEMA:
                raise RS0ExecutionError(f"RS0_SOURCE_ROW_SCHEMA_MISMATCH:{path}:{line_no}")
            if row.get("source_role") != expected_role:
                raise RS0ExecutionError(f"RS0_SOURCE_ROW_ROLE_MISMATCH:{path}:{line_no}")
            forbidden=sorted(FORBIDDEN_FIELDS.intersection(row))
            if forbidden:
                raise RS0ExecutionError("RS0_FORBIDDEN_SOURCE_FIELD:" + ",".join(forbidden))
            if row.get("instrument") != "GBPUSD" or row.get("side") not in {"BID","ASK"} or row.get("clock") not in {"15M","2H_A_L"}:
                raise RS0ExecutionError(f"RS0_SOURCE_ROW_SCOPE_MISMATCH:{path}:{line_no}")
            fvt=str(row.get("first_valid_time",""))
            cutoff=str(row.get("evaluation_cutoff",""))
            if not fvt or not cutoff or fvt > cutoff:
                raise RS0ExecutionError(f"RS0_SOURCE_ROW_CAUSALITY_FAIL:{path}:{line_no}")
            count += 1
            yield row
    if count == 0:
        raise RS0ExecutionError(f"RS0_SOURCE_STREAM_EMPTY:{path}")

def checkpoint_identity(*, locator_sha256: str, candidate_ids: Iterable[str], completed_rows: int) -> str:
    payload={
        "schema":"ovc-c2p2-rs0-checkpoint-identity/v1",
        "locator_sha256":locator_sha256,
        "candidate_ids":sorted(candidate_ids),
        "completed_rows":int(completed_rows),
    }
    encoded=json.dumps(payload, sort_keys=True, separators=(",",":"), ensure_ascii=False).encode()
    return sha256(encoded).hexdigest()
