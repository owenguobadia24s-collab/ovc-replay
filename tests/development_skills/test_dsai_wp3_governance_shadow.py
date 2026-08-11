from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from ovc.development.skills import (
    MANDATORY_ADVERSARIAL_FAMILIES,
    build_curation_record,
    build_programme_skill_bootstrap_template,
    build_skill_release_bundle,
    compile_knowledge_pack,
    evaluate_corpus_qualification_readiness,
    reusable_fixture_ids,
    score_historical_replay_case,
    shadow_authority_resolver,
    shadow_preflight,
    shadow_prerequisite_resolver,
    shadow_scope_guard,
)
from ovc.development.skills.registry import validate_against_schema


ROOT = Path(__file__).resolve().parents[2]


class DSAIWP3GovernanceShadowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.candidates = json.loads(
            (ROOT / "registries/development/skills/governance_candidates_v0_1.json").read_text(encoding="utf-8")
        )
        self.corpus = json.loads(
            (ROOT / "fixtures/development_skills/wp3_adversarial_corpus_v0_1.json").read_text(encoding="utf-8")
        )
        self.history = json.loads(
            (ROOT / "fixtures/development_skills/wp3_historical_replay_v0_1.json").read_text(encoding="utf-8")
        )

    def test_e1_candidates_are_shadow_only_non_trusted_and_no_write(self) -> None:
        self.assertEqual(len(self.candidates["entries"]), 4)
        for row in self.candidates["entries"]:
            self.assertEqual(row["maturity"], "EXPERIMENTAL")
            self.assertEqual(row["execution_mode"], "SHADOW")
            self.assertEqual(row["authority_effect"], "NONE")
            self.assertEqual(row["write_permission"], "DENY")
            self.assertNotEqual(row["maturity"], "TRUSTED")
            self.assertIn("+sha256:", row["release_id"])

    def test_e2_golden_shadow_interpretations_pass_without_control(self) -> None:
        receipts = [
            shadow_preflight({
                "repository_sha": "a" * 40,
                "plan_id": "PLAN",
                "packet_id": "WP",
                "source_precedence_resolved": True,
                "scope_status": "IN_SCOPE",
                "prerequisites_complete": True,
            }),
            shadow_authority_resolver(recorded_authority={"implementation": "BOUNDED"}, requested_delta="NONE"),
            shadow_scope_guard(requested_paths=["src/ovc/development/skills/a.py"], allowed_prefixes=["src/ovc/development/skills"]),
            shadow_prerequisite_resolver(required=["G2"], observed={"G2": "COMPLETED"}),
        ]
        for receipt in receipts:
            self.assertEqual(receipt["evaluation_status"], "PASS")
            self.assertEqual(receipt["disposition"], "PASS")
            self.assertFalse(receipt["controlling"])
            self.assertEqual(receipt["authority_effect"], "NONE")
            self.assertEqual(receipt["writes_performed"], [])
            self.assertFalse(receipt["tool_broker_used"])

    def test_e3_correct_refusal_is_pass_behaviour(self) -> None:
        reserved = shadow_authority_resolver(
            recorded_authority={"implementation": "BOUNDED"},
            requested_delta="TRUSTED_PROMOTION",
        )
        scope = shadow_scope_guard(
            requested_paths=["registries/authority/forbidden.json"],
            allowed_prefixes=["src/ovc/development/skills"],
        )
        prereq = shadow_prerequisite_resolver(required=["G2", "G3"], observed={"G2": "COMPLETED"})
        for receipt in (reserved, scope, prereq):
            self.assertEqual(receipt["evaluation_status"], "PASS")
            self.assertEqual(receipt["disposition"], "BLOCK")
            self.assertTrue(receipt["correct_refusal"])
            self.assertEqual(receipt["authority_effect"], "NONE")

    def test_e4_adversarial_seed_has_all_mandatory_families_but_blocks_qualification_pending_human_review(self) -> None:
        families = {row["fixture_family"] for row in self.corpus["curation_records"]}
        self.assertEqual(families, set(MANDATORY_ADVERSARIAL_FAMILIES))
        readiness = evaluate_corpus_qualification_readiness(self.corpus["curation_records"])
        self.assertEqual(readiness["status"], "BLOCK")
        self.assertFalse(readiness["qualification_eligible"])
        self.assertEqual(set(readiness["review_gaps"]), set(MANDATORY_ADVERSARIAL_FAMILIES))
        self.assertIn("INDEPENDENT_HUMAN_REVIEW_MISSING", readiness["reason_codes"])

    def test_curation_record_schema_and_independent_review_requirements(self) -> None:
        record = build_curation_record(
            fixture_family="AUTHORITY_CONFUSION",
            governing_source="OVC-DSA-DESIGN-SPEC-0.1-REVISED-1-RATIFIED",
            author_role="CURATOR",
            reviewer_role="INDEPENDENT_REVIEWER",
            curation_effort_minutes=15,
            fixture_ids=["A1"],
            independent_review_state="ACCEPTED",
        )
        schema = json.loads(
            (ROOT / "schemas/development/skills/adversarial_corpus_curation_record_v0_1.schema.json").read_text(encoding="utf-8")
        )
        validate_against_schema(record, schema)
        ready_records = []
        for family in MANDATORY_ADVERSARIAL_FAMILIES:
            ready_records.append(build_curation_record(
                fixture_family=family,
                governing_source="OVC-DSA-DESIGN-SPEC-0.1-REVISED-1-RATIFIED",
                author_role="CURATOR",
                reviewer_role="INDEPENDENT_REVIEWER",
                curation_effort_minutes=10,
                fixture_ids=[f"{family}.1"],
                independent_review_state="ACCEPTED",
            ))
        readiness = evaluate_corpus_qualification_readiness(ready_records)
        self.assertEqual(readiness["status"], "PASS")
        self.assertEqual(reusable_fixture_ids(ready_records), sorted(f"{family}.1" for family in MANDATORY_ADVERSARIAL_FAMILIES))

    def test_historical_replay_scores_governing_interpretation_not_operator_outcome(self) -> None:
        for case in self.history["cases"]:
            result = score_historical_replay_case(
                actual_interpretation=case["reference_interpretation"],
                case=case,
            )
            self.assertEqual(result["status"], "PASS")
            self.assertFalse(result["operator_outcome_used_for_scoring"])
            changed = copy.deepcopy(case)
            changed["operator_outcome"] = "INVERTED_FOR_TEST"
            result2 = score_historical_replay_case(
                actual_interpretation=case["reference_interpretation"],
                case=changed,
            )
            self.assertEqual(result2["status"], "PASS")
            self.assertFalse(result2["operator_outcome_used_for_scoring"])

    def test_bootstrap_template_cannot_create_programme_state_or_authority(self) -> None:
        template = build_programme_skill_bootstrap_template(
            programme_id="OVC-NEW-PROGRAMME",
            plan_id="OVC-NEW-PLAN",
            initial_packet="WP0",
        )
        schema = json.loads(
            (ROOT / "schemas/development/skills/programme_skill_bootstrap_template_v0_1.schema.json").read_text(encoding="utf-8")
        )
        validate_against_schema(template, schema)
        self.assertFalse(template["may_create_programme_state"])
        self.assertFalse(template["may_grant_authority"])
        with self.assertRaisesRegex(ValueError, "cannot create or grant"):
            build_programme_skill_bootstrap_template(
                programme_id="OVC-NEW-PROGRAMME",
                plan_id="OVC-NEW-PLAN",
                initial_packet="WP0",
                requested_authority={"ACTIVE": True},
            )

    def test_knowledge_packs_and_releases_rebuild_from_exact_sources(self) -> None:
        packs = json.loads(
            (ROOT / "registries/development/skills/governance_knowledge_packs_v0_1.json").read_text(encoding="utf-8")
        )
        source_fixture = json.loads(
            (ROOT / "fixtures/development_skills/wp3_governance_knowledge_sources_v0_1.json").read_text(encoding="utf-8")
        )
        source_records = source_fixture["sources"]
        by_pack = {row["knowledge_pack_id"]: row for row in packs["entries"]}
        self.assertEqual(len(by_pack), 4)
        for row in packs["entries"]:
            rebuilt = compile_knowledge_pack(
                knowledge_pack_id=row["knowledge_pack_id"],
                source_requirements=[{"artifact_id": value, "fragment_selectors": []} for value in sorted(source_records)],
                source_records=source_records,
                compiled_content=row["compiled_content"],
            )
            self.assertEqual(rebuilt["source_set_hash"], row["source_set_hash"])
            self.assertEqual(rebuilt["compiled_pack_hash"], row["compiled_pack_hash"])
            self.assertEqual(rebuilt["authority_effect"], "NONE")
        for candidate in self.candidates["entries"]:
            pack = by_pack[candidate["knowledge_pack_id"]]
            fields = {
                "capability_ids": candidate["capability_ids"],
                "execution_mode": "SHADOW",
                "failure_policy": "FAIL_CLOSED",
                "authority_effect": "NONE",
                "write_permission": "DENY",
                "knowledge_pack_binding": {
                    "knowledge_pack_id": candidate["knowledge_pack_id"],
                    "compiled_pack_hash": candidate["knowledge_pack_hash"],
                },
                "implementation_entrypoint": candidate["implementation_entrypoint"],
            }
            rebuilt = build_skill_release_bundle(
                skill_id=candidate["skill_id"],
                logical_name=candidate["logical_name"],
                semantic_version=candidate["semantic_version"],
                fields=fields,
                field_classification={key: "NORMATIVE" for key in fields},
                source_refs=[
                    "OVC-DSA-DESIGN-SPEC-0.1-REVISED-1-RATIFIED",
                    "OVC-DSAI-IMPLEMENTATION-PLAN-0.2",
                ],
            )
            self.assertEqual(rebuilt["release_id"], candidate["release_id"])
            self.assertEqual(rebuilt["authority_effect"], "NONE")
            self.assertEqual(pack["compiled_pack_hash"], candidate["knowledge_pack_hash"])


if __name__ == "__main__":
    unittest.main()
