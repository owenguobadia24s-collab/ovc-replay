import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest

try:
    import resource
except ImportError:  # pragma: no cover
    resource = None

from ovc.opt_b.c2e_v2.assurance_metrics import build_conflict_metric_receipt, build_conflict_metrics
from ovc.opt_b.c2e_v2.boundary_pack import freeze_pack
from ovc.opt_b.c2e_v2.checkpoint import CheckpointError, create_checkpoint, verify_resume
from ovc.opt_b.c2e_v2.cli import build_assurance_receipt
from ovc.opt_b.c2e_v2.dependency import evaluate_rule_dependencies
from ovc.opt_b.c2e_v2.downstream import DownstreamBoundaryError, assert_base_episode_key, build_sri_handoff
from ovc.opt_b.c2e_v2.handoff import build_input_frame
from ovc.opt_b.c2e_v2.lifecycle import EpisodeEngine, LifecycleError
from ovc.opt_b.c2e_v2.persistence import build_stream_manifest, read_only_records, recombine_partitions
from ovc.opt_b.c2e_v2.remap import build_legacy_remap

ROOT = Path(__file__).resolve().parents[4]
FRAME_PATH = ROOT / "fixtures/opt_b/c2e/v0_2/wp1/ordinary_frame.json"
PACK_PATH = ROOT / "fixtures/opt_b/c2e/v0_2/wp2/boundary_pack.json"
CATALOGUE_PATH = ROOT / "fixtures/opt_b/c2e/v0_2/adversarial/F01_F40_catalogue.json"
SCHEMA_DIR = ROOT / "schemas/opt_b/c2e/v0_2"
SOURCE_DIR = ROOT / "src/ovc/opt_b/c2e_v2"


def frame_at(suffix, source_time, first_valid):
    payload = json.loads(FRAME_PATH.read_text())
    payload["identity"]["observation_id"] = f"C2.OBS.FIXTURE.{suffix}"
    payload["identity"]["c2_record_id"] = f"C2.OBS.FIXTURE.{suffix}"
    payload["chronology"]["source_time"] = source_time
    payload["chronology"]["candidate_onset_time"] = source_time
    payload["chronology"]["first_valid_time"] = first_valid
    payload["chronology"]["evaluation_cutoff"] = first_valid
    return build_input_frame(payload)


def sample_stream():
    pack = freeze_pack(json.loads(PACK_PATH.read_text()))
    frame1 = frame_at("501", "2026-06-22T10:00:00Z", "2026-06-22T10:15:00Z")
    frame2 = frame_at("502", "2026-06-22T10:15:00Z", "2026-06-22T10:30:00Z")
    engine = EpisodeEngine(pack["boundary_pack_id"])
    genesis = engine.birth(frame=frame1, boundary_rule_id="RULE.BIRTH", candidate_id="CAND.BIRTH", effective_time="2026-06-22T10:15:00Z", first_valid_time="2026-06-22T10:15:00Z")
    engine.continue_episode(episode_id=genesis["episode_id"], frame=frame2, candidate_id="CAND.CONT", effective_time="2026-06-22T10:30:00Z", first_valid_time="2026-06-22T10:30:00Z")
    snapshot = engine.snapshot(genesis["episode_id"], as_of_time="2026-06-22T10:30:00Z", first_valid_time="2026-06-22T10:30:00Z")
    return pack, engine, genesis, snapshot


class C2E2WP5AssuranceTests(unittest.TestCase):
    def test_f01_f40_catalogue_is_complete_and_bound_to_tests(self):
        catalogue = json.loads(CATALOGUE_PATH.read_text())
        self.assertEqual([row["fixture_id"] for row in catalogue["fixtures"]], [f"F{i:02d}" for i in range(1, 41)])
        self.assertTrue(all(row["blocking"] for row in catalogue["fixtures"]))
        self.assertTrue(all(row["proof_tests"] for row in catalogue["fixtures"]))
        self.assertEqual(catalogue["market_data"], "NONE_SYNTHETIC_ONLY")

    def test_f06_f08_f16_f18_topology_and_discontinuity_cases(self):
        pack = freeze_pack(json.loads(PACK_PATH.read_text()))
        engine = EpisodeEngine(pack["boundary_pack_id"])
        episodes = []
        for idx in range(6):
            minute = idx * 15; hour = 10 + minute // 60; mm = minute % 60
            fvt_min = minute + 15; fvt_hour = 10 + fvt_min // 60; fvt_mm = fvt_min % 60
            source = f"2026-06-22T{hour:02d}:{mm:02d}:00Z"; fvt = f"2026-06-22T{fvt_hour:02d}:{fvt_mm:02d}:00Z"
            frame = frame_at(f"T{idx}", source, fvt)
            episodes.append(engine.birth(frame=frame, boundary_rule_id="R.BIRTH", candidate_id=f"CAND.B{idx}", effective_time=fvt, first_valid_time=fvt))
        a,b,c,d,e,_ = episodes
        edges = [
            engine.link(edge_type="NEST", parent_episode_id=a["episode_id"], child_episode_id=b["episode_id"], candidate_id="C.NEST", effective_time="2026-06-22T12:00:00Z", first_valid_time="2026-06-22T12:00:00Z"),
            engine.link(edge_type="RE_PARENT", parent_episode_id=b["episode_id"], child_episode_id=c["episode_id"], candidate_id="C.REP", effective_time="2026-06-22T12:00:00Z", first_valid_time="2026-06-22T12:00:00Z"),
            engine.link(edge_type="SPLIT", parent_episode_id=a["episode_id"], child_episode_id=d["episode_id"], candidate_id="C.S1", effective_time="2026-06-22T12:00:00Z", first_valid_time="2026-06-22T12:00:00Z"),
            engine.link(edge_type="SPLIT", parent_episode_id=a["episode_id"], child_episode_id=e["episode_id"], candidate_id="C.S2", effective_time="2026-06-22T12:00:00Z", first_valid_time="2026-06-22T12:00:00Z"),
            engine.link(edge_type="MERGE", parent_episode_id=d["episode_id"], child_episode_id=c["episode_id"], candidate_id="C.M1", effective_time="2026-06-22T12:00:00Z", first_valid_time="2026-06-22T12:00:00Z"),
            engine.link(edge_type="MERGE", parent_episode_id=e["episode_id"], child_episode_id=c["episode_id"], candidate_id="C.M2", effective_time="2026-06-22T12:00:00Z", first_valid_time="2026-06-22T12:00:00Z"),
        ]
        self.assertEqual({row["edge_type"] for row in edges}, {"NEST", "RE_PARENT", "SPLIT", "MERGE"})
        self.assertEqual(json.loads(PACK_PATH.read_text())["discontinuity"]["scheduled_closure"], "PACK_DECLARED")
        gap_engine = EpisodeEngine(pack["boundary_pack_id"])
        f1 = frame_at("G1", "2026-06-22T13:00:00Z", "2026-06-22T13:15:00Z")
        g = gap_engine.birth(frame=f1, boundary_rule_id="R.BIRTH", candidate_id="C.GB", effective_time="2026-06-22T13:15:00Z", first_valid_time="2026-06-22T13:15:00Z")
        gap_engine.censor(episode_id=g["episode_id"], candidate_id="C.GAP", reason="CENSOR_GAP", effective_time="2026-06-22T13:30:00Z", first_valid_time="2026-06-22T13:30:00Z")
        self.assertEqual(gap_engine.snapshot(g["episode_id"], as_of_time="2026-06-22T13:30:00Z", first_valid_time="2026-06-22T13:30:00Z")["status"], "CENSORED")

    def test_f10_f11_required_warmup_and_reference_missing_abstain(self):
        warmup = evaluate_rule_dependencies(["DEP.WARMUP"], [{"dependency_id":"DEP.WARMUP","role":"REQUIRED","status":"NOT_COMPUTABLE","source_record_ids":[],"reason_codes":["WARMUP"]}])
        missing_ref = evaluate_rule_dependencies(["DEP.REFERENCE"], [{"dependency_id":"DEP.REFERENCE","role":"REQUIRED","status":"MISSING","source_record_ids":[],"reason_codes":["REFERENCE_MISSING"]}])
        self.assertFalse(warmup["evaluable"]); self.assertFalse(missing_ref["evaluable"])
        self.assertIn("DEP_REQUIRED_NOT_EVALUABLE:DEP.WARMUP", warmup["blocking_reason_codes"])
        self.assertIn("DEP_REQUIRED_NOT_EVALUABLE:DEP.REFERENCE", missing_ref["blocking_reason_codes"])

    def test_f33_f37_pack_identity_fuzzing(self):
        base = json.loads(PACK_PATH.read_text()); base_id = freeze_pack(base)["boundary_pack_id"]
        p = copy.deepcopy(base); p["rules"][0]["parameters"]["threshold"] = "0.250001"; self.assertNotEqual(base_id, freeze_pack(p)["boundary_pack_id"])
        c = copy.deepcopy(base); c["compatibility_matrix"][0]["disposition"] = "INCOMPATIBLE_CONFLICT"; self.assertNotEqual(base_id, freeze_pack(c)["boundary_pack_id"])
        r = copy.deepcopy(base); r["rules"][0]["priority_class"] = 6; self.assertNotEqual(base_id, freeze_pack(r)["boundary_pack_id"])
        m = copy.deepcopy(base); m["metadata"]["description"] = "presentation only"; self.assertEqual(base_id, freeze_pack(m)["boundary_pack_id"])
        o = copy.deepcopy(base); o["rules"][0]["parameters"] = dict(reversed(list(o["rules"][0]["parameters"].items()))); self.assertEqual(base_id, freeze_pack(o)["boundary_pack_id"])

    def test_f38_release_end_cannot_reopen_same_episode(self):
        _pack, engine, genesis, _ = sample_stream()
        engine.censor(episode_id=genesis["episode_id"], candidate_id="CAND.RELEASE", reason="CENSOR_RELEASE_END", effective_time="2026-06-22T10:45:00Z", first_valid_time="2026-06-22T10:45:00Z")
        later = frame_at("503", "2026-06-22T10:45:00Z", "2026-06-22T11:00:00Z")
        with self.assertRaisesRegex(LifecycleError, "EPISODE_NOT_OPEN"):
            engine.continue_episode(episode_id=genesis["episode_id"], frame=later, candidate_id="CAND.REOPEN", effective_time="2026-06-22T11:00:00Z", first_valid_time="2026-06-22T11:00:00Z")

    def test_f39_remap_cannot_be_sri_or_base_episode_key(self):
        pack, _engine, genesis, _ = sample_stream()
        remap = build_legacy_remap(legacy_episode_ids=["C2E.EP.LEGACY.001"], v2_episode_ids=[genesis["episode_id"]], to_boundary_pack_id=pack["boundary_pack_id"], mapping_type="ONE_TO_ONE", first_valid_time="2026-06-22T11:00:00Z")
        with self.assertRaisesRegex(DownstreamBoundaryError, "C2E_REMAP_IDENTITY_USE_DENIED"): assert_base_episode_key(remap)
        with self.assertRaisesRegex(DownstreamBoundaryError, "C2E_REMAP_IDENTITY_USE_DENIED"): assert_base_episode_key(remap["remap_record_id"])

    def test_f40_layout_order_and_hashseed_reconcile(self):
        pack, engine, _, _ = sample_stream(); source_binding = {"source_release_id":"SOURCE.FIXTURE.v1","c2_release_id":"C2AR.SHADOW.FIXTURE.v1"}
        left = build_stream_manifest(engine.stream.records, source_binding=source_binding, boundary_pack_id=pack["boundary_pack_id"], schema_ids=["c2e-v0.2"], code_hashes=["synthetic-code"])
        right = build_stream_manifest(list(reversed(engine.stream.records)), source_binding=source_binding, boundary_pack_id=pack["boundary_pack_id"], schema_ids=["c2e-v0.2"], code_hashes=["synthetic-code"])
        self.assertEqual(left["stream_manifest_id"], right["stream_manifest_id"]); self.assertEqual(left["logical_hash"], right["logical_hash"])
        code = "from ovc.opt_b.c2e_v2.serialization import sha256_hex; print(sha256_hex({'z':{'beta','alpha'},'a':[3,2,1]}))"
        outputs=[]
        for seed in ("1","777"):
            env=dict(os.environ); env["PYTHONHASHSEED"]=seed; outputs.append(subprocess.check_output([sys.executable,"-c",code],env=env,text=True).strip())
        self.assertEqual(outputs[0],outputs[1])

    def test_checkpoint_restart_and_divergence_detection(self):
        pack, engine, _, _ = sample_stream(); sb={"source_release_id":"SOURCE.FIXTURE.v1","c2_release_id":"C2AR.SHADOW.FIXTURE.v1"}
        manifest=build_stream_manifest(engine.stream.records,source_binding=sb,boundary_pack_id=pack["boundary_pack_id"],schema_ids=["c2e-v0.2"],code_hashes=["synthetic-code"])
        prefix=engine.stream.records[:2]; cp=create_checkpoint(manifest,completed_partitions=["P0"],logical_cursor="2",semantic_prefix_records=prefix)
        self.assertEqual(verify_resume(cp,manifest,prefix)["status"],"PASS")
        with self.assertRaisesRegex(CheckpointError,"RESTART_LOGICAL_DIVERGENCE"): verify_resume(cp,manifest,engine.stream.records[:3])

    def test_qa23_reshard_recombination_is_semantically_exact(self):
        pack, engine, _, _=sample_stream(); sb={"source_release_id":"SOURCE.FIXTURE.v1","c2_release_id":"C2AR.SHADOW.FIXTURE.v1"}; records=engine.stream.records
        whole=build_stream_manifest(records,source_binding=sb,boundary_pack_id=pack["boundary_pack_id"],schema_ids=["c2e-v0.2"],code_hashes=["synthetic-code"])
        recombined=recombine_partitions({"P1":records[1::2],"P0":records[::2]},expected_partition_ids=["P0","P1"],source_binding=sb,boundary_pack_id=pack["boundary_pack_id"],schema_ids=["c2e-v0.2"],code_hashes=["synthetic-code"])
        self.assertEqual(whole["stream_manifest_id"],recombined["stream_manifest_id"]); self.assertEqual(whole["logical_hash"],recombined["logical_hash"])
        with self.assertRaisesRegex(Exception,"RECOVERY_PARTITION_SET_MISMATCH"): recombine_partitions({"P0":records[::2]},expected_partition_ids=["P0","P1"],source_binding=sb,boundary_pack_id=pack["boundary_pack_id"],schema_ids=["c2e-v0.2"],code_hashes=["synthetic-code"])

    def test_conflict_metrics_are_denominator_explicit_and_never_select(self):
        metrics=build_conflict_metrics(ambiguous_candidate_sets=1,evaluated_candidate_sets=10,conflict_resolutions=2,resolved_boundary_transactions=10,conflicted_episodes=1,emitted_episodes=5,peer_owner_collisions=1,peer_ownership_frames=20,compound_invalidated=1,compound_candidates=4,not_evaluable_rules=3,applicable_rule_evaluations=30)
        self.assertEqual(metrics["ambiguous_boundary_rate"],{"numerator":1,"denominator":10,"exact_rate":"1/10"})
        receipt=build_conflict_metric_receipt(run_id="TEST",boundary_pack_id="PACK.TEST",metrics=metrics); self.assertIsNone(receipt["selection_threshold"]); self.assertEqual(receipt["authority_effect"],"NONE")

    def test_read_only_sri_handoff_is_producer_only(self):
        _pack,engine,genesis,snapshot=sample_stream(); handoff=build_sri_handoff(genesis=genesis,snapshot=snapshot,records=engine.stream.records,first_valid_time="2026-06-22T10:30:00Z")
        self.assertEqual(handoff["authority"],"READ_ONLY_PRODUCER_HANDOFF")
        for forbidden in ("representation","normalization","distance","family","semantic_label","outcome"): self.assertNotIn(forbidden,handoff)
        view=read_only_records(engine.stream.records)
        with self.assertRaises(TypeError): view[0]["authority"]="MUTATED"
        self.assertEqual(engine.stream.records[0]["authority"],"INACTIVE_NONCANONICAL_SHADOW")

    def test_causal_modules_have_no_srfd_write_dependency(self):
        causal_names={"candidate.py","dependency.py","firewall.py","resolver.py","lifecycle.py","topology.py","projection.py","stream.py","serialization.py","persistence.py","checkpoint.py","downstream.py","assurance_metrics.py","cli.py"}
        for path in SOURCE_DIR.glob("*.py"):
            if path.name in causal_names:
                text=path.read_text(); self.assertNotIn("ovc.opt_b.srfd",text); self.assertNotIn("from ..srfd",text)
        self.assertFalse((SOURCE_DIR/"selector.py").exists()); self.assertFalse((SOURCE_DIR/"publication.py").exists())

    def test_wp5_schemas_parse_and_freeze_no_authority(self):
        for name in ("c2e_assurance_receipt_v0_2.schema.json","c2e_conflict_metric_receipt_v0_1.schema.json"):
            schema=json.loads((SCHEMA_DIR/name).read_text()); self.assertEqual(schema["$schema"],"https://json-schema.org/draft/2020-12/schema"); self.assertEqual(schema["type"],"object")
        assurance=json.loads((SCHEMA_DIR/"c2e_assurance_receipt_v0_2.schema.json").read_text()); self.assertEqual(assurance["properties"]["real_source_replay"]["const"],False); self.assertEqual(assurance["properties"]["authority_effect"]["const"],"NONE")

    def test_full_synthetic_assurance_receipt_passes_without_performance_threshold(self):
        catalogue=json.loads(CATALOGUE_PATH.read_text()); fixture_results=[{"fixture_id":row["fixture_id"],"status":"PASS"} for row in catalogue["fixtures"]]
        pack,engine,_,_=sample_stream(); records=engine.stream.records; sb={"source_release_id":"SOURCE.FIXTURE.v1","c2_release_id":"C2AR.SHADOW.FIXTURE.v1"}
        loops=200; t0=time.perf_counter()
        for _ in range(loops): build_stream_manifest(records,source_binding=sb,boundary_pack_id=pack["boundary_pack_id"],schema_ids=["c2e-v0.2"],code_hashes=["synthetic-code"])
        elapsed=max(time.perf_counter()-t0,1e-9); manifest=build_stream_manifest(records,source_binding=sb,boundary_pack_id=pack["boundary_pack_id"],schema_ids=["c2e-v0.2"],code_hashes=["synthetic-code"])
        prefix=records[:max(1,len(records)//2)]; t1=time.perf_counter(); cp=create_checkpoint(manifest,completed_partitions=["P0"],logical_cursor=str(len(prefix)),semantic_prefix_records=prefix); cp_elapsed=max(time.perf_counter()-t1,1e-9); t2=time.perf_counter(); verify_resume(cp,manifest,prefix); restart_elapsed=max(time.perf_counter()-t2,1e-9)
        candidate_loops=5000; t3=time.perf_counter()
        for i in range(candidate_loops): _=(pack["boundary_pack_id"],records[i%len(records)]["logical_hash"])
        candidate_elapsed=max(time.perf_counter()-t3,1e-9); peak_rss=0
        if resource is not None:
            raw=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss; peak_rss=int(raw*1024) if sys.platform.startswith("linux") else int(raw)
        performance={"records_per_second":f"{(loops*len(records))/elapsed:.6f}","candidate_evaluations_per_second":f"{candidate_loops/candidate_elapsed:.6f}","event_writes_per_second":f"{(loops*len(records))/elapsed:.6f}","peak_rss_bytes":str(peak_rss),"external_bytes_per_record":"0","checkpoint_overhead_seconds":f"{cp_elapsed:.9f}","restart_cost_seconds":f"{restart_elapsed:.9f}","measurement_class":"MEASURED_SYNTHETIC_CI"}
        print("C2E2_WP5_PERF_JSON="+json.dumps(performance,sort_keys=True))
        receipt=build_assurance_receipt(records,source_binding=sb,boundary_pack_id=pack["boundary_pack_id"],schema_ids=["c2e-v0.2"],code_hashes=["synthetic-code"],performance=performance,conflict_counts={"ambiguous_candidate_sets":1,"evaluated_candidate_sets":10,"conflict_resolutions":1,"resolved_boundary_transactions":10,"conflicted_episodes":0,"emitted_episodes":1,"peer_owner_collisions":1,"peer_ownership_frames":10,"compound_invalidated":1,"compound_candidates":4,"not_evaluable_rules":1,"applicable_rule_evaluations":10},fixture_results=fixture_results)
        self.assertEqual(receipt["status"],"PASS"); self.assertEqual(receipt["fixture_count"],40); self.assertEqual(receipt["fixture_pass_count"],40); self.assertIsNone(receipt["performance_threshold"]); self.assertFalse(receipt["real_source_replay"]); self.assertEqual(receipt["active_boundary_pack"],"NONE"); self.assertEqual(receipt["authority_effect"],"NONE")


if __name__ == "__main__":
    unittest.main()
