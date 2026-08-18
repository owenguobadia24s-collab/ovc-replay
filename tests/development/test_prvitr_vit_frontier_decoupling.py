from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from ovc.development.skills.vit_frontier_decoupling import (
    FrontierIntegrationAssuranceGeneration,
    SourceHead,
    a1_proof_id,
    build_a2_proof,
    build_frontier_ledger_envelope,
    build_frontier_lineage,
    classify_frontier_movement,
    compose_pip_tree,
    create_prospective_commit,
    diff_tree_paths,
    git_tree,
    tree_is_in_commit_ancestry,
    validate_frontier_ledger_envelope,
)
from ovc.development.skills.vit_materialisation import (
    PhysicalIntegrationLease,
    PhysicalMaterialisationTransaction,
    materialisation_receipt,
    validate_lease,
)
from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_routing import (
    build_vit_lineage_record,
    validate_vit_lineage_record,
)

AUTHORITY = "a" * 64
FRONTIER = "b" * 64
RESULT_ID = "c" * 64


class FrontierFixture:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.git("init", "-b", "main")
        self.git("config", "user.name", "OVC Test")
        self.git("config", "user.email", "test@ovc.invalid")
        (self.root / "README.md").write_text("base\n", encoding="utf-8")
        self.git("add", "README.md")
        self.git("commit", "-m", "base")
        self.base_commit = self.git("rev-parse", "HEAD")
        self.base_tree = self.git("rev-parse", "HEAD^{tree}")

        payload = self.root / "payload.txt"
        payload.write_text("immutable packet\n", encoding="utf-8")
        self.payload_blob = self.git("hash-object", "-w", str(payload))
        payload.unlink()
        self.pip = {
            "schema_version": "packet-integration-payload/v0.1",
            "programme_id": "PRVITR-VIT-FRONTIER-DECOUPLING",
            "packet_id": "FD-WP1",
            "logical_changes": [
                {
                    "op": "ADD",
                    "path": "payload.txt",
                    "blob_sha": self.payload_blob,
                    "mode": "100644",
                }
            ],
            "authority_manifest_id": AUTHORITY,
            "dependency_frontier_id": FRONTIER,
            "completion_transition": {"status": "COMPLETED"},
            "dependency_footprint": {
                "dependency_paths": ["contracts/owned/**"],
                "semantic_authority_paths": ["registries/authority/owned/**"],
                "identity_binding_paths": ["schemas/owned/**"],
            },
        }
        self.source_result_tree = compose_pip_tree(
            self.root, self.base_tree, self.pip["logical_changes"]
        )
        self.source_commit = create_prospective_commit(
            self.root,
            predecessor_commit=self.base_commit,
            result_tree=self.source_result_tree,
            generation_id="1" * 64,
        )
        self.source = SourceHead(
            commit_sha=self.source_commit,
            tree_sha=self.source_result_tree,
            pr_number=77,
            head_ref="packet/fd-wp1",
            development_base_commit=self.base_commit,
            development_base_tree=self.base_tree,
        )
        self.source_lineage = build_vit_lineage_record(
            programme_id=self.pip["programme_id"],
            packet_id=self.pip["packet_id"],
            pip_identity_payload=self.pip,
            train_generation_id="FD-TRAIN",
            ordinal=1,
            predecessor_tree_sha=self.base_tree,
            result_tree_sha=self.source_result_tree,
            apply_profile="INTEGRATION_APPLY_PROFILE_REFERENCE_v0_1",
            source_head=asdict(self.source),
        )

    def git(self, *args: str, check: bool = True) -> str:
        proc = subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if check and proc.returncode != 0:
            raise AssertionError(proc.stderr)
        return proc.stdout.strip()

    def advance_main(self, path: str, content: str) -> tuple[str, str]:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        self.git("add", path)
        self.git("commit", "-m", f"advance {path}")
        return self.git("rev-parse", "HEAD"), self.git("rev-parse", "HEAD^{tree}")

    def close(self) -> None:
        self.temp.cleanup()


class PRVITRVITFrontierDecouplingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = FrontierFixture()

    def tearDown(self) -> None:
        self.fx.close()

    def test_unrelated_main_movement_preserves_pip_pr_and_a0_but_renews_placement(self) -> None:
        new_main, new_tree = self.fx.advance_main(
            "docs/unrelated/receipt.json", '{"ok":true}\n'
        )
        self.assertTrue(
            tree_is_in_commit_ancestry(
                self.fx.root,
                tree_sha=self.fx.base_tree,
                descendant_commit=new_main,
            )
        )
        movement = classify_frontier_movement(
            pip=self.fx.pip,
            source_predecessor_tree=self.fx.base_tree,
            current_predecessor_tree=new_tree,
            changed_paths=diff_tree_paths(self.fx.root, self.fx.base_tree, new_tree),
        )
        self.assertEqual(movement.disposition, "PLACEMENT_RECOMPUTE_ONLY")
        self.assertTrue(movement.a0_reuse_allowed)
        prospective = compose_pip_tree(
            self.fx.root, new_tree, self.fx.pip["logical_changes"]
        )
        refreshed = build_frontier_lineage(
            source_lineage_record=self.fx.source_lineage,
            source_head=self.fx.source,
            predecessor_commit=new_main,
            predecessor_tree=new_tree,
            prospective_result_tree=prospective,
            movement=movement,
        )
        source = validate_vit_lineage_record(self.fx.source_lineage)
        current = validate_vit_lineage_record(refreshed)
        self.assertEqual(current.pip_id, source.pip_id)
        self.assertNotEqual(current.generation_id, source.generation_id)
        self.assertNotEqual(current.placement_id, source.placement_id)
        self.assertEqual(
            refreshed["frontier_resolution"]["source_head"]["commit_sha"],
            self.fx.source_commit,
        )
        self.assertEqual(
            refreshed["frontier_resolution"]["pr_role"],
            "TRANSPORT_AND_SOURCE_PROVENANCE_ONLY",
        )
        # Current main is not required to be an ancestor of the source PR head.
        ancestry = subprocess.run(
            [
                "git",
                "-C",
                str(self.fx.root),
                "merge-base",
                "--is-ancestor",
                new_main,
                self.fx.source_commit,
            ],
            check=False,
        )
        self.assertNotEqual(ancestry.returncode, 0)

    def test_global_integration_movement_reuses_a0_and_renews_a1_a2(self) -> None:
        _, new_tree = self.fx.advance_main(
            "tools/ci/vit_routing_preflight.py", "print('changed')\n"
        )
        movement = classify_frontier_movement(
            pip=self.fx.pip,
            source_predecessor_tree=self.fx.base_tree,
            current_predecessor_tree=new_tree,
            changed_paths=diff_tree_paths(self.fx.root, self.fx.base_tree, new_tree),
        )
        self.assertEqual(movement.disposition, "ASSURANCE_RENEWAL_REQUIRED")
        self.assertTrue(movement.a0_reuse_allowed)
        self.assertTrue(movement.a1_renewal_required)
        self.assertTrue(movement.a2_renewal_required)
        self.assertFalse(movement.payload_rebuild_required)

    def test_payload_dependency_and_authority_changes_block_same_pip(self) -> None:
        _, payload_tree = self.fx.advance_main("payload.txt", "other writer\n")
        payload = classify_frontier_movement(
            pip=self.fx.pip,
            source_predecessor_tree=self.fx.base_tree,
            current_predecessor_tree=payload_tree,
            changed_paths=("payload.txt",),
        )
        self.assertEqual(payload.disposition, "PAYLOAD_REBUILD_REQUIRED")
        self.assertFalse(payload.a0_reuse_allowed)

        dependency = classify_frontier_movement(
            pip=self.fx.pip,
            source_predecessor_tree=self.fx.base_tree,
            current_predecessor_tree="9" * 40,
            changed_paths=("contracts/owned/spec.md",),
        )
        self.assertEqual(dependency.disposition, "PAYLOAD_REBUILD_REQUIRED")

        authority = classify_frontier_movement(
            pip=self.fx.pip,
            source_predecessor_tree=self.fx.base_tree,
            current_predecessor_tree="8" * 40,
            changed_paths=("registries/authority/owned/live.json",),
        )
        self.assertEqual(authority.disposition, "AUTHORITY_REVIEW_REQUIRED")
        self.assertTrue(authority.authority_review_required)

    def test_assurance_generation_binds_a0_to_pip_and_a1_a2_to_new_tree(self) -> None:
        new_main, new_tree = self.fx.advance_main("docs/u.json", "{}\n")
        movement = classify_frontier_movement(
            pip=self.fx.pip,
            source_predecessor_tree=self.fx.base_tree,
            current_predecessor_tree=new_tree,
            changed_paths=("docs/u.json",),
        )
        prospective = compose_pip_tree(
            self.fx.root, new_tree, self.fx.pip["logical_changes"]
        )
        lineage = build_frontier_lineage(
            source_lineage_record=self.fx.source_lineage,
            source_head=self.fx.source,
            predecessor_commit=new_main,
            predecessor_tree=new_tree,
            prospective_result_tree=prospective,
            movement=movement,
        )
        validated = validate_vit_lineage_record(lineage)
        assurance = FrontierIntegrationAssuranceGeneration(
            source_head_id=self.fx.source.source_head_id,
            source_head_commit=self.fx.source_commit,
            pip_id=validated.pip_id,
            vit_generation_id=validated.generation_id,
            placement_id=validated.placement_id,
            predecessor_commit=new_main,
            predecessor_tree=new_tree,
            prospective_result_tree=prospective,
            authority_manifest_id=AUTHORITY,
            dependency_frontier_id=FRONTIER,
            policy_id="test-policy",
            a0_result_ids=(RESULT_ID,),
            a1_proof_id=a1_proof_id(lineage),
            assurance_stage="A2_QUALIFIED",
            a2_result_ids=("d" * 64,),
        )
        self.assertEqual(len(assurance.assurance_generation_id), 64)
        self.assertEqual(assurance.pip_id, validate_vit_lineage_record(self.fx.source_lineage).pip_id)
        self.assertEqual(assurance.prospective_result_tree, prospective)

    def test_source_head_is_provenance_and_does_not_change_pip_or_placement_ids(self) -> None:
        alternate_commit = create_prospective_commit(
            self.fx.root,
            predecessor_commit=self.fx.base_commit,
            result_tree=self.fx.source_result_tree,
            generation_id="2" * 64,
        )
        alternate = SourceHead(
            commit_sha=alternate_commit,
            tree_sha=self.fx.source_result_tree,
            pr_number=78,
            head_ref="packet/fd-wp1-transport-renewal",
            development_base_commit=self.fx.base_commit,
            development_base_tree=self.fx.base_tree,
        )
        alternate_lineage = build_vit_lineage_record(
            programme_id=self.fx.pip["programme_id"],
            packet_id=self.fx.pip["packet_id"],
            pip_identity_payload=self.fx.pip,
            train_generation_id="FD-TRAIN",
            ordinal=1,
            predecessor_tree_sha=self.fx.base_tree,
            result_tree_sha=self.fx.source_result_tree,
            apply_profile="INTEGRATION_APPLY_PROFILE_REFERENCE_v0_1",
            source_head=asdict(alternate),
        )
        left = validate_vit_lineage_record(self.fx.source_lineage)
        right = validate_vit_lineage_record(alternate_lineage)
        self.assertNotEqual(left.source_head_id, right.source_head_id)
        self.assertEqual(left.pip_id, right.pip_id)
        self.assertEqual(left.generation_id, right.generation_id)
        self.assertEqual(left.placement_id, right.placement_id)

    def test_a0_a1_and_a2_assurance_stages_are_fail_closed(self) -> None:
        kwargs = {
            "source_head_id": self.fx.source.source_head_id,
            "source_head_commit": self.fx.source_commit,
            "pip_id": validate_vit_lineage_record(self.fx.source_lineage).pip_id,
            "vit_generation_id": validate_vit_lineage_record(self.fx.source_lineage).generation_id,
            "placement_id": validate_vit_lineage_record(self.fx.source_lineage).placement_id,
            "predecessor_commit": self.fx.base_commit,
            "predecessor_tree": self.fx.base_tree,
            "prospective_result_tree": self.fx.source_result_tree,
            "authority_manifest_id": AUTHORITY,
            "dependency_frontier_id": FRONTIER,
            "policy_id": "test-policy",
            "a0_result_ids": (RESULT_ID,),
            "a1_proof_id": "e" * 64,
        }
        with self.assertRaisesRegex(VitContractError, "A2_RESULTS_BEFORE"):
            FrontierIntegrationAssuranceGeneration(
                **kwargs,
                assurance_stage="A0_A1_BOUND",
                a2_result_ids=("d" * 64,),
            )
        with self.assertRaisesRegex(VitContractError, "A2_RESULTS_REQUIRED"):
            FrontierIntegrationAssuranceGeneration(
                **kwargs,
                assurance_stage="A2_QUALIFIED",
            )

    def test_late_frontier_ledger_envelope_round_trips_and_is_content_addressed(self) -> None:
        new_main, new_tree = self.fx.advance_main("docs/u2.json", "{}\n")
        movement = classify_frontier_movement(
            pip=self.fx.pip,
            source_predecessor_tree=self.fx.base_tree,
            current_predecessor_tree=new_tree,
            changed_paths=("docs/u2.json",),
        )
        prospective = compose_pip_tree(
            self.fx.root, new_tree, self.fx.pip["logical_changes"]
        )
        frontier = build_frontier_lineage(
            source_lineage_record=self.fx.source_lineage,
            source_head=self.fx.source,
            predecessor_commit=new_main,
            predecessor_tree=new_tree,
            prospective_result_tree=prospective,
            movement=movement,
        )
        validated = validate_vit_lineage_record(frontier)
        a2 = build_a2_proof(
            frontier_lineage=frontier,
            workflow_run_id="9001",
            run_attempt="2",
        )
        assurance = FrontierIntegrationAssuranceGeneration(
            source_head_id=self.fx.source.source_head_id,
            source_head_commit=self.fx.source_commit,
            pip_id=validated.pip_id,
            vit_generation_id=validated.generation_id,
            placement_id=validated.placement_id,
            predecessor_commit=new_main,
            predecessor_tree=new_tree,
            prospective_result_tree=prospective,
            authority_manifest_id=AUTHORITY,
            dependency_frontier_id=FRONTIER,
            policy_id="test-policy",
            a0_result_ids=(RESULT_ID,),
            a1_proof_id=a1_proof_id(frontier),
            assurance_stage="A2_QUALIFIED",
            a2_result_ids=(a2["record_id"],),
        )
        envelope = build_frontier_ledger_envelope(
            frontier_lineage=frontier,
            assurance_generation=assurance,
            a2_proof=a2,
        )
        decoded = validate_frontier_ledger_envelope(envelope)
        self.assertEqual(decoded["frontier_lineage_record_id"], envelope["frontier_lineage_record_id"])
        self.assertEqual(decoded["assurance_generation_id"], assurance.assurance_generation_id)
        self.assertEqual(decoded["a2_proof_id"], a2["record_id"])
        self.assertEqual(decoded["envelope_record_id"], envelope["record_id"])

    def test_frontier_and_freeze_schemas_are_closed_and_bind_late_ledger_envelope(self) -> None:
        root = Path(__file__).resolve().parents[2]
        frontier_schema = json.loads(
            (root / "schemas/development/skills/prvitr_vit_frontier_decoupling_v0_1.schema.json").read_text(encoding="utf-8")
        )
        freeze_schema = json.loads(
            (root / "schemas/development/skills/vit_live_physical_transaction_freeze_v1.schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual(frontier_schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertFalse(frontier_schema["additionalProperties"])
        for definition in frontier_schema["$defs"].values():
            if definition.get("type") == "object":
                self.assertFalse(definition["additionalProperties"])
        self.assertIn("frontier_ledger_envelope", freeze_schema["properties"])
        self.assertFalse(freeze_schema["$defs"]["frontierLedgerEnvelope"]["additionalProperties"])

    def test_physical_lease_aborts_only_after_frozen_predecessor_moves(self) -> None:
        lease = PhysicalIntegrationLease(
            lease_id="lease",
            expected_predecessor_commit=self.fx.base_commit,
            expected_predecessor_tree=self.fx.base_tree,
            holder="FD-WP1",
        )
        self.assertEqual(
            validate_lease(lease, self.fx.base_commit, self.fx.base_tree),
            "LEASE_VALID",
        )
        self.assertEqual(
            validate_lease(lease, "7" * 40, "6" * 40),
            "PREDECESSOR_MOVED",
        )

    def test_a3_requires_exact_post_write_tree_equality(self) -> None:
        transaction = PhysicalMaterialisationTransaction(
            vit_generation_id="1" * 64,
            ticket_id="ticket",
            train_generation_id="train",
            expected_predecessor_commit=self.fx.base_commit,
            expected_predecessor_tree=self.fx.base_tree,
            expected_result_tree=self.fx.source_result_tree,
            authority_frontier_id=AUTHORITY,
            assurance_frontier_id=FRONTIER,
            materialisation_profile="LIVE_PHYSICAL_MAIN",
        )
        passed = materialisation_receipt(
            transaction, self.fx.source_commit, self.fx.source_result_tree
        )
        failed = materialisation_receipt(
            transaction, self.fx.source_commit, "f" * 40
        )
        self.assertTrue(passed.equality)
        self.assertEqual(passed.outcome, "MATERIALISED_EQUIVALENT")
        self.assertFalse(failed.equality)
        self.assertEqual(failed.outcome, "POST_WRITE_TREE_MISMATCH")


if __name__ == "__main__":
    unittest.main()
