import copy
from dataclasses import asdict
import json
from pathlib import Path
import unittest

from ovc.opt_b.esl.compiler import compile_structural_occurrence
from ovc.opt_b.esl.sri_compat import (
    SRICompatibilityError,
    SRICompatibilityPack,
    compile_sri_compatibility_record,
    pack_from_mapping,
)

ROOT = Path(__file__).resolve().parents[3]
BOOTSTRAP = ROOT / "fixtures/opt_b/esl/wp3/bootstrap_c2_input.json"
PACK = ROOT / "fixtures/opt_b/esl/wp5/sri_adapter_pack.json"
MANIFEST = ROOT / "registries/opt_b/esl/SRI_COMPATIBILITY_ADAPTER_MANIFEST_v0_1.json"
CROSSWALK = ROOT / "registries/opt_b/esl/SRI_HISTORICAL_CROSSWALK_v0_1.json"
SCHEMA = ROOT / "schemas/opt_b/esl/sri_compatibility_record_v0_1.schema.json"


class ESLIWP5SRICompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = json.loads(BOOTSTRAP.read_text(encoding="utf-8"))
        cls.occurrence = compile_structural_occurrence(
            source["c2_observation"],
            source["profile_outputs"],
            source_generation_id=source["source_generation_id"],
        )
        cls.pack_json = json.loads(PACK.read_text(encoding="utf-8"))
        cls.pack = pack_from_mapping(cls.pack_json)

    def compile(self, occurrence=None, pack=None, context_inputs=None):
        return compile_sri_compatibility_record(
            occurrence or self.occurrence,
            pack or self.pack,
            source_population_id="ESLI.POP.BOOTSTRAP.001",
            context_inputs=context_inputs,
        )

    def test_wp5_01_projection_is_deterministic_and_source_immutable(self):
        source = asdict(self.occurrence)
        before = copy.deepcopy(source)
        first = self.compile(source)
        source["facets"] = list(reversed(source["facets"]))
        second = self.compile(source)
        self.assertEqual(first["representation_id"], second["representation_id"])
        self.assertEqual(first, second)
        self.assertEqual(before, asdict(self.occurrence))
        self.assertEqual(first["representation_id"], "sri1:" + first["logical_hash"])

    def test_wp5_02_exact_occurrence_frontier_chronology_and_domain_are_bound(self):
        result = self.compile()
        self.assertEqual(result["source_occurrence"]["occurrence_record_id"], self.occurrence.occurrence_record_id)
        self.assertEqual(result["source_occurrence"]["occurrence_pack_id"], self.occurrence.occurrence_pack_id)
        self.assertEqual(result["source_occurrence"]["first_valid_time"], self.occurrence.first_valid_time)
        self.assertEqual(result["source_occurrence"]["evaluation_cutoff"], self.occurrence.evaluation_cutoff)
        self.assertEqual(result["comparability"]["comparability_domain_id"], self.occurrence.comparability_domain_id)
        self.assertEqual(result["comparability"]["generation"], "ESLI.SRI.COMP.GEN.1")

    def test_wp5_03_missing_and_not_evaluable_states_are_preserved_without_imputation(self):
        result = self.compile()
        self.assertEqual(result["missingness"]["ORGANISATION"], "NOT_EVALUABLE")
        self.assertEqual(result["missingness"]["INTERACTION"], "MISSING")
        self.assertIsNone(result["structural_raw"]["ORGANISATION"]["value"])
        self.assertIsNone(result["structural_raw"]["INTERACTION"]["value"])
        self.assertEqual(result["information_loss"]["implicit_imputation"], "PROHIBITED")
        self.assertEqual(result["structural_derived"], {})
        self.assertEqual(result["structural_normalized"], {})
        self.assertEqual(result["comparison_only"], {})

    def test_wp5_04_omission_requires_exact_information_loss_declaration(self):
        pack = SRICompatibilityPack(
            adapter_pack_id="ESLI.SRI.PACK.ABLATED.v0.1",
            version="0.1",
            representation_class="SRI-R6",
            exposed_dimensions=("LOCATION", "MOTION", "ORGANISATION"),
            omitted_dimensions=("INTERACTION",),
            information_loss_dimensions=("INTERACTION",),
            comparability_domain_id=self.occurrence.comparability_domain_id,
            comparability_generation="ESLI.SRI.COMP.GEN.1",
        )
        result = self.compile(pack=pack)
        self.assertNotIn("INTERACTION", result["structural_raw"])
        self.assertEqual(result["information_loss"]["omitted_dimensions"], ["INTERACTION"])
        with self.assertRaisesRegex(SRICompatibilityError, "INFORMATION_LOSS"):
            SRICompatibilityPack(
                adapter_pack_id="BAD", version="0.1", representation_class="SRI-R6",
                exposed_dimensions=("LOCATION", "MOTION", "ORGANISATION"),
                omitted_dimensions=("INTERACTION",), information_loss_dimensions=(),
                comparability_domain_id=self.occurrence.comparability_domain_id,
                comparability_generation="ESLI.SRI.COMP.GEN.1",
            )

    def test_wp5_05_context_is_exact_declared_representation_input_only(self):
        with self.assertRaisesRegex(SRICompatibilityError, "UNDECLARED_CONTEXT"):
            self.compile(context_inputs={"session": "LONDON"})
        pack = SRICompatibilityPack(
            adapter_pack_id="ESLI.SRI.PACK.CONTEXT.v0.1", version="0.1", representation_class="SRI-R7",
            exposed_dimensions=("LOCATION", "MOTION", "ORGANISATION", "INTERACTION"),
            omitted_dimensions=(), information_loss_dimensions=(),
            comparability_domain_id=self.occurrence.comparability_domain_id,
            comparability_generation="ESLI.SRI.COMP.GEN.1",
            context_input_fields=("session",), context_role="REPRESENTATION_INPUT",
        )
        result = self.compile(pack=pack, context_inputs={"session": "LONDON"})
        self.assertEqual(result["context"]["values"], {"session": "LONDON"})
        with self.assertRaisesRegex(SRICompatibilityError, "CONTEXT_ROLE"):
            SRICompatibilityPack(
                adapter_pack_id="BAD.CONTEXT", version="0.1", representation_class="SRI-R7",
                exposed_dimensions=("LOCATION", "MOTION", "ORGANISATION", "INTERACTION"),
                omitted_dimensions=(), information_loss_dimensions=(),
                comparability_domain_id=self.occurrence.comparability_domain_id,
                comparability_generation="ESLI.SRI.COMP.GEN.1",
                context_input_fields=("session",), context_role="STRATIFIER",
            )

    def test_wp5_06_forbidden_scientific_and_execution_fields_fail_recursively(self):
        for key in ("family_id", "prototype_id", "distance_result", "outcome", "validation_label", "probability", "risk", "exposure", "execution"):
            source = asdict(self.occurrence)
            source["facets"][0]["value"] = {"safe": "x", key: "FORBIDDEN"}
            with self.subTest(key=key):
                with self.assertRaisesRegex(SRICompatibilityError, "ESL_SRI_FORBIDDEN_FIELD"):
                    self.compile(source)

    def test_wp5_07_pack_or_comparability_generation_change_changes_identity(self):
        first = self.compile()
        pack2 = SRICompatibilityPack(
            adapter_pack_id=self.pack.adapter_pack_id,
            version=self.pack.version,
            representation_class=self.pack.representation_class,
            exposed_dimensions=self.pack.exposed_dimensions,
            omitted_dimensions=self.pack.omitted_dimensions,
            information_loss_dimensions=self.pack.information_loss_dimensions,
            comparability_domain_id=self.pack.comparability_domain_id,
            comparability_generation="ESLI.SRI.COMP.GEN.2",
            historical_aliases=self.pack.historical_aliases,
        )
        second = self.compile(pack=pack2)
        self.assertNotEqual(first["representation_id"], second["representation_id"])
        with self.assertRaisesRegex(SRICompatibilityError, "COMPARABILITY_DOMAIN_MISMATCH"):
            bad = SRICompatibilityPack(
                adapter_pack_id="BAD.DOMAIN", version="0.1", representation_class="SRI-R8",
                exposed_dimensions=("LOCATION", "MOTION", "ORGANISATION", "INTERACTION"),
                omitted_dimensions=(), information_loss_dimensions=(),
                comparability_domain_id="OTHER.DOMAIN", comparability_generation="GEN.1",
            )
            self.compile(pack=bad)

    def test_wp5_08_hidden_source_fields_are_not_projected(self):
        source = asdict(self.occurrence)
        source["extensions"]["UNDISCLOSED_NON_SCIENTIFIC_NOTE"] = "MUST_NOT_APPEAR"
        result = self.compile(source)
        self.assertNotIn("MUST_NOT_APPEAR", json.dumps(result, sort_keys=True))

    def test_wp5_09_historical_crosswalk_is_one_to_one_addressability_not_identity(self):
        crosswalk = json.loads(CROSSWALK.read_text(encoding="utf-8"))
        rows = crosswalk["rows"]
        self.assertEqual(len(rows), 9)
        self.assertEqual({row["forward_class"] for row in rows}, {f"SRI-R{i}" for i in range(1, 10)})
        self.assertEqual({row["srfd_alias"] for row in rows}, {f"SRFDI-R{i}" for i in range(1, 10)})
        self.assertTrue(all(row["status"] == "SEMANTIC_ALIAS_ADDRESSABLE" for row in rows))
        self.assertTrue(all(row["identity_relation"] == "NONE" for row in rows))
        self.assertIn("NO_IDENTITY_REWRITE", crosswalk["policy"])

    def test_wp5_10_manifest_schema_and_authority_boundary_are_materialised(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(manifest["packet_id"], "ESLI-WP5")
        self.assertEqual(manifest["gate_id"], "ESLI-G5")
        self.assertEqual(manifest["method_id"], "METHOD_NEUTRAL_IDENTITY_PROJECTION_v0_1")
        self.assertEqual(manifest["authority"]["authority_effect"], "NONE")
        self.assertEqual(manifest["authority"]["representation_activation"], "NONE")
        self.assertEqual(manifest["authority"]["family_promotion"], "NONE")
        self.assertEqual(manifest["authority"]["semantic_promotion"], "NONE")
        self.assertEqual(schema["properties"]["authority"]["properties"]["validation_consumption"]["const"], "LOCKED_UNCONSUMED")

    def test_wp5_11_method_selection_is_not_available_in_this_packet(self):
        with self.assertRaisesRegex(SRICompatibilityError, "METHOD_SELECTION_FORBIDDEN"):
            SRICompatibilityPack(
                adapter_pack_id="BAD.METHOD", version="0.1", representation_class="SRI-R1",
                exposed_dimensions=("LOCATION", "MOTION", "ORGANISATION", "INTERACTION"),
                omitted_dimensions=(), information_loss_dimensions=(),
                comparability_domain_id=self.occurrence.comparability_domain_id,
                comparability_generation="GEN.1", method_id="SELECTED_BEST_METHOD",
            )


if __name__ == "__main__":
    unittest.main()
