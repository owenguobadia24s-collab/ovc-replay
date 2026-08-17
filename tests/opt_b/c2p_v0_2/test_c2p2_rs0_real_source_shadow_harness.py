from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts/c2p2_rs0_real_source_shadow.py"
AUTHORITY = REPO_ROOT / "registries/authority/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_AUTHORITY_v0_2.json"
WORKFLOW = REPO_ROOT / ".github/workflows/c2p2-rs0-real-source-shadow-run.yml"
TRIGGER_REL = "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_TRIGGER_v0_1.json"
OVERRIDE = REPO_ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_NOVIT_OPERATOR_OVERRIDE_v0_1.json"


def test_real_source_harness_accepts_exact_fresh_grun_bindings() -> None:
    env = dict(os.environ)
    src = str(REPO_ROOT / "src")
    env["PYTHONPATH"] = src if not env.get("PYTHONPATH") else os.pathsep.join([src, env["PYTHONPATH"]])
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "validate-repo-bindings", "--repo-root", str(REPO_ROOT)],
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
    )
    assert completed.returncode == 0, (
        "fresh-GRUN binding validation failed in isolated subprocess\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )
    payload = json.loads(completed.stdout)
    assert payload["authority_id"] == "AUTH.C2P2.RS0.REAL_SOURCE_SHADOW.ONE_RUN.v0.2"
    assert payload["candidate_generation_id"] == "C2P2-PS0-EMPIRICAL-RUNTIME-GENERATION-v3"
    assert payload["runtime_binding_id"] == "C2P2_RS0_EMPIRICAL_RUNTIME_BINDING_v0_1"
    assert payload["source_materialisation_id"] == "C2P2.RS0.CURRENT.C2VNEXT.C2E.2021_2023.v1"
    assert payload["capacity"]["concurrency_limit"] == 1
    assert payload["capacity"]["reduced_precision"] == "FORBIDDEN"
    assert payload["capacity"]["population_change"] == "FORBIDDEN"


def test_fresh_grun_authority_remains_single_use_and_non_selecting() -> None:
    authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))
    assert authority["execution_count_limit"] == 1
    assert authority["execution_count_consumed"] == 0
    assert authority["run_count_remaining"] == 1
    assert authority["candidate_generation"]["selection_state"] == "COMPARATIVE_SET_ONLY_NO_WINNER"
    assert authority["candidate_generation"]["active_object_pack_id"] is None
    assert authority["non_transitive_denials"]["objectpack_selection"] == "NONE"
    assert authority["non_transitive_denials"]["c2p_activation"] == "NONE"
    assert authority["non_transitive_denials"]["validation"] == "LOCKED_UNCONSUMED"


def test_no_vit_operator_override_is_bounded_to_this_execution_packet() -> None:
    override = json.loads(OVERRIDE.read_text(encoding="utf-8"))
    assert override["packet_id"] == "C2P2-RS0-REAL-SOURCE-SHADOW-RUN"
    assert override["decision"] == "PASS"
    assert override["vit"]["required_for_this_execution_branch"] is False
    assert override["vit"]["permanent_main_integration_authority"] == "NOT_GRANTED_BY_THIS_OVERRIDE"
    assert override["preserved_semantic_scope"]["run_count"] == 1
    assert override["preserved_semantic_scope"]["selection"] == "NONE"
    assert override["preserved_semantic_scope"]["activation"] == "NONE"


def test_execution_workflow_is_exact_trigger_marker_gated() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "run/c2p2-rs0-real-source-shadow-novit-20260817" in workflow
    assert TRIGGER_REL in workflow
    assert "cancel-in-progress: false" in workflow
    assert "contents: write" in workflow
    assert "run-id: '32010902424'" in workflow
    assert "Fail workflow closed when the authorised comparative run did not complete" in workflow
