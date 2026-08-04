from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FREEZE_PATH = ROOT / "registries/opt_b/c2/vnext/C2_INTEGRATED_SHADOW_FREEZE_v1.jsonc"


def git_blob_sha(payload: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload).hexdigest()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


class IntegratedShadowFreezeTests(unittest.TestCase):
    def test_freeze_digest_and_every_source_ledger_blob_are_exact(self) -> None:
        freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
        expected = freeze.pop("freeze_sha256")
        self.assertEqual(expected, canonical_sha256(freeze))
        self.assertEqual("SHADOW_FROZEN", freeze["maturity"])
        self.assertTrue(freeze["effective"])
        self.assertEqual("60db2b7a41360a4a1e3a1739659cf9c3774a0290", freeze["effective_baseline_commit"])
        self.assertEqual(5, len(freeze["source_revisions"]))
        for source in freeze["source_revisions"]:
            payload = (ROOT / source["ledger_path"]).read_bytes()
            self.assertEqual(source["ledger_git_blob_sha"], git_blob_sha(payload), source["domain"])
            ledger = json.loads(payload.decode("utf-8"))
            self.assertEqual(source["revision_id"], ledger["revision_id"])
            self.assertEqual("SHADOW_EXPERIMENT", ledger["maturity"])
            self.assertEqual("SHADOW_FROZEN", source["frozen_maturity"])
            self.assertEqual("CEAR-G6", ledger["freeze_gate"])

    def test_freeze_is_a_separate_supersession_not_in_place_mutation(self) -> None:
        freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
        self.assertEqual("NO_IN_PLACE_MUTATION_NEW_VERSION_AND_SUPERSESSION_REQUIRED", freeze["pinning"]["mutation_policy"])
        source_paths = {item["ledger_path"] for item in freeze["source_revisions"]}
        self.assertNotIn(str(FREEZE_PATH.relative_to(ROOT)), source_paths)
        self.assertTrue(freeze["pinning"]["repository_commit_pins_all_referenced_contract_schema_registry_fixture_implementation_and_test_bytes"])
        self.assertTrue(freeze["pinning"]["revision_ledger_blob_shas_recorded"])

    def test_freeze_grants_no_active_runtime_or_downstream_authority(self) -> None:
        freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
        self.assertTrue(all(value == "NONE" for value in freeze["active_authority"].values()))
        active = (ROOT / "registries/opt_b/c2/C2_ACTIVE_SELECTORS.yaml").read_text(encoding="utf-8")
        self.assertIn("SELECTOR.OPT-B.C2.GBPUSD.v2", active)
        self.assertIn("OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2", active)
        self.assertIn("LOCKED_UNCONSUMED", active)

    def test_formula_registry_is_the_only_declared_profile_registry(self) -> None:
        freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
        registry_path = ROOT / freeze["formula_profile_registry"]
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        self.assertEqual("SHADOW_FROZEN", registry["maturity"])
        self.assertIsNone(registry["active_profile_id"])
        self.assertIsNone(registry["canonical_profile_id"])
        self.assertEqual(5, len(registry["profiles"]))
        self.assertTrue(all(item["authority"] == "SHADOW_FROZEN_READ_ONLY" for item in registry["profiles"]))


if __name__ == "__main__":
    unittest.main()
