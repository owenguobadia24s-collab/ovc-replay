from __future__ import annotations

import gzip
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Iterator, Mapping

from .engine import C2ScopeEngine
from .price_parent import OptAPriceParentIndex, VerifiedOptARelease


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


class FirstValidParentResolver:
    """Select only the latest parent structure first-valid by the local close."""

    def __init__(self, snapshots: Iterable[tuple[str, tuple[dict[str, Any], ...]]]):
        self.snapshots = list(snapshots)
        times = [item[0] for item in self.snapshots]
        if times != sorted(times) or len(times) != len(set(times)):
            raise ReplayError("NON_MONOTONIC_PARENT_FIRST_VALID_TIMES")
        self.index = 0
        self.active: tuple[dict[str, Any], ...] = ()

    def __call__(self, record: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
        local_close = str(record["close_time"])
        while self.index < len(self.snapshots) and self.snapshots[self.index][0] <= local_close:
            self.active = self.snapshots[self.index][1]
            self.index += 1
        return self.active


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


def _write_scope_replay(
    *,
    records: Iterable[dict[str, Any]],
    role: str,
    clock: str,
    side: str,
    evaluation_scope: str,
    output_dir: Path,
    parent_levels: Callable[[Mapping[str, Any]], Iterable[Mapping[str, Any]]] | None = None,
    collect_levels: bool = False,
) -> tuple[int, int, list[tuple[str, tuple[dict[str, Any], ...]]]]:
    scope_slug = evaluation_scope.replace(".", "_")
    state_path = output_dir / "states" / role.lower() / clock / side / f"{scope_slug}.jsonl"
    transition_path = output_dir / "transitions" / role.lower() / clock / side / f"{scope_slug}.jsonl"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    transition_path.parent.mkdir(parents=True, exist_ok=True)
    engine = C2ScopeEngine(evaluation_scope)
    state_count = transition_count = 0
    snapshots: list[tuple[str, tuple[dict[str, Any], ...]]] = []
    with state_path.open("w", encoding="utf-8", newline="\n") as states, transition_path.open(
        "w", encoding="utf-8", newline="\n"
    ) as transitions:
        for record in records:
            current_scope = _scope(record, role)
            if current_scope[:3] != (role, clock, side):
                raise ReplayError(f"SCOPE_DRIFT:{(role, clock, side)}:{current_scope[:3]}")
            result = engine.process(
                record,
                parent_levels=parent_levels(record) if parent_levels is not None else (),
            )
            current = result.state
            current["role"] = role
            states.write(json.dumps(current, sort_keys=True, separators=(",", ":")) + "\n")
            state_count += 1
            transition = result.transition
            if transition is not None:
                transition["role"] = role
                transition["clock"] = clock
                transition["side"] = side
                transition["evaluation_scope_id"] = evaluation_scope
                transitions.write(json.dumps(transition, sort_keys=True, separators=(",", ":")) + "\n")
                transition_count += 1
            if collect_levels:
                snapshots.append((str(current["first_valid_time"]), result.levels))
    return state_count, transition_count, snapshots


def _scope_paths(verified: VerifiedRelease, clock: str, side: str) -> list[Path]:
    prefix = f"records/{clock}/{side}/"
    return [
        path
        for path in verified.record_paths
        if path.relative_to(verified.root / "files").as_posix().startswith(prefix)
    ]


def _joined_records(
    verified: VerifiedRelease,
    price_release: VerifiedOptARelease,
    *,
    clock: str,
    side: str,
) -> Iterator[dict[str, Any]]:
    index = OptAPriceParentIndex(price_release)
    previous_time = ""
    for shard in _scope_paths(verified, clock, side):
        seen = False
        for record in read_jsonl(shard):
            seen = True
            try:
                joined = index.join(
                    record,
                    c1_release_id=verified.binding.release_id,
                    c1_manifest_id=verified.binding.manifest_id,
                )
            except ValueError as exc:
                raise ReplayError(f"EXACT_PARENT_JOIN_FAILED:{verified.binding.role}:{exc}") from exc
            if previous_time and joined["open_time"] <= previous_time:
                raise ReplayError(
                    f"NON_MONOTONIC_JOINED_SCOPE:{verified.binding.role}:{clock}:{side}:{joined['open_time']}"
                )
            previous_time = joined["open_time"]
            yield joined
        if not seen:
            raise ReplayError(f"EMPTY_RECORD_SHARD:{shard}")


def run_verified_role_replay(
    verified: VerifiedRelease,
    price_release: VerifiedOptARelease,
    output_dir: Path,
) -> ReplaySummary:
    binding = verified.binding
    if price_release.binding.role != binding.role:
        raise ReplayError("C1_OPT_A_VERIFIED_ROLE_MISMATCH")
    input_count = state_count = transition_count = 0
    scope_count = 0
    for side in ("BID", "ASK"):
        two_h_records = _joined_records(verified, price_release, clock="2H_A_L", side=side)
        two_h_states, two_h_transitions, parent_snapshots = _write_scope_replay(
            records=two_h_records,
            role=binding.role,
            clock="2H_A_L",
            side=side,
            evaluation_scope="GBPUSD-2H-A-L-LOCAL-v0.1",
            output_dir=output_dir,
            collect_levels=True,
        )
        input_count += two_h_states
        state_count += two_h_states
        transition_count += two_h_transitions
        scope_count += 1

        local_states, local_transitions, _ = _write_scope_replay(
            records=_joined_records(verified, price_release, clock="15M", side=side),
            role=binding.role,
            clock="15M",
            side=side,
            evaluation_scope="GBPUSD-15M-LOCAL-v0.1",
            output_dir=output_dir,
        )
        input_count += local_states
        state_count += local_states
        transition_count += local_transitions
        scope_count += 1

        latest_parent = FirstValidParentResolver(parent_snapshots)

        combined_states, combined_transitions, _ = _write_scope_replay(
            records=_joined_records(verified, price_release, clock="15M", side=side),
            role=binding.role,
            clock="15M",
            side=side,
            evaluation_scope="GBPUSD-15M-WITH-2H-PARENT-v0.1",
            output_dir=output_dir,
            parent_levels=latest_parent,
        )
        state_count += combined_states
        transition_count += combined_transitions
        scope_count += 1
    return ReplaySummary(
        binding.role,
        binding.release_id,
        input_count,
        state_count,
        transition_count,
        0,
        scope_count,
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
            engine = C2ScopeEngine(scope[3])
            for record in sorted(scoped_records, key=lambda item: str(item["close_time"])):
                result = engine.process(record)
                current = result.state
                current["role"] = role
                states.write(json.dumps(current, sort_keys=True, separators=(",", ":")) + "\n")
                total_states += 1
                transition = result.transition
                if transition is not None:
                    transition.update({"role": role, "clock": scope[1], "side": scope[2], "evaluation_scope_id": scope[3]})
                    transitions.write(json.dumps(transition, sort_keys=True, separators=(",", ":")) + "\n")
                    total_transitions += 1
    return ReplaySummary(role, release_id, len(records), total_states, total_transitions, 0, len(scopes))
