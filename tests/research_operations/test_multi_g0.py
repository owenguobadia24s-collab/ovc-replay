from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class MultiG0Tests(unittest.TestCase):
    def test_validator_passes(self) -> None:
        path = ROOT / "scripts/research_operations/validate_multi_g0.py"
        spec = importlib.util.spec_from_file_location("validate_multi_g0", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.main(), 0)

    def test_operator_decisions_are_atomic(self) -> None:
        value = load("docs/releases/multi-g0-operator-decisions-v0-1/MULTI_G0_OPERATOR_DECISION.json")
        self.assertEqual(tuple(value["decisions"]), ("CCR-G0", "C2E-G0", "C25-G0"))
        self.assertTrue(all(item["decision"] == "PASS" for item in value["decisions"].values()))

    def test_activation_remains_denied(self) -> None:
        ccr = load("registries/research_operations/clock_continuity/OVC_CCR_PROGRAMME_STATE_v0_1.json")
        c2e = load("registries/research_operations/c2e/OVC_C2E_PROGRAMME_STATE_v0_1.json")
        c25 = load("registries/research_operations/c2_5/OVC_C25_PROGRAMME_STATE_v0_1.json")
        self.assertEqual(ccr["authority"]["clock_or_continuity_activation"], "DENIED")
        self.assertEqual(c2e["authority"]["c2e_activation"], "DENIED")
        self.assertEqual(c25["authority"]["event_promotion_or_activation"], "DENIED")

    def test_variants_and_rules_are_bounded(self) -> None:
        ccr = load("registries/research_operations/clock_continuity/OVC_CCR_VARIANT_AND_METRIC_REGISTRY_v0_1.json")
        c2e = load("registries/research_operations/c2e/OVC_C2E_BOUNDARY_AND_LIFECYCLE_REGISTRY_v0_1.json")
        c25 = load("registries/research_operations/c2_5/OVC_C25_BOUNDED_RULE_REGISTRY_v0_1.json")
        self.assertEqual(len(ccr["variants"]), 3)
        self.assertEqual(set(c2e["variants"]), {"STRICT", "PRIMARY", "PERMISSIVE"})
        self.assertEqual(len(c25["included_rules"]), 4)
        self.assertEqual(len(c25["excluded_rules"]), 4)

    def test_final_operator_gates_remain(self) -> None:
        for path, gate_packet in (
            ("registries/research_operations/clock_continuity/OVC_CCR_PROGRAMME_STATE_v0_1.json", "CCR-WP5"),
            ("registries/research_operations/c2e/OVC_C2E_PROGRAMME_STATE_v0_1.json", "C2E-WP6"),
            ("registries/research_operations/c2_5/OVC_C25_PROGRAMME_STATE_v0_1.json", "C25-WP6"),
        ):
            value = load(path)
            final = next(item for item in value["packets"] if item["packet_id"] == gate_packet)
            self.assertEqual(final["authority_required"], "OPERATOR_REQUIRED_FINAL")


if __name__ == "__main__":
    unittest.main()
