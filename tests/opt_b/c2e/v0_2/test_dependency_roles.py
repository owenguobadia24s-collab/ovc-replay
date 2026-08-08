from ovc.opt_b.c2e_v2.dependency import evaluate_rule_dependencies


def test_dependency_failure_is_selective():
    results = [
        {"dependency_id":"DEP.LOCAL","role":"REQUIRED","status":"COMPUTABLE","source_record_ids":["LOC.1"],"reason_codes":[]},
        {"dependency_id":"DEP.PARENT","role":"OPTIONAL","status":"NOT_COMPUTABLE","source_record_ids":[],"reason_codes":["AVAIL_REQUIRED_PARENT_MISSING"]},
    ]
    local = evaluate_rule_dependencies(["DEP.LOCAL"], results)
    parent_relative = evaluate_rule_dependencies(["DEP.LOCAL","DEP.PARENT"], [
        results[0],
        {**results[1], "role":"REQUIRED"},
    ])
    assert local["evaluable"] is True
    assert parent_relative["evaluable"] is False
    assert parent_relative["blocking_reason_codes"] == ["DEP_REQUIRED_NOT_EVALUABLE:DEP.PARENT"]
