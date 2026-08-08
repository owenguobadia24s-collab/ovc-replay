import copy
import json
from pathlib import Path
import unittest

from ovc.opt_b.sfc.c2e_adapter import SFCSourceError, adapt_c2e_handoff
from ovc.opt_b.sfc.representation import (
    NormalizationPack,
    RepresentationPack,
    SFCRepresentationError,
    compile_bundle,
    compile_population,
    compile_representation,
    fit_minmax,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "fixtures/opt_b/sfc/wp2/c2e_stream_fixture.json"


class SFCWP2C2ERepresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text())
        cls.source_objects = cls.fixture.pop("source_objects")

    def adapt(self, record=None, source_objects=None, cutoff="2026-06-01T02:00:00Z"):
        return adapt_c2e_handoff(record or copy.deepcopy(self.fixture), source_objects=source_objects or copy.deepcopy(self.source_objects), evaluation_cutoff=cutoff)

    def test_f01_adapter_is_deterministic_across_object_order(self):
        first = self.adapt()
        shuffled = dict(reversed(list(self.source_objects.items())))
        second = self.adapt(source_objects=shuffled)
        self.assertEqual(first["source_record_hash"], second["source_record_hash"])
        self.assertEqual(first, second)

    def test_f02_open_as_of_representation_is_not_rewritten_by_terminal_record(self):
        open_record = self.adapt()
        pack = RepresentationPack("SFC.R1.SYN", "SRI-R1", ("LOCATION","MOTION","ORGANISATION","INTERACTION"))
        population = compile_population([open_record], population_rule_pack_id="SFC.POP.RULE.SYN", population_cutoff="2026-06-01T02:00:00Z")
        open_rep = compile_representation(open_record, pack, source_population_id=population["population_id"])
        terminal_source = copy.deepcopy(self.fixture)
        terminal_source["lifecycle_status"] = "TERMINAL"
        terminal_source["snapshot_reference"] = "SNAP.002"
        terminal_source["first_valid_time"] = "2026-06-01T03:00:00Z"
        terminal = self.adapt(terminal_source, cutoff="2026-06-01T03:00:00Z")
        terminal_rep = compile_representation(terminal, pack, source_population_id=population["population_id"])
        self.assertEqual(open_rep["first_valid_time"], "2026-06-01T02:00:00Z")
        self.assertNotEqual(open_rep["representation_id"], terminal_rep["representation_id"])
        self.assertEqual(open_rep["comparison_only"]["lifecycle_status"], "OPEN")

    def test_f04_family_outcome_validation_leakage_is_rejected(self):
        for key in ("family_id", "outcome", "validation_label", "probability", "risk", "exposure", "execution"):
            source = copy.deepcopy(self.fixture)
            source[key] = "FORBIDDEN"
            with self.assertRaises(SFCSourceError):
                self.adapt(source)

    def test_f05_raw_is_preserved_with_normalized_values(self):
        adapted = self.adapt()
        population = compile_population([adapted], population_rule_pack_id="SFC.POP.RULE.SYN", population_cutoff="2026-06-01T02:00:00Z")
        norm = fit_minmax([adapted], ["LOCATION","MOTION"], fit_population_id=population["population_id"], fit_cutoff="2026-06-01T02:00:00Z")
        pack = RepresentationPack("SFC.R4.SYN", "SRI-R4", ("LOCATION","MOTION"))
        rep = compile_representation(adapted, pack, source_population_id=population["population_id"], normalization_pack=norm)
        self.assertTrue(rep["structural_raw"])
        self.assertTrue(rep["structural_normalized"])
        self.assertNotEqual(rep["structural_raw"], rep["structural_normalized"])

    def test_f06_f07_normalization_fit_cutoff(self):
        adapted = self.adapt()
        norm = fit_minmax([adapted], ["LOCATION"], fit_population_id="POP", fit_cutoff="2026-06-01T02:00:00Z")
        self.assertIsInstance(norm, NormalizationPack)
        with self.assertRaises(SFCRepresentationError):
            fit_minmax([adapted], ["LOCATION"], fit_population_id="POP", fit_cutoff="2026-06-01T01:59:59Z")

    def test_f08_optional_missingness_is_masked_but_required_missing_fails(self):
        adapted = self.adapt()
        pack = RepresentationPack("SFC.R8.SYN", "SRI-R8", ("LOCATION",), ("OPTIONAL_ACTIVITY",))
        rep = compile_representation(adapted, pack, source_population_id="POP")
        self.assertTrue(rep["missingness"]["OPTIONAL_ACTIVITY"])
        bad = copy.deepcopy(self.source_objects)
        for obj in bad.values():
            if "structural" in obj:
                obj["structural"].pop("LOCATION", None)
        adapted_bad = self.adapt(source_objects=bad)
        with self.assertRaises(SFCRepresentationError):
            compile_representation(adapted_bad, pack, source_population_id="POP")

    def test_f33_legacy_object_without_c2e_producer_lineage_fails_closed(self):
        legacy = {"episode_id":"legacy","state_key":"flattened","first_valid_time":"2026-06-01T02:00:00Z"}
        with self.assertRaisesRegex(SFCSourceError, "SFC_SOURCE_SCHEMA_INVALID"):
            adapt_c2e_handoff(legacy, source_objects={}, evaluation_cutoff="2026-06-01T02:00:00Z")

    def test_population_denominators_and_bundle_are_explicit(self):
        adapted = self.adapt()
        pop = compile_population([adapted], population_rule_pack_id="RULE", population_cutoff="2026-06-01T02:00:00Z")
        self.assertEqual((pop["denominator_total_seen"], pop["denominator_eligible"], pop["denominator_excluded"]), (1,1,0))
        pack = RepresentationPack("SFC.R1.SYN", "SRI-R1", ("LOCATION","MOTION"))
        rep = compile_representation(adapted, pack, source_population_id=pop["population_id"])
        bundle = compile_bundle([rep], bundle_role="PRIMARY", source_population_id=pop["population_id"], representation_pack_id=pack.representation_pack_id, comparability_domain_id=pack.comparability_domain_id)
        self.assertEqual(bundle["ordered_representation_ids"], [rep["representation_id"]])


if __name__ == "__main__":
    unittest.main()
