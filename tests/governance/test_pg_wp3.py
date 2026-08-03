import json
import unittest
from copy import deepcopy
from pathlib import Path

from ovc.programme_genesis import GraphValidationError, impact_analysis, validate_graph


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_ROOT = ROOT / "registries/governance/programme_genesis"
FIXTURE = ROOT / "fixtures/governance/programme_genesis/valid_pg_dependency_graph_v0_1.json"
SCHEMA = ROOT / "schemas/governance/programme_genesis/dependency_graph_v0_1.schema.json"
CONTRACT = ROOT / "contracts/governance/programme_genesis/DEPENDENCY_GRAPH_AND_IMPACT_CONTRACT_v0_1.md"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def edge_registry() -> dict[str, dict]:
    registry = load_json(REGISTRY_ROOT / "EDGE_TYPE_REGISTRY_v0_1.json")
    return {row["edge_type"]: row for row in registry["edge_types"]}


class ProgrammeGenesisWP3Tests(unittest.TestCase):
    def test_pre_migration_graph_is_valid_and_authority_neutral(self) -> None:
        graph = load_json(FIXTURE)
        result = validate_graph(graph["nodes"], graph["edges"], edge_registry())
        self.assertEqual("PASS", result["status"])
        self.assertEqual(0, result["hard_cycle_count"])
        self.assertEqual("PASS", result["authority_path_status"])
        self.assertEqual([], [finding for finding in result["findings"] if finding["severity"] in {"BLOCK", "QUARANTINE"}])
        self.assertEqual(len(graph["nodes"]), result["node_count"])
        self.assertEqual(len(graph["edges"]), result["edge_count"])

    def test_graph_hash_and_findings_are_input_order_independent(self) -> None:
        graph = load_json(FIXTURE)
        first = validate_graph(graph["nodes"], graph["edges"], edge_registry())
        second = validate_graph(list(reversed(graph["nodes"])), list(reversed(graph["edges"])), edge_registry())
        self.assertEqual(first["graph_sha256"], second["graph_sha256"])
        self.assertEqual(first["findings"], second["findings"])

    def test_hard_dependency_cycle_is_quarantined(self) -> None:
        graph = load_json(FIXTURE)
        cycle_edge = deepcopy(graph["edges"][4])
        cycle_edge.update({
            "edge_id": "PGEDGE.G2.REQUIRES.WP3.CYCLE",
            "from_node": "DECISION.PG-G2",
            "to_node": "PACKET.PG-WP3",
        })
        result = validate_graph(graph["nodes"], graph["edges"] + [cycle_edge], edge_registry())
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, result["hard_cycle_count"])
        self.assertTrue(any(finding["code"] == "HARD_DEPENDENCY_CYCLE" and finding["severity"] == "QUARANTINE" for finding in result["findings"]))

    def test_inferred_hard_prerequisite_is_quarantined(self) -> None:
        graph = load_json(FIXTURE)
        edges = deepcopy(graph["edges"])
        edges[0]["source_kind"] = "ADAPTER_INFERRED"
        result = validate_graph(graph["nodes"], edges, edge_registry())
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any(finding["code"] == "INFERRED_HARD_PREREQUISITE" for finding in result["findings"]))

    def test_graph_edge_cannot_grant_authority(self) -> None:
        graph = load_json(FIXTURE)
        edges = deepcopy(graph["edges"])
        edges[0]["authority_effect"] = "GRANTED_BY_GRAPH"
        result = validate_graph(graph["nodes"], edges, edge_registry())
        self.assertEqual("FAIL", result["status"])
        self.assertEqual("FAIL", result["authority_path_status"])
        self.assertTrue(any(finding["code"] == "GRAPH_AUTHORITY_GRANT" for finding in result["findings"]))

    def test_unknown_edge_type_and_orphan_endpoint_fail_closed(self) -> None:
        graph = load_json(FIXTURE)
        edges = deepcopy(graph["edges"])
        edges[0]["edge_type"] = "INVENTED_EDGE"
        edges[1]["to_node"] = "MISSING.NODE"
        result = validate_graph(graph["nodes"], edges, edge_registry())
        codes = {finding["code"] for finding in result["findings"]}
        self.assertEqual("FAIL", result["status"])
        self.assertIn("UNKNOWN_EDGE_TYPE", codes)
        self.assertIn("ORPHAN_EDGE_ENDPOINT", codes)

    def test_impact_analysis_finds_transitive_downstream_migration_boundary(self) -> None:
        graph = load_json(FIXTURE)
        impact = impact_analysis(graph["nodes"], graph["edges"], ["DECISION.PG-G2"])
        self.assertEqual(
            ["GATE.PG-G3A", "PACKET.PG-WP3", "PACKET.PG-WP4"],
            impact["downstream_impacted"],
        )
        self.assertEqual(["PACKET.PG-WP3"], impact["direct_downstream"])
        self.assertEqual("NONE_DERIVED_ANALYSIS_ONLY", impact["authority_effect"])
        self.assertTrue(impact["operator_decision_required_for_any_authority_change"])

    def test_impact_analysis_rejects_unknown_changed_nodes(self) -> None:
        graph = load_json(FIXTURE)
        with self.assertRaisesRegex(GraphValidationError, "unknown changed nodes"):
            impact_analysis(graph["nodes"], graph["edges"], ["UNKNOWN.NODE"])

    def test_schema_and_contract_preserve_pg_g3a_boundary(self) -> None:
        schema = load_json(SCHEMA)
        self.assertEqual("NONE_DERIVED_GRAPH_ONLY", schema["properties"]["authority_effect"]["const"])
        self.assertFalse(schema["properties"]["migration_enabled"]["const"])
        self.assertEqual("NONE", schema["$defs"]["edge"]["properties"]["authority_effect"]["const"])
        text = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("`PG-G3A` remains a mandatory operator acknowledgement", text)
        self.assertIn("any hard dependency cycle is `QUARANTINE`", text)
        self.assertIn("graph may display authority lineage but cannot create", text)
        self.assertIn("Only `ACKNOWLEDGE_CONTINUE` may release `PG-WP4`", text)


if __name__ == "__main__":
    unittest.main()
