from __future__ import annotations

import ast
import inspect
import unittest

from ovc.shared_systems import stage0


def valid_binding_registry():
    registry = {
        "schema": "grt-governance-binding-registry/v0.2",
        "serialization_profile": "canonical-json-v1",
        "programme_bindings": [],
        "inheritance_rules": [],
        "shared_service_bindings": [
            {
                "registry_section": "shared_service_bindings",
                "binding_id": stage0.BINDING_ID,
                "service_id": stage0.PROGRAMME_ID,
                "owner_programme_id": stage0.PROGRAMME_ID,
                "implementation_roots": [],
                "consumer_programmes": [],
                "service_contracts": [],
                "allowed_extension_points": [],
                "responsibility_boundary": {
                    "owns": [
                        "common machinery semantics",
                        "shared contracts",
                        "compatibility and adapters",
                        "reference implementations",
                    ],
                    "does_not_own": [
                        "domain truth",
                        "programme identity",
                        "repository law",
                        "scientific or activation authority",
                    ],
                },
                "binding_status": "RESOLVED",
                "service_state": "INACTIVE_NOT_IMPLEMENTED",
                "evidence_class": "EXPLICIT_REPOSITORY_DECISION",
                "source_id": "docs/programmes/grt-v0-2/shared-service-bindings/OVC_SHARED_SYSTEMS_V0_1_OPERATOR_DECISION.json",
                "reason_codes": [],
                "authority_effect": "NONE_GOVERNANCE_PROJECTION",
            }
        ],
        "generated_artifact_rules": [],
        "maintenance_responsibilities": [],
        "genesis_crosswalks": [],
        "historical_associations": [],
        "conflicts": [],
        "authority_effect": "NONE_GOVERNANCE_PROJECTION",
        "active_enforcement": "NONE",
    }
    registry["canonical_hash"] = stage0.canonical_hash_without(
        registry, "canonical_hash"
    )
    return registry


def valid_decision():
    return {
        "decision_id": stage0.G0A_DECISION_ID,
        "decision": "PASS",
        "programme_id": stage0.PROGRAMME_ID,
        "effective_authority_envelope": {
            "envelope_id": "SHSI-AE-v0.2-R1",
            "authorized_sequence": ["SHSI-WP0", "SHSI-WP1"],
        },
    }


class SharedSystemsStage0Tests(unittest.TestCase):
    def test_binding_fixture_matches_ratified_generation(self):
        registry = valid_binding_registry()
        self.assertEqual(registry["canonical_hash"], stage0.EXPECTED_BINDING_HASH)
        result = stage0.verify_binding_registry(registry)
        self.assertEqual(result["owner_programme_id"], stage0.PROGRAMME_ID)

    def test_stage0_proof_is_exact_roundtrip(self):
        proof = stage0.build_stage0_proof(
            design_sha256="a" * 64,
            plan_sha256="b" * 64,
            operator_decision=valid_decision(),
            binding_registry=valid_binding_registry(),
            baseline_commit="c" * 40,
            baseline_tree="d" * 40,
        )
        self.assertEqual(proof["bootstrap"]["cycle_count"], 0)
        self.assertEqual(proof["bootstrap"]["forbidden_edge_count"], 0)
        self.assertEqual(len(proof["proof_hash"]), 64)

    def test_forbidden_edge_fails_closed(self):
        edges = list(stage0.NORMATIVE_EDGES)
        edges.append((stage0.BOOTSTRAP_NODES[1], stage0.BOOTSTRAP_NODES[5]))
        with self.assertRaisesRegex(
            stage0.SharedSystemsStage0Error, "BOOTSTRAP_FORBIDDEN"
        ):
            stage0.validate_bootstrap_graph(edges)

    def test_cycle_fails_closed(self):
        edges = list(stage0.NORMATIVE_EDGES)
        edges.append((stage0.BOOTSTRAP_NODES[-1], stage0.BOOTSTRAP_NODES[0]))
        with self.assertRaises(stage0.SharedSystemsStage0Error):
            stage0.validate_bootstrap_graph(edges)

    def test_owner_conflict_fails_closed(self):
        registry = valid_binding_registry()
        registry["conflicts"] = [{"service_id": stage0.PROGRAMME_ID}]
        registry["canonical_hash"] = stage0.canonical_hash_without(
            registry, "canonical_hash"
        )
        with self.assertRaisesRegex(
            stage0.SharedSystemsStage0Error, "OWNER_BINDING_CONFLICT"
        ):
            stage0.verify_binding_registry(registry)

    def test_wrong_owner_fails_closed(self):
        registry = valid_binding_registry()
        registry["shared_service_bindings"][0]["owner_programme_id"] = "OTHER"
        registry["canonical_hash"] = stage0.canonical_hash_without(
            registry, "canonical_hash"
        )
        with self.assertRaisesRegex(
            stage0.SharedSystemsStage0Error, "BINDING_HASH_GENERATION_MISMATCH"
        ):
            stage0.verify_binding_registry(registry)

    def test_binding_hash_tamper_fails_closed(self):
        registry = valid_binding_registry()
        registry["authority_effect"] = "MUTATED"
        with self.assertRaisesRegex(
            stage0.SharedSystemsStage0Error, "BINDING_CANONICAL_HASH_MISMATCH"
        ):
            stage0.verify_binding_registry(registry)

    def test_g0a_must_be_pass(self):
        decision = valid_decision()
        decision["decision"] = "DEFER"
        with self.assertRaisesRegex(stage0.SharedSystemsStage0Error, "G0A_NOT_PASS"):
            stage0.build_stage0_proof(
                design_sha256="a" * 64,
                plan_sha256="b" * 64,
                operator_decision=decision,
                binding_registry=valid_binding_registry(),
                baseline_commit="c" * 40,
                baseline_tree="d" * 40,
            )

    def test_stage1_barrier(self):
        self.assertFalse(
            stage0.stage1_ready(current_gate="SHSI-G0B", g0b_status="APPROVED")
        )
        self.assertTrue(
            stage0.stage1_ready(current_gate="SHSI-G1", g0b_status="COMPLETED")
        )

    def test_stage0_imports_only_standard_library(self):
        tree = ast.parse(inspect.getsource(stage0))
        allowed_roots = {"__future__", "copy", "hashlib", "json", "re", "typing"}
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".")[0])
        self.assertLessEqual(roots, allowed_roots)


if __name__ == "__main__":
    unittest.main()
