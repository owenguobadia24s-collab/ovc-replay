from ovc.research_operations.bcwt.task_invariant import task_invariant_preserved, task_organisational_signature


def state(*, family="LOCAL_BELOW", phase="SYNC", z="NOT_ESTABLISHED", candidates=None, source_break=False):
    if candidates is None:
        candidates = []
    return {"components": {
        "E_t": {"source_break": source_break},
        "Gamma_t": {"status": "AVAILABLE", "current_family": family, "relation": {"current": {"code": "LOCAL:DOWN", "layer": "LOCAL", "polarity": "DOWN"}}},
        "Z_t": {"status": z, "masking_regime": "LOCAL", "regime": "R", "current_masking_family": "LOCAL_BELOW", "initial_concealer_family": "LOCAL_BELOW"},
        "S_t": {"status": "AVAILABLE", "candidates": candidates},
        "Phi_t": {"status": "AVAILABLE", "phase_t": phase, "coupling": {"status": "EVALUABLE", "handover_ready": True}},
    }}


def test_exact_same_preserved():
    assert task_invariant_preserved(state(), state())["state"] == "PRESERVED"


def test_family_change_reconfigures():
    assert task_invariant_preserved(state(), state(family="LOCAL_ABOVE"))["state"] == "RECONFIGURED"


def test_track_identity_and_age_are_ignored():
    c1 = {"side":"BELOW","stage":"REACHABLE","dominance_state":"DOMINANT","H4_overlap":True,"H8_overlap":False,"support_depth":8,"expiry_critical":False,"track_id":"a","track_age":1,"seq":3}
    c2 = {**c1, "track_id":"b", "track_age":99, "seq":999}
    assert task_invariant_preserved(state(candidates=[c1]), state(candidates=[c2]))["state"] == "PRESERVED"


def test_candidate_semantic_change_reconfigures():
    c1 = {"side":"BELOW","stage":"REACHABLE","dominance_state":"DOMINANT","H4_overlap":True,"H8_overlap":False,"support_depth":8,"expiry_critical":False}
    c2 = {**c1, "stage":"REMOTE_SUPPORT_ONLY"}
    assert task_invariant_preserved(state(candidates=[c1]), state(candidates=[c2]))["state"] == "RECONFIGURED"


def test_source_break_censors():
    assert task_invariant_preserved(state(), state(source_break=True))["state"] == "CENSORED"


def test_uncomparable_fails_closed():
    b = state(); b["components"]["Gamma_t"]["status"] = "NOT_EVALUABLE"
    assert task_invariant_preserved(state(), b)["state"] == "NOT_EVALUABLE"


def test_not_established_z_is_explicit_comparable_absence():
    status, _ = task_organisational_signature(state(z="NOT_ESTABLISHED"))
    assert status == "EVALUABLE"


def test_available_z_semantic_change_reconfigures():
    a = state(z="AVAILABLE"); b = state(z="AVAILABLE"); b["components"]["Z_t"]["regime"] = "OTHER"
    assert task_invariant_preserved(a, b)["state"] == "RECONFIGURED"
