from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

from ovc.opt_b.market_grammar import (
    ComponentClass,
    ComponentStats,
    ExclusivityRule,
    PredicateDomain,
    classify_component,
    infer_domain,
    migrate_legacy_component,
    validate_predicate_domain,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/market_grammar/wp1/predicate_classifier_cases.json"
DOMAIN_REGISTRY = ROOT / "registries/opt_b/market_grammar/MG_PREDICATE_DOMAIN_REGISTRY_v0_1.json"
EXCLUSIVITY_REGISTRY = ROOT / "registries/opt_b/market_grammar/MG_EXCLUSIVITY_REGISTRY_v0_1.json"
CLASS_REGISTRY = ROOT / "registries/opt_b/market_grammar/MG_COMPONENT_CLASS_REGISTRY_v0_1.json"
COMPONENT_SCHEMA = ROOT / "schemas/opt_b/market_grammar/component_stats_v0_1.schema.json"
EXCLUSIVITY_SCHEMA = ROOT / "schemas/opt_b/market_grammar/exclusivity_rule_v0_1.schema.json"
RUNNER = ROOT / "scripts/market_grammar/run_mg_wp1_fixture.py"


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"not object: {path}")
    return value


def make_stats(value: dict) -> ComponentStats:
    return ComponentStats(**value)


def make_rule(value: dict) -> ExclusivityRule:
    return ExclusivityRule(
        rule_id=value["rule_id"],
        feature_key=value["feature_key"],
        domain=value["domain"],
        object_scope=value["object_scope"],
        clock_scope=value["clock_scope"],
        time_scope=value["time_scope"],
        mutually_exclusive_values=tuple(value["mutually_exclusive_values"]),
        registry_version=value["registry_version"],
    )


def load_runner():
    spec = importlib.util.spec_from_file_location("run_mg_wp1_fixture", RUNNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PredicateDomainAndClassifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = load(FIXTURE)
        cls.domain_registry = load(DOMAIN_REGISTRY)
        cls.exclusivity_registry = load(EXCLUSIVITY_REGISTRY)
        cls.class_registry = load(CLASS_REGISTRY)
        cls.rules = {
            item["rule_id"]: make_rule(item)
            for item in cls.exclusivity_registry["rules"]
        }

    def test_six_domains_and_eight_classes_are_exact(self) -> None:
        self.assertEqual(
            {
                "STRUCTURAL",
                "TEMPORAL",
                "OBJECT_BINDING",
                "CONTEXT",
                "COMPUTABILITY",
                "PROVENANCE",
            },
            {item.value for item in PredicateDomain},
        )
        self.assertEqual(
            {
                "INVARIANT",
                "COMMON",
                "NORMAL_VARIATION",
                "HIGH_CARDINALITY_VARIATION",
                "MISSINGNESS_VARIATION",
                "LOGICAL_CONFLICT",
                "OPTIONAL",
                "RARE",
            },
            {item.value for item in ComponentClass},
        )
        self.assertEqual(
            {item.value for item in PredicateDomain},
            set(self.domain_registry["domain_enum"]),
        )
        self.assertEqual(
            {item.value for item in ComponentClass},
            {item["id"] for item in self.class_registry["classes"]},
        )
        self.assertFalse(
            self.class_registry["frequency_alone_proves_logical_conflict"]
        )
        self.assertIsNone(
            self.class_registry["legacy_direct_mappings"]["CONTRADICTORY"]
        )

    def test_reserved_fields_cannot_be_structural(self) -> None:
        expected = {
            "source_release_id": PredicateDomain.PROVENANCE,
            "manifest_id": PredicateDomain.PROVENANCE,
            "content_sha256": PredicateDomain.PROVENANCE,
            "provider_name": PredicateDomain.PROVENANCE,
            "clock_id": PredicateDomain.CONTEXT,
            "parent_clock_id": PredicateDomain.CONTEXT,
            "missingness": PredicateDomain.COMPUTABILITY,
            "first_valid_time": PredicateDomain.TEMPORAL,
            "episode_id": PredicateDomain.OBJECT_BINDING,
        }
        for key, domain in expected.items():
            self.assertIs(domain, infer_domain(key))
            with self.assertRaisesRegex(ValueError, f"reserved for {domain.value}"):
                validate_predicate_domain(key, PredicateDomain.STRUCTURAL)
        self.assertIs(
            PredicateDomain.STRUCTURAL,
            validate_predicate_domain("motion.direction", "STRUCTURAL"),
        )

    def test_fixture_classifications_are_exact_and_deterministic(self) -> None:
        for case in self.fixture["cases"]:
            stats = make_stats(case["stats"])
            rule_id = case.get("exclusivity_rule_id")
            rules = [self.rules[rule_id]] if rule_id else []
            first = classify_component(stats, rules)
            second = classify_component(stats, tuple(reversed(rules)))
            self.assertEqual(case["expected_class"], first.value, case["case_id"])
            self.assertIs(first, second)

    def test_frequency_alone_never_implies_logical_conflict(self) -> None:
        stats = ComponentStats(
            feature_key="motion.character",
            domain=PredicateDomain.STRUCTURAL,
            object_scope="STATE_RECORD",
            clock_id="15M",
            first_valid_time="2026-06-01T00:00:00Z",
            total_eligible=100,
            missing_count=0,
            value_counts={"TRENDING": 65, "ROTATIONAL": 35},
        )
        self.assertIs(
            ComponentClass.NORMAL_VARIATION,
            classify_component(stats),
        )
        migrated = migrate_legacy_component("CONTRADICTORY", stats)
        self.assertEqual("NORMAL_VARIATION", migrated["new_class"])
        self.assertEqual(
            "RECOMPUTED_WITH_TYPED_COMPONENT_CLASSIFIER",
            migrated["reason"],
        )

    def test_logical_conflict_requires_exact_feature_domain_and_object_scope(self) -> None:
        rule = self.rules["MG-EXCL-MOTION-DIRECTION-v0.1"]
        valid = ComponentStats(
            feature_key="motion.direction",
            domain="STRUCTURAL",
            object_scope="STATE_RECORD",
            clock_id="15M",
            first_valid_time="2026-06-01T00:00:00Z",
            total_eligible=2,
            missing_count=0,
            value_counts={"UP": 1, "DOWN": 1},
        )
        wrong_scope = ComponentStats(
            feature_key="motion.direction",
            domain="STRUCTURAL",
            object_scope="RELATION_RECORD",
            clock_id="15M",
            first_valid_time="2026-06-01T00:00:00Z",
            total_eligible=2,
            missing_count=0,
            value_counts={"UP": 1, "DOWN": 1},
        )
        self.assertIs(
            ComponentClass.LOGICAL_CONFLICT,
            classify_component(valid, [rule]),
        )
        self.assertIs(
            ComponentClass.NORMAL_VARIATION,
            classify_component(wrong_scope, [rule]),
        )
        migrated = migrate_legacy_component("CONTRADICTORY", valid, [rule])
        self.assertEqual("LOGICAL_CONFLICT", migrated["new_class"])
        self.assertEqual("EXACT_EXCLUSIVITY_PROOF", migrated["reason"])

    def test_invalid_fixtures_are_rejected(self) -> None:
        for case in self.fixture["invalid_cases"]:
            with self.assertRaisesRegex(
                ValueError,
                case["expected_error_contains"],
                msg=case["case_id"],
            ):
                if case["operation"] == "VALIDATE_DOMAIN":
                    validate_predicate_domain(
                        case["feature_key"], case["requested_domain"]
                    )
                elif case["operation"] == "CREATE_EXCLUSIVITY_RULE":
                    make_rule(case["rule"])
                elif case["operation"] == "CREATE_STATS":
                    make_stats(case["stats"])
                else:
                    self.fail(f"unknown operation: {case['operation']}")

    def test_provenance_and_computability_are_not_structural_eligible(self) -> None:
        for domain, key in (
            (PredicateDomain.PROVENANCE, "source_release_id"),
            (PredicateDomain.COMPUTABILITY, "computability_status"),
        ):
            stats = ComponentStats(
                feature_key=key,
                domain=domain,
                object_scope="STATE_RECORD",
                clock_id="15M",
                first_valid_time="2026-06-01T00:00:00Z",
                total_eligible=10,
                missing_count=0,
                value_counts={str(index): 1 for index in range(8)},
            )
            migrated = migrate_legacy_component("CONTRADICTORY", stats)
            self.assertFalse(migrated["structural_eligible"])
            self.assertNotEqual("LOGICAL_CONFLICT", migrated["new_class"])

    def test_schemas_and_registries_preserve_scope_constraints(self) -> None:
        stats_schema = load(COMPONENT_SCHEMA)
        exclusivity_schema = load(EXCLUSIVITY_SCHEMA)
        self.assertEqual(
            self.domain_registry["domain_enum"],
            stats_schema["properties"]["domain"]["enum"],
        )
        self.assertEqual(
            "SAME_CLOCK",
            exclusivity_schema["properties"]["clock_scope"]["const"],
        )
        self.assertEqual(
            "EXACT_FIRST_VALID_TIME",
            exclusivity_schema["properties"]["time_scope"]["const"],
        )
        self.assertEqual("PROHIBITED", self.exclusivity_registry["wildcards"])
        for rule in self.exclusivity_registry["rules"]:
            self.assertEqual("SAME_CLOCK", rule["clock_scope"])
            self.assertEqual("EXACT_FIRST_VALID_TIME", rule["time_scope"])
            self.assertNotIn(rule["domain"], {"PROVENANCE", "COMPUTABILITY"})

    def test_fixture_runner_is_complete(self) -> None:
        result = load_runner().run()
        self.assertEqual("PASS", result["status"])
        self.assertEqual(len(self.fixture["cases"]), result["valid_case_count"])
        self.assertEqual(
            len(self.fixture["invalid_cases"]), result["invalid_case_count"]
        )
        self.assertEqual(
            sorted(case["case_id"] for case in self.fixture["cases"]),
            sorted(item["case_id"] for item in result["results"]),
        )


if __name__ == "__main__":
    unittest.main()
