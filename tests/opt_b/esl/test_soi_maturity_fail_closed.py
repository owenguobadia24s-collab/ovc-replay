import copy
import json
from pathlib import Path
import unittest

from ovc.opt_b.esl.soi_compat import (
    SOICompatibilityError,
    invoke_soi_topology,
    topology_registry_from_mapping,
)

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "registries/opt_b/esl/SOI_TOPOLOGY_MATURITY_v0_1.json"
SCHEMA = ROOT / "schemas/opt_b/esl/soi_topology_maturity_v0_1.schema.json"


class ESLIWP6IAV03MaturityFailClosedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    def test_iav03_interface_only_topologies_emit_no_placeholder_result(self):
        for topology in ("HIERARCHY", "OVERLAP", "GRAPH", "CONTINUUM", "COMPOSITION"):
            with self.subTest(topology=topology):
                with self.assertRaisesRegex(
                    SOICompatibilityError,
                    "SOI_ADAPTER_NOT_MATERIALIZED:" + topology,
                ):
                    invoke_soi_topology(topology, topology_registry=self.registry)

    def test_iav03_registry_schema_preserves_exact_inactive_boundary(self):
        entries = topology_registry_from_mapping(self.registry)
        self.assertEqual(entries["FAMILY"].maturity, "EXECUTABLE_INACTIVE")
        self.assertEqual(
            {name for name, entry in entries.items() if entry.maturity == "INTERFACE_ONLY"},
            {"HIERARCHY", "OVERLAP", "GRAPH", "CONTINUUM", "COMPOSITION"},
        )
        properties = self.schema["properties"]
        self.assertEqual(properties["packet_id"]["const"], "ESLI-WP6")
        self.assertEqual(properties["gate_id"]["const"], "ESLI-G6")
        self.assertEqual(properties["canonical_topology"]["const"], "NONE")
        self.assertEqual(properties["topology_activation"]["const"], "NONE")
        self.assertEqual(properties["scientific_selection"]["const"], "NONE")
        self.assertEqual(properties["authority_effect"]["const"], "NONE")

    def test_iav03_interface_only_cannot_be_relabelled_executable(self):
        mutated = copy.deepcopy(self.registry)
        for row in mutated["entries"]:
            if row["topology_id"] == "GRAPH":
                row["maturity"] = "EXECUTABLE_INACTIVE"
                row["adapter_id"] = "UNAUTHORISED"
                row["source_programme_id"] = "UNAUTHORISED"
                row["source_result_type"] = "UNAUTHORISED"
                row["reason_code"] = None
                break
        with self.assertRaisesRegex(
            SOICompatibilityError,
            "SOI_EXECUTABLE_TOPOLOGY_NOT_AUTHORISED:GRAPH",
        ):
            topology_registry_from_mapping(mutated)


if __name__ == "__main__":
    unittest.main()
