"""Deterministic full-stack FSR orchestration from sealed synthetic source.

The hidden construction ledger is deliberately not imported or opened here. Post-run
adjudication lives in a separate WP11 module.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
from typing import Any

from .opt_a.fsr_synthetic import build_opt_a_fixture, c1_handoff_records
from .opt_b.c1.builder import build as build_c1
from .opt_b.c2_vnext.fsr_rehearsal_strict import run_fsr_c2_vnext_strict
from .opt_b.market_grammar.fsr_c2e_adapter import run_fsr_c2e
from .opt_b.market_grammar.fsr_grammar_adapter import run_fsr_market_grammar
from .opt_b.srfd.fsr_adapter import run_fsr_srfd
from .research_operations.canonical import canonical_sha256
from .research_operations.fsr_projection import project_fsr_research_operations

PROGRAMME_ID = "OVC-FULL-STACK-SYNTHETIC-FRESH-DISCOVERY-REHEARSAL-v0.1"
UPPER_BOUNDARY_REL = Path("docs/releases/full-stack-synthetic-fresh-discovery-v0-1/fsr-wp7/FSR_WP7_UPPER_LAYER_IMPLEMENTATION_BOUNDARY.json")


def _c1_stream(handoff: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for clock in ("15M", "2H_A_L"):
        for side in ("BID", "ASK"):
            group = sorted(
                (item for item in handoff if item["clock_id"] == clock and item["price_side"] == side),
                key=lambda item: item["open_time"],
            )
            prior = None
            for current in group:
                output.append(dataclasses.asdict(build_c1(current, prior)))
                prior = current
    return output


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_full_stack(*, repo_root: Path, output_root: Path, source_commit: str) -> dict[str, Any]:
    opt_a = build_opt_a_fixture(output_root / "opt_a", repo_root=repo_root)
    handoff = c1_handoff_records(opt_a)
    c1 = _c1_stream(handoff)
    c1_hash = canonical_sha256(c1)
    c2 = run_fsr_c2_vnext_strict(opt_a, c1)
    c2e = run_fsr_c2e(c2)
    srfd = run_fsr_srfd(c2, c2e)
    grammar = run_fsr_market_grammar(c2, c2e, srfd)
    upper_boundary_sha = _file_sha256(repo_root / UPPER_BOUNDARY_REL)
    ro = project_fsr_research_operations(
        source_commit=source_commit,
        opt_a=opt_a,
        c1_logical_sha256=c1_hash,
        c2=c2,
        c2e=c2e,
        srfd=srfd,
        grammar=grammar,
        upper_layer_boundary_sha256=upper_boundary_sha,
    )
    stage_hashes = {
        "OPT_A": opt_a["manifest_sha256"],
        "C1": c1_hash,
        "C2": c2["logical_sha256"],
        "C2E": c2e["logical_sha256"],
        "SRFD": srfd["logical_sha256"],
        "MARKET_GRAMMAR": grammar["logical_sha256"],
        "RESEARCH_OPERATIONS": ro["logical_sha256"],
    }
    run_manifest = {
        "schema": "ovc-fsr-full-stack-run-manifest/v1",
        "programme_id": PROGRAMME_ID,
        "source_commit": source_commit,
        "fixture_id": opt_a["fixture_id"],
        "source_manifest_id": opt_a["manifest_id"],
        "stage_hashes": stage_hashes,
        "counts": {
            "source_rows": sum(item["row_count"] for item in opt_a["source_inventory"]),
            "opt_a_observations": len(opt_a["observations"]),
            "opt_a_quarantine": len(opt_a["quarantine"]),
            "c1_records": len(c1),
            "c2_snapshots": c2["snapshot_count"],
            "c2_transitions": c2["transition_count"],
            "c2e_episodes": c2e["episode_count"],
            "c2e_not_evaluable": c2e["not_evaluable_count"],
            "srfd_representations": sum(srfd["representation_counts"].values()),
            "srfd_family_catalogs": len(srfd["family_benchmark"]["catalogs"]),
            "srfd_residual_assignments": srfd["family_benchmark"]["residual_count"],
            "grammar_releases": grammar["grammar_count"],
            "research_records": len(ro["records"]),
            "read_model_nodes": len(ro["read_model"]["nodes"]),
        },
        "highest_implemented_output": "MARKET_GRAMMAR_SHADOW" if grammar["status"] == "EXECUTED_SHADOW" else "SRFD_FAMILY_EVIDENCE",
        "not_reached": [
            "OccurrenceContext standalone forward object",
            "C2P persistent structural objects",
            "revised C2.5 forward event projection",
            "canonical forward C3",
        ],
        "hidden_construction_consumed": False,
        "authority": {
            "market_evidence": False,
            "canonical": False,
            "promotable": False,
            "synthetic": True,
            "selector_mutation": "NONE",
            "publication": "NONE",
            "validation_consumption": "DENIED",
            "probability_risk_exposure_execution": "NONE",
        },
    }
    run_manifest["logical_sha256"] = canonical_sha256(run_manifest)
    return {
        "opt_a": opt_a,
        "c1_handoff": handoff,
        "c1": c1,
        "c2": c2,
        "c2e": c2e,
        "srfd": srfd,
        "market_grammar": grammar,
        "research_operations": ro,
        "run_manifest": run_manifest,
    }


def replay_identity(result: dict[str, Any]) -> dict[str, Any]:
    manifest = result["run_manifest"]
    return {
        "fixture_id": manifest["fixture_id"],
        "source_manifest_id": manifest["source_manifest_id"],
        "stage_hashes": manifest["stage_hashes"],
        "counts": manifest["counts"],
        "highest_implemented_output": manifest["highest_implemented_output"],
        "not_reached": manifest["not_reached"],
        "logical_sha256": manifest["logical_sha256"],
    }
