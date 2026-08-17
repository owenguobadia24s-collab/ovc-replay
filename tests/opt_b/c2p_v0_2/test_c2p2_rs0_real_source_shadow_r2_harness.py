from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sqlite3


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/c2p2_rs0_real_source_shadow_r2.py"
WORKFLOW = ROOT / ".github/workflows/c2p2-rs0-real-source-shadow-run-r2.yml"
AUTHORITY = ROOT / "registries/authority/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_AUTHORITY_v0_3.json"
PRIOR_CONSUMPTION = ROOT / "registries/authority/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_CONSUMPTION_v0_1.json"

spec = importlib.util.spec_from_file_location("c2p2_rs0_r2", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_r2_repo_bindings_are_exact_and_single_use() -> None:
    bindings = module.validate_repo_bindings(ROOT)
    assert bindings["authority_id"] == "AUTH.C2P2.RS0.REAL_SOURCE_SHADOW.ONE_RUN.v0.3"
    assert bindings["candidate_ids"] == sorted(bindings["candidate_ids"])
    assert len(bindings["candidate_ids"]) == 3
    assert bindings["adapter_id"] == "C2P2_RS0_EMPIRICAL_RUNTIME_SPOOLED_ADAPTER_v0_1"


def test_r2_authority_preserves_prior_consumption_and_denials() -> None:
    authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))
    prior = json.loads(PRIOR_CONSUMPTION.read_text(encoding="utf-8"))
    assert prior["execution_count_consumed"] == 1
    assert prior["run_count_remaining"] == 0
    assert authority["execution_count_limit"] == 1
    assert authority["execution_count_consumed"] == 0
    assert authority["run_count_remaining"] == 1
    assert authority["non_transitive_denials"]["objectpack_selection"] == "NONE"
    assert authority["non_transitive_denials"]["c2p_activation"] == "NONE"
    assert authority["non_transitive_denials"]["validation"] == "LOCKED_UNCONSUMED"


def test_compact_summary_materialises_whole_population_aggregates_without_ranking(tmp_path: Path) -> None:
    database = tmp_path / "runtime-spool.sqlite3"
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE decisions (ordinal INTEGER PRIMARY KEY, value_json TEXT NOT NULL);
        CREATE TABLE tracklets (tracklet_id TEXT PRIMARY KEY, ordinal INTEGER NOT NULL, scope_key TEXT NOT NULL, state TEXT NOT NULL, value_json TEXT NOT NULL);
        CREATE TABLE assertions (assertion_id TEXT PRIMARY KEY, ordinal INTEGER NOT NULL, scope_key TEXT NOT NULL, value_json TEXT NOT NULL);
        CREATE TABLE evidence_vectors (ordinal INTEGER PRIMARY KEY, value_json TEXT NOT NULL);
        """
    )
    connection.execute("INSERT INTO decisions VALUES (0, ?)", (json.dumps({"terminal_decision": "GENESIS"}),))
    connection.execute("INSERT INTO decisions VALUES (1, ?)", (json.dumps({"terminal_decision": "UPDATE"}),))
    connection.execute("INSERT INTO tracklets VALUES ('t', 0, 's', 'CONFIRMED', ?)", (json.dumps({"state": "CONFIRMED"}),))
    connection.execute("INSERT INTO assertions VALUES ('a', 0, 's', ?)", (json.dumps({"observation_count": 4}),))
    connection.execute("INSERT INTO evidence_vectors VALUES (0, ?)", (json.dumps({
        "same_object_pair_supported": True,
        "c2e_dependency_disposition": "NOT_APPLICABLE_C2_ONLY",
        "predicate_results": {"P": True},
    }),))
    connection.commit()
    connection.close()

    manifest = {
        "counts": {"processed_source_record_ids": 2, "candidates": 2, "tracklets": 1, "object_assertions": 1, "match_decisions": 2, "evidence_vectors": 1},
        "stream_sha256": {"candidates": "c", "tracklets": "t", "object_assertions": "a", "match_decisions": "d", "evidence_vectors": "e", "processed_source_record_ids": "p"},
        "indexes_sha256": "i",
        "adapter_result_sha256": "r",
    }
    summary = module.compact_scientific_summary(database, manifest)
    assert summary["decision_terminal_counts"] == {"GENESIS": 1, "UPDATE": 1}
    assert summary["tracklet_state_counts"] == {"CONFIRMED": 1}
    assert summary["assertion_observation_stats"]["observation_count_mean"] == 4
    assert summary["evidence_same_object_support_counts"] == {"SUPPORTED": 1}
    assert "score" not in json.dumps(summary).lower()
    assert "rank" not in json.dumps(summary).lower()


def test_r2_workflow_is_exact_branch_push_only_and_non_promotional() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "run/c2p2-rs0-real-source-shadow-r2-20260817" in text
    assert "C2P2_RS0_REAL_SOURCE_SHADOW_RUN_R2_TRIGGER_v0_1.json" in text
    assert "pull_request:" not in text
    assert "actions/download-artifact@v4" in text
    assert "AUTH.C2P2.RS0.REAL_SOURCE_SHADOW.ONE_RUN.v0.3" in text
    assert "C2P2-RS0-SCIENTIFIC-REVIEW-SELECTION" in text
    assert "SELECT_OBJECTPACK" not in text
    assert "ACTIVATE_C2P" not in text
