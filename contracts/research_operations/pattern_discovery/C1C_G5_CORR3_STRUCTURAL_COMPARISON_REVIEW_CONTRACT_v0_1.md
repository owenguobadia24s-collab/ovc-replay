# C1C-G5-CORR3 Structural Comparison Review Contract v0.1

## 1. Authority

This contract implements the operator decision:

`OVC APPROVE C1C-G5-CORRECTIVE-PILOT-REVIEW DEFER`

recorded after the signed C1C-G5-CORR2 return. It authorises only packet `C1C-G5-CORR3` and returns to `C1C-G5-CORRECTIVE-PILOT-REVIEW`.

The exact remaining object is:

`PDPILOT-CANDIDATE-bab63b935155e4d9033aed81`

The prior finding is:

`PD-DEFER-CORR2-STRUCTURAL-COMPARISON-INCOMPLETE-001`

No second machine replay is required or authorised.

## 2. Purpose

CORR3 exposes existing preserved-artifact facts needed to review the one remaining deferred pilot object:

1. the exact assigned medoid fingerprint;
2. the frozen composite-distance domain components and weighted contributions;
3. the recorded and independently recomputed total distance;
4. the cluster p90 outlier threshold and classification consistency;
5. exact-window duplication, dedup-key and same-scope overlap status;
6. comparison availability;
7. the existing `LONG_PERSISTENCE` trigger derivation and the distinction between pre-window trigger history and post-trigger candidate-window fingerprint duration.

This is a read-only explanation and verification packet. It does not choose a new medoid, rebuild a cluster, change a distance pack, change a trigger threshold or alter the machine run.

## 3. Exact source artifacts

The runner reads only the immutable corrective pilot root for:

- `derived/candidates.jsonl`;
- `derived/fingerprints.jsonl`;
- `derived/cluster-versions.jsonl`;
- `derived/trigger-events.jsonl`;
- `review/console-bundle.json`;
- the signed structured-review-v2 evidence;
- the signed CORR2 review receipt and evidence inventory;
- the CORR2 closure ledger and final gate input.

Every returned CORR2 file is bound by its exact SHA-256 in `C1C_G5_CORR3_AUTHORITY_BINDING.json`. The signed receipt and inventory must verify against operator `OVC.OPERATOR.PRIMARY.LOCAL.V1` and signing binding `RPS.SIGNING.50092c28981fef08f53a6cb5`.

## 4. Deterministic comparison rule

The target fingerprint must resolve to exactly one `ClusterVersion` assignment in its exact structural partition. The assigned medoid must resolve to exactly one preserved fingerprint in the same partition.

The runner rebuilds only the deterministic scale statistics from the exact preserved partition population and calls the already-frozen `PD.DISTANCE.v0.1` implementation. It must prove:

- cluster input count and input-set hash match the preserved partition population;
- distance-pack ID matches `PD.DISTANCE.v0.1`;
- rebuilt scale-pack ID matches the preserved `ClusterVersion`;
- recomputed total distance equals the recorded assignment distance to 1e-12;
- weighted domain contributions sum to the same total to 1e-12;
- outlier-list membership equals the deterministic rule `distance > outlier_threshold_p90`.

Any mismatch fails closed. CORR3 cannot repair or reinterpret it.

## 5. Duplicate and overlap status

Duplicate and overlap presentation is descriptive only.

- Candidate identity must occur exactly once.
- Fingerprint identity must occur exactly once.
- Exact-window peers use instrument, side, clock, scope, window start and window end.
- Dedup-key peers use the preserved `candidate_dedup_key`.
- Overlap peers use strict interval overlap within the same instrument, side, clock and scope.

Overlap does not imply duplication, invalidity or semantic similarity. No candidate is merged, suppressed, removed or relabelled.

## 6. LONG_PERSISTENCE derivation

`TR-PER-001` is frozen as `LONG_PERSISTENCE`. The implementation fires on the first closed C2 record where the trailing equal-state run reaches the frozen default threshold of four records.

That trigger is evaluated from C2 history through `trigger_first_valid_at` before the candidate window opens. The fingerprint fields `duration_records` and `max_persistence` describe the candidate window after it opens. They are different scopes and are not required to equal the trigger-history run length.

CORR3 documents this existing derivation only. It cannot change the trigger registry, threshold, evaluator, first-valid rule or closure profile.

## 7. Operator review

`prepare` generates an append-only `corr3-prepared` directory containing:

- the structural comparison context;
- an enriched read-only Console bundle;
- a one-object review template.

The only permitted final dispositions are:

- `WORKFLOW_ACCEPTED`;
- `DEFER_PILOT_OBJECT`;
- `REJECT_PILOT_OBJECT`.

A changed, second, duplicate or missing candidate fails closed. Finalisation requires the existing operator Ed25519 key and is prohibited in CI.

## 8. Preservation

The CORR2 rejection of `PDPILOT-CANDIDATE-4f41e21b6cd075e0fdbc40e4` is immutable under CORR3. The four non-deferred structured-v2 decisions remain bound by their canonical hash. All signed v1, v2 and CORR2 evidence remains preserved.

## 9. Authority retained

The following remain denied or absent:

- machine replay and provider intake;
- trigger, distance-pack, clustering, threshold or model change;
- canonical Discovery processing or append;
- semantic, family, candidate or novelty promotion;
- selector or release mutation;
- R2 publication;
- Validation consumption;
- probability, risk, exposure, trading, execution or agent-write authority.

Every CORR3 output remains `PILOT_ONLY` and `NON_PROMOTABLE`.

## 10. Final gate

Finalisation produces a signed receipt, closure ledger, signed evidence inventory and final gate input. A `PASS` recommendation is possible only when the remaining object is no longer deferred and every identity, hash, signature, comparison and preservation check passes.

The final decision remains operator-reserved: `PASS`, `DEFER`, `BLOCK`, `QUARANTINE` or `SUPERSEDE`.

## 11. Rollback

Revert CORR3 code, schemas, tests and repository court records through a new non-destructive commit. Preserve the immutable machine run, all prepared or signed external artifacts and every earlier decision. Never delete, rewrite, relabel, append, publish or promote a pilot object as rollback.
