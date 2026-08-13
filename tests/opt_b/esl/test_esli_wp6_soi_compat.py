import copy
import json
from pathlib import Path
import unittest

from ovc.opt_b.esl.soi_compat import (
    SOICompatibilityError,
    TOPOLOGY_IDS,
    adapt_family_catalog,
    family_binding_from_mapping,
    invoke_soi_topology,
    topology_registry_from_mapping,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = ROOT / "fixtures/opt_b/esl/wp6"
PRESENT = FIXTURE_ROOT / "family_catalog_present.json"
NULL_FAMILY = FIXTURE_ROOT / "family_catalog_no_stable_family.json"
TOPOLOGY_REGISTRY = ROOT / "registries/opt_b/esl/SOI_TOPOLOGY_MATURITY_v0_1.json"
ADAPTER_MANIFEST = ROOT / "registries/opt_b/esl/SOI_FAMILY_COMPATIBILITY_ADAPTER_MANIFEST_v0_1.json"
SCHEMA = ROOT / "schemas/opt_b/esl/soi_view_result_v0_1.schema.json"
CONTRACT = ROOT / "contracts/opt_b/esl/SOI_COMPATIBILITY_INTERFACE_v0_1.md"


class ESLIWP6SOICompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.present = json.loads(PRESENT.read_text(encoding="utf-8"))
        cls.null_family = json.loads(NULL_FAMILY.read_text(encoding="utf-8"))
        cls.registry = json.loads(TOPOLOGY_REGISTRY.read_text(encoding="utf-8"))
        cls.manifest = json.loads(ADAPTER_MANIFEST.read_text(encoding="utf-8"))

    def test_wp6_01_topology_registry_is_complete_and_maturity_is_fail_closed(self):
        entries = topology_registry_from_mapping(self.registry)
        self.assertEqual(set(entries), set(TOPOLOGY_IDS))
        self.assertEqual(entries["FAMILY"].maturity, "EXECUTABLE_INACTIVE")
        for topology_id in ("HIERARCHY", "OVERLAP", "GRAPH", "CONTINUUM", "COMPOSITION"):
            self.assertEqual(entries[topology_id].maturity, "INTERFACE_ONLY")
            self.assertEqual(entries[topology_id].reason_code, "SOI_ADAPTER_NOT_MATERIALIZED")
            with self.subTest(topology=topology_id):
                with self.assertRaisesRegex(
                    SOICompatibilityError, f"SOI_ADAPTER_NOT_MATERIALIZED:{topology_id}"
                ):
                    invoke_soi_topology(topology_id, topology_registry=self.registry)

    def test_wp6_02_family_adapter_is_deterministic_and_source_immutable(self):
        source = copy.deepcopy(self.present)
        before = copy.deepcopy(source)
        first = adapt_family_catalog(source, adapter_manifest=self.manifest)
        second = adapt_family_catalog(source, adapter_manifest=self.manifest)
        self.assertEqual(first, second)
        self.assertEqual(source, before)
        self.assertEqual(first["soi_view_result_id"], "soi1:" + first["logical_hash"])

    def test_wp6_03_exact_source_programme_catalog_hash_and_chronology_are_bound(self):
        result = invoke_soi_topology(
            "FAMILY",
            topology_registry=self.registry,
            adapter_manifest=self.manifest,
            source_result=self.present,
        )
        binding = result["source_binding"]
        self.assertEqual(binding["source_programme_id"], "OVC-SFC-v0.1")
        self.assertEqual(binding["source_programme_disposition"], "COMPLETED_PRESERVED")
        self.assertEqual(binding["source_result_id"], self.present["family_catalog_id"])
        self.assertEqual(binding["source_logical_hash"], self.present["logical_hash"])
        self.assertEqual(result["chronology"]["first_valid_time"], self.present["first_valid_time"])
        self.assertEqual(result["chronology"]["evaluation_cutoff"], self.present["evaluation_cutoff"])

    def test_wp6_04_topology_and_method_are_explicitly_separate(self):
        result = adapt_family_catalog(self.present, adapter_manifest=self.manifest)
        self.assertEqual(result["topology"]["topology_id"], "FAMILY")
        self.assertEqual(result["method"]["topology_id"], "FAMILY")
        self.assertEqual(result["method"]["source_family_method_id"], "MEDOID_STAR_CONFORMANCE")
        self.assertEqual(result["method"]["method_topology_separation"], "EXPLICIT")
        self.assertEqual(result["method"]["scientific_selection"], "NONE")
        self.assertNotEqual(
            result["method"]["source_family_method_id"],
            result["topology"]["topology_id"],
        )

    def test_wp6_05_raw_family_assignments_residuals_and_ambiguity_are_preserved(self):
        result = adapt_family_catalog(self.present, adapter_manifest=self.manifest)
        topology_result = result["topology_result"]
        self.assertEqual(topology_result["evidence_status"], "FAMILY_EVIDENCE_PRESENT")
        self.assertEqual(len(topology_result["families"]), 2)
        by_occurrence = {row["occurrence_id"]: row for row in topology_result["assignments"]}
        self.assertEqual(by_occurrence["E"]["status"], "AMBIGUOUS")
        self.assertEqual(len(by_occurrence["E"]["family_ids"]), 2)
        self.assertEqual(by_occurrence["F"]["status"], "RESIDUAL")
        self.assertEqual(by_occurrence["G"]["status"], "NOT_COMPARABLE")
        self.assertEqual(topology_result["residual_ids"], ["F"])

    def test_wp6_06_no_stable_family_is_scoped_null_not_no_organisation(self):
        result = adapt_family_catalog(self.null_family, adapter_manifest=self.manifest)
        self.assertEqual(result["topology_result"]["evidence_status"], "NO_STABLE_FAMILY")
        self.assertEqual(result["topology_result"]["families"], [])
        self.assertEqual(
            result["epistemic_boundary"]["no_stable_family_scope"],
            "FAMILY_TOPOLOGY_ONLY",
        )
        self.assertEqual(
            result["epistemic_boundary"]["organisation_absence_inference"],
            "FORBIDDEN",
        )
        self.assertEqual(
            result["epistemic_boundary"]["organisation_evidence_set"],
            "NOT_MATERIALIZED_WP7_OWNED",
        )
        self.assertEqual(result["topology_result"]["noise_ids"], ["B"])
        self.assertEqual(result["topology_result"]["singleton_ids"], ["C"])

    def test_wp6_07_source_hash_tampering_fails_closed(self):
        tampered = copy.deepcopy(self.present)
        tampered["denominator_eligible"] += 1
        with self.assertRaisesRegex(SOICompatibilityError, "LOGICAL_HASH_MISMATCH"):
            adapt_family_catalog(tampered, adapter_manifest=self.manifest)

    def test_wp6_08_reserved_scientific_semantic_and_execution_fields_fail_recursively(self):
        for key in (
            "outcome",
            "validation_label",
            "probability",
            "risk",
            "exposure",
            "execution",
            "semantic_term",
            "mechanism",
            "causal_claim",
            "production_selector",
        ):
            source = copy.deepcopy(self.present)
            source["families"][0]["within_family_evidence"][key] = "FORBIDDEN"
            with self.subTest(key=key):
                with self.assertRaisesRegex(SOICompatibilityError, "SOI_FORBIDDEN_FIELD"):
                    adapt_family_catalog(source, adapter_manifest=self.manifest)

    def test_wp6_09_authority_remains_inactive_and_no_selection_or_promotion_exists(self):
        result = adapt_family_catalog(self.present, adapter_manifest=self.manifest)
        authority = result["authority"]
        self.assertEqual(authority["authority_effect"], "NONE")
        self.assertEqual(authority["topology_activation"], "NONE")
        self.assertEqual(authority["family_promotion"], "NONE")
        self.assertEqual(authority["method_selection"], "NONE")
        self.assertEqual(authority["scientific_support_disposition"], "NONE")
        self.assertEqual(authority["semantic_promotion"], "NONE")
        self.assertEqual(authority["validation_consumption"], "LOCKED_UNCONSUMED")
        self.assertEqual(authority["publication"], "NONE")

    def test_wp6_10_family_manifest_binds_preserved_sfc_and_not_an_algorithm_selection(self):
        binding = family_binding_from_mapping(self.manifest)
        self.assertEqual(binding.source_programme_id, "OVC-SFC-v0.1")
        self.assertEqual(binding.source_programme_disposition, "COMPLETED_PRESERVED")
        self.assertEqual(binding.source_result_type, "SFC.FamilyCatalog.v0.1")
        self.assertEqual(binding.authority_state, "INACTIVE_CONFORMANCE_ONLY")
        self.assertEqual(self.manifest["source_policy"], "EXACT_PRESERVED_FAMILY_CATALOG_ONLY_NO_RECOMPUTATION")
        self.assertEqual(self.manifest["authority"]["method_selection"], "NONE")

    def test_wp6_11_unknown_topology_and_missing_family_inputs_fail_closed(self):
        with self.assertRaisesRegex(SOICompatibilityError, "SOI_TOPOLOGY_UNKNOWN"):
            invoke_soi_topology("UNKNOWN", topology_registry=self.registry)
        with self.assertRaisesRegex(SOICompatibilityError, "SOI_FAMILY_ADAPTER_INPUTS_REQUIRED"):
            invoke_soi_topology("FAMILY", topology_registry=self.registry)

    def test_wp6_12_family_source_authority_and_schema_are_exact(self):
        bad_authority = copy.deepcopy(self.present)
        bad_authority["authority_state"] = "ACTIVE"
        from ovc.opt_b.sfc.serialization import logical_hash
        payload = dict(bad_authority)
        payload.pop("logical_hash")
        bad_authority["logical_hash"] = logical_hash(payload)
        with self.assertRaisesRegex(SOICompatibilityError, "AUTHORITY_NOT_INACTIVE"):
            adapt_family_catalog(bad_authority, adapter_manifest=self.manifest)

        extra = copy.deepcopy(self.present)
        extra["unexpected"] = "field"
        payload = dict(extra)
        payload.pop("logical_hash")
        extra["logical_hash"] = logical_hash(payload)
        with self.assertRaisesRegex(SOICompatibilityError, "SCHEMA_INVALID"):
            adapt_family_catalog(extra, adapter_manifest=self.manifest)

    def test_wp6_13_contract_schema_registry_and_manifest_are_materialised(self):
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        contract = CONTRACT.read_text(encoding="utf-8")
        self.assertEqual(schema["properties"]["topology"]["properties"]["topology_id"]["enum"], list(TOPOLOGY_IDS))
        self.assertEqual(
            schema["properties"]["authority"]["properties"]["topology_activation"]["const"],
            "NONE",
        )
        self.assertEqual(
            schema["properties"]["epistemic_boundary"]["properties"]["organisation_evidence_set"]["const"],
            "NOT_MATERIALIZED_WP7_OWNED",
        )
        self.assertIn("SOI_ADAPTER_NOT_MATERIALIZED", contract)
        self.assertIn("WP6 adds no hierarchy, overlap, graph, continuum, composition", contract)
        self.assertEqual(self.registry["packet_id"], "ESLI-WP6")
        self.assertEqual(self.manifest["packet_id"], "ESLI-WP6")


if __name__ == "__main__":
    unittest.main()
