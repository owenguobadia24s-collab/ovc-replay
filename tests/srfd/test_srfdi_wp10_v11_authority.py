from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.opt_b.srfd.wp10_v10_interface import SCIENCE_IDENTITY_SHA256
from ovc.opt_b.srfd.wp10_v11_interface import FROZEN_ENVIRONMENT_PROFILE_SHA256, HARDENING_REHEARSAL_SHA256
from srfd._current_pointer_compat import assert_lawful_v10_pointer

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v1-1"
MANIFEST = BASE / "SRFD_JUNE_AUTHORITY_MANIFEST_CANDIDATE_v1_1.json"
TOKEN = BASE / "SRFD_JUNE_AUTHORITY_TOKEN_v1_1.json"
DECISION = BASE / "SRFD_JUNE_AUTHORITY_OPERATOR_DECISION_v1_1.json"
READY_STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_48_WP10_V11_READY.json"
BLOCKED_STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_49_WP10_V11_PREFLIGHT_ENV_BLOCKED.json"
SUPERSEDED_STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_50_WP10_V11_ENV_SUPERSEDED.json"
SUPERSESSION = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v1-1/SRFDI_WP10_V11_ENVIRONMENT_PROFILE_SUPERSESSION.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"
OLD_TOKEN = "SRFD.JUNE.AUTH.7b52e77176fa43d246891ec61d3d0130afe8cb7b5e296f3a705dc83e7fe95b9f"
OLD_BINDING = "3029d32692f20e724d95ed0b63acf79b1709769f4b8603e9371acee50cd642b5"
NEW_ENV = "e08aaf02871d23979b47f2ce928b2098d775eab3e483ff3602db2794afa13eef"
NEW_HARDENING = "445d4bb6646ad61b045b3cb0bd51078be194c7423277b23df52f8bc85b88d0d8"


class SRFDIWP10V11AuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = json.loads(MANIFEST.read_text())
        cls.t = json.loads(TOKEN.read_text())
        cls.d = json.loads(DECISION.read_text())
        cls.ready = json.loads(READY_STATE.read_text())
        cls.blocked = json.loads(BLOCKED_STATE.read_text())
        cls.sup = json.loads(SUPERSESSION.read_text())
        cls.state = json.loads(SUPERSEDED_STATE.read_text())
        cls.p = json.loads(POINTER.read_text())

    def test_historical_v11_authority_is_preserved_but_superseded_unused(self):
        self.assertEqual(OLD_TOKEN, self.t["token_id"])
        self.assertEqual("AUTHORIZED_UNCONSUMED", self.t["state"])
        self.assertEqual(OLD_BINDING, self.t["run_binding_sha256"])
        self.assertFalse(self.blocked["authority"]["token_consumed"])
        self.assertEqual(OLD_TOKEN, self.sup["superseded_authority"]["token_id"])
        self.assertEqual(OLD_BINDING, self.sup["superseded_authority"]["run_binding_sha256"])
        self.assertFalse(self.sup["superseded_authority"]["token_was_consumed"])
        self.assertEqual("SUPERSEDED_UNUSED_UNCONSUMED_DO_NOT_REUSE", self.sup["superseded_authority"]["disposition"])

    def test_science_is_unchanged_while_execution_environment_is_superseded(self):
        self.assertEqual(SCIENCE_IDENTITY_SHA256, self.m["run_binding"]["science_identity_sha256"])
        self.assertEqual(SCIENCE_IDENTITY_SHA256, self.state["science_identity_sha256"])
        self.assertEqual("NONE", self.sup["cause"]["scientific_delta"])
        self.assertEqual(NEW_ENV, FROZEN_ENVIRONMENT_PROFILE_SHA256)
        self.assertEqual(NEW_HARDENING, HARDENING_REHEARSAL_SHA256)
        self.assertEqual(NEW_ENV, self.state["environment_profile_sha256"])
        self.assertEqual(NEW_HARDENING, self.state["hardening_rehearsal_sha256"])

    def test_source_counts_and_reserved_boundaries_remain_frozen(self):
        self.assertEqual(9420, self.m["frozen_counts"]["source_record_count"])
        self.assertEqual(8598, self.m["frozen_counts"]["eligible_record_count"])
        self.assertEqual(36, self.m["frozen_counts"]["comparability_domain_count"])
        self.assertEqual(1944, self.m["frozen_counts"]["family_configuration_count"])
        self.assertEqual(2020, self.m["frozen_counts"]["work_unit_count"])
        self.assertEqual("DENIED", self.state["authority"]["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.state["authority"]["validation_2025"])
        self.assertEqual("NONE", self.state["authority"]["scientific_promotion"])
        self.assertEqual("NONE", self.state["authority"]["selector_family_semantic_publication"])
        self.assertEqual("NONE", self.state["authority"]["probability_risk_exposure_execution"])

    def test_historical_supersession_required_fresh_post_merge_authority_regeneration(self):
        self.assertEqual("READY", self.state["status"])
        self.assertFalse(self.state["science_execution_started"])
        self.assertIsNone(self.state["authority"]["fresh_authority_token_id"])
        self.assertFalse(self.state["authority"]["fresh_authority_token_consumed"])
        self.assertEqual("NONE_PENDING_POST_MERGE_REGENERATION", self.state["authority"]["fresh_authority_token_state"])
        self.assertEqual("SRFDI-WP10-v1.1-FRESH-AUTHORITY-REGENERATION", self.state["next_packet"])
        self.assertEqual("FRESH_AUTHORITY_REGENERATION_BOUNDARY", self.state["stop_condition"])
        self.assertTrue(assert_lawful_v10_pointer(self, self.p))


if __name__ == "__main__":
    unittest.main()
