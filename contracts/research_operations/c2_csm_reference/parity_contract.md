# C2-CSM Historical Reference Parity Contract v0.1

Programme: `OVC-EML-C2S-SPTO-CONFORMANCE-PREREG-v0.1`

Parity is historical conformance evidence only. It cannot grant current C2 authority.

## Preconditions

A parity assertion may be made only for mechanics whose source-completeness state is `EXACT_IMPLEMENTATION_BOUND`. Missing or source-derived mechanics are `NOT_EVALUABLE_SOURCE_LIMITED`; they are never backfilled from output counts or downstream consumer code.

## Required parity planes

When source-complete mechanics exist, WP2/WP3 SHALL compare:

- object/lifecycle state;
- relation state;
- independent boundary-role succession;
- atomic/compound transition state;
- open compound/development state;
- structural-map snapshot identity;
- append-only succession identity;
- source-break/reset behavior;
- typed C2LIB read-surface outputs where an exact source is available.

## Determinism

Logical reference output identity MUST remain identical across clean process, worker, shard, cache, checkpoint/restart and serialization paths. Runtime/process identifiers are prohibited from logical identity.

## Historical corpus anchors

The known frozen evidence corpus is 25 cases / 2,328 bars / 408 objects, including 10 temporally disjoint holdout cases with 10/10 integrity PASS. These are necessary evidence anchors, not substitute semantic definitions.

## Allowed dispositions

- `PARITY_PASS`
- `PARITY_FAIL`
- `NOT_EVALUABLE_SOURCE_LIMITED`
- `QUARANTINED_SOURCE_CONFLICT`

WP3 independent review determines whether the overall historical port is `COMPLETE` or `PARTIAL_SOURCE_LIMITED`.
