from __future__ import annotations

import gzip
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Iterator, Mapping

from .persistence import apply_persistence
from .state import build_parallel_state
from .transitions import build_transition


DISCOVERY_RELEASE = "OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1"
DEVELOPMENT_RELEASE = "OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1"
DISCOVERY_MANIFEST = "MANIFEST.C1.OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1.r1"
DEVELOPMENT_MANIFEST = "MANIFEST.C1.OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1.r1"


class ReplayError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReleaseBinding:
    role: str
    release_id: str
    manifest_id: str
    manifest_sha256: str
    record_file_count: int
    payload_file_count: int
    scope_shard_counts: tuple[tuple[str, str, int], ...]


RELEASE_BINDINGS = {
    "DISCOVERY": ReleaseBinding(
        "DISCOVERY",
        DISCOVERY_RELEASE,
        DISCOVERY_MANIFEST,
        "6abd6d1fb74e7f3797e9add2435eaa5e487b612efd2f4b5f4f4c59679820d5d2",
        144,
        145,
        (("15M", "ASK", 36), ("15M", "BID", 36), ("2H_A_L", "ASK", 36), ("2H_A_L", "BID", 36)),
    ),
    "DEVELOPMENT": ReleaseBinding(
        "DEVELOPMENT",
        DEVELOPMENT_RELEASE,
        DEVELOPMENT_MANIFEST,
        "ca83f2d9d948be426f3d80ebc91cc981f92546dfdd07268d71938d618c51f017",
        48,
        49,
        (("15M", "ASK", 12), ("15M", "BID", 12), ("2H_A_L", "ASK", 12), ("2H_A_L", "BID", 12)),
    ),
}
_ALLOWED = {role: binding.release_id for role, binding in RELEASE_BINDINGS.items()}
_RECORD_PATH = re.compile(r"^records/(15M|2H_A_L)/(BID|ASK)/[^/]+\.c1\.jsonl\.gz$")
_SYNTHETIC_HANDOFF_FIELDS = {
    "c1_record_id",
    "c1_release_id",
    "c1_manifest_id",
    "opt_a_release_id",
    "opt_a_manifest_id",
    "role",
    "authority_state",
    "instrument",
    "clock",
    "side",
    "close_time",
    "first_valid_time",
    "measurements",
    "quality_state",
}
_ENGINE_PRICE_FIELDS = {
    "open",
    "high",
    "low",
    "close",
    "range_low",
    "range_high",
    "swing_low",
    "swing_high",
    "prior_range",
}


@dataclass(frozen=True)
class VerifiedRelease:
    root: Path
    binding: ReleaseBinding
    manifest_sha256: str
    payload_bytes: int
    record_paths: tuple[Path, ...]
    scope_shard_counts: tuple[tuple[str, str, int], ...]

    @property
    def payload_object_count(self) -> int:
        return self.binding.payload_file_count

    @property
    def canonical_object_count(self) -> int:
        return self.binding.payload_file_count + 1


@dataclass(frozen=True)
class ReplaySummary:
    role: str
    release_id: str
    input_records: int
    state_records: int
    transition_records: int
    rejected_records: int
    scope_count: int = 1


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_object(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReplayError(f"{code}:{path}") from exc
    if not isinstance(value, dict):
        raise ReplayError(f"{code}:{path}")
    return value


def _safe_relative_path(raw: Any) -> PurePosixPath:
    if not isinstance(raw, str) or not raw:
        raise ReplayError("INVALID_MANIFEST_PATH")
    path = PurePosixPath(raw)
    if path.is_absolute() or "." in path.parts or ".." in path.parts or "\\" in raw:
        raise ReplayError(f"UNSAFE_MANIFEST_PATH:{raw}")
    return path


def verify_canonical_release(root: Path, binding: ReleaseBinding) -> VerifiedRelease:
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise ReplayError(f"MISSING_MANIFEST:{manifest_path}")
    manifest_sha = sha256(manifest_path)
    if manifest_sha != binding.manifest_sha256:
        raise ReplayError(f"MANIFEST_SHA256_MISMATCH:{binding.role}")
    manifest = _load_object(manifest_path, "INVALID_MANIFEST")
    if manifest.get("release_id") != binding.release_id:
        raise ReplayError(f"WRONG_MANIFEST_RELEASE:{binding.role}")
    if manifest.get("manifest_id") != binding.manifest_id:
        raise ReplayError(f"WRONG_MANIFEST_ID:{binding.role}")
    files = manifest.get("files")
    if not isinstance(files, list) or len(files) != binding.payload_file_count:
        raise ReplayError(f"WRONG_MANIFEST_FILE_COUNT:{binding.role}")
    if manifest.get("file_count") != binding.payload_file_count:
        raise ReplayError(f"WRONG_DECLARED_FILE_COUNT:{binding.role}")
    if manifest.get("record_file_count") != binding.record_file_count:
        raise ReplayError(f"WRONG_DECLARED_RECORD_FILE_COUNT:{binding.role}")

    declared: set[str] = set()
    record_paths: list[Path] = []
    scopes: Counter[tuple[str, str]] = Counter()
    payload_bytes = 0
    descriptor: Path | None = None
    for item in files:
        if not isinstance(item, dict):
            raise ReplayError("INVALID_MANIFEST_FILE_ENTRY")
        relative = _safe_relative_path(item.get("path"))
        key = relative.as_posix()
        if key in declared:
            raise ReplayError(f"DUPLICATE_MANIFEST_PATH:{key}")
        declared.add(key)
        local = root / "files" / Path(*relative.parts)
        if not local.is_file() or local.is_symlink():
            raise ReplayError(f"MISSING_OR_UNSAFE_PAYLOAD:{key}")
        if local.stat().st_size != item.get("size_bytes"):
            raise ReplayError(f"PAYLOAD_SIZE_MISMATCH:{key}")
        if sha256(local) != item.get("sha256"):
            raise ReplayError(f"PAYLOAD_SHA256_MISMATCH:{key}")
        payload_bytes += local.stat().st_size
        match = _RECORD_PATH.fullmatch(key)
        if match:
            scopes[(match.group(1), match.group(2))] += 1
            record_paths.append(local)
        elif key == "release-descriptor.json":
            descriptor = local
        else:
            raise ReplayError(f"UNDECLARED_PAYLOAD_ROLE:{key}")

    actual = {
        path.relative_to(root / "files").as_posix()
        for path in (root / "files").rglob("*")
        if path.is_file()
    }
    if actual != declared:
        raise ReplayError(f"LOCAL_PAYLOAD_INVENTORY_MISMATCH:{binding.role}")
    if descriptor is None:
        raise ReplayError(f"MISSING_RELEASE_DESCRIPTOR:{binding.role}")
    descriptor_value = _load_object(descriptor, "INVALID_RELEASE_DESCRIPTOR")
    if descriptor_value.get("release_id") != binding.release_id or descriptor_value.get("role") != binding.role:
        raise ReplayError(f"RELEASE_DESCRIPTOR_BINDING_MISMATCH:{binding.role}")
    if descriptor_value.get("formula_registry_id") != "C1.FORMULAS.v0.1":
        raise ReplayError(f"FORMULA_REGISTRY_MISMATCH:{binding.role}")
    if len(record_paths) != binding.record_file_count:
        raise ReplayError(f"RECORD_SHARD_COUNT_MISMATCH:{binding.role}")
    expected_scopes = {(clock, side): count for clock, side, count in binding.scope_shard_counts}
    if dict(scopes) != expected_scopes:
        raise ReplayError(f"SCOPE_SHARD_INVENTORY_MISMATCH:{binding.role}")
    if manifest.get("payload_bytes") != payload_bytes:
        raise ReplayError(f"PAYLOAD_BYTES_MISMATCH:{binding.role}")
    return VerifiedRelease(
        root=root,
        binding=binding,
        manifest_sha256=manifest_sha,
        payload_bytes=payload_bytes,
        record_paths=tuple(sorted(record_paths, key=lambda path: path.relative_to(root / "files").as_posix())),
        scope_shard_counts=tuple((clock, side, count) for (clock, side), count in sorted(scopes.items())),
    )


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.name.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", newline="") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ReplayError(f"INVALID_JSONL:{path}:{line_number}") from exc
            if not isinstance(payload, dict):
                raise ReplayError(f"NON_OBJECT_RECORD:{path}:{line_number}")
            yield payload


def _scope(record: Mapping[str, Any], role: str) -> tuple[str, str, str, str]:
    clock = str(record.get("clock", ""))
    side = str(record.get("side", record.get("price_side", "")))
    if clock not in {"15M", "2H_A_L"} or side not in {"BID", "ASK"}:
        raise ReplayError("RECORD_SCOPE_OUTSIDE_APPROVED_PROFILE")
    evaluation_scope = str(
        record.get("evaluation_scope_id", "C2.SCOPE.15M.LOCAL" if clock == "15M" else "C2.SCOPE.2H_A_L.PARENT")
    )
    return role, clock, side, evaluation_scope


def _assert_engine_compatible(record: Mapping[str, Any], binding: ReleaseBinding) -> None:
    if not _SYNTHETIC_HANDOFF_FIELDS.issubset(record):
        missing = ",".join(sorted(_SYNTHETIC_HANDOFF_FIELDS - set(record)))
        raise ReplayError(
            "PUBLISHED_C1_RECORD_SHAPE_NOT_C2_HANDOFF_ENVELOPE:"
            f"{binding.role}:missing={missing}"
        )
    measurements = record.get("measurements")
    if not isinstance(measurements, Mapping):
        raise ReplayError(f"INVALID_MEASUREMENTS:{binding.role}")
    missing_price = sorted(_ENGINE_PRICE_FIELDS - set(measurements))
    if missing_price:
        raise ReplayError(
            "C2_REQUIRED_PRICE_AND_STRUCTURE_INPUTS_UNAVAILABLE:"
            f"{binding.role}:missing={','.join(missing_price)}"
        )
    if record.get("c1_release_id") != binding.release_id or record.get("c1_manifest_id") != binding.manifest_id:
        raise ReplayError(f"RECORD_MANIFEST_BINDING_MISMATCH:{binding.role}")
    if record.get("role") != binding.role:
        raise ReplayError(f"RECORD_ROLE_MISMATCH:{binding.role}")


def _write_scope_replay(
    *,
    records: Iterable[dict[str, Any]],
    scope: tuple[str, str, str, str],
    output_dir: Path,
) -> tuple[int, int, int]:
    role, clock, side, evaluation_scope = scope
    scope_slug = evaluation_scope.replace(".", "_")
    state_path = output_dir / "states" / role.lower() / clock / side / f"{scope_slug}.jsonl"
    transition_path = output_dir / "transitions" / role.lower() / clock / side / f"{scope_slug}.jsonl"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    transition_path.parent.mkdir(parents=True, exist_ok=True)
    previous: dict[str, Any] | None = None
    previous_time = ""
    input_count = state_count = transition_count = 0
    with state_path.open("w", encoding="utf-8", newline="\n") as states, transition_path.open(
        "w", encoding="utf-8", newline="\n"
    ) as transitions:
        for record in records:
            input_count += 1
            current_scope = _scope(record, role)
            if current_scope != scope:
                raise ReplayError(f"SCOPE_DRIFT:{scope}:{current_scope}")
            close_time = str(record["close_time"])
            if previous_time and close_time <= previous_time:
                raise ReplayError(f"NON_MONOTONIC_SCOPE_CHRONOLOGY:{scope}:{close_time}")
            current = apply_persistence(build_parallel_state(record), previous)
            current["role"] = role
            current["evaluation_scope_id"] = evaluation_scope
            states.write(json.dumps(current, sort_keys=True, separators=(",", ":")) + "\n")
            state_count += 1
            transition = build_transition(current, previous)
            if transition is not None:
                transition["role"] = role
                transition["clock"] = clock
                transition["side"] = side
                transition["evaluation_scope_id"] = evaluation_scope
                transitions.write(json.dumps(transition, sort_keys=True, separators=(",", ":")) + "\n")
                transition_count += 1
            previous = current
            previous_time = close_time
    return input_count, state_count, transition_count


def run_verified_role_replay(verified: VerifiedRelease, output_dir: Path) -> ReplaySummary:
    binding = verified.binding
    by_scope: dict[tuple[str, str, str, str], list[Path]] = {}
    first: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for path in verified.record_paths:
        iterator = read_jsonl(path)
        try:
            record = next(iterator)
        except StopIteration as exc:
            raise ReplayError(f"EMPTY_RECORD_SHARD:{path}") from exc
        scope = _scope(record, binding.role)
        _assert_engine_compatible(record, binding)
        first.setdefault(scope, record)
        by_scope.setdefault(scope, []).append(path)

    input_count = state_count = transition_count = 0
    for scope, paths in sorted(by_scope.items()):
        def records() -> Iterator[dict[str, Any]]:
            for shard in paths:
                for record in read_jsonl(shard):
                    _assert_engine_compatible(record, binding)
                    yield record

        inputs, states, transitions = _write_scope_replay(records=records(), scope=scope, output_dir=output_dir)
        input_count += inputs
        state_count += states
        transition_count += transitions
    return ReplaySummary(
        binding.role,
        binding.release_id,
        input_count,
        state_count,
        transition_count,
        0,
        len(by_scope),
    )


def run_role_replay(*, role: str, release_id: str, input_path: Path, output_dir: Path) -> ReplaySummary:
    expected = _ALLOWED.get(role)
    if expected is None:
        raise ReplayError("WRONG_ROLE")
    if release_id != expected:
        raise ReplayError("WRONG_RELEASE_ID")
    if not input_path.is_file():
        raise ReplayError(f"MISSING_INPUT:{input_path}")

    records = list(read_jsonl(input_path))
    scopes: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for record in records:
        scopes.setdefault(_scope(record, role), []).append(record)
    output_dir.mkdir(parents=True, exist_ok=True)
    state_path = output_dir / f"{role.lower()}_states.jsonl"
    transition_path = output_dir / f"{role.lower()}_transitions.jsonl"
    total_states = total_transitions = 0
    with state_path.open("w", encoding="utf-8", newline="\n") as states, transition_path.open(
        "w", encoding="utf-8", newline="\n"
    ) as transitions:
        for scope, scoped_records in sorted(scopes.items()):
            previous: dict[str, Any] | None = None
            previous_time = ""
            for record in sorted(scoped_records, key=lambda item: str(item["close_time"])):
                close_time = str(record["close_time"])
                if previous_time and close_time <= previous_time:
                    raise ReplayError(f"NON_MONOTONIC_SCOPE_CHRONOLOGY:{scope}:{close_time}")
                current = apply_persistence(build_parallel_state(record), previous)
                current["role"] = role
                current["evaluation_scope_id"] = scope[3]
                states.write(json.dumps(current, sort_keys=True, separators=(",", ":")) + "\n")
                total_states += 1
                transition = build_transition(current, previous)
                if transition is not None:
                    transition.update({"role": role, "clock": scope[1], "side": scope[2], "evaluation_scope_id": scope[3]})
                    transitions.write(json.dumps(transition, sort_keys=True, separators=(",", ":")) + "\n")
                    total_transitions += 1
                previous = current
                previous_time = close_time
    return ReplaySummary(role, release_id, len(records), total_states, total_transitions, 0, len(scopes))
