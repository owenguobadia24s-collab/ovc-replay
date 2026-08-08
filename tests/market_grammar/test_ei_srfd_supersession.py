from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/market-grammar-empirical-integration-june-v0-1/ei-supersession"
DECISION = BASE / "EI_SRFD_SUPERSESSION_OPERATOR_DECISION.json"
QA = BASE / "EI_SRFD_SUPERSESSION_QA_PACKET.json"
CROSSWALK = ROOT / "registries/opt_b/market_grammar/EI_SRFD_ROUTE_SUPERSESSION_v0_1.json"
STATE = ROOT / "registries/opt_b/market_grammar/OVC_MG_EI_JUNE_PROGRAMME_STATE_v0_1.jsonc"
OLD_MODULE = ROOT / "src/ovc/opt_b/market_grammar/structural_projection.py"
SRFD_SRI = ROOT / "src/ovc/opt_b/srfd/representation.py"
SRFD_ADAPTER = ROOT / "src/ovc/opt_b/srfd/source_adapter_v02.py"
SRFD_COMPILER = ROOT / "src/ovc/opt_b/srfd/real_source_packs.py"
SRFD_REGISTRY = ROOT / "registries/research/srfd/real_source_representation_packs_v0_2.json"
SRFD_FREEZE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp9s/SRFDI_G9S_FREEZE_OPERATOR_DECISION.json"


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(path)
    return value


class EiSrfdSupersessionTests(unittest.TestCase):
    def test_operator_decision_preserves_history_and_supersedes_route(self) -> None:
        decision = load(DECISION)
        self.assertEqual("SUPERSEDE", decision["decision"])
        self.assertEqual("OPERATOR_EXPLICIT", decision["decision_authority"])
        self.assertEqual(
            "OVC APPROVE EI-WP2/EI-WP3 SUPERSEDE_WITH_SRFD_SRI_REPRESENTATIONPACK",
            decision["operator_command"],
        )
        self.assertEqual("COMPLETED_PRESERVED_AS_HISTORICAL_IMPLEMENTATION_EVIDENCE", decision["historical_preservation"]["EI-WP2"])
        self.assertEqual("SUPERSEDED_NO_EMPIRICAL_RUN_WAS_STARTED", decision["supersession"]["EI-WP3"])
        self.assertEqual("NONE", decision["authority_effect"]["scientific_promotion"])
        self.assertEqual("UNCHANGED_ALREADY_AUTHORIZED_BY_SEPARATE_SRFDI-G-JUNE-AUTH", decision["authority_effect"]["srfd_june_execution"])

    def test_crosswalk_points_to_implemented_frozen_srfd_route(self) -> None:
        crosswalk = load(CROSSWALK)
        self.assertEqual("SRFD_SRI_REPRESENTATIONPACK_ONLY", crosswalk["routing_rules"]["new_empirical_c2_to_representation_family_work"])
        self.assertEqual(0, crosswalk["routing_rules"]["old_ei_wp2_projection_runtime_consumer_count_expected"])
        for path in (SRFD_SRI, SRFD_ADAPTER, SRFD_COMPILER, SRFD_REGISTRY, SRFD_FREEZE):
            self.assertTrue(path.exists(), path)
        freeze = load(SRFD_FREEZE)
        registry = load(SRFD_REGISTRY)
        self.assertEqual("PREREGISTRATION_FREEZE", freeze["decision"])
        self.assertEqual(
            "7d93994836bfcff6c5a0b39db33692f70b1a25782bee43c7b6329d17568561c0",
            freeze["approved_candidate"]["representation_pack_registry_v0_2_logical_sha256"],
        )
        self.assertEqual("OVC-SRFD-REAL-SOURCE-REPRESENTATION-PACKS-0.2", registry["registry_id"])

    def test_old_projection_has_no_active_runtime_consumer(self) -> None:
        self.assertTrue(OLD_MODULE.exists())
        offenders = []
        for path in (ROOT / "src/ovc").rglob("*.py"):
            if path == OLD_MODULE:
                continue
            text = path.read_text(encoding="utf-8")
            if "market_grammar.structural_projection" in text or "project_revised_c2_state" in text or "project_revised_c2_states" in text:
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual([], offenders)

    def test_programme_is_superseded_without_rewriting_completed_evidence(self) -> None:
        state = load(STATE)
        packets = {item["packet_id"]: item for item in state["packets"]}
        self.assertEqual("SUPERSEDED", state["status"])
        self.assertEqual("COMPLETED", packets["EI-WP0"]["status"])
        self.assertEqual("COMPLETED", packets["EI-WP1"]["status"])
        self.assertEqual("COMPLETED", packets["EI-WP2"]["status"])
        self.assertEqual("SUPERSEDED_FOR_FUTURE_EMPIRICAL_USE_BY_SRFD_SRI_REPRESENTATIONPACK", packets["EI-WP2"]["route_disposition"])
        self.assertEqual("SUPERSEDED", packets["EI-WP3"]["status"])
        self.assertFalse(packets["EI-WP3"]["empirical_run_started"])
        self.assertEqual(371, packets["EI-WP3"]["blocked_pr"])
        self.assertEqual("SUPERSEDED", packets["EI-WP4"]["status"])
        self.assertIsNone(state["next_packet"])

    def test_qa_requires_exact_head_and_has_no_new_authority(self) -> None:
        qa = load(QA)
        self.assertEqual("PASS_IMPLEMENTATION_HEAD", qa["status"])
        self.assertEqual([], qa["blockers"])
        self.assertEqual("PASS", qa["qa_recommendation"])
        self.assertIn("SRFDI-G-JUNE-AUTH", qa["warnings"][0])


if __name__ == "__main__":
    unittest.main()
