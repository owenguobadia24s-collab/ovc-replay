from __future__ import annotations
import json
from pathlib import Path
import unittest
from ovc.development.skills import LocalToolBroker, build_tool_request, decide_tool_request, issue_credential_handle, negative_reachability_probe, redact_sensitive, resolve_security_envelope, sandbox_leakage_probe, security_containment
from ovc.development.skills.registry import validate_against_schema
ROOT=Path(__file__).resolve().parents[2]
def envelope(**overrides):
    base=dict(skill_id="OVC-SKILL-020",capability_ids=["TEST_EXECUTION"],allowed_semantic_actions=["READ_REPOSITORY","READ_FILE","RUN_TESTS","WRITE_FILE"],read_prefixes=["src/ovc","tests"],write_prefixes=["src/ovc/development/skills"],semantic_owners=["DSAI"],logical_credential_ids=["GITHUB_LOGICAL"],network_allowlist=[]); base.update(overrides); return resolve_security_envelope(**base)
class DSAIWP5SecurityRuntimeTests(unittest.TestCase):
    def test_hard_deny_adversarial_suite(self):
        env=envelope(); fixture=json.loads((ROOT/"fixtures/development_skills/wp5_security_adversarial_v0_1.json").read_text())
        for case in fixture["cases"]:
            req=build_tool_request(action=case["action"],resource_class="VALIDATION" if case["family"]=="VALIDATION_LEAKAGE" else "GENERAL"); row=decide_tool_request(env,req); self.assertEqual(row["decision"],"DENY",case); self.assertFalse(row["raw_credentials_exposed"])
    def test_filesystem_scope_and_semantic_ownership(self):
        env=envelope(write_authority_active=True); good=decide_tool_request(env,build_tool_request(action="WRITE_FILE",path="src/ovc/development/skills/x.py",semantic_owner="DSAI")); self.assertEqual(good["decision"],"ALLOW")
        for row in [decide_tool_request(env,build_tool_request(action="WRITE_FILE",path="registries/authority/x.json",semantic_owner="DSAI")),decide_tool_request(env,build_tool_request(action="WRITE_FILE",path="src/ovc/development/skills/x.py",semantic_owner="OTHER")),decide_tool_request(env,build_tool_request(action="READ_FILE",path="../secret"))]: self.assertEqual(row["decision"],"DENY")
    def test_network_is_deny_by_default(self):
        row=decide_tool_request(envelope(),build_tool_request(action="READ_FILE",path="src/ovc/x.py",network_target="example.com")); self.assertEqual(row["decision"],"DENY"); self.assertIn("NETWORK_DENY_DEFAULT",row["reason_codes"])
    def test_credentials_are_logical_and_redacted(self):
        self.assertFalse(issue_credential_handle(logical_credential_id="GITHUB_LOGICAL")["secret_material_included"])
        with self.assertRaisesRegex(ValueError,"raw secret"): issue_credential_handle(logical_credential_id="GITHUB_LOGICAL",raw_secret="secret")
        with self.assertRaisesRegex(ValueError,"raw credentials"): build_tool_request(action="READ_REPOSITORY",raw_credential="secret")
        redacted=redact_sensitive({"token":"abc","nested":{"password":"p"},"safe":"ok"}); self.assertEqual(redacted["token"],"[REDACTED]"); self.assertEqual(redacted["nested"]["password"],"[REDACTED]"); self.assertEqual(redacted["safe"],"ok")
    def test_negative_reachability_and_sandbox_environment_path_leakage(self):
        self.assertEqual(negative_reachability_probe(envelope())["status"],"PASS")
        self.assertEqual(sandbox_leakage_probe(environment={"PATH":"/usr/bin"},discovered_paths=["src/ovc/development/skills"])["status"],"PASS")
        self.assertEqual(sandbox_leakage_probe(environment={"PATH":"/usr/bin","OVC_VALIDATION_ROOT":"hidden"},discovered_paths=[])["status"],"BLOCK")
        self.assertEqual(sandbox_leakage_probe(environment={"PATH":"/usr/bin"},discovered_paths=["validation/private"])["status"],"BLOCK")
    def test_tool_broker_inactive_default_and_test_mode_no_side_effect(self):
        env=envelope(); req=build_tool_request(action="READ_FILE",path="src/ovc/development/skills/security.py"); self.assertEqual(LocalToolBroker().dispatch(envelope=env,request=req)["status"],"DENY"); test=LocalToolBroker(test_mode=True).dispatch(envelope=env,request=req); self.assertEqual(test["status"],"PASS"); self.assertFalse(test["side_effect_performed"])
        write_env=envelope(write_authority_active=True); write=LocalToolBroker(test_mode=True).dispatch(envelope=write_env,request=build_tool_request(action="WRITE_FILE",path="src/ovc/development/skills/x.py",semantic_owner="DSAI")); self.assertEqual(write["status"],"DENY"); self.assertEqual(write["reason"],"WP5_WRITE_ADAPTER_INACTIVE")
    def test_s3_s4_containment_is_synchronous(self):
        for level in ("S3","S4"): row=security_containment(severity=level); self.assertTrue(row["privileged_actions_denied"]); self.assertTrue(row["terminate_sandbox"])
        self.assertFalse(security_containment(severity="S1")["terminate_sandbox"])
    def test_security_schemas_closed(self):
        for name in ("execution_security_envelope_v0_1.schema.json","tool_request_v0_1.schema.json","security_decision_record_v0_1.schema.json","security_profile_registry_v0_1.schema.json"):
            schema=json.loads((ROOT/"schemas/development/skills"/name).read_text()); self.assertEqual(schema["$schema"],"https://json-schema.org/draft/2020-12/schema"); self.assertEqual(schema["type"],"object"); self.assertFalse(schema["additionalProperties"])
        validate_against_schema(envelope(),json.loads((ROOT/"schemas/development/skills/execution_security_envelope_v0_1.schema.json").read_text()))
if __name__=="__main__": unittest.main()
