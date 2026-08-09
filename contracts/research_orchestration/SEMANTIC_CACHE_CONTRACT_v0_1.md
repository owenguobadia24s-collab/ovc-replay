# IROF Semantic Cache Contract v0.1

Status: INACTIVE EXECUTION OPTIMISATION. Scientific effect: NONE.

## Identity

A reusable entry is addressed only by `SemanticCacheKey`. Meaning-bearing inputs include stage/version, parent semantic hashes, contract/schema/implementation identities, pack bindings, population, chronology, comparability, context role and code identity where declared. Hostname, worker count, scheduling policy, cache counters and physical artifact location are not semantic key fields.

## Reuse rules

- exact semantic key only;
- artifact lifecycle MUST be `COMPLETE`;
- artifact owner stage and semantic-cache key MUST match;
- parent semantic hashes are immutable key material;
- content hash is verified when a deterministic observed hash is available;
- `STAGING`, `SUPERSEDED` and `QUARANTINED` artifacts are never reusable;
- corruption or duplicate-key semantic conflict is quarantined and treated as a miss;
- physical relocation with unchanged semantics/content remains reusable;
- cache hit/miss/bytes/work telemetry cannot enter scientific hashes.

`bytes_avoided` and `work_units_avoided` may be reported only when supplied by a deterministic measurement; the cache does not invent savings estimates.

## Compatibility boundary

SRFD's existing `src/ovc/opt_b/srfd/semantic_cache.py` remains untouched. IROF generalises the same exact-key and quarantine patterns without rewriting SRFD public behavior. A later source-adapter integration may wrap SRFD cache behavior only after exact compatibility assurance.

## Failure posture

A miss always falls back to lawful compute under the unchanged StageSpec and owner authority. Cache failure cannot trigger sampling, pack change, threshold change, profile degradation, source substitution or scientific status normalisation.

## Rollback

Disable/unregister the IROF cache adapter and recompute. Scientific output identity is unchanged.
