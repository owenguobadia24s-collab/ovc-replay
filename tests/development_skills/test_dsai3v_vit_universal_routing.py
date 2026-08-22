from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ovc.development.skills.siq_core import WAIT, build_queue_state, queue_head
from ovc.development.skills.vit_apply import REFERENCE_APPLY_PROFILE
from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_routing import (
    REGISTERED_EXCEPTION,
    UNLAWFUL,
    VIT_MANDATORY,
    build_vit_lineage_record,
    build_vit_payload_lineage_record,
    classify_main_movement,
    validate_vit_lineage_record,
)
from tools.ci.vit_lineage_source import ResolvedLineageSource, resolve_lineage_source
from tools.ci.vit_routing_preflight import check_pull_request_event

ROOT = Path(__file__).resolve().parents[2]
REGISTER = ROOT / "registries/development/skills/VIT_ROUTING_COVERAGE_REGISTER_v0_1.json"
AUDIT = ROOT / "docs/releases/development-skills-architecture-v0-3-vit/universal-routing/DSAI3V_VIT_ROUTING_AUDIT_v0_1.json"


def pip_payload(programme: str = "PROGRAMME", packet: str = "PACKET", changes: list[dict] | None = None) -> dict:
    return {
        "schema_version": "packet-integration-payload/v0.1",
        "programme_id": programme,
        "packet_id": packet,
        "logical_changes": changes or [{"op":"ADD","path":"records/example.json","blob_sha":"1" * 40,"mode":"100644"}],
        "authority_manifest_id": "2" * 64,
        "dependency_frontier_id": "3" * 64,
        "completion_transition": {"status": "COMPLETED"},
    }


def lineage_record(programme: str = "PROGRAMME", packet: str = "PACKET", *, predecessor: str = "a" * 40, result: str = "b" * 40, changes: list[dict] | None = None) -> dict:
    return build_vit_lineage_record(
        programme_id=programme,
        packet_id=packet,
        pip_identity_payload=pip_payload(programme, packet, changes),
        train_generation_id="TRAIN-1",
        ordinal=1,
        predecessor_tree_sha=predecessor,
        result_tree_sha=result,
        apply_profile=REFERENCE_APPLY_PROFILE,
    )


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git","-C",str(repo),*args],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True).stdout.strip()


def b64_lineage(record: dict) -> str:
    raw=json.dumps(record,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def canonical_bytes(record: dict) -> bytes:
    return json.dumps(record,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")


class Dsai3vUniversalRoutingTests(unittest.TestCase):
    def test_coverage_register_classifies_every_actuator(self) -> None:
        record = json.loads(REGISTER.read_text(encoding="utf-8"))
        self.assertEqual(record["unregistered_bypass_policy"], "FAIL_CLOSED")
        rows = record["actuators"]
        ids = [row["actuator_id"] for row in rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(row["route_class"] in {VIT_MANDATORY, REGISTERED_EXCEPTION, UNLAWFUL} for row in rows))
        route = {row["actuator_id"]: row["route_class"] for row in rows}
        self.assertEqual(route["SIQ_QUEUE_CANDIDATE_ADMISSION"], VIT_MANDATORY)
        self.assertEqual(route["OPERATOR_REQUIRED_GATE_PACKET"], VIT_MANDATORY)
        self.assertEqual(route["LEGACY_FRESH_MAIN_RECONCILE"], UNLAWFUL)

    def test_lineage_is_content_addressed_and_tamper_fails(self) -> None:
        record = lineage_record()
        validated = validate_vit_lineage_record(record)
        self.assertEqual(validated.pip_id, record["pip_id"])
        self.assertEqual(validated.generation_id, record["generation_id"])
        self.assertEqual(validated.placement_id, record["placement_id"])
        tampered = json.loads(json.dumps(record))
        tampered["generation"]["ordinal"] = 2
        with self.assertRaises(VitContractError):
            validate_vit_lineage_record(tampered)

    def test_payload_only_lineage_is_forward_default(self) -> None:
        record = build_vit_payload_lineage_record(
            programme_id="PROGRAMME", packet_id="PACKET", pip_identity_payload=pip_payload()
        )
        validated = validate_vit_lineage_record(record)
        self.assertTrue(validated.late_binding)
        self.assertIsNone(validated.generation_id)
        self.assertIsNone(validated.placement_id)
        self.assertNotIn("placement", record)

    def test_unrelated_main_advance_is_zero_payload_and_zero_aa0_rebuild(self) -> None:
        pip = "d" * 64
        result = classify_main_movement(previous_pip_id=pip,current_pip_id=pip,dependency_frontier_changed=False,authority_changed=False,packet_local_defect_changed_payload=False)
        self.assertEqual(result["disposition"], "PLACEMENT_RECOMPUTE_ONLY")
        self.assertFalse(result["payload_rebuild_required"])
        self.assertFalse(result["assurance_renewal_required"])

    def test_identity_bearing_packet_defect_requires_payload_rebuild(self) -> None:
        result = classify_main_movement(previous_pip_id="d"*64,current_pip_id="e"*64,dependency_frontier_changed=False,authority_changed=False,packet_local_defect_changed_payload=True)
        self.assertEqual(result["disposition"], "PAYLOAD_REBUILD_REQUIRED")
        self.assertTrue(result["payload_rebuild_required"])

    def test_historical_cases_separate_bypass_from_real_payload_change(self) -> None:
        audit = json.loads(AUDIT.read_text(encoding="utf-8"))
        cases = {row["case_id"]: row for row in audit["stale_main_case_reproduction"]}
        self.assertEqual(cases["PATH2-944-945"]["classification"], "VIT_BYPASS")
        self.assertFalse(cases["PATH2-944-945"]["payload_rebuild_required"])
        self.assertEqual(cases["C2P2-946-948"]["classification"], "VIT_BYPASS")
        self.assertEqual(cases["C2P2-948-951"]["classification"], "LEGITIMATE_PAYLOAD_REBUILD")
        self.assertTrue(cases["C2P2-948-951"]["payload_rebuild_required"])
        self.assertEqual(cases["RCCR-949-950"]["classification"], "VIT_BYPASS")
        self.assertFalse(cases["RCCR-949-950"]["operator_required_is_exception"])

    def test_siq_candidate_without_lineage_fails_closed(self) -> None:
        candidate={"packet_id":"DIRECT","plan_id":"PLAN","candidate_head_sha":"a"*40,"baseline_main_sha":"b"*40,"ready_sequence":1,"implementation_complete":True,"qa_status":"PASS","authority_delta":"NONE","gate_class":"AUTO_EXECUTABLE","preliminary_assurance_pass":True,"rollback_defined":True,"dependency_footprint_pinned":True}
        state=build_queue_state([candidate])
        self.assertEqual(state.candidates[0].queue_state,WAIT)
        self.assertIn("VIT_LINEAGE_REQUIRED",state.candidates[0].reason_codes)
        self.assertIsNone(queue_head(state))

    def test_immutable_git_blob_lineage_is_canonical_and_content_addressed(self) -> None:
        record = lineage_record(); raw = canonical_bytes(record); blob_sha = "a" * 40
        source = resolve_lineage_source(f"VIT-Lineage-Blob: {blob_sha}",fetch_blob=lambda observed: raw if observed == blob_sha else b"")
        assert source is not None
        self.assertEqual(source.record, record)
        self.assertEqual(source.source, "IMMUTABLE_GIT_BLOB")
        self.assertEqual(source.immutable_ref, blob_sha)
        self.assertEqual(len(source.content_sha256), 64)

    def test_immutable_git_blob_rejects_noncanonical_json_and_dual_source(self) -> None:
        record = lineage_record(); noncanonical = json.dumps(record, indent=2).encode("utf-8")
        with self.assertRaisesRegex(RuntimeError, "NOT_CANONICAL_JSON"):
            resolve_lineage_source("VIT-Lineage-Blob: " + "b" * 40,fetch_blob=lambda _: noncanonical)
        body = "VIT-Lineage-Blob: " + "c" * 40 + "\nVIT-Lineage-B64: " + b64_lineage(record)
        with self.assertRaisesRegex(RuntimeError, "MULTIPLE_SOURCES"):
            resolve_lineage_source(body, fetch_blob=lambda _: canonical_bytes(record))

    def test_pr_preflight_accepts_detached_payload_without_live_main_placement_or_pr_metadata(self) -> None:
        with TemporaryDirectory() as tmp:
            root=Path(tmp); git(root,"init","-q"); git(root,"config","user.email","vit@example.invalid"); git(root,"config","user.name","VIT Test")
            (root/"base.txt").write_text("base\n",encoding="utf-8"); git(root,"add","base.txt"); git(root,"commit","-qm","base")
            base_sha=git(root,"rev-parse","HEAD")
            (root/"payload.txt").write_text("payload\n",encoding="utf-8"); git(root,"add","payload.txt"); git(root,"commit","-qm","payload")
            head_sha=git(root,"rev-parse","HEAD"); blob=git(root,"rev-parse","HEAD:payload.txt")
            register_path=root/"registries/development/skills/VIT_ROUTING_COVERAGE_REGISTER_v0_1.json"; register_path.parent.mkdir(parents=True); register_path.write_text(json.dumps({"unregistered_bypass_policy":"FAIL_CLOSED","registered_pr_exceptions":[]}),encoding="utf-8")
            record=build_vit_payload_lineage_record(programme_id="PROGRAMME",packet_id="PACKET",pip_identity_payload=pip_payload(changes=[{"op":"ADD","path":"payload.txt","blob_sha":blob,"mode":"100644"}]))
            source=ResolvedLineageSource(record=record,source="DETACHED_QUALIFICATION_LEDGER",immutable_ref="4"*64,content_sha256="5"*64)
            event={"number":1,"pull_request":{"body":"Human review only","head":{"sha":head_sha,"ref":"feature"},"base":{"sha":base_sha,"ref":"main"}}}
            with patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}, clear=False):
                with patch("tools.ci.vit_routing_preflight.resolve_candidate_lineage", return_value=source):
                    result=check_pull_request_event(root=root,event=event)
                    self.assertTrue(result.startswith("VIT_MANDATORY_LATE_BINDING:PACKET:"))
                with patch("tools.ci.vit_routing_preflight.resolve_candidate_lineage", side_effect=RuntimeError("VIT_QUALIFICATION_REQUIRED")):
                    with self.assertRaisesRegex(RuntimeError, "VIT_QUALIFICATION_REQUIRED"):
                        check_pull_request_event(root=root,event=event)


if __name__ == "__main__":
    unittest.main()
