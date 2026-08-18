#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import shutil
from typing import Any, Callable, Iterable, Iterator, Mapping

from ovc.opt_b.c2p_v0_2.rs0_empirical_runtime_source_order import (
    inspect_source_kind_segments,
    merge_source_factories_with_kind_segmentation,
)
from ovc.opt_b.c2p_v0_2.rs0_empirical_semantics import evaluate_pair, normalize_candidate_source_row
from ovc.opt_b.c2p_v0_2.sd_discrimination import CANDIDATE_IDS, make_edge, run_streaming_discrimination

PROGRAMME_ID = "OVC-C2P2-SCIENTIFIC-DISCRIMINATION-v0.1"
PLAN_ID = "OVC-C2P2-SCIENTIFIC-DISCRIMINATION-PLAN-v0.1"
GATE_ID = "C2P2-SD-GREAL"
PACKET_ID = "C2P2-SD-GREAL-RUN"
AUTHORITY_ID = "AUTH.C2P2.SD.GREAL.ONE_RUN.v0.1"
TOKEN_ID = "TOKEN.C2P2.SD.GREAL.ONE_RUN.v0.1"
EXPECTED_BASE_CANDIDATES = 1_489_144
EXPECTED_OWNER_STREAMS = 24
EXPECTED_EDGES = EXPECTED_BASE_CANDIDATES - EXPECTED_OWNER_STREAMS
STORAGE_LIMIT = 17_179_869_184
MEMORY_LIMIT = 1_160_593_408
CONCURRENCY_LIMIT = 1
CHECKPOINT_CADENCE = 4096
BLINDING_KEY = "C2P2-SD-PRESENTATION-BLIND-v0.1"

GENERATION_ID = "C2P2-PS0-EMPIRICAL-RUNTIME-GENERATION-v3"
GENERATION_SHA = "c7f0160f7bb8d75b92d4aa95116895c25c44c987e2e78a8352c0e491244bbf1a"
CANDIDATE_HASHES = {
    "C2P2-PS0-OP-A-STRICT-CONTINUITY-v3": "a8cb003521c62129044a4d62cb9a4d5a967cd3ef9d933fb1090ac4dad0843102",
    "C2P2-PS0-OP-B-RELATIONAL-CONTINUITY-v3": "a91f50c12438c4d5263d36b48e40acc0a5e146b474307721a4108ac2398a752e",
    "C2P2-PS0-OP-C-EPISODE-ENRICHED-CONTINUITY-v3": "29f8ac9a5844b425901fda90299f911a48a85422a390771753ffd5b894b1c52c",
}
SEMANTIC_IDS = {
    CANDIDATE_IDS[0]: "C2P2-PS0-OP-A-STRICT-CONTINUITY-v2",
    CANDIDATE_IDS[1]: "C2P2-PS0-OP-B-RELATIONAL-CONTINUITY-v2",
    CANDIDATE_IDS[2]: "C2P2-PS0-OP-C-EPISODE-ENRICHED-CONTINUITY-v2",
}
SOURCE_MATERIALISATION_ID = "C2P2.RS0.CURRENT.C2VNEXT.C2E.2021_2023.v1"
SOURCE_MATERIALISATION_SHA = "f7e772ca550fe9b1fb69c45ceca6e55f48da3b9cc02d88bb7b8dd1b74dd6766b"
SOURCE_ARTIFACT_ID = 9283576949
SOURCE_ARTIFACT_DIGEST = "sha256:482781f5b7921d64219650ff4711027337dbfe677b22415df37708848471976e"
RUNTIME_BINDING_ID = "C2P2_RS0_INDEXED_OUTCOME_EQUIVALENT_RUNTIME_BINDING_v0_3"
EVIDENCE_CONTRACT_ID = "C2P2_RS0_NEGATIVE_COVERAGE_CERTIFICATE_v0_2"
SOURCE_ORDER_BINDING_ID = "C2P2_RS0_EMPIRICAL_RUNTIME_SPOOLED_ADAPTER_BINDING_v0_2"

RELEASE = Path("docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-sd")
AUTHORITY_PATH = Path("registries/authority/C2P2_SD_GREAL_AUTHORITY_v0_1.json")
DECISION_PATH = RELEASE / "C2P2_SD_GREAL_OPERATOR_DECISION_v0_1.json"
GATE_PATH = RELEASE / "C2P2_SD_GREAL_GATE_PACKET_v0_1.json"
FREEZE_PATH = RELEASE / "C2P2_SD_WP0_INPUT_FREEZE_v0_1.json"
DEPENDENCY_PATH = Path("registries/opt_b/c2p/v0_2/research/C2P2_RS0_C2E_DEPENDENCY_ROLE_REGISTRY_v0_1.json")

SOURCE_FILES = {
    "c2-vnext-rs0-source-ask.jsonl": (752_536, "6ad6823ab7f957b3a9b4a51a43816cdb2b117a36282dfe094d7dc90570947be1"),
    "c2-vnext-rs0-source-bid.jsonl": (752_536, "81c03a3b2006451a42a76a24ea059e66496c95f71d1e6c811b477eb1640464a4"),
    "c2e-v0-2-rs0-source-ask.jsonl": (292_260, "0043dccb10f206c0197d442c7698d739ab2c7b6215677765c4c3b84d41a43a2f"),
    "c2e-v0-2-rs0-source-bid.jsonl": (292_260, "0618862c9825a0e7ef21fe00166bc92671f0267b5ca067a64788849a89837672"),
}

class GREALPreflightError(RuntimeError):
    pass

def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))

def logical_hash(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()

def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def line_count(path: Path) -> int:
    with path.open("rb") as handle:
        return sum(1 for _ in handle)

def directory_bytes(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())

def validate_repo_bindings(repo_root: Path) -> dict[str, Any]:
    decision = load_json(repo_root / DECISION_PATH)
    if decision.get("gate_id") != GATE_ID or decision.get("decision") != "PASS":
        raise GREALPreflightError("SD_GREAL_OPERATOR_DECISION_NOT_PASS")
    if decision.get("approved_authority_delta") != "ONE_EXACT_FULL_POPULATION_DISCOVERY_SHADOW_REPLAY_FOR_DISAGREEMENT_EVIDENCE_ONLY":
        raise GREALPreflightError("SD_GREAL_OPERATOR_DELTA_DRIFT")
    cap = decision.get("approved_capacity", {})
    expected_cap = {
        "external_storage_limit_bytes": STORAGE_LIMIT,
        "peak_memory_limit_bytes": MEMORY_LIMIT,
        "concurrency_limit": CONCURRENCY_LIMIT,
        "checkpoint_cadence_source_records": CHECKPOINT_CADENCE,
    }
    if cap != expected_cap:
        raise GREALPreflightError("SD_GREAL_OPERATOR_CAPACITY_DRIFT")
    gate = load_json(repo_root / GATE_PATH)
    if gate.get("gate_id") != GATE_ID or gate.get("status") != "GATE_READY" or gate.get("recommended_decision") != "PASS":
        raise GREALPreflightError("SD_GREAL_GATE_NOT_READY")
    if gate.get("proposed_capacity") != cap:
        raise GREALPreflightError("SD_GREAL_GATE_CAPACITY_DRIFT")
    bindings = gate.get("required_bindings", {})
    expected = {
        "candidate_generation_id": GENERATION_ID,
        "candidate_generation_logical_sha256": GENERATION_SHA,
        "evidence_contract_id": EVIDENCE_CONTRACT_ID,
        "runtime_binding_id": RUNTIME_BINDING_ID,
        "source_artifact_digest": SOURCE_ARTIFACT_DIGEST,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "source_materialisation_id": SOURCE_MATERIALISATION_ID,
        "source_materialisation_logical_sha256": SOURCE_MATERIALISATION_SHA,
        "source_order_binding_id": SOURCE_ORDER_BINDING_ID,
    }
    for key, value in expected.items():
        if bindings.get(key) != value:
            raise GREALPreflightError(f"SD_GREAL_REQUIRED_BINDING_DRIFT:{key}")
    if bindings.get("sampling") != "FORBIDDEN" or bindings.get("reduced_precision") != "FORBIDDEN" or bindings.get("semantic_or_threshold_change") != "FORBIDDEN":
        raise GREALPreflightError("SD_GREAL_METHOD_FIREWALL_DRIFT")
    authority = load_json(repo_root / AUTHORITY_PATH)
    if authority.get("authority_id") != AUTHORITY_ID or authority.get("state") != "AUTHORISED_NOT_STARTED":
        raise GREALPreflightError("SD_GREAL_AUTHORITY_NOT_LAUNCHABLE")
    if authority.get("execution_count_limit") != 1 or authority.get("execution_count_consumed") != 0 or authority.get("run_count_remaining") != 1:
        raise GREALPreflightError("SD_GREAL_SINGLE_USE_NOT_AVAILABLE")
    if authority.get("fresh_run_token_id") != TOKEN_ID or authority.get("fresh_run_token_state") != "UNCONSUMED":
        raise GREALPreflightError("SD_GREAL_TOKEN_NOT_AVAILABLE")
    if authority.get("run_mode") != "FULL_POPULATION_DISAGREEMENT_EVIDENCE_REPLAY_ONLY" or authority.get("capacity") != cap:
        raise GREALPreflightError("SD_GREAL_AUTHORITY_DRIFT")
    if authority.get("candidate_generation", {}).get("candidate_logical_hashes") != CANDIDATE_HASHES:
        raise GREALPreflightError("SD_GREAL_CANDIDATE_HASH_DRIFT")
    if authority.get("candidate_generation", {}).get("selection_state") != "COMPARATIVE_SET_ONLY_NO_WINNER":
        raise GREALPreflightError("SD_GREAL_SELECTION_STATE_DRIFT")
    if authority.get("active_object_pack_id") is not None or authority.get("c2p_activation") != "NONE":
        raise GREALPreflightError("SD_GREAL_ACTIVATION_FORBIDDEN")
    freeze = load_json(repo_root / FREEZE_PATH)
    fi = freeze.get("frozen_inputs", {})
    if fi.get("candidate_generation_id") != GENERATION_ID or fi.get("candidate_generation_logical_sha256") != GENERATION_SHA or fi.get("candidate_hashes") != CANDIDATE_HASHES:
        raise GREALPreflightError("SD_GREAL_WP0_GENERATION_DRIFT")
    if fi.get("source_materialisation_logical_sha256") != SOURCE_MATERIALISATION_SHA or fi.get("source_artifact_digest") != SOURCE_ARTIFACT_DIGEST:
        raise GREALPreflightError("SD_GREAL_WP0_SOURCE_DRIFT")
    dependency = load_json(repo_root / DEPENDENCY_PATH)
    if dependency.get("entries") != []:
        raise GREALPreflightError("SD_GREAL_C2E_DEPENDENCY_REGISTRY_NOT_EMPTY")
    return {"authority_id": AUTHORITY_ID, "token_id": TOKEN_ID, "capacity": cap}

def locate_source_root(root: Path) -> Path:
    nested = root / "c2p2-rs0-current-source"
    candidate = nested if nested.is_dir() else root
    if all((candidate / name).is_file() for name in SOURCE_FILES):
        return candidate
    raise GREALPreflightError("SD_GREAL_SOURCE_FILES_NOT_FOUND")

def jsonl_factory(path: Path) -> Callable[[], Iterable[Mapping[str, Any]]]:
    def factory() -> Iterable[Mapping[str, Any]]:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    yield json.loads(line)
    return factory

def preflight_source(repo_root: Path, source_root: Path, output_dir: Path) -> dict[str, Any]:
    validate_repo_bindings(repo_root)
    src = locate_source_root(source_root)
    observed: dict[str, Any] = {}
    for name, (expected_rows, expected_sha) in SOURCE_FILES.items():
        path = src / name
        rows = line_count(path)
        digest = file_sha256(path)
        if rows != expected_rows or digest != expected_sha:
            raise GREALPreflightError(f"SD_GREAL_SOURCE_FILE_DRIFT:{name}:{rows}:{digest}")
        observed[name] = {"rows": rows, "sha256": digest}
    c2_files = [src / "c2-vnext-rs0-source-ask.jsonl", src / "c2-vnext-rs0-source-bid.jsonl"]
    inspections = [inspect_source_kind_segments(jsonl_factory(path)()) for path in c2_files]
    base_candidates = sum(int(row["base_candidate_rows"]) for row in inspections)
    if base_candidates != EXPECTED_BASE_CANDIDATES:
        raise GREALPreflightError(f"SD_GREAL_BASE_CANDIDATE_COUNT_DRIFT:{base_candidates}")
    plan = {
        "schema": "ovc-c2p2-sd-greal-source-plan/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "authority_id": AUTHORITY_ID,
        "source_root": str(src.resolve()),
        "source_files": observed,
        "c2_source_files": [str(path.resolve()) for path in c2_files],
        "source_order_inspections": inspections,
        "base_candidate_rows": base_candidates,
        "expected_owner_streams": EXPECTED_OWNER_STREAMS,
        "expected_identity_edges": EXPECTED_EDGES,
        "real_source_read": True,
        "semantic_execution_started": False,
        "selection": "NONE",
        "activation": "NONE",
        "validation": "LOCKED_UNCONSUMED",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "source-plan-greal.json", plan)
    return plan

def owner_stream_key(material: Mapping[str, Any], raw: Mapping[str, Any]) -> str:
    return logical_hash({
        "schema": "ovc-c2p2-sd-owner-stream-key/v1",
        "hard_scope": material["hard_scope"],
        "source_record_kind": material["source_record_kind"],
        "owner_geometry_class": material["owner_geometry_class"],
        "raw_structural_role_id": raw["structural_role_id"],
        "raw_geometry_kind_id": raw["geometry_kind_id"],
    })

def disposition(semantic_id: str, previous: Mapping[str, Any], current: Mapping[str, Any], dependency: Mapping[str, Any]) -> str:
    pair = evaluate_pair(semantic_id, previous, current, dependency)
    return "SAME" if pair["same_object_pair_supported"] else "NO_CORRESPONDENCE"

def context_view(raw: Mapping[str, Any], material: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source_record_id": raw["source_record_id"], "source_record_kind": raw["source_record_kind"],
        "first_valid_time": raw["first_valid_time"], "evaluation_cutoff": raw["evaluation_cutoff"],
        "structural_role_id": raw["structural_role_id"], "geometry_kind_id": raw["geometry_kind_id"],
        "geometry_signature": raw["geometry_signature"], "relation_topology": raw["relation_topology"],
        "owner_geometry_class": material["owner_geometry_class"], "hard_scope": material["hard_scope"],
    }

def edge_stream(source_plan: Mapping[str, Any], dependency: Mapping[str, Any], counters: dict[str, Any]) -> Iterator[dict[str, Any]]:
    factories = [jsonl_factory(Path(path)) for path in source_plan["c2_source_files"]]
    previous: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    disposition_counts: Counter[str] = Counter()
    owner_rows: Counter[str] = Counter()
    base_rows = edges = 0
    for raw_row in merge_source_factories_with_kind_segmentation(factories):
        raw = dict(raw_row)
        material = normalize_candidate_source_row(raw)
        base_rows += 1
        key = owner_stream_key(material, raw)
        owner_rows[key] += 1
        prior = previous.get(key)
        if prior is not None:
            prior_raw, prior_material = prior
            candidate_dispositions = {
                candidate_id: disposition(SEMANTIC_IDS[candidate_id], prior_material, material, dependency)
                for candidate_id in CANDIDATE_IDS
            }
            disposition_counts["|".join(candidate_dispositions[candidate_id] for candidate_id in CANDIDATE_IDS)] += 1
            breaks: list[str] = []
            if prior_raw["structural_role_id"] != raw["structural_role_id"]:
                breaks.append("DECLARED_STRUCTURAL_ROLE_CHANGE")
            if prior_raw["geometry_kind_id"] != raw["geometry_kind_id"]:
                breaks.append("DECLARED_GEOMETRY_KIND_CHANGE")
            edges += 1
            yield make_edge(
                prior_source_record_id=str(prior_raw["source_record_id"]), current_source_record_id=str(raw["source_record_id"]),
                first_valid_time=str(raw["first_valid_time"]), evaluation_cutoff=str(raw["evaluation_cutoff"]),
                instrument=str(raw["instrument"]), side=str(raw["side"]), clock=str(raw["clock"]),
                structural_role_id=str(raw["structural_role_id"]), geometry_kind_id=str(raw["geometry_kind_id"]),
                candidate_dispositions=candidate_dispositions, confirmed_hard_breaks=breaks,
                owner_constitution_evidence={
                    "owner_stream_key": key,
                    "hard_scope_constant": prior_material["hard_scope"] == material["hard_scope"],
                    "source_record_kind_constant": prior_material["source_record_kind"] == material["source_record_kind"],
                    "owner_geometry_class_equal": prior_material["owner_geometry_class"] == material["owner_geometry_class"],
                    "raw_structural_role_constant": prior_raw["structural_role_id"] == raw["structural_role_id"],
                    "raw_geometry_kind_constant": prior_raw["geometry_kind_id"] == raw["geometry_kind_id"],
                    "elapsed_time_is_not_a_break": True,
                    "unobserved_break_types_not_inferred": ["EXPLICIT_UPSTREAM_INVALIDATION", "SPLIT_PARENT_DISPOSITION", "MERGE_PARENT_DISPOSITION", "REQUIRED_SOURCE_DISCONTINUITY"],
                },
                review_context={"prior": context_view(prior_raw, prior_material), "current": context_view(raw, material), "successor": None},
            )
        previous[key] = (raw, material)
    counters.update({
        "base_candidate_rows": base_rows,
        "owner_stream_count": len(owner_rows),
        "identity_edge_count": edges,
        "candidate_disposition_signature_counts": dict(sorted(disposition_counts.items())),
    })

def execute(repo_root: Path, source_plan_path: Path, output_dir: Path, github_run_id: int) -> int:
    validate_repo_bindings(repo_root)
    source_plan = load_json(source_plan_path)
    if source_plan.get("base_candidate_rows") != EXPECTED_BASE_CANDIDATES:
        raise GREALPreflightError("SD_GREAL_SOURCE_PLAN_BASE_COUNT_DRIFT")
    output_dir.mkdir(parents=True, exist_ok=True)
    start = {
        "schema": "ovc-c2p2-sd-greal-start-receipt/v1", "programme_id": PROGRAMME_ID,
        "gate_id": GATE_ID, "authority_id": AUTHORITY_ID, "fresh_run_token_id": TOKEN_ID,
        "github_actions_run_id": github_run_id, "semantic_execution_started": True,
        "authority_consumed_at_semantic_launch": True, "selection": "NONE", "activation": "NONE",
        "validation": "LOCKED_UNCONSUMED",
    }
    write_json(output_dir / "run-greal-start-receipt.json", start)
    consumption_path = output_dir / "C2P2_SD_GREAL_CONSUMPTION_v0_1.json"
    consumption = {
        "schema": "ovc-c2p2-sd-greal-consumption/v1", "programme_id": PROGRAMME_ID,
        "gate_id": GATE_ID, "authority_id": AUTHORITY_ID, "fresh_run_token_id": TOKEN_ID,
        "fresh_run_token_state": "CONSUMED", "execution_count_limit": 1, "execution_count_consumed": 1,
        "run_count_remaining": 0, "github_actions_run_id": github_run_id, "semantic_execution_started": True,
        "status": "RUNNING_SINGLE_USE_CONSUMED", "rerun": "FORBIDDEN_AFTER_SEMANTIC_LAUNCH",
    }
    write_json(consumption_path, consumption)
    ledger_dir = output_dir / "full-population-discrimination"
    if ledger_dir.exists():
        shutil.rmtree(ledger_dir)
    dependency = load_json(repo_root / DEPENDENCY_PATH)
    counters: dict[str, Any] = {}
    try:
        summary = run_streaming_discrimination(edge_stream(source_plan, dependency, counters), output_dir=ledger_dir, blinding_key=BLINDING_KEY)
        if counters.get("base_candidate_rows") != EXPECTED_BASE_CANDIDATES:
            raise GREALPreflightError(f"SD_GREAL_BASE_POPULATION_DRIFT:{counters.get('base_candidate_rows')}")
        if counters.get("owner_stream_count") != EXPECTED_OWNER_STREAMS:
            raise GREALPreflightError(f"SD_GREAL_OWNER_STREAM_COUNT_DRIFT:{counters.get('owner_stream_count')}")
        if counters.get("identity_edge_count") != EXPECTED_EDGES or summary.get("total_edges") != EXPECTED_EDGES:
            raise GREALPreflightError(f"SD_GREAL_EDGE_COUNT_DRIFT:{counters.get('identity_edge_count')}:{summary.get('total_edges')}")
        bytes_used = directory_bytes(output_dir)
        if bytes_used > STORAGE_LIMIT:
            raise GREALPreflightError(f"SD_GREAL_STORAGE_LIMIT_EXCEEDED:{bytes_used}>{STORAGE_LIMIT}")
        wp4 = {
            "schema": "ovc-c2p2-sd-wp4-real-source-ledger-summary/v1", "programme_id": PROGRAMME_ID,
            "packet_id": "C2P2-SD-WP4", "status": "COMPLETED_FULL_POPULATION", "github_actions_run_id": github_run_id,
            "source_materialisation_id": SOURCE_MATERIALISATION_ID, "candidate_generation_id": GENERATION_ID,
            "base_candidate_rows": counters["base_candidate_rows"], "owner_stream_count": counters["owner_stream_count"],
            "identity_edge_count": counters["identity_edge_count"],
            "candidate_disposition_signature_counts": counters["candidate_disposition_signature_counts"],
            "disagreement_ledger_rows": summary["disagreement_ledger_rows"], "confirmed_hard_break_rows": summary["confirmed_hard_break_rows"],
            "hard_falsification_counts": summary["hard_falsification_counts"], "ledger_sha256": summary["ledger_sha256"],
            "clock_disposition": {"15M": "BASE_CANDIDATE_IDENTITY_EDGE_POPULATION", "2H_A_L": "CONTEXT_ONLY_NOT_BASE_CANDIDATE_UNDER_FROZEN_RUNTIME"},
            "sampling": "FORBIDDEN_NONE_USED", "reduced_precision": "FORBIDDEN_NONE_USED",
            "semantic_or_threshold_change": "NONE", "selection": "NONE", "activation": "NONE", "validation": "LOCKED_UNCONSUMED",
        }
        write_json(output_dir / "C2P2_SD_WP4_REAL_SOURCE_LEDGER_SUMMARY_v0_1.json", wp4)
        wp5 = {
            "schema": "ovc-c2p2-sd-wp5-blind-review-packet/v1", "programme_id": PROGRAMME_ID,
            "packet_id": "C2P2-SD-WP5", "status": "COMPLETED_BLIND_PACKET_GENERATED", "github_actions_run_id": github_run_id,
            "blind_review_rows": summary["blind_review_rows"], "representative_selector_rows": summary["representative_selector_rows"],
            "confirmed_hard_break_rows": summary["confirmed_hard_break_rows"], "blind_review_manifest_sha256": summary["blind_review_manifest_sha256"],
            "candidate_names_hidden": summary["candidate_names_in_review_manifest"] is False,
            "unblinding_map_emitted": summary["unblinding_map_emitted"],
            "allowed_labels": ["SAME", "DIFFERENT", "AMBIGUOUS", "NOT_EVALUABLE"],
            "future_information_forbidden": True,
            "manifest_relative_path": "full-population-discrimination/blind-review-manifest.jsonl",
            "ledger_relative_path": "full-population-discrimination/disagreement-ledger.jsonl",
            "selection": "NONE", "activation": "NONE", "validation": "LOCKED_UNCONSUMED",
        }
        write_json(output_dir / "C2P2_SD_WP5_BLIND_REVIEW_PACKET_v0_1.json", wp5)
        result = {
            "schema": "ovc-c2p2-sd-greal-run-result/v1", "programme_id": PROGRAMME_ID, "packet_id": PACKET_ID,
            "gate_id": GATE_ID, "authority_id": AUTHORITY_ID, "fresh_run_token_id": TOKEN_ID,
            "github_actions_run_id": github_run_id, "status": "COMPLETED_FULL_POPULATION_DISAGREEMENT_EVIDENCE",
            "authority": {"execution_count_consumed": 1, "run_count_remaining": 0},
            "source_materialisation_id": SOURCE_MATERIALISATION_ID, "candidate_generation_id": GENERATION_ID,
            "wp4_summary": wp4, "wp5_blind_packet": wp5, "next_operator_gate": "C2P2-SD-GADJ",
            "selection_state": "COMPARATIVE_SET_ONLY_NO_WINNER", "active_object_pack_id": None,
            "c2p_activation": "NONE", "validation": "LOCKED_UNCONSUMED", "ec1_candidate_defining_use": "FORBIDDEN",
            "publication_probability_risk_exposure_trading_execution_agent_write": "NONE",
        }
        write_json(output_dir / "C2P2_SD_GREAL_RUN_RESULT_v0_1.json", result)
        consumption["status"] = "CONSUMED_COMPLETED"
        consumption["next_operator_gate"] = "C2P2-SD-GADJ"
        write_json(consumption_path, consumption)
        return 0
    except Exception as exc:
        consumption.update({"status": "CONSUMED_POST_LAUNCH_FAILURE", "failure_type": type(exc).__name__, "failure_detail": str(exc), "next_operator_gate": "C2P2-SD-GREAL-RECOVERY"})
        write_json(consumption_path, consumption)
        result = {
            "schema": "ovc-c2p2-sd-greal-run-result/v1", "programme_id": PROGRAMME_ID, "packet_id": PACKET_ID,
            "gate_id": GATE_ID, "authority_id": AUTHORITY_ID, "fresh_run_token_id": TOKEN_ID,
            "github_actions_run_id": github_run_id, "status": "BLOCKED_POST_LAUNCH_SINGLE_USE_CONSUMED",
            "failure_type": type(exc).__name__, "failure_detail": str(exc),
            "authority": {"execution_count_consumed": 1, "run_count_remaining": 0},
            "next_operator_gate": "C2P2-SD-GREAL-RECOVERY", "selection_state": "COMPARATIVE_SET_ONLY_NO_WINNER",
            "active_object_pack_id": None, "c2p_activation": "NONE", "validation": "LOCKED_UNCONSUMED",
            "publication_probability_risk_exposure_trading_execution_agent_write": "NONE",
        }
        write_json(output_dir / "C2P2_SD_GREAL_RUN_RESULT_v0_1.json", result)
        return 2

def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate-repo-bindings")
    validate.add_argument("--repo-root", default=".")
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--repo-root", default=".")
    preflight.add_argument("--source-root", required=True)
    preflight.add_argument("--output-dir", required=True)
    run = sub.add_parser("execute")
    run.add_argument("--repo-root", default=".")
    run.add_argument("--source-plan", required=True)
    run.add_argument("--output-dir", required=True)
    run.add_argument("--github-run-id", type=int, required=True)
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    if args.command == "validate-repo-bindings":
        print(canonical_json(validate_repo_bindings(repo_root)))
        return 0
    if args.command == "preflight":
        output_dir = Path(args.output_dir).resolve()
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        print(canonical_json(preflight_source(repo_root, Path(args.source_root), output_dir)))
        return 0
    if args.command == "execute":
        return execute(repo_root, Path(args.source_plan), Path(args.output_dir), args.github_run_id)
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
