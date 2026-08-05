from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from ovc.opt_b.c2_vnext.disposition_evidence import (
    DENIED,
    DispositionEvidenceError,
    build_disposition_evidence,
)


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def dump_lines(path: Path, values: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n" for item in values),
        encoding="utf-8",
    )


def fixture(root: Path) -> tuple[Path, Path]:
    repo = root / "repo"
    replay = root / "replay"
    registry = {
        "active": False,
        "canonical": False,
        "method_pack": {
            "method_pack_id": "METHOD.1",
            "version": "1",
            "active": False,
            "canonical": False,
            "minimum_motif_support": 2,
            "family_distance_threshold": 0.35,
            "common_component_frequency": 0.75,
            "optional_component_frequency": 0.25,
        },
    }
    dump(repo / "registries/opt_b/c2/vnext/C2_FUNCTIONAL_DISCOVERY_METHOD_CANDIDATE_v0_1.jsonc", registry)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=repo, check=True)

    opportunities = []
    for index, (side, outcome, timestamp) in enumerate([
        ("BID", "COMPUTABLE", "2026-06-02T00:00:00Z"),
        ("ASK", "COMPUTABLE", "2026-06-09T00:00:00Z"),
        ("BID", "COMPUTABLE", "2026-06-16T00:00:00Z"),
        ("ASK", "CENSORED", "2026-06-23T00:00:00Z"),
    ]):
        opportunities.append({
            "opportunity_id": f"OPP.{index}",
            "clock_id": "15M",
            "side": side,
            "frame_id": "LOCAL",
            "object_family": "AXIS_BUNDLE",
            "ordered_development": [{"x": 1}, {"x": 2}],
            "duration_observations": 2,
            "first_valid_time": timestamp,
            "opportunity_outcome": outcome,
        })
    candidate = {
        "rule_candidate_id": "RULE.1",
        "functional_core_id": "CORE.1",
        "family_id": "FAMILY.1",
        "method_pack_id": "METHOD.1",
        "source_opportunity_ids": ["OPP.0", "OPP.1"],
        "source_fingerprint_ids": ["FP.0", "FP.1"],
        "ast": {"operator": "ALL_OF", "clauses": [{"operator": "MEASUREMENT_COMPARISON"}]},
        "active": False,
        "canonical": False,
        "selector_authority": "NONE",
        "event_authority": "NONE",
        "episode_authority": "NONE",
        "semantic_authority": "NONE",
        "outcome_authority": "NONE",
    }
    evaluation = {
        "rule_candidate_id": "RULE.1",
        "evaluation_population_id": "EVAL.1",
        "complete_accounting": True,
        "outcome_counts": {"CENSORED": 1, "MATCHED": 2, "NOT_MATCHED": 1},
        "results": [
            {"opportunity_id": "OPP.0", "evaluation_outcome": "MATCHED"},
            {"opportunity_id": "OPP.1", "evaluation_outcome": "MATCHED"},
            {"opportunity_id": "OPP.2", "evaluation_outcome": "NOT_MATCHED"},
            {"opportunity_id": "OPP.3", "evaluation_outcome": "CENSORED"},
        ],
    }
    controls = {
        "control_set_id": "CTRL.1",
        "member_count": 2,
        "matched_count": 2,
        "unmatched_count": 0,
        "duration_bin_size": 2,
        "hidden_nearest_or_best_selection": False,
        "unmatched_requests": [],
        "content_sha256": "c" * 64,
    }
    motifs = {
        "motifs": [
            {"motif_id": "M1", "support_count": 2, "signature_tokens": ["a", "b"]},
            {"motif_id": "M2", "support_count": 5, "signature_tokens": ["a", "c"]},
        ],
        "negative_candidates": [
            {"motif_candidate_id": "M3", "support_count": 1, "signature_tokens": ["z"]}
        ],
    }
    families = {"families": [{
        "family_id": "FAMILY.1",
        "member_count": 2,
        "member_opportunity_ids": ["OPP.0", "OPP.1"],
        "distance_threshold": 0.35,
        "provisional": True,
        "semantic_authority": "NONE",
    }]}
    cores = {"functional_cores": [{
        "functional_core_id": "CORE.1",
        "family_id": "FAMILY.1",
        "member_count": 2,
        "classification_counts": {"INVARIANT": 1, "CONTRADICTORY": 2},
        "semantic_name": None,
        "provisional": True,
        "component_matrix": [
            {"feature_key": "x", "feature_value": "A", "count": 2, "frequency": 1.0, "classification": "INVARIANT"},
            {"feature_key": "y", "feature_value": "A", "count": 1, "frequency": 0.5, "classification": "CONTRADICTORY"},
            {"feature_key": "y", "feature_value": "B", "count": 1, "frequency": 0.5, "classification": "CONTRADICTORY"},
        ],
    }]}
    for run in ("run-001", "run-002", "restart-verification"):
        evidence = replay / run / "evidence"
        dump_lines(evidence / "opportunity-population.jsonl", opportunities)
        dump(evidence / "motifs.json", motifs)
        dump(evidence / "families.json", families)
        dump(evidence / "functional-cores.json", cores)
        dump_lines(evidence / "rule-candidates.jsonl", [candidate])
        dump_lines(evidence / "rule-evaluations.jsonl", [evaluation])
        dump_lines(evidence / "matched-controls.jsonl", [controls])
        dump(replay / run / "output-manifest.json", {
            "binding_id": "BIND.1",
            "binding_sha256": "b" * 64,
            "code_commit": "1" * 40,
            "logical_population_sha256": "l" * 64,
            "counts": {"records": 4, "rule_candidates": 1},
            "interval": {"target": "June"},
            "complete_accounting": True,
            "first_valid_chronology": True,
            "legacy_seed_count": 0,
            "outcome_dependency_count": 0,
            "validation_dependency_count": 0,
            "active": False,
            "canonical": False,
            "authority": "PROVISIONAL_DISCOVERY_RESEARCH_ONLY",
        })
    dump(replay / "orchestration-receipt.json", {
        "result": "PASS",
        "binding_sha256": "b" * 64,
        "logical_population_sha256": "l" * 64,
        "clean_run_count": 2,
        "authority": DENIED,
    })
    dump(replay / "determinism-receipt.json", {
        "result": "PASS",
        "discrepancies": [],
        "artifact_inventory_match": True,
        "count_reconciliation_match": True,
        "logical_hash_match": True,
        "restart_exercised": True,
    })
    dump(replay / "restart-receipt.json", {
        "result": "PASS",
        "checkpoint_loaded": True,
        "logical_hash_matches_clean_runs": True,
        "resumed_to_completion": True,
    })
    return replay, repo


class DispositionEvidenceTests(unittest.TestCase):
    def test_build_is_deterministic_complete_and_authority_neutral(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            replay, repo = fixture(Path(tmp))
            first = build_disposition_evidence(replay, repo)
            second = build_disposition_evidence(replay, repo)
            first.pop("created_at_utc")
            second.pop("created_at_utc")
            self.assertEqual(first, second)
            self.assertEqual("GATE_READY_OPERATOR_DISPOSITIONS_REQUIRED", first["status"])
            self.assertEqual(1, first["rule_candidate_count"])
            candidate = first["rule_candidates"][0]
            self.assertEqual(2, candidate["matched_count"])
            self.assertEqual(1, candidate["counterexample_count"])
            self.assertTrue(candidate["matched_controls"]["complete_control_coverage"])
            self.assertTrue(candidate["independent_recurrence_observed"])
            self.assertIsNone(candidate["operator_decision"])
            self.assertEqual(
                "DEFERRED_NO_LAWFUL_LEGACY_MATCH_POPULATION",
                first["legacy_benchmark_surface"]["status"],
            )
            self.assertEqual(DENIED, first["authority"])
            self.assertFalse(first["active"])
            self.assertFalse(first["canonical"])
            self.assertRegex(first["content_sha256"], r"^[0-9a-f]{64}$")

    def test_parameter_and_redundancy_surfaces_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            replay, repo = fixture(Path(tmp))
            result = build_disposition_evidence(replay, repo)
            surface = result["parameter_and_perturbation_surface"]
            self.assertEqual(3, len(surface["support_threshold_surface"]))
            self.assertEqual(3, len(surface["family_distance_surface"]))
            self.assertGreaterEqual(len(surface["component_frequency_surface"]), 3)
            self.assertEqual([], result["redundancy_and_cooccurrence_surface"])
            self.assertEqual("NONE", surface["selection_effect"])

    def test_manifest_or_terminal_failure_is_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            replay, repo = fixture(Path(tmp))
            receipt = json.loads((replay / "determinism-receipt.json").read_text())
            receipt["logical_hash_match"] = False
            dump(replay / "determinism-receipt.json", receipt)
            with self.assertRaisesRegex(DispositionEvidenceError, "DETERMINISM_ASSERTION_FAILED"):
                build_disposition_evidence(replay, repo)

    def test_legacy_manifest_is_post_discovery_and_authority_neutral(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            replay, repo = fixture(Path(tmp))
            manifest = Path(tmp) / "legacy.json"
            dump(manifest, {"benchmarks": [{
                "legacy_rule_id": "LEGACY.1",
                "benchmark_only": True,
                "matched_opportunity_ids": ["OPP.0", "OPP.2"],
            }]})
            result = build_disposition_evidence(
                replay, repo, legacy_benchmark_manifest=manifest
            )
            legacy = result["legacy_benchmark_surface"]
            self.assertEqual("COMPUTABLE", legacy["status"])
            self.assertEqual(1, legacy["mappings"][0]["comparisons"][0]["intersection_count"])
            for key in (
                "legacy_seed_count", "legacy_filter_count", "legacy_score_count",
                "legacy_stop_count", "legacy_promotion_count",
            ):
                self.assertEqual(0, legacy[key])


if __name__ == "__main__":
    unittest.main()
