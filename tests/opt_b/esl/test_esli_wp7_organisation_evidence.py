import copy
import json
from pathlib import Path
import unittest

from ovc.opt_b.esl.organisation_evidence import (
    OrganisationEvidenceError,
    apply_organisation_decision_rule_pack,
    assemble_organisation_evidence_set,
    assert_no_stable_organisation_claim_lawful,
    build_correspondence_edge,
    build_disagreement_record,
    build_invariant_evidence_record,
    build_metric_record,
    validate_decision_rule_pack_interface,
)
from ovc.opt_b.esl.soi_compat import adapt_family_catalog

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = ROOT / "fixtures/opt_b/esl/wp6"
PRESENT = FIXTURE_ROOT / "family_catalog_present.json"
NULL_FAMILY = FIXTURE_ROOT / "family_catalog_no_stable_family.json"
ADAPTER_MANIFEST = ROOT / "registries/opt_b/esl/SOI_FAMILY_COMPATIBILITY_ADAPTER_MANIFEST_v0_1.json"
RULE_PACK = ROOT / "registries/opt_b/esl/ORGANISATION_DECISION_RULE_PACK_INTERFACE_v0_1.json"
STATUS_REGISTRY = ROOT / "registries/opt_b/esl/ORGANISATION_EVIDENCE_STATUS_v0_1.json"
SCHEMA = ROOT / "schemas/opt_b/esl/organisation_evidence_set_v0_1.schema.json"
CONTRACT = ROOT / "contracts/opt_b/esl/ORGANISATION_EVIDENCE_CONSTITUTION_v0_1.md"
EXPECTATIONS = ROOT / "fixtures/opt_b/esl/wp7/organisation_evidence_expectations.json"


class ESLIWP7OrganisationEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = json.loads(ADAPTER_MANIFEST.read_text(encoding="utf-8"))
        cls.present_view = adapt_family_catalog(
            json.loads(PRESENT.read_text(encoding="utf-8")),
            adapter_manifest=manifest,
        )
        cls.null_view = adapt_family_catalog(
            json.loads(NULL_FAMILY.read_text(encoding="utf-8")),
            adapter_manifest=manifest,
        )
        cls.rule_pack = json.loads(RULE_PACK.read_text(encoding="utf-8"))
        cls.expectations = json.loads(EXPECTATIONS.read_text(encoding="utf-8"))

    def test_wp7_01_metric_names_exact_universe_numerator_denominator_and_value(self):
        metric = build_metric_record(
            view_result=self.present_view,
            metric_id="ORG.METRIC.ASSIGNED_RATE.v1",
            eligible_universe_id="POP.ELIGIBLE.v1",
            numerator=4,
            denominator=8,
            exclusions=["EXCLUDED_BY_SCOPE"],
            missingness=["MISSING_OPTIONAL_CONTEXT"],
        )
        self.assertEqual(metric["numerator"], 4)
        self.assertEqual(metric["denominator"], 8)
        self.assertEqual(metric["value_decimal"], "0.5")
        self.assertEqual(metric["status"], "EVALUATED")
        self.assertEqual(metric["topology_id"], "FAMILY")
        self.assertTrue(metric["metric_record_id"].startswith("orgm1:"))

    def test_wp7_02_undefined_denominator_abstains_instead_of_fabricating_zero(self):
        metric = build_metric_record(
            view_result=self.present_view,
            metric_id="ORG.METRIC.EMPTY.v1",
            eligible_universe_id="POP.EMPTY.v1",
            numerator=0,
            denominator=0,
        )
        self.assertEqual(metric["status"], "NOT_EVALUABLE")
        self.assertIsNone(metric["value_decimal"])
        with self.assertRaisesRegex(
            OrganisationEvidenceError,
            "UNDEFINED_DENOMINATOR_MUST_ABSTAIN",
        ):
            build_metric_record(
                view_result=self.present_view,
                metric_id="ORG.METRIC.BAD_EMPTY.v1",
                eligible_universe_id="POP.EMPTY.v1",
                numerator=0,
                denominator=0,
                status="EVALUATED",
            )

    def test_wp7_03_correspondence_is_directional_evidence_and_never_identity_merge(self):
        edge = build_correspondence_edge(
            subject_view_result=self.present_view,
            object_view_result=self.null_view,
            relation="CONTRADICTS",
            evidence_refs=["EVIDENCE.COMPARISON.1"],
        )
        self.assertEqual(edge["directionality"], "DIRECTIONAL")
        self.assertEqual(edge["identity_merge"], "FORBIDDEN")
        self.assertNotEqual(edge["subject_view_result_id"], edge["object_view_result_id"])
        reverse = build_correspondence_edge(
            subject_view_result=self.null_view,
            object_view_result=self.present_view,
            relation="CONTRADICTS",
            evidence_refs=["EVIDENCE.COMPARISON.1"],
        )
        self.assertNotEqual(edge["correspondence_edge_id"], reverse["correspondence_edge_id"])

    def test_wp7_04_disagreement_is_typed_by_axis_not_collapsed_to_one_score(self):
        record = build_disagreement_record(
            view_result_ids=[
                self.present_view["soi_view_result_id"],
                self.null_view["soi_view_result_id"],
            ],
            axis="METHOD",
            status="OBSERVED",
            evidence_refs=["EVIDENCE.METHOD.DISAGREEMENT.1"],
            first_valid_time="2026-06-01T01:00:00Z",
            evaluation_cutoff="2026-06-01T01:00:00Z",
        )
        self.assertEqual(record["axis"], "METHOD")
        self.assertEqual(record["scalar_collapse"], "FORBIDDEN")
        self.assertEqual(record["status"], "OBSERVED")

    def test_wp7_05_invariant_evidence_preserves_content_and_view_identities(self):
        record = build_invariant_evidence_record(
            view_result_ids=[
                self.present_view["soi_view_result_id"],
                self.null_view["soi_view_result_id"],
            ],
            invariant_kind="CORE",
            content_refs=["OCCURRENCE.A", "OCCURRENCE.B"],
            evidence_refs=["EVIDENCE.CORE.1"],
            first_valid_time="2026-06-01T01:00:00Z",
            evaluation_cutoff="2026-06-01T01:00:00Z",
        )
        self.assertEqual(record["invariant_kind"], "CORE")
        self.assertEqual(record["identity_merge"], "FORBIDDEN")
        self.assertEqual(record["content_refs"], ["OCCURRENCE.A", "OCCURRENCE.B"])

    def test_wp7_06_evidence_set_is_deterministic_and_has_no_scientific_disposition(self):
        metric = build_metric_record(
            view_result=self.present_view,
            metric_id="ORG.METRIC.ASSIGNED_RATE.v1",
            eligible_universe_id="POP.ELIGIBLE.v1",
            numerator=4,
            denominator=8,
        )
        kwargs = dict(
            view_results=[self.null_view, self.present_view],
            metric_records=[metric],
            declared_topology_ids=["FAMILY"],
            tested_envelope_complete=False,
            decision_rule_pack_interface=self.rule_pack,
        )
        first = assemble_organisation_evidence_set(**kwargs)
        second = assemble_organisation_evidence_set(**kwargs)
        self.assertEqual(first, second)
        self.assertEqual(first["scientific_disposition"], "NOT_EVALUATED_RULE_PACK_REQUIRED")
        self.assertEqual(first["organisation_absence_claim"], "NOT_MADE")
        self.assertEqual(first["view_scoped_nulls"], ["NO_STABLE_FAMILY"])
        self.assertTrue(first["organisation_evidence_set_id"].startswith("orges1:"))

    def test_wp7_07_no_stable_family_does_not_imply_no_stable_organisation(self):
        evidence_set = assemble_organisation_evidence_set(
            view_results=[self.null_view],
            declared_topology_ids=["FAMILY"],
            tested_envelope_complete=False,
        )
        self.assertEqual(evidence_set["view_scoped_nulls"], ["NO_STABLE_FAMILY"])
        with self.assertRaisesRegex(
            OrganisationEvidenceError,
            "REQUIRES_COMPLETE_ENVELOPE",
        ):
            assert_no_stable_organisation_claim_lawful(
                evidence_set=evidence_set,
                proposed_disposition="NO_STABLE_ORGANISATION",
            )

    def test_wp7_08_even_complete_all_topology_envelope_requires_executable_rule_pack(self):
        evidence_set = copy.deepcopy(
            assemble_organisation_evidence_set(
                view_results=[self.null_view],
                declared_topology_ids=["FAMILY"],
                tested_envelope_complete=False,
            )
        )
        evidence_set["tested_envelope"] = {
            "declared_topology_ids": [
                "FAMILY",
                "HIERARCHY",
                "OVERLAP",
                "GRAPH",
                "CONTINUUM",
                "COMPOSITION",
            ],
            "complete": True,
        }
        with self.assertRaisesRegex(
            OrganisationEvidenceError,
            "REQUIRES_EXECUTABLE_RULE_PACK",
        ):
            assert_no_stable_organisation_claim_lawful(
                evidence_set=evidence_set,
                proposed_disposition="NO_STABLE_ORGANISATION",
            )

    def test_wp7_09_rule_pack_is_interface_only_and_application_fails_closed(self):
        interface = validate_decision_rule_pack_interface(self.rule_pack)
        self.assertEqual(interface["maturity"], "INTERFACE_ONLY")
        self.assertFalse(interface["executable"])
        self.assertEqual(interface["thresholds"], [])
        evidence_set = assemble_organisation_evidence_set(view_results=[self.present_view])
        with self.assertRaisesRegex(
            OrganisationEvidenceError,
            "RULE_PACK_NOT_EXECUTABLE",
        ):
            apply_organisation_decision_rule_pack(
                evidence_set,
                decision_rule_pack=self.rule_pack,
            )

    def test_wp7_10_reserved_fields_and_authority_escalation_fail_closed(self):
        bad = copy.deepcopy(self.present_view)
        bad["topology_result"]["probability"] = 0.7
        with self.assertRaisesRegex(OrganisationEvidenceError, "FORBIDDEN_FIELD"):
            build_metric_record(
                view_result=bad,
                metric_id="ORG.METRIC.BAD.v1",
                eligible_universe_id="POP.BAD.v1",
                numerator=1,
                denominator=1,
            )
        bad_authority = copy.deepcopy(self.present_view)
        bad_authority["authority"]["scientific_support_disposition"] = "SUPPORTED"
        from ovc.opt_b.esl.canonical import sha256_canonical
        payload = dict(bad_authority)
        payload.pop("soi_view_result_id")
        payload.pop("logical_hash")
        bad_authority["logical_hash"] = sha256_canonical(payload)
        bad_authority["soi_view_result_id"] = "soi1:" + bad_authority["logical_hash"]
        with self.assertRaisesRegex(OrganisationEvidenceError, "AUTHORITY_ENVELOPE_INVALID"):
            assemble_organisation_evidence_set(view_results=[bad_authority])

    def test_wp7_11_contract_schema_registry_and_fixture_are_materialised(self):
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        status_registry = json.loads(STATUS_REGISTRY.read_text(encoding="utf-8"))
        contract = CONTRACT.read_text(encoding="utf-8")
        self.assertEqual(schema["properties"]["scientific_disposition"]["const"], "NOT_EVALUATED_RULE_PACK_REQUIRED")
        self.assertIn("NO_STABLE_ORGANISATION", status_registry["scientific_dispositions"])
        self.assertEqual(status_registry["authority_effect"], "NONE")
        self.assertIn("eligible universe", contract)
        self.assertIn("NO_STABLE_FAMILY", contract)
        self.assertEqual(self.expectations["packet_id"], "ESLI-WP7")
        self.assertEqual(self.expectations["no_support_thresholds_invented"], True)

    def test_wp7_12_authority_remains_inactive_across_all_records(self):
        metric = build_metric_record(
            view_result=self.present_view,
            metric_id="ORG.METRIC.ASSIGNED_RATE.v1",
            eligible_universe_id="POP.ELIGIBLE.v1",
            numerator=4,
            denominator=8,
        )
        evidence_set = assemble_organisation_evidence_set(
            view_results=[self.present_view],
            metric_records=[metric],
        )
        for record in (metric, evidence_set):
            authority = record["authority"]
            self.assertEqual(authority["authority_effect"], "NONE")
            self.assertEqual(authority["topology_activation"], "NONE")
            self.assertEqual(authority["method_selection"], "NONE")
            self.assertEqual(authority["scientific_support_disposition"], "NONE")
            self.assertEqual(authority["semantic_promotion"], "NONE")
            self.assertEqual(authority["validation_consumption"], "LOCKED_UNCONSUMED")
            self.assertEqual(authority["publication"], "NONE")


if __name__ == "__main__":
    unittest.main()
