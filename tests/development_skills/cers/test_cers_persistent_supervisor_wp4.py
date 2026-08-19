from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.development.skills.cers.admission import (
    canonical_record_sha256,
    validate_inactive_admission_registry,
)


ROOT = Path(__file__).resolve().parents[3]
CERS_REGISTRIES = ROOT / "registries" / "development" / "skills" / "cers"


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class CersPersistentSupervisorWp4Tests(unittest.TestCase):
    def setUp(self):
        self.registry = load(
            "registries/development/skills/cers/"
            "CERS_PERSISTENT_PROGRAMME_ADMISSION_REGISTRY_v0_2.json"
        )
        self.root_registry = load(
            "registries/development/skills/cers/CERS_PROGRAMME_ROOT_REGISTRY_v0_1.json"
        )

    def programme_roots(self) -> dict[str, str]:
        roots: dict[str, str] = {}
        for row in self.root_registry["roots"]:
            source = load(row["path"])
            roots[source["programme_id"]] = row["path"]
        return roots

    def test_registry_is_inactive_exhaustive_and_fail_closed(self):
        self.assertEqual(self.registry["status"], "INACTIVE_PREACTIVATION")
        self.assertEqual(self.registry["unknown_or_absent_programme"], "DENY")
        self.assertFalse(self.registry["future_programme_auto_admission"])
        self.assertEqual(self.registry["authority_effect"], "NONE")
        self.assertEqual(
            validate_inactive_admission_registry(
                self.registry, programme_roots=self.programme_roots()
            ),
            (),
        )

    def test_only_exact_cers_owner_authority_is_admitted(self):
        self.assertEqual(len(self.registry["entries"]), 1)
        admission = self.registry["entries"][0]
        self.assertEqual(admission["programme_id"], "OVC-DSAI3V-CERS-CONFORMANCE-v0.1")
        self.assertEqual(admission["status"], "INACTIVE_PREACTIVATION")
        self.assertEqual(admission["authority_effect"], "NONE")
        self.assertEqual(admission["operator_boundary_policy"], "PARK")
        self.assertEqual(
            admission["write_domain_rule"],
            "PACKET_DECLARED_WRITE_DOMAIN_AND_SEMANTIC_OWNER_ONLY",
        )
        self.assertEqual(admission["eligible_packet_classes"], ["LOW_RISK_IMPLEMENTATION"])
        self.assertEqual(admission["allowed_side_effect_classes"], ["BRANCH_REVERSIBLE"])
        self.assertIn("MERGE", admission["explicit_prohibitions"])
        self.assertIn("ACTIVE_VALIDATION", admission["explicit_prohibitions"])
        owner_source = ROOT / admission["owner_authority_source"]
        self.assertTrue(owner_source.is_file())
        self.assertIn("CERS-PS-WP4", owner_source.read_text(encoding="utf-8"))

    def test_each_admission_matches_the_wp1_record_schema_and_hash(self):
        schema = load("schemas/development/skills/cers/cers_persistent_records_v0_1.schema.json")
        admission_schema = schema["$defs"]["PersistentProgrammeAdmission"]
        required = set(admission_schema["required"])
        allowed = set(admission_schema["properties"])
        hashes = {
            row["admission_id"]: row["canonical_sha256"]
            for row in self.registry["entry_hashes"]
        }
        for admission in self.registry["entries"]:
            self.assertEqual(set(admission), required)
            self.assertEqual(set(admission), allowed)
            self.assertEqual(
                admission["schema"],
                admission_schema["properties"]["schema"]["const"],
            )
            self.assertEqual(admission["operator_boundary_policy"], "PARK")
            self.assertEqual(admission["authority_effect"], "NONE")
            self.assertEqual(
                hashes[admission["admission_id"]], canonical_record_sha256(admission)
            )

    def test_all_non_admitted_roots_have_registered_typed_reasons(self):
        reason_registry = load(
            "registries/development/skills/cers/CERS_PERSISTENT_REASON_CODE_REGISTRY_v0_2.json"
        )
        known_codes = set(reason_registry["codes"])
        exclusions = self.registry["exclusions"]
        self.assertEqual(len(exclusions), 5)
        for exclusion in exclusions:
            self.assertTrue(exclusion["reason_codes"])
            self.assertLessEqual(set(exclusion["reason_codes"]), known_codes)
        terminal = {
            row["programme_id"]
            for row in exclusions
            if "PROGRAMME_TERMINAL_NO_NEXT_PACKET" in row["reason_codes"]
        }
        self.assertEqual(
            terminal,
            {
                "OVC-DSAI-VIT-v0.3",
                "OVC-DSAI3V-ASYNC-ASSURANCE-CONFORMANCE-v0.1",
                "OVC-DSAI-v0.2",
                "OVC-PRVIT-LIVE-REMEDIATION-CONFORMANCE-v0.1",
            },
        )

    def test_grt_operator_boundary_is_excluded_not_inferred(self):
        grt = next(
            row for row in self.registry["exclusions"] if row["root_id"] == "GRT_V0_2"
        )
        self.assertIn("OPERATOR_REQUIRED_BOUNDARY", grt["reason_codes"])
        self.assertIn("PREREQUISITE_UNSATISFIED", grt["reason_codes"])
        self.assertIn("WRITE_DOMAIN_UNKNOWN_OR_DENIED", grt["reason_codes"])
        state = load("registries/implementation/grt_v0_2/OVC_GRT2_STATE_v0_11.json")
        self.assertEqual(state["g3_status"], "NOT_AUTHORISED_READINESS_EVIDENCE_INCOMPLETE")

    def test_wp4_state_advances_only_to_shadow_qualification(self):
        state = load(
            "registries/implementation/dsai3v_cers_v0_1/"
            "OVC_DSAI3V_CERS_STATE_v0_14.json"
        )
        self.assertEqual(state["next_packet"], "CERS-PS-WP5")
        self.assertEqual(state["wp4"]["status"], "COMPLETED")
        self.assertEqual(state["wp4"]["registry_status"], "INACTIVE_PREACTIVATION")
        self.assertEqual(
            state["persistent_general_dispatch"],
            "DENIED_PENDING_CERS-G-PERSISTENT-SUPERVISOR-ACTIVATION",
        )
        self.assertEqual(state["post_pilot_dispatch_state"], "DISABLE_NEW_DISPATCH")


if __name__ == "__main__":
    unittest.main()
