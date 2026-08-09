# SRFDI-WP10 Execution Resilience Packet v0.1

Programme: `OVC-SRFD-BENCHMARK-v0.1`  
Resolution path: steps **2, 3 and 4** of the operator instruction `OVC Run the path to resolution 1. 0 7.`

## Step 2 — supersede only the execution route

The failed v0.6 scientific attempt is not rewritten and its token remains consumed. This packet supersedes only the process route that required one uninterrupted host invocation. The frozen v0.4 science, 8,598 eligible records, 36 comparability domains, 35,380,668 pair opportunities, 1,944 family configurations and T0 capacity envelope are unchanged.

## Step 3 — durable checkpoint/resume

`src/ovc/opt_b/srfd/wp10_execution_resilience.py` adds:

- append-once token-consumption ledger;
- immutable `RunStartReceipt`;
- exact `RunBinding` hash;
- atomic committed checkpoint receipts;
- append-only checkpoint sequence and work-unit history;
- per-work-unit output hashes;
- deterministic resume that skips already committed units;
- fail-closed binding/corruption/sequence/history checks;
- interrupted/resumed equivalence assurance.

A temporary/uncommitted checkpoint has no authority. The first uncommitted unit may be recomputed inside the same run; a committed unit may not be silently replaced.

## Step 4 — run-scoped authority

The authority model is changed from “one token must survive one process” to:

`one fresh token -> one immutable run_id -> zero or more process invocations -> verified committed checkpoints -> one completion`.

The token is consumed exactly once at run start. Later invocations do not reuse the token; they continue the same run using the immutable start receipt plus the latest verified checkpoint.

## Production granularity

The minimum family-grid checkpoint unit is one family configuration within one comparability domain. This is computational decomposition only. It cannot sample or change any representation, distance, family method, threshold, sensitivity, population or scientific decision rule.

## Authority boundary

Fresh June execution is still denied by this packet. A new exact `SRFDI-G-JUNE-AUTH v0.7` must bind the merged implementation and frozen inputs before WP10 may start.

Provider fetch remains denied. Validation remains locked/unconsumed. No method/family/representation/semantic promotion, selector mutation, publication, probability, risk, exposure, trading or execution authority is created.
