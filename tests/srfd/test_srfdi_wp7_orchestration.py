from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import unittest

from ovc.opt_b.srfd.orchestration import (
    OrchestrationError, artifact_reference, authority_guard, canonicalize_records,
    deterministic_fixture_manifest, research_operations_event, run_pipeline,
)
from ovc.opt_b.srfd.serialization import canonical_json_bytes

ROOT = Path(__file__).resolve().parents[2]


def stages():
    return {
        "population": lambda state: {**state,"records":canonicalize_records(state["records"])},
        "representation": lambda state: {**state,"represented":[item["record_id"] for item in state["records"]]},
        "compatibility": lambda state: {**state,"comparable":True},
        "distance": lambda state: {**state,"pair_count":len(state["represented"])*(len(state["represented"])-1)//2},
        "family": lambda state: {**state,"family_evidence":"NO_STABLE_FAMILY"},
        "sensitivity": lambda state: {**state,"sensitivity":"UNRESOLVED"},
        "correspondence": lambda state: {**state,"correspondence":[]},
        "invariant_core": lambda state: {**state,"cores":[]},
        "stability": lambda state: {**state,"stability":"UNRESOLVED"},
        "failure_attribution": lambda state: {**state,"limiting_layer":"family"},
        "packet": lambda state: {**state,"packet":"READY"},
    }


class SRFDIWP7OrchestrationTests(unittest.TestCase):
    def test_full_fixture_catalog_is_exact_and_unique(self) -> None:
        catalog = json.loads((ROOT / "fixtures/opt_b/srfd/SRFDI_FIXTURE_CATALOG_v0_1.json").read_text())
        manifest = deterministic_fixture_manifest(catalog)
        self.assertEqual(30,manifest["fixture_count"])
        self.assertEqual([f"FX-{index:03d}" for index in range(1,31)],manifest["fixture_ids"])

    def test_checkpoint_restart_is_logically_and_byte_equivalent(self) -> None:
        initial = {"records":[{"record_id":"B"},{"record_id":"A"}],"authority_state":"FIXTURE_ONLY"}
        full = run_pipeline(initial,stages())
        partial = run_pipeline(initial,stages(),stop_after="family")
        checkpoint_dict = partial["last_checkpoint"]
        from ovc.opt_b.srfd.orchestration import CheckpointReceipt
        checkpoint = CheckpointReceipt(
            checkpoint_dict["checkpoint_id"],checkpoint_dict["completed_stage_index"],checkpoint_dict["completed_stage"],
            checkpoint_dict["state"],checkpoint_dict["state_logical_hash"],tuple(checkpoint_dict["stage_receipts"]),checkpoint_dict["authority_state"]
        )
        resumed = run_pipeline(initial,stages(),checkpoint=checkpoint)
        self.assertEqual(full["state_logical_hash"],resumed["state_logical_hash"])
        self.assertEqual(canonical_json_bytes(full["state"]),canonical_json_bytes(resumed["state"]))

    def test_corrupt_checkpoint_fails_closed(self) -> None:
        initial = {"records":[{"record_id":"A"}],"authority_state":"FIXTURE_ONLY"}
        partial = run_pipeline(initial,stages(),stop_after="population")
        c = partial["last_checkpoint"]
        from ovc.opt_b.srfd.orchestration import CheckpointReceipt
        checkpoint = CheckpointReceipt(c["checkpoint_id"],c["completed_stage_index"],c["completed_stage"],{"corrupt":True},c["state_logical_hash"],tuple(c["stage_receipts"]),c["authority_state"])
        with self.assertRaisesRegex(OrchestrationError,"CAP_RESTART_FAILURE"):
            run_pipeline(initial,stages(),checkpoint=checkpoint)

    def test_authority_guard_denies_all_reserved_paths(self) -> None:
        denied = ["canonical_r2_publication","selector_change","c2e_activation","c2g_activation","validation_consumption","june_market_benchmark","probability","risk","exposure","execution"]
        for action in denied:
            with self.assertRaises(OrchestrationError,msg=action):
                authority_guard(action)
        authority_guard("fixture_local_compute")

    def test_artifact_catalogue_hook_is_compact_external_only(self) -> None:
        ref = artifact_reference(artifact_id="A",sha256="a"*64,location="external://srfd/run/A.json",media_type="application/json")
        event = research_operations_event(event_type="ARTIFACT_REGISTERED",target_id="A",artifact_refs=[ref])
        self.assertEqual("NONE",event["authority_effect"])
        with self.assertRaisesRegex(OrchestrationError,"AUTH_SCOPE_EXPANSION"):
            artifact_reference(artifact_id="A",sha256="a"*64,location="git://raw/payload.bin",media_type="application/octet-stream")

    def test_input_permutation_is_canonicalized(self) -> None:
        first = run_pipeline({"records":[{"record_id":"B"},{"record_id":"A"}]},stages())
        second = run_pipeline({"records":[{"record_id":"A"},{"record_id":"B"}]},stages())
        self.assertEqual(first["state_logical_hash"],second["state_logical_hash"])


if __name__ == "__main__":
    unittest.main()
