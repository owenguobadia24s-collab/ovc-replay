from __future__ import annotations

import json
import unittest
from pathlib import Path

import ovc
from ovc.active_stack import load_active_stack
from ovc.opt_a import AUTHORITY_STATE as OPT_A_HISTORICAL_STATE
from ovc.opt_a import CURRENT_AUTHORITY_STATE as OPT_A_CURRENT_STATE
from ovc.opt_b.c1 import AUTHORITY_STATE as C1_HISTORICAL_STATE
from ovc.opt_b.c1 import CURRENT_AUTHORITY_STATE as C1_CURRENT_STATE
from ovc.opt_b.c2 import AUTHORITY_STATE as C2_HISTORICAL_STATE
from ovc.opt_b.c2 import CURRENT_AUTHORITY_STATE as C2_CURRENT_STATE
from ovc.opt_b.c2_vnext import AUTHORITY_STATE as C2_VNEXT_CURRENT_STATE
from ovc.opt_b.c2e_v2 import AUTHORITY_STATE as C2E_CURRENT_STATE


ROOT = Path(__file__).resolve().parents[1]


class ActiveTreeFoundationTests(unittest.TestCase):
    def test_clean_namespaces_import_and_current_states_resolve(self) -> None:
        self.assertEqual(ovc.__version__, "0.2.0")
        # Historical namespace tokens remain readable for exact replay compatibility.
        self.assertEqual(OPT_A_HISTORICAL_STATE, "DESIGN_AND_FIXTURES_ONLY")
        self.assertEqual(C1_HISTORICAL_STATE, "B1_G5_SHADOW_SELECTED_C2_DENIED")
        self.assertEqual(C2_HISTORICAL_STATE, "DESIGN_AND_FIXTURES_ONLY")
        # Current authority is resolved separately and does not rewrite historical tokens.
        self.assertEqual(
            OPT_A_CURRENT_STATE,
            "ACTIVE_SEALED_OBSERVATION_INPUT_DISCOVERY_DEVELOPMENT_VALIDATION_LOCKED",
        )
        self.assertEqual(C1_CURRENT_STATE, "ACTIVE_DISCOVERY_AND_DEVELOPMENT")
        self.assertEqual(C2_CURRENT_STATE, "LEGACY_INACTIVE_NEW_EVIDENCE_DENIED")
        self.assertEqual(C2_VNEXT_CURRENT_STATE, "ACTIVE_CORE_DISCOVERY_AND_DEVELOPMENT")
        self.assertEqual(
            C2E_CURRENT_STATE,
            "ACTIVE_ENGINE_CURRENT_OPERATOR_SELECTED_PACK_MARKET_ENVELOPE_BOUND",
        )

    def test_legacy_engine_is_not_in_active_source_tree(self) -> None:
        self.assertFalse((ROOT / "src" / "ovc_opt_b").exists())
        self.assertTrue((ROOT / "legacy" / "quarantine" / "abcd-engine-v1-c0ad7ba").is_dir())

    def test_current_active_stack_supersedes_early_repository_authority_snapshot(self) -> None:
        state = load_active_stack(ROOT)
        self.assertEqual(
            state["active_spine"],
            ["OPT-A", "OPT-B.C1.v2", "OPT-B.C2.vNext", "OPT-B.C2E.v0.2"],
        )
        self.assertEqual(state["market_envelope"]["validation"], "LOCKED_UNCONSUMED")
        self.assertIn("OPT-B.C2.v2", state["classifications"]["LEGACY_INACTIVE"])
        self.assertIn("OCCURRENCE_CONTEXT.v0.1", state["classifications"]["ACTIVE_FOUNDATION"])
        self.assertIn("RESEARCH_OPERATIONS_FOUNDATION", state["classifications"]["ACTIVE_FOUNDATION"])

        historical = (ROOT / "registries" / "authority" / "ACTIVE_AUTHORITY.yaml").read_text(encoding="utf-8")
        self.assertIn("snapshot_date: 2026-07-26", historical)
        self.assertEqual(
            state["precedence"]["historical_repository_authority_effect"],
            "SUPERSEDED_SNAPSHOT_FOR_CURRENT_STACK_CLASSIFICATION",
        )
        self.assertEqual(
            state["precedence"]["historical_repository_authority_snapshot"],
            "registries/authority/ACTIVE_AUTHORITY.yaml",
        )

    def test_current_implementation_registry_matches_stack_classification(self) -> None:
        registry = (ROOT / "registries" / "implementation" / "IMPLEMENTATION_REGISTRY.yaml").read_text(encoding="utf-8")
        self.assertIn("schema: ovc-implementation-registry/v2", registry)
        self.assertIn("current_authority_pointer: registries/governance/active_stack/CURRENT_ACTIVE_STACK_POINTER.json", registry)
        self.assertIn("id: OPT-B-C2-V2", registry)
        self.assertIn("state: LEGACY_INACTIVE", registry)
        self.assertIn("id: OPT-B-C2-VNEXT", registry)
        self.assertIn("authority: ACTIVE_EXACT_NINE_COMPONENT_CORE_DISCOVERY_DEVELOPMENT", registry)
        self.assertIn("id: OPT-B-C2E-V0-2", registry)
        self.assertIn("ACTIVE_ENGINE_CURRENT_OPERATOR_SELECTED_PACK_MARKET_ENVELOPE_BOUND", registry)
        self.assertIn("validation_consumption: LOCKED_UNCONSUMED", registry)
        self.assertIn("probability_risk_exposure_trading_execution_agent_write: NONE", registry)


if __name__ == "__main__":
    unittest.main()
