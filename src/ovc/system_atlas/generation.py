from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from .canonical import canonical_json_bytes, canonical_sha256
from .core import OBJECT_ARRAYS, validate_system_graph


class AtlasGenerationError(ValueError):
    """Raised when an Atlas generation cannot be packaged or published safely."""


PARTITIONS = ("ATLAS_PUBLIC_METADATA", "ATLAS_INTERNAL", "ATLAS_RESTRICTED")
PARTITION_RANK = {name: rank for rank, name in enumerate(PARTITIONS)}
HIGH_RISK_PREDICATES = {"OWNS", "GOVERNS", "ACTIVE", "AUTHORISED", "CURRENT", "CANONICAL", "PUBLISHED"}
FAMILY_ID_KEYS = dict(OBJECT_ARRAYS)
ROOT_SCHEMA = "ovc-atlas-generation-root-manifest/v1"
PARTITION_SCHEMA = "ovc-atlas-generation-partition-manifest/v1"
FILE_ORDER = tuple(FAMILY_ID_KEYS)


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise AtlasGenerationError(code)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _partition_max(values: Iterable[str]) -> str:
    rows = list(values)
    _require(bool(rows), "ATLAS_VISIBILITY_PARTITION_REQUIRED")
    _require(all(row in PARTITION_RANK for row in rows), "ATLAS_VISIBILITY_PARTITION_UNKNOWN")
    return max(rows, key=PARTITION_RANK.__getitem__)


def _jsonl(rows: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(row) + b"\n" for row in rows)


def _parse_jsonl(value: bytes) -> list[dict[str, Any]]:
    if not value:
        return []
    return [json.loads(line) for line in value.decode("utf-8").splitlines()]


def _family_rows_by_partition(graph: Mapping[str, Any]) -> dict[str, dict[str, list[dict[str, Any]]]]:
    by_partition = {partition: {family: [] for family in FILE_ORDER} for partition in PARTITIONS}
    evidence_partition = {
        row["evidence_id"]: row["visibility_partition"] for row in graph["evidence_references"]
    }
    entity_partition: dict[str, str] = {}
    for entity in graph["entities"]:
        declared = entity["visibility_partition"]
        referenced = [evidence_partition[ref] for ref in entity["evidence_refs"]]
        required = _partition_max([declared, *referenced])
        _require(
            PARTITION_RANK[declared] >= PARTITION_RANK[required],
            f"ATLAS_VISIBILITY_DOWNGRADE_ENTITY:{entity['entity_id']}",
        )
        entity_partition[entity["entity_id"]] = declared

    assertion_partition: dict[str, str] = {}
    for assertion in graph["assertions"]:
        partition = _partition_max(
            [entity_partition[assertion["subject_id"]], *(evidence_partition[ref] for ref in assertion["evidence_refs"])]
        )
        assertion_partition[assertion["assertion_id"]] = partition

    for evidence in graph["evidence_references"]:
        by_partition[evidence["visibility_partition"]]["evidence_references"].append(dict(evidence))
    for entity in graph["entities"]:
        by_partition[entity_partition[entity["entity_id"]]]["entities"].append(dict(entity))
    for relationship in graph["relationships"]:
        partition = _partition_max(
            [
                entity_partition[relationship["subject_id"]],
                entity_partition[relationship["object_id"]],
                *(evidence_partition[ref] for ref in relationship["evidence_refs"]),
            ]
        )
        by_partition[partition]["relationships"].append(dict(relationship))
    for assertion in graph["assertions"]:
        by_partition[assertion_partition[assertion["assertion_id"]]]["assertions"].append(dict(assertion))
    for conflict in graph["conflicts"]:
        partition = _partition_max(
            [
                entity_partition[conflict["subject_id"]],
                *(assertion_partition[ref] for ref in conflict["competing_assertion_ids"]),
                *(evidence_partition[ref] for ref in conflict["evidence_refs"]),
            ]
        )
        by_partition[partition]["conflicts"].append(dict(conflict))

    for families in by_partition.values():
        for family, rows in families.items():
            rows.sort(key=lambda row: row[FAMILY_ID_KEYS[family]])
    return by_partition


def derive_source_currentness_proofs(
    graph: Mapping[str, Any], repository_root: Path | str | None
) -> dict[str, dict[str, str]]:
    evidence = {row["evidence_id"]: row for row in graph["evidence_references"]}
    generation = graph["generation"]
    for assertion in graph["assertions"]:
        if assertion["status"] == "CANONICAL" and assertion["predicate"] in {"OWNS", "GOVERNS"}:
            role = assertion["scope"]["dimensions"].get("owner_role")
            _require(isinstance(role, str) and bool(role), f"ATLAS_OWNER_ROLE_REQUIRED:{assertion['assertion_id']}")
    required_evidence = {
        evidence_id
        for assertion in graph["assertions"]
        if assertion["status"] == "CANONICAL" and assertion["predicate"] in HIGH_RISK_PREDICATES
        for evidence_id in assertion["evidence_refs"]
    }
    if not required_evidence:
        return {}
    _require(repository_root is not None, "ATLAS_SOURCE_CURRENTNESS_REPOSITORY_REQUIRED")
    root = Path(repository_root)

    def git_resolve(specification: str, failure: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", specification],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        _require(completed.returncode == 0, failure)
        return completed.stdout.strip()

    commit = generation["repository_commit"]
    tree = generation["repository_tree"]
    _require(git_resolve(f"{commit}^{{tree}}", "ATLAS_SOURCE_COMMIT_UNRESOLVED") == tree, "ATLAS_SOURCE_TREE_MISMATCH")
    proofs: dict[str, dict[str, str]] = {}
    for evidence_id in sorted(required_evidence):
        source = evidence[evidence_id]
        _require(source.get("repository_commit") == commit, f"ATLAS_SOURCE_COMMIT_MISMATCH:{evidence_id}")
        _require(source.get("repository_tree") == tree, f"ATLAS_SOURCE_TREE_MISMATCH:{evidence_id}")
        source_path = source.get("source_path")
        _require(isinstance(source_path, str) and bool(source_path), f"ATLAS_SOURCE_PATH_REQUIRED:{evidence_id}")
        blob = git_resolve(f"{commit}:{source_path}", f"ATLAS_SOURCE_BLOB_UNRESOLVED:{evidence_id}")
        _require(blob == source.get("source_blob_sha"), f"ATLAS_SOURCE_BLOB_MISMATCH:{evidence_id}")
        proofs[evidence_id] = {
            "source_currentness": "CURRENT",
            "derivation": "EXACT_REPOSITORY_TREE_AND_BLOB",
            "repository_commit": commit,
            "repository_tree": tree,
            "source_blob_sha": blob,
        }
    return proofs


def _enforce_high_risk_prerequisites(graph: Mapping[str, Any], source_currentness_proofs: Mapping[str, Mapping[str, Any]]) -> None:
    evidence = {row["evidence_id"]: row for row in graph["evidence_references"]}
    generation = graph["generation"]
    for assertion in graph["assertions"]:
        if assertion["status"] != "CANONICAL" or assertion["predicate"] not in HIGH_RISK_PREDICATES:
            continue
        if assertion["predicate"] in {"OWNS", "GOVERNS"}:
            role = assertion["scope"]["dimensions"].get("owner_role")
            _require(isinstance(role, str) and bool(role), f"ATLAS_OWNER_ROLE_REQUIRED:{assertion['assertion_id']}")
        for evidence_id in assertion["evidence_refs"]:
            proof = source_currentness_proofs.get(evidence_id)
            _require(isinstance(proof, Mapping), f"ATLAS_SOURCE_CURRENTNESS_PROOF_REQUIRED:{evidence_id}")
            source = evidence[evidence_id]
            _require(proof.get("source_currentness") == "CURRENT", f"ATLAS_SOURCE_NOT_CURRENT:{evidence_id}")
            _require(
                proof.get("derivation") == "EXACT_REPOSITORY_TREE_AND_BLOB",
                f"ATLAS_SOURCE_CURRENTNESS_NOT_DERIVED:{evidence_id}",
            )
            _require(proof.get("repository_commit") == generation["repository_commit"], f"ATLAS_SOURCE_COMMIT_MISMATCH:{evidence_id}")
            _require(proof.get("repository_tree") == generation["repository_tree"], f"ATLAS_SOURCE_TREE_MISMATCH:{evidence_id}")
            _require(proof.get("source_blob_sha") == source["source_blob_sha"], f"ATLAS_SOURCE_BLOB_MISMATCH:{evidence_id}")


@dataclass(frozen=True)
class GenerationBundle:
    root_hash: str
    root_manifest: dict[str, Any]
    files: dict[str, bytes]

    def file(self, relative_path: str) -> bytes:
        return self.files[relative_path]


def build_reference_generation(
    graph: Mapping[str, Any],
    registries: Mapping[str, Any],
    *,
    repository_root: Path | str | None = None,
    predecessor_root_hash: str | None = None,
    maximum_records: int | None = None,
) -> GenerationBundle:
    validate_system_graph(graph, registries)
    proofs = derive_source_currentness_proofs(graph, repository_root)
    _enforce_high_risk_prerequisites(graph, proofs)
    total_records = sum(len(graph[family]) for family in FILE_ORDER)
    if maximum_records is not None and total_records > maximum_records:
        raise AtlasGenerationError("CAPACITY_EXCEEDED:ATLAS_CORE_SILENT_SAMPLING_FORBIDDEN")

    partition_rows = _family_rows_by_partition(graph)
    files: dict[str, bytes] = {}
    root_partitions: dict[str, Any] = {}
    total_counts = {family: 0 for family in FILE_ORDER}
    for partition in PARTITIONS:
        file_records: dict[str, Any] = {}
        partition_counts: dict[str, int] = {}
        for family in FILE_ORDER:
            path = f"partitions/{partition}/{family}.jsonl"
            content = _jsonl(partition_rows[partition][family])
            files[path] = content
            count = len(partition_rows[partition][family])
            partition_counts[family] = count
            total_counts[family] += count
            file_records[f"{family}.jsonl"] = {"sha256": _sha256_bytes(content), "record_count": count}
        partition_body = {
            "schema": PARTITION_SCHEMA,
            "partition": partition,
            "graph_logical_hash": graph["graph_logical_hash"],
            "files": file_records,
            "counts": partition_counts,
            "authority_effect": "NONE_PARTITIONED_READ_ONLY_GRAPH",
        }
        partition_hash = canonical_sha256(partition_body)
        partition_manifest = dict(partition_body, partition_hash=partition_hash)
        manifest_path = f"partitions/{partition}/manifest.json"
        manifest_bytes = canonical_json_bytes(partition_manifest, trailing_newline=True)
        files[manifest_path] = manifest_bytes
        root_partitions[partition] = {
            "partition_hash": partition_hash,
            "manifest_sha256": _sha256_bytes(manifest_bytes),
            "counts": partition_counts,
        }

    proof_hash = canonical_sha256(proofs)
    root_body = {
        "schema": ROOT_SCHEMA,
        "programme_id": "OVC-SYSTEM-ATLAS-CONFORMANCE-v0.1",
        "graph_id": graph["graph_id"],
        "graph_logical_hash": graph["graph_logical_hash"],
        "generation_id": graph["generation"]["generation_id"],
        "repository_commit": graph["generation"]["repository_commit"],
        "repository_tree": graph["generation"]["repository_tree"],
        "completeness_profile": graph["completeness_profile"],
        "court_record_status": graph["court_record_status"],
        "partitions": root_partitions,
        "counts": total_counts,
        "source_currentness_proof_hash": proof_hash,
        "predecessor_root_hash": predecessor_root_hash,
        "retention_status": "PROVISIONAL_RETAIN_ALL_NO_DESTRUCTIVE_COMPACTION",
        "authority_effect": "NONE_CONTENT_ADDRESSED_READ_ONLY_GENERATION",
    }
    root_hash = canonical_sha256(root_body)
    root_manifest = dict(root_body, root_hash=root_hash)
    files["manifest.json"] = canonical_json_bytes(root_manifest, trailing_newline=True)
    bundle = GenerationBundle(root_hash=root_hash, root_manifest=root_manifest, files=files)
    verify_generation_bundle(bundle)
    return bundle


def build_incremental_generation(
    graph: Mapping[str, Any],
    registries: Mapping[str, Any],
    *,
    previous_bundle: GenerationBundle,
    repository_root: Path | str | None = None,
    maximum_records: int | None = None,
) -> GenerationBundle:
    candidate = build_reference_generation(
        graph,
        registries,
        repository_root=repository_root,
        predecessor_root_hash=previous_bundle.root_hash,
        maximum_records=maximum_records,
    )
    reused: dict[str, bytes] = {}
    for path, content in candidate.files.items():
        prior = previous_bundle.files.get(path)
        reused[path] = prior if prior == content else content
    incremental = GenerationBundle(candidate.root_hash, candidate.root_manifest, reused)
    verify_generation_bundle(incremental)
    return incremental


def generation_equivalence_receipt(reference: GenerationBundle, incremental: GenerationBundle) -> dict[str, Any]:
    paths = sorted(set(reference.files) | set(incremental.files))
    comparisons = [
        {
            "path": path,
            "reference_sha256": _sha256_bytes(reference.files.get(path, b"")),
            "incremental_sha256": _sha256_bytes(incremental.files.get(path, b"")),
            "equal": reference.files.get(path) == incremental.files.get(path),
        }
        for path in paths
    ]
    passed = reference.root_hash == incremental.root_hash and all(row["equal"] for row in comparisons)
    return {
        "schema": "ovc-atlas-generation-equivalence-receipt/v1",
        "reference_root_hash": reference.root_hash,
        "incremental_root_hash": incremental.root_hash,
        "file_comparisons": comparisons,
        "result": "PASS" if passed else "FAIL_QUARANTINE_INCREMENTAL",
        "optimized_authority": "NONE_REFERENCE_SEMANTICS_CONTROL",
    }


def verify_generation_bundle(bundle: GenerationBundle) -> dict[str, Any]:
    manifest = dict(bundle.root_manifest)
    observed_root = manifest.pop("root_hash", None)
    _require(observed_root == canonical_sha256(manifest), "ATLAS_GENERATION_ROOT_HASH_MISMATCH")
    _require(observed_root == bundle.root_hash, "ATLAS_GENERATION_ROOT_ID_MISMATCH")
    _require(bundle.files.get("manifest.json") == canonical_json_bytes(bundle.root_manifest, trailing_newline=True), "ATLAS_ROOT_MANIFEST_BYTES_MISMATCH")
    for partition, root_row in bundle.root_manifest["partitions"].items():
        manifest_path = f"partitions/{partition}/manifest.json"
        raw_manifest = bundle.files.get(manifest_path)
        _require(raw_manifest is not None, f"ATLAS_PARTITION_MANIFEST_MISSING:{partition}")
        _require(_sha256_bytes(raw_manifest) == root_row["manifest_sha256"], f"ATLAS_PARTITION_MANIFEST_HASH_MISMATCH:{partition}")
        partition_manifest = json.loads(raw_manifest)
        partition_body = dict(partition_manifest)
        partition_hash = partition_body.pop("partition_hash", None)
        _require(partition_hash == canonical_sha256(partition_body), f"ATLAS_PARTITION_ROOT_HASH_MISMATCH:{partition}")
        _require(partition_hash == root_row["partition_hash"], f"ATLAS_PARTITION_ROOT_ID_MISMATCH:{partition}")
        for filename, file_row in partition_manifest["files"].items():
            path = f"partitions/{partition}/{filename}"
            content = bundle.files.get(path)
            _require(content is not None, f"ATLAS_PARTITION_FILE_MISSING:{path}")
            _require(_sha256_bytes(content) == file_row["sha256"], f"ATLAS_PARTITION_FILE_HASH_MISMATCH:{path}")
            _require(len(_parse_jsonl(content)) == file_row["record_count"], f"ATLAS_PARTITION_FILE_COUNT_MISMATCH:{path}")
    return {"status": "PASS", "root_hash": bundle.root_hash, "authority_effect": "NONE_VALIDATION_ONLY"}


def materialize_generation(bundle: GenerationBundle, external_atlas_root: Path | str) -> Path:
    verify_generation_bundle(bundle)
    root = Path(external_atlas_root)
    target = root / "generations" / bundle.root_hash
    if target.exists():
        loaded = load_generation_bundle(target)
        _require(loaded.files == bundle.files, "ATLAS_EXISTING_GENERATION_BYTES_MISMATCH")
        return target
    for path, content in sorted(bundle.files.items()):
        destination = target / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    return target


def load_generation_bundle(generation_directory: Path | str) -> GenerationBundle:
    directory = Path(generation_directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    files: dict[str, bytes] = {}
    for path in directory.rglob("*"):
        if path.is_file():
            files[path.relative_to(directory).as_posix()] = path.read_bytes()
    bundle = GenerationBundle(root_hash=manifest["root_hash"], root_manifest=manifest, files=files)
    verify_generation_bundle(bundle)
    return bundle


def publish_current_generation(
    bundle: GenerationBundle,
    external_atlas_root: Path | str,
    *,
    pre_publish_main: Mapping[str, str],
    rechecked_main: Mapping[str, str],
) -> dict[str, Any]:
    target = materialize_generation(bundle, external_atlas_root)
    expected = {
        "commit": bundle.root_manifest["repository_commit"],
        "tree": bundle.root_manifest["repository_tree"],
    }
    _require(dict(pre_publish_main) == expected, "ATLAS_PRE_PUBLISH_MAIN_NOT_CANDIDATE_SOURCE")
    current = dict(rechecked_main) == expected
    receipt_body = {
        "schema": "ovc-atlas-pre-publish-currentness-receipt/v1",
        "root_hash": bundle.root_hash,
        "pre_publish_main": dict(pre_publish_main),
        "rechecked_main": dict(rechecked_main),
        "result": "PASS_CURRENT_POINTER_SWITCHED" if current else "STALE_MAIN_MOVED_POINTER_NOT_SWITCHED",
        "candidate_disposition": "CURRENT" if current else "HISTORICAL_RETAINED",
        "authority_effect": "NONE_EXTERNAL_POINTER_MAINTENANCE_ONLY",
    }
    receipt = dict(receipt_body, receipt_hash=canonical_sha256(receipt_body))
    receipt_path = Path(external_atlas_root) / "milestones" / "publication_receipts" / f"{receipt['receipt_hash']}.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_bytes(canonical_json_bytes(receipt, trailing_newline=True))
    if current:
        pointer = {
            "schema": "ovc-atlas-current-generation-pointer/v1",
            "root_hash": bundle.root_hash,
            "repository_commit": expected["commit"],
            "repository_tree": expected["tree"],
            "generation_directory": target.relative_to(Path(external_atlas_root)).as_posix(),
            "publication_receipt_hash": receipt["receipt_hash"],
            "authority_effect": "NONE_READ_ONLY_CURRENT_POINTER",
        }
        pointer_path = Path(external_atlas_root) / "generations" / "CURRENT.json"
        temporary = pointer_path.with_suffix(".json.pending")
        temporary.write_bytes(canonical_json_bytes(pointer, trailing_newline=True))
        os.replace(temporary, pointer_path)
    return receipt


def retention_inventory(external_atlas_root: Path | str) -> dict[str, Any]:
    generation_root = Path(external_atlas_root) / "generations"
    retained = sorted(
        path.name for path in generation_root.iterdir() if path.is_dir() and len(path.name) == 64
    ) if generation_root.exists() else []
    return {
        "schema": "ovc-atlas-provisional-retention-inventory/v1",
        "retained_generation_roots": retained,
        "retention_status": "PROVISIONAL_RETAIN_ALL",
        "destructive_compaction": "DENIED_PENDING_ATLAS_RETENTION_BUDGET",
        "authority_effect": "NONE_INVENTORY_ONLY",
    }
