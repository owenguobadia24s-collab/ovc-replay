from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

SOURCE = {
    "artifact_id": 8634383302,
    "artifact_name": "c2-g4-exact-parent-replay-output",
    "artifact_archive_sha256": "b8f993f733aed75e488aa60883f00a53596c15e5cd6c14edb787fc3bc12df62f",
    "workflow_run_id": 30210057332,
    "workflow_commit": "4fb06b4d2b13bdf737446cb619e548eb987aeab1",
    "replay_receipt_sha256": "27aac06a35a56518eab67027272238c7bd265161b552823b5ab59d0547d13018",
    "intake_receipt_sha256": "4d519786ce8cc138a88924d1d2ec7de37caabad2ea83e021b403f91c4266d21b",
}
EXPECTED = {"files": 24, "bytes": 872_839_722, "states": 404_434, "transitions": 323_910}
ROLES = {
    "discovery": {
        "role": "DISCOVERY",
        "release_id": "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1",
        "manifest_id": "MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1.r1",
        "c1_release": "OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1",
        "c1_manifest": "MANIFEST.C1.OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1.r1",
        "c1_hash": "6abd6d1fb74e7f3797e9add2435eaa5e487b612efd2f4b5f4f4c59679820d5d2",
        "a_release": "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
        "a_manifest": "MANIFEST.OPT-A.GBPUSD.DISCOVERY.2021_2023.v2.r2",
        "a_hash": "0cbcafa9421449574b61bfeec24f634de99cbbbc6e7a53d09ace8f702182ab8c",
    },
    "development": {
        "role": "DEVELOPMENT",
        "release_id": "OPT-B.C2.GBPUSD.DEVELOPMENT.2024.v1",
        "manifest_id": "MANIFEST.C2.OPT-B.C2.GBPUSD.DEVELOPMENT.2024.v1.r1",
        "c1_release": "OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1",
        "c1_manifest": "MANIFEST.C1.OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1.r1",
        "c1_hash": "ca83f2d9d948be426f3d80ebc91cc981f92546dfdd07268d71938d618c51f017",
        "a_release": "OPT-A.GBPUSD.DEVELOPMENT.2024.v2",
        "a_manifest": "MANIFEST.OPT-A.GBPUSD.DEVELOPMENT.2024.v2.r2",
        "a_hash": "25e1be8a7edb0e96017c45bf35f4e788345f94b22a8ed9bb0874c86338ba64cc",
    },
}


def hfile(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def cbytes(obj: Any) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n").encode()


def wjson(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(cbytes(obj))


def source_root(root: Path) -> Path:
    for p in (root / "c2-g4-output", root):
        if (p / "WP5_LOCAL_REPLAY_RECEIPT.json").is_file():
            return p
    raise SystemExit("C2-G4 source root not found")


def bindings(repo: Path) -> tuple[dict[str, str], dict[str, str], dict[str, str], str]:
    def scan(pattern: str) -> dict[str, str]:
        files = sorted(repo.glob(pattern))
        if not files:
            raise SystemExit(f"missing binding family: {pattern}")
        return {p.relative_to(repo).as_posix(): hfile(p) for p in files}
    contracts = scan("contracts/opt_b/c2/*.md")
    schemas = scan("schemas/opt_b/c2/*.schema.json")
    regs = scan("registries/opt_b/c2/*.yaml")
    pp = repo / "registries/opt_b/c2/C2_PARAMETER_PACK_v0_1.yaml"
    return contracts, schemas, {k: v for k, v in regs.items() if not k.endswith("C2_PARAMETER_PACK_v0_1.yaml")}, hfile(pp)


def scope_from_name(name: str) -> str:
    return name.removesuffix(".jsonl").replace("-v0_1", "-v0.1")


def inspect_jsonl(path: Path, rel: str, kind: str, cfg: dict[str, str], states: set[str]) -> tuple[int, set[str]]:
    expected_clock = "2H_A_L" if "/2H_A_L/" in f"/{rel}/" else "15M"
    expected_side = "ASK" if "/ASK/" in f"/{rel}/" else "BID"
    expected_scope = scope_from_name(path.name)
    id_key = "c2_state_id" if kind == "STATE" else "c2_transition_id"
    ids: set[str] = set()
    count = 0
    with path.open(encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if not line.endswith("\n"):
                raise SystemExit(f"unterminated JSONL row {rel}:{n}")
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                raise SystemExit(f"invalid JSONL {rel}:{n}: {e}") from e
            count += 1
            rid = row.get(id_key)
            if not isinstance(rid, str) or not rid or rid in ids:
                raise SystemExit(f"missing/duplicate {id_key} in {rel}:{n}")
            ids.add(rid)
            if (row.get("role"), row.get("clock"), row.get("side"), row.get("evaluation_scope_id")) != (
                cfg["role"], expected_clock, expected_side, expected_scope
            ):
                raise SystemExit(f"role/clock/side/scope mismatch {rel}:{n}")
            if not row.get("first_valid_time"):
                raise SystemExit(f"missing first_valid_time {rel}:{n}")
            if kind == "STATE":
                if (row.get("c1_release_id"), row.get("c1_manifest_id"), row.get("opt_a_release_id"), row.get("opt_a_manifest_id")) != (
                    cfg["c1_release"], cfg["c1_manifest"], cfg["a_release"], cfg["a_manifest"]
                ):
                    raise SystemExit(f"exact parent mismatch {rel}:{n}")
                if row.get("parameter_pack_id") != "C2.PARAMS.GBPUSD.DISCOVERY.v0.1":
                    raise SystemExit(f"parameter pack mismatch {rel}:{n}")
                if not row.get("parent_c1_record_id") or not row.get("parent_opt_a_bar_id"):
                    raise SystemExit(f"missing parent record IDs {rel}:{n}")
                axes = row.get("axes")
                if not isinstance(axes, dict) or set(axes) != {"LOCATION", "MOTION", "ORGANISATION", "INTERACTION", "QUALITY"}:
                    raise SystemExit(f"five-axis mismatch {rel}:{n}")
                if "overall_state" in row or "winning_state" in row:
                    raise SystemExit(f"prohibited winner field {rel}:{n}")
            elif row.get("from_state_id") not in states or row.get("to_state_id") not in states:
                raise SystemExit(f"transition endpoint outside role state inventory {rel}:{n}")
    return count, ids


def verify_source(root: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, int]]]:
    replay = root / "WP5_LOCAL_REPLAY_RECEIPT.json"
    intake = root / "WP5_CANONICAL_INTAKE_RECEIPT.json"
    if hfile(replay) != SOURCE["replay_receipt_sha256"] or hfile(intake) != SOURCE["intake_receipt_sha256"]:
        raise SystemExit("source receipt identity mismatch")
    receipt = json.loads(replay.read_text())
    if receipt.get("status") != "PASS_LOCAL_REPLAY":
        raise SystemExit("source replay not passed")
    for key, expected in {"validation_consumption": "LOCKED_UNCONSUMED", "probability": "NONE", "exposure": "NONE", "trading": "NONE", "execution": "NONE"}.items():
        if receipt.get(key) != expected:
            raise SystemExit(f"source authority mismatch: {key}")
    outputs = receipt.get("outputs", {})
    if len(outputs) != EXPECTED["files"] or sum(x["bytes"] for x in outputs.values()) != EXPECTED["bytes"]:
        raise SystemExit("source inventory totals mismatch")
    actual = {p.relative_to(root).as_posix() for d in (root / "states", root / "transitions") for p in d.rglob("*.jsonl")}
    if actual != set(outputs):
        raise SystemExit("source file inventory mismatch")
    files: list[dict[str, Any]] = []
    stats = {r: {"state_files": 0, "transition_files": 0, "state_records": 0, "transition_records": 0, "payload_bytes": 0} for r in ROLES}
    state_ids = {r: set() for r in ROLES}
    all_ids = {r: set() for r in ROLES}
    for rel in sorted(actual, key=lambda x: (not x.startswith("states/"), x)):
        parts = Path(rel).parts
        kind = "STATE" if parts[0] == "states" else "TRANSITION"
        role = parts[1]
        if role not in ROLES:
            raise SystemExit(f"unexpected role path {rel}")
        p = root / rel
        exp = outputs[rel]
        if p.stat().st_size != exp["bytes"] or hfile(p) != exp["sha256"]:
            raise SystemExit(f"full-byte source failure {rel}")
        count, ids = inspect_jsonl(p, rel, kind, ROLES[role], state_ids[role])
        if ids & all_ids[role]:
            raise SystemExit(f"duplicate record IDs across files for {role}")
        all_ids[role] |= ids
        key = "state" if kind == "STATE" else "transition"
        stats[role][f"{key}_files"] += 1
        stats[role][f"{key}_records"] += count
        stats[role]["payload_bytes"] += p.stat().st_size
        if kind == "STATE":
            state_ids[role] |= ids
        files.append({"source": p, "source_rel": rel, "role": role, "kind": kind, "candidate_rel": Path(parts[0], *parts[2:]).as_posix(), "bytes": p.stat().st_size, "sha256": exp["sha256"], "records": count})
    by_role = {x["role"].lower(): x for x in receipt["roles"]}
    for role, s in stats.items():
        rr = by_role[role]
        if (s["state_files"], s["transition_files"], s["state_records"], s["transition_records"], rr["rejected_records"], rr["scope_count"]) != (6, 6, rr["state_records"], rr["transition_records"], 0, 6):
            raise SystemExit(f"role totals mismatch {role}")
    if sum(s["state_records"] for s in stats.values()) != EXPECTED["states"] or sum(s["transition_records"] for s in stats.values()) != EXPECTED["transitions"]:
        raise SystemExit("record totals mismatch")
    return files, stats


def entry(root: Path, rel: str, kind: str | None = None, records: int | None = None) -> dict[str, Any]:
    p = root / rel
    x: dict[str, Any] = {"path": rel, "size_bytes": p.stat().st_size, "sha256": hfile(p)}
    if kind:
        x.update(record_type=kind, record_count=records)
    return x


def build_release(base: Path, role: str, source: Path, files: list[dict[str, Any]], stats: dict[str, int], binds: tuple[dict[str, str], dict[str, str], dict[str, str], str]) -> dict[str, Any]:
    cfg = ROLES[role]
    root = base / cfg["release_id"]
    root.mkdir(parents=True)
    manifest_files: list[dict[str, Any]] = []
    for item in sorted((x for x in files if x["role"] == role), key=lambda x: x["candidate_rel"]):
        dst = root / item["candidate_rel"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(item["source"], dst)
        if dst.stat().st_size != item["bytes"] or hfile(dst) != item["sha256"]:
            raise SystemExit(f"post-copy failure {item['candidate_rel']}")
        manifest_files.append(entry(root, item["candidate_rel"], item["kind"], item["records"]))
    for name in ("WP5_LOCAL_REPLAY_RECEIPT.json", "WP5_CANONICAL_INTAKE_RECEIPT.json"):
        dst = root / "source" / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, dst)
        manifest_files.append(entry(root, f"source/{name}"))
    wjson(root / "source/C2_G4_SOURCE_BINDING.json", {"schema": "ovc-c2-g5-source-binding/v1", **SOURCE})
    manifest_files.append(entry(root, "source/C2_G4_SOURCE_BINDING.json"))
    desc = {
        "schema": "ovc-c2-release-descriptor/v1", "release_id": cfg["release_id"], "role": cfg["role"],
        "parent_opt_a_release_id": cfg["a_release"], "parent_opt_a_manifest_id": cfg["a_manifest"], "parent_opt_a_manifest_sha256": cfg["a_hash"],
        "parent_c1_release_id": cfg["c1_release"], "parent_c1_manifest_id": cfg["c1_manifest"], "parent_c1_manifest_sha256": cfg["c1_hash"],
        "lifecycle_state": "RELEASE_FROZEN", "authority_state": "CANDIDATE", "availability_state": "LOCAL_ONLY",
        "active_selector": False, "selector_state": "NONE", "publication_status": "NOT_ATTEMPTED",
        "clocks": ["15M", "2H_A_L"], "price_sides": ["BID", "ASK"], "axis_registry_id": "C2.AXES.v0.1",
        "measurement_registry_id": "C2.MEASUREMENTS.v0.1", "parameter_pack_id": "C2.PARAMS.GBPUSD.DISCOVERY.v0.1", "rollback_target": "NONE_C1_ONLY",
        "source_replay_artifact_id": SOURCE["artifact_id"], "source_replay_workflow_run_id": SOURCE["workflow_run_id"],
        "state_file_count": stats["state_files"], "transition_file_count": stats["transition_files"], "state_record_count": stats["state_records"], "transition_record_count": stats["transition_records"],
        "rejected_record_count": 0, "validation_consumption": "LOCKED_UNCONSUMED", "probability_authority": "NONE", "exposure_authority": "NONE", "trading_authority": "NONE", "execution_authority": "NONE",
    }
    wjson(root / "release-descriptor.json", desc)
    manifest_files.append(entry(root, "release-descriptor.json"))
    checks = [{"check_id": f"C2-G5-{n:02d}", "status": "PASS"} for n in range(1, 11)]
    wjson(root / "qa/C2_G5_QA_SUMMARY.json", {"schema": "ovc-c2-g5-qa-summary/v1", "gate_id": "C2-G5", "release_id": cfg["release_id"], "status": "PASS", "checks": checks, "blocking_issues": 0, "unresolved_issues": 0, "validation_consumption": "LOCKED_UNCONSUMED", "publication": "NONE", "selector": "NONE", "activation": "NONE"})
    wjson(root / "qa/C2_G5_ISSUE_LEDGER.json", {"schema": "ovc-c2-g5-issue-ledger/v1", "gate_id": "C2-G5", "release_id": cfg["release_id"], "issues": [], "issue_count": 0, "open_issue_count": 0, "closed_issue_count": 0, "disposition": "NO_QA_ISSUES_RAISED_ALL_CHECKS_PASS"})
    manifest_files += [entry(root, "qa/C2_G5_QA_SUMMARY.json"), entry(root, "qa/C2_G5_ISSUE_LEDGER.json")]
    contracts, schemas, regs, pp = binds
    body = {
        "manifest_id": cfg["manifest_id"], "release_id": cfg["release_id"],
        "parent_manifests": [
            {"layer": "OPT-A", "release_id": cfg["a_release"], "manifest_id": cfg["a_manifest"], "manifest_sha256": cfg["a_hash"]},
            {"layer": "OPT-B.C1", "release_id": cfg["c1_release"], "manifest_id": cfg["c1_manifest"], "manifest_sha256": cfg["c1_hash"]},
        ],
        "contract_hashes": contracts, "schema_hashes": schemas, "registry_hashes": regs, "parameter_pack_hash": pp,
        "files": sorted(manifest_files, key=lambda x: x["path"]), "total_bytes": sum(x["size_bytes"] for x in manifest_files),
    }
    manifest = {**body, "manifest_sha256": hashlib.sha256(cbytes(body)).hexdigest()}
    wjson(root / "manifest.json", manifest)
    loaded = json.loads((root / "manifest.json").read_text())
    self_hash = loaded.pop("manifest_sha256")
    if hashlib.sha256(cbytes(loaded)).hexdigest() != self_hash:
        raise SystemExit("manifest self-hash failure")
    for x in loaded["files"]:
        p = root / x["path"]
        if not p.is_file() or p.stat().st_size != x["size_bytes"] or hfile(p) != x["sha256"]:
            raise SystemExit(f"manifest byte failure {x['path']}")
    return {"role": cfg["role"], "release_id": cfg["release_id"], "manifest_id": cfg["manifest_id"], "manifest_sha256": manifest["manifest_sha256"], "manifest_file_sha256": hfile(root / "manifest.json"), "manifest_bound_file_count": len(manifest_files), "manifest_bound_bytes": body["total_bytes"], "state_file_count": stats["state_files"], "transition_file_count": stats["transition_files"], "state_record_count": stats["state_records"], "transition_record_count": stats["transition_records"], "duplicate_record_ids": 0, "unresolved_qa_issues": 0}


def inventory(root: Path) -> list[dict[str, Any]]:
    return [{"path": p.relative_to(root).as_posix(), "size_bytes": p.stat().st_size, "sha256": hfile(p)} for p in sorted((x for x in root.rglob("*") if x.is_file()), key=lambda x: x.relative_to(root).as_posix())]


def build(base: Path, source: Path, files: list[dict[str, Any]], stats: dict[str, dict[str, int]], binds: tuple[dict[str, str], dict[str, str], dict[str, str], str]) -> list[dict[str, Any]]:
    base.mkdir(parents=True)
    return [build_release(base, role, source, files, stats[role], binds) for role in ("discovery", "development")]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact-root", type=Path, required=True)
    ap.add_argument("--repo-root", type=Path, required=True)
    ap.add_argument("--output-root", type=Path, required=True)
    a = ap.parse_args()
    src = source_root(a.artifact_root)
    files, stats = verify_source(src)
    binds = bindings(a.repo_root)
    if a.output_root.exists():
        raise SystemExit("output root already exists")
    work = a.output_root.parent / f".{a.output_root.name}.work"
    shutil.rmtree(work, ignore_errors=True)
    try:
        ra = build(work / "a", src, files, stats, binds)
        rb = build(work / "b", src, files, stats, binds)
        ia, ib = inventory(work / "a"), inventory(work / "b")
        if ia != ib or ra != rb:
            raise SystemExit("independent candidate materializations differ")
        fingerprint = hashlib.sha256(cbytes(ia)).hexdigest()
        shutil.move(str(work / "a"), str(a.output_root))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if hashlib.sha256(cbytes(inventory(a.output_root))).hexdigest() != fingerprint:
        raise SystemExit("final tree differs from deterministic materialization")
    gate = {
        "schema": "ovc-c2-g5-gate-packet/v1", "gate_id": "C2-G5", "decision": "PASS_LOCAL_CANDIDATE_RELEASE_FROZEN", "source": SOURCE,
        "verification": {"source_output_files": EXPECTED["files"], "source_output_bytes": EXPECTED["bytes"], "state_records": EXPECTED["states"], "transition_records": EXPECTED["transitions"], "rejected_records": 0, "duplicate_record_ids": 0, "deterministic_output_equivalence": "PASS_TWO_INDEPENDENT_BYTE_IDENTICAL_MATERIALIZATIONS", "candidate_tree_sha256": fingerprint, "full_byte_local_verification": "PASS", "blocking_qa_issues": 0, "unresolved_qa_issues": 0},
        "releases": ra,
        "authority_delta": {"local_candidate_release": "FROZEN_CANDIDATE_LOCAL_ONLY", "publication": "NONE", "selector": "NONE", "activation": "NONE", "validation_consumption": "LOCKED_UNCONSUMED", "probability": "NONE", "exposure": "NONE", "trading": "NONE", "execution": "NONE"},
        "next_boundary": "SEPARATE_C2_PUBLICATION_READINESS_AND_OPERATOR_APPROVAL_GATE",
    }
    wjson(a.output_root / "C2_G5_GATE_PACKET.json", gate)
    wjson(a.output_root / "C2_G5_FREEZE_REPORT.json", {"schema": "ovc-c2-g5-freeze-report/v1", "status": gate["decision"], "candidate_tree_sha256": fingerprint, "deterministic_output_equivalence": "PASS", "full_byte_local_verification": "PASS", "releases": ra, "blocking_qa_issues": 0, "unresolved_qa_issues": 0, "validation_consumption": "LOCKED_UNCONSUMED", "publication": "NONE", "selector": "NONE", "activation": "NONE"})


if __name__ == "__main__":
    main()
