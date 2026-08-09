#!/usr/bin/env python3
"""C2E-AG1 evidence-only restart-equivalence harness.

This harness is deliberately separate from the frozen WP6 executor.  It verifies
and imports the exact external WP6 executor, executes the exact frozen June
population only when explicitly run in ``execute`` mode, checkpoints at the
natural completed-partition boundary (ASK complete), simulates a process
restart by serializing/reloading the prefix, restores closed-partition episode
projection state, then executes BID and compares the resulting scientific
artifacts byte-for-byte with the already-lawful uninterrupted WP6 run A/B.

``verify-baseline-only`` is read-only: it never executes source replay.  It only
checks that the persisted uninterrupted stream contains a unique natural ASK ->
BID partition boundary and that the closed ASK partition can be reconstructed
from the existing stream prefix consistently with the final persisted ASK
snapshots.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import sys
import tarfile
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Mapping

EXPECTED_EXECUTOR_SHA256 = "98e87b229ad82475970b72da169b115aa99eb736926b97ce2c1b339c9028fe6a"
EXPECTED_BASELINE_LOGICAL_OUTPUT_SHA256 = "18519e37a16bc1f73148f3764ec1444d1fcd36fce82e9a1d585f712fb02d6988"
RESTART_CUT = "PARTITION_END:ASK"
SCIENTIFIC_FILES = (
    "c2e-input-frame-index-v0_3.jsonl",
    "c2e-boundary-evaluations-v2.jsonl",
    "c2e-event-stream-v0_2.jsonl",
    "c2e-boundary-disagreement-ledger.jsonl",
    "c2e-not-evaluable-candidates.jsonl",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]], canonical_bytes) -> None:
    with path.open("wb") as f:
        for row in rows:
            f.write(canonical_bytes(row) + b"\n")


def import_executor(path: Path) -> ModuleType:
    observed = sha256_file(path)
    if observed != EXPECTED_EXECUTOR_SHA256:
        raise RuntimeError(f"EXECUTOR_SHA256_MISMATCH:{observed}")
    spec = importlib.util.spec_from_file_location("c2e_wp6_frozen_executor", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("EXECUTOR_IMPORT_SPEC_FAILED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def extract_run_archive(tgz: Path, dest: Path) -> Path:
    with tarfile.open(tgz, "r:gz") as tf:
        tf.extractall(dest)
    roots = [p for p in dest.iterdir() if p.is_dir()]
    if len(roots) != 1:
        raise RuntimeError("BASELINE_ARCHIVE_ROOT_CARDINALITY")
    return roots[0]


def episode_side_map(records: list[Mapping[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in records:
        if row.get("schema") == "c2e_episode_genesis/v0_2":
            result[str(row["episode_id"])] = str(row["side"])
    return result


def baseline_partition_boundary(records: list[Mapping[str, Any]]) -> int:
    """Return exclusive record index at the end of the ASK partition."""
    first_bid = None
    for index, row in enumerate(records):
        if row.get("schema") == "c2e_episode_genesis/v0_2" and row.get("side") == "BID":
            first_bid = index
            break
    if first_bid is None or first_bid <= 0:
        raise RuntimeError("BID_PARTITION_START_NOT_FOUND")
    prefix = records[:first_bid]
    sides = episode_side_map(prefix)
    if not sides or set(sides.values()) != {"ASK"}:
        raise RuntimeError("ASK_PREFIX_PARTITION_IDENTITY_FAILED")
    if not any(
        r.get("schema") == "c2e_boundary_event/v0_2"
        and r.get("lifecycle_action") == "CENSOR_RELEASE_END"
        and any(sides.get(str(eid)) == "ASK" for eid in r.get("episode_ids", []))
        for r in prefix
    ):
        raise RuntimeError("ASK_RELEASE_END_CENSOR_MISSING")
    return first_bid


def restore_closed_partition_engine(ex: ModuleType, prefix_records: list[Mapping[str, Any]], *, pack_id: str, source_release_id: str):
    """Restore the completed ASK partition from its persisted append-only prefix."""
    engine = ex.ReplayEngine(pack_id, source_release_id)
    engine.records = [copy.deepcopy(dict(row)) for row in prefix_records]
    genesis_side: dict[str, str] = {}
    for row in prefix_records:
        schema = row.get("schema")
        if schema == "c2e_episode_genesis/v0_2":
            eid = str(row["episode_id"])
            genesis_side[eid] = str(row["side"])
            engine.episodes[eid] = ex.EpisodeState(eid, "OPEN", [], [], [], "", [])
        elif schema == "c2e_boundary_event/v0_2":
            action = str(row.get("lifecycle_action"))
            for raw_eid in row.get("episode_ids", []):
                eid = str(raw_eid)
                if eid not in engine.episodes:
                    raise RuntimeError(f"RESTORE_EVENT_EPISODE_MISSING:{eid}")
                engine.episodes[eid].boundary_ids.append(str(row["boundary_event_id"]))
                if action in {"CENSOR_GAP", "CENSOR_RELEASE_END"}:
                    engine.episodes[eid].status = "CENSORED"
                elif action == "TERMINATE":
                    engine.episodes[eid].status = "TERMINATED"
                elif action == "TERMINATE_CONFLICT":
                    engine.episodes[eid].status = "CONFLICTED"
        elif schema == "c2e_membership_delta/v0_2":
            eid = str(row["episode_id"])
            if eid not in engine.episodes:
                raise RuntimeError(f"RESTORE_MEMBERSHIP_EPISODE_MISSING:{eid}")
            if row.get("operation") == "ADD":
                engine.episodes[eid].member_ids.append(str(row["frame_id"]))
        elif schema == "c2e_phase_segment/v0_2":
            eid = str(row["episode_id"])
            if eid not in engine.episodes:
                raise RuntimeError(f"RESTORE_PHASE_EPISODE_MISSING:{eid}")
            engine.episodes[eid].phase_ids.append(str(row["phase_segment_id"]))
        elif schema == "c2e_episode_snapshot/v0_2":
            raise RuntimeError("PREFIX_MUST_PRECEDE_FINAL_SNAPSHOTS")
    if not genesis_side or set(genesis_side.values()) != {"ASK"}:
        raise RuntimeError("RESTORE_PARTITION_SIDE_MISMATCH")
    if engine.active_by_side:
        raise RuntimeError("RESTORE_PARTITION_MUST_HAVE_NO_ACTIVE_SIDE")
    if any(state.status != "CENSORED" for state in engine.episodes.values()):
        raise RuntimeError("RESTORE_PARTITION_HAS_NONCENSORED_EPISODE")
    return engine


def validate_restored_ask_against_baseline(ex: ModuleType, run_root: Path) -> dict[str, Any]:
    records = load_jsonl(run_root / "c2e-event-stream-v0_2.jsonl")
    boundary = baseline_partition_boundary(records)
    prefix = records[:boundary]
    genesis = [r for r in prefix if r.get("schema") == "c2e_episode_genesis/v0_2"]
    if not genesis:
        raise RuntimeError("ASK_GENESIS_EMPTY")
    pack_id = str(genesis[0]["boundary_pack_id"])
    source_release_id = str(genesis[0]["source_release_id"])
    restored = restore_closed_partition_engine(ex, prefix, pack_id=pack_id, source_release_id=source_release_id)
    baseline_snaps = {
        str(r["episode_id"]): r
        for r in records
        if r.get("schema") == "c2e_episode_snapshot/v0_2" and str(r["episode_id"]) in restored.episodes
    }
    if len(baseline_snaps) != len(restored.episodes):
        raise RuntimeError("ASK_SNAPSHOT_CARDINALITY_MISMATCH")
    for eid, state in restored.episodes.items():
        snap = baseline_snaps[eid]
        if state.status != snap["status"]:
            raise RuntimeError(f"ASK_RESTORE_STATUS_MISMATCH:{eid}")
        if sorted(state.member_ids) != sorted(snap["member_ids"]):
            raise RuntimeError(f"ASK_RESTORE_MEMBER_MISMATCH:{eid}")
        if sorted(state.phase_ids) != sorted(snap["phase_segment_ids"]):
            raise RuntimeError(f"ASK_RESTORE_PHASE_MISMATCH:{eid}")
        if sorted(state.boundary_ids) != sorted(snap["boundary_event_ids"]):
            raise RuntimeError(f"ASK_RESTORE_BOUNDARY_MISMATCH:{eid}")
    ordered_hashes = [str(r["logical_hash"]) for r in prefix]
    return {
        "status": "PASS",
        "mode": "READ_ONLY_BASELINE_RECONSTRUCTION",
        "restart_cut": RESTART_CUT,
        "prefix_record_count": len(prefix),
        "restored_episode_count": len(restored.episodes),
        "semantic_prefix_hash": ex.sha256_obj(ordered_hashes),
        "authority_effect": "NONE",
        "real_source_replay_executed": False,
    }


def _rule(ex: ModuleType, pack: Mapping[str, Any], rid: str) -> dict[str, Any]:
    return ex._rule(pack, rid)


def process_side(ex: ModuleType, *, side: str, materialisation: Mapping[str, Any], pack: Mapping[str, Any], source_build_commit: str,
                 engine, frame_index: list[dict[str, Any]], evaluations: list[dict[str, Any]], disagreements: list[dict[str, Any]],
                 blocked_candidates: list[dict[str, Any]], counters: dict[str, int]) -> None:
    manifest = materialisation["manifest"]
    bundles = [b for b in materialisation["bundles"] if str(b["side"]) == side]
    bundles.sort(key=lambda b: (b["first_valid_time"], b["observation_id"]))
    previous = None
    for bundle in bundles:
        frame = ex.build_frame(
            bundle,
            predecessor_observation_id=(previous["identity"]["observation_id"] if previous is not None else None),
            observations=materialisation["observations"], parent_observations=materialisation["parent_observations"],
            profiles=materialisation["profiles"], memberships=materialisation["memberships"], contexts=materialisation["contexts"],
            levels=materialisation["levels"], containers=materialisation["containers"], relation_sets=materialisation["relation_sets"],
            materialisation_manifest=manifest, source_build_commit=source_build_commit,
        )
        frame_index.append({
            "schema":"c2e_input_frame_index/v0_1","frame_id":frame["frame_id"],"logical_hash":frame["logical_hash"],
            "lineage_hash":frame["lineage_hash"],"observation_id":frame["identity"]["observation_id"],"side":frame["identity"]["side"],
            "first_valid_time":frame["chronology"]["first_valid_time"],"continuity_segment_id":frame["chronology"]["continuity_segment_id"],
            "predecessor_observation_id":frame["chronology"].get("predecessor_observation_id"),
            "structural_signature_sha256":frame["comparison"]["structural_signature_sha256"],
            "parent_signature_sha256":frame["comparison"]["parent_signature_sha256"],"context_bundle_id":frame["context"].get("context_resolution_bundle_id"),
            "source_relation_set_count":sum(1 for x in frame["lineage"]["parent_record_ids"] if str(x).startswith("C2.RELATION.SET.")),
            "authority":"INACTIVE_NONCANONICAL_SHADOW",
        })
        matched = ex.evaluate_predicates(frame, previous)
        legacy = ex.evaluate_legacy_predicates(frame, previous)
        if matched != legacy:
            counters["legacy_disagreements"] += 1
            disagreements.append({
                "schema":"c2e_boundary_disagreement/v0_1","side":side,"frame_id":frame["frame_id"],
                "first_valid_time":frame["chronology"]["first_valid_time"],
                "corrected_matched_rules":[r for r in ex.RULE_IDS if matched[r]],
                "legacy_matched_rules":[r for r in ex.RULE_IDS if legacy[r]],"authority":"COMPARATOR_ONLY",
            })
        candidates = []
        for rid in ex.RULE_IDS:
            c = ex._candidate(_rule(ex, pack, rid), frame, matched[rid], frame["chronology"]["first_valid_time"])
            if c is not None:
                if not c["evaluable"]:
                    counters["candidate_not_evaluable"] += 1
                    blocked_candidates.append(c)
                candidates.append(c)
        resolved = ex.resolve_candidates(pack, candidates)
        if resolved["status"] != "RESOLVED":
            counters["resolver_conflicts"] += 1
            raise RuntimeError(f"BOUNDARY_RESOLUTION_CONFLICT:{side}:{frame['frame_id']}:{resolved['reason_codes']}")
        actions = []
        for c in resolved["resolved"]:
            action = c["lifecycle_action"]
            if action == "CENSOR_GAP": engine.censor(side, c, "CENSOR_GAP"); counters["censor_gap"] += 1
            elif action == "RE_PARENT": engine.reparent(side, c); counters["re_parent"] += 1
            elif action == "PHASE_MUTATION": engine.phase(side, frame, c); counters["phase_mutation"] += 1
            elif action == "CONTINUATION": engine.continuation(side, frame, c); counters["continuation"] += 1
            elif action == "BIRTH": engine.birth(frame, c); counters["birth"] += 1
            else: raise RuntimeError(f"UNSUPPORTED_LIFECYCLE_ACTION:{action}")
            actions.append(action)
        evaluations.append({
            "schema":"c2e_boundary_evaluation/v0_2","side":side,"frame_id":frame["frame_id"],
            "first_valid_time":frame["chronology"]["first_valid_time"],"matched_rules":[r for r in ex.RULE_IDS if matched[r]],
            "resolved_actions":actions,"blocked_candidate_ids":[c["candidate_id"] for c in candidates if not c["evaluable"]],
            "authority":"INACTIVE_NONCANONICAL_SHADOW",
        })
        previous = frame
    if previous is None:
        raise RuntimeError(f"SIDE_POPULATION_EMPTY:{side}")
    release_matched = ex.evaluate_predicates(previous, previous, release_end=True)
    candidate = ex._candidate(_rule(ex, pack, ex.RULE_IDS[1]), previous, release_matched[ex.RULE_IDS[1]], ex.TARGET_END)
    if candidate is None or not candidate["evaluable"]:
        raise RuntimeError("RELEASE_END_CANDIDATE_NOT_EVALUABLE")
    engine.censor(side, candidate, "CENSOR_RELEASE_END")
    counters["censor_release_end"] += 1
    evaluations.append({
        "schema":"c2e_boundary_evaluation/v0_2","side":side,"frame_id":previous["frame_id"],"first_valid_time":ex.TARGET_END,
        "matched_rules":[ex.RULE_IDS[1]],"resolved_actions":["CENSOR_RELEASE_END"],"blocked_candidate_ids":[],
        "authority":"INACTIVE_NONCANONICAL_SHADOW",
    })


def compare_scientific_files(ex: ModuleType, output: Mapping[str, Any], baseline_root: Path, out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    mapping = {
        "c2e-input-frame-index-v0_3.jsonl": output["frame_index"],
        "c2e-boundary-evaluations-v2.jsonl": output["evaluations"],
        "c2e-event-stream-v0_2.jsonl": output["records"],
        "c2e-boundary-disagreement-ledger.jsonl": output["disagreements"],
        "c2e-not-evaluable-candidates.jsonl": output["blocked_candidates"],
    }
    results: dict[str, str] = {}
    for name, rows in mapping.items():
        candidate = out_dir / name
        write_jsonl(candidate, rows, ex.canonical_bytes)
        baseline = baseline_root / name
        if candidate.read_bytes() != baseline.read_bytes():
            raise RuntimeError(f"SCIENTIFIC_ARTIFACT_MISMATCH:{name}")
        results[name] = sha256_file(candidate)
    return results


def execute_restart(ex: ModuleType, *, materialisation_root: Path, pack_path: Path, run_manifest_path: Path,
                    baseline_a_root: Path, baseline_b_root: Path | None, out_dir: Path) -> dict[str, Any]:
    pack = ex.load_json(pack_path)
    man = ex.load_json(run_manifest_path)
    materialisation = ex.load_materialisation(
        materialisation_root,
        man["source_materialisation"]["manifest_logical_sha256"],
        man["source_materialisation"]["target_bundles_sha256"],
        man["source_population"]["logical_population_sha256"],
    )
    baseline_manifest = load_json(baseline_a_root / "c2e-wp6-run-output-manifest.json")
    if baseline_manifest["logical_output_sha256"] != EXPECTED_BASELINE_LOGICAL_OUTPUT_SHA256:
        raise RuntimeError("BASELINE_A_LOGICAL_OUTPUT_IDENTITY_MISMATCH")
    if baseline_b_root is not None:
        b_manifest = load_json(baseline_b_root / "c2e-wp6-run-output-manifest.json")
        if b_manifest["logical_output_sha256"] != EXPECTED_BASELINE_LOGICAL_OUTPUT_SHA256:
            raise RuntimeError("BASELINE_B_LOGICAL_OUTPUT_IDENTITY_MISMATCH")
        for name in SCIENTIFIC_FILES:
            if (baseline_a_root / name).read_bytes() != (baseline_b_root / name).read_bytes():
                raise RuntimeError(f"BASELINE_A_B_SCIENTIFIC_MISMATCH:{name}")
    counters = {k: 0 for k in ("birth","continuation","phase_mutation","re_parent","censor_gap","censor_release_end","legacy_disagreements","candidate_not_evaluable","resolver_conflicts")}
    frame_index: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []
    disagreements: list[dict[str, Any]] = []
    blocked_candidates: list[dict[str, Any]] = []
    engine = ex.ReplayEngine(str(pack["boundary_pack_id"]), str(materialisation["manifest"]["materialisation_id"]))
    process_side(ex, side="ASK", materialisation=materialisation, pack=pack, source_build_commit=man["source_build_commit"],
                 engine=engine, frame_index=frame_index, evaluations=evaluations, disagreements=disagreements,
                 blocked_candidates=blocked_candidates, counters=counters)
    baseline_records = load_jsonl(baseline_a_root / "c2e-event-stream-v0_2.jsonl")
    baseline_cut = baseline_partition_boundary(baseline_records)
    baseline_prefix = baseline_records[:baseline_cut]
    if [ex.canonical_bytes(r) for r in engine.records] != [ex.canonical_bytes(r) for r in baseline_prefix]:
        raise RuntimeError("ASK_PREFIX_NOT_IDENTICAL_TO_UNINTERRUPTED_BASELINE")
    baseline_stream_manifest = load_json(baseline_a_root / "c2e-stream-manifest-v0_2.json")
    checkpoint = ex._record("checkpoint", {
        "stream_manifest_id": baseline_stream_manifest["stream_manifest_id"],
        "completed_partitions": ["ASK"],
        "logical_cursor": RESTART_CUT,
        "semantic_prefix_hash": ex.sha256_obj([str(r["logical_hash"]) for r in engine.records]),
        "replaceable": True,
        "authority": "OPERATIONAL_NON_SEMANTIC",
    })
    restart_dir = out_dir / "restart_boundary"
    restart_dir.mkdir(parents=True, exist_ok=True)
    prefix_path = restart_dir / "ask-prefix-stream.jsonl"
    checkpoint_path = restart_dir / "ask-checkpoint.json"
    write_jsonl(prefix_path, engine.records, ex.canonical_bytes)
    checkpoint_path.write_bytes(ex.canonical_bytes(checkpoint) + b"\n")
    del engine
    persisted_prefix = load_jsonl(prefix_path)
    persisted_checkpoint = load_json(checkpoint_path)
    observed_prefix_hash = ex.sha256_obj([str(r["logical_hash"]) for r in persisted_prefix])
    if observed_prefix_hash != persisted_checkpoint["semantic_prefix_hash"]:
        raise RuntimeError("RESTART_PREFIX_HASH_DIVERGENCE")
    if persisted_checkpoint["stream_manifest_id"] != baseline_stream_manifest["stream_manifest_id"]:
        raise RuntimeError("RESTART_STREAM_MANIFEST_BINDING_MISMATCH")
    engine = restore_closed_partition_engine(
        ex, persisted_prefix,
        pack_id=str(pack["boundary_pack_id"]), source_release_id=str(materialisation["manifest"]["materialisation_id"]),
    )
    process_side(ex, side="BID", materialisation=materialisation, pack=pack, source_build_commit=man["source_build_commit"],
                 engine=engine, frame_index=frame_index, evaluations=evaluations, disagreements=disagreements,
                 blocked_candidates=blocked_candidates, counters=counters)
    snapshots = engine.snapshots(ex.TARGET_END)
    output = {
        "frame_index": frame_index, "evaluations": evaluations, "records": engine.records, "snapshots": snapshots,
        "disagreements": disagreements, "blocked_candidates": blocked_candidates, "counters": counters,
    }
    if len(frame_index) != 4072 or len([r for r in engine.records if r.get("schema") == "c2e_membership_delta/v0_2"]) != 4072:
        raise RuntimeError("RESTART_RECONCILIATION_COUNT_FAILED")
    scientific_hashes = compare_scientific_files(ex, output, baseline_a_root, out_dir / "restart-output")
    receipt = {
        "schema": "c2e_ag1_restart_equivalence_receipt/v0_1",
        "programme_id": "OVC-C2E-CAUSAL-EPISODE-CONFORMANCE-v0.2",
        "gate_id": "C2E-AG1",
        "gap_id": "C2E-AG1-GAP-001",
        "requirement": "restart_equivalence",
        "status": "PASS",
        "restart_cut": RESTART_CUT,
        "source_materialisation_id": materialisation["manifest"]["materialisation_id"],
        "source_materialisation_logical_sha256": materialisation["manifest"]["logical_sha256"],
        "source_population_logical_sha256": man["source_population"]["logical_population_sha256"],
        "boundary_pack_id": pack["boundary_pack_id"],
        "boundary_pack_logical_sha256": pack.get("logical_sha256"),
        "frozen_executor_sha256": EXPECTED_EXECUTOR_SHA256,
        "baseline_uninterrupted_logical_output_sha256": EXPECTED_BASELINE_LOGICAL_OUTPUT_SHA256,
        "ask_prefix_record_count": len(persisted_prefix),
        "checkpoint_id": persisted_checkpoint["checkpoint_id"],
        "checkpoint_semantic_prefix_hash": observed_prefix_hash,
        "scientific_artifact_equivalence": "PASS_BYTE_IDENTICAL_TO_WP6_RUN_A_AND_RUN_B",
        "scientific_artifact_hashes": scientific_hashes,
        "frame_count": len(frame_index),
        "stream_record_count": len(engine.records),
        "counters": counters,
        "provider_intake": "NONE",
        "sampling": "NONE",
        "validation_consumption": "NONE",
        "active_c2e": "NONE",
        "active_boundary_pack": "NONE",
        "authority_effect": "NONE",
    }
    receipt["logical_sha256"] = ex.sha256_obj(receipt)
    (out_dir / "C2E_AG1_RESTART_EQUIVALENCE_RECEIPT.json").write_bytes(ex.canonical_bytes(receipt) + b"\n")
    return receipt


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("verify-baseline-only", "execute"))
    p.add_argument("--executor", type=Path, required=True)
    p.add_argument("--baseline-run-a", type=Path, required=True)
    p.add_argument("--baseline-run-b", type=Path)
    p.add_argument("--materialisation-root", type=Path)
    p.add_argument("--pack", type=Path)
    p.add_argument("--run-manifest", type=Path)
    p.add_argument("--outdir", type=Path)
    args = p.parse_args()
    ex = import_executor(args.executor)
    with tempfile.TemporaryDirectory(prefix="c2e_ag1_baseline_a_") as a_tmp:
        a_root = extract_run_archive(args.baseline_run_a, Path(a_tmp))
        if args.mode == "verify-baseline-only":
            result = validate_restored_ask_against_baseline(ex, a_root)
            print(json.dumps(result, sort_keys=True))
            return 0
        if not all((args.baseline_run_b, args.materialisation_root, args.pack, args.run_manifest, args.outdir)):
            raise SystemExit("execute mode requires --baseline-run-b --materialisation-root --pack --run-manifest --outdir")
        with tempfile.TemporaryDirectory(prefix="c2e_ag1_baseline_b_") as b_tmp:
            b_root = extract_run_archive(args.baseline_run_b, Path(b_tmp))
            result = execute_restart(
                ex,
                materialisation_root=args.materialisation_root,
                pack_path=args.pack,
                run_manifest_path=args.run_manifest,
                baseline_a_root=a_root,
                baseline_b_root=b_root,
                out_dir=args.outdir,
            )
            print(json.dumps(result, sort_keys=True))
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
