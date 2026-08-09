# IROF Capacity and Telemetry Contract v0.1

Status: INACTIVE RESOURCE CONTROL / OBSERVABILITY. Scientific effect: NONE.

## Separation

Capacity governs *how* an unchanged experiment is scheduled and whether current resources can complete it. Telemetry records measured execution facts. Neither may change what is being tested.

A capacity decision is bound to an immutable ExperimentIdentity containing semantic run, population, profile, stage-spec and pack identities. `CAPACITY_EXCEEDED` preserves that identity exactly and has `scientific_effect=NONE`.

## Permitted recovery

Only operational recovery is permitted: reduce workers, serialize, resume later, move physical storage, or retry the same experiment. Sampling the population, dropping methods/configurations, reducing a scientific grid, changing thresholds/denominators/packs or substituting a profile is prohibited.

## Scheduling

The generic scheduler may select only DAG-ready stages whose declared parents are complete. Worker limits affect scheduling order/concurrency only and cannot enter semantic output hashes.

## Telemetry

Every metric has typed availability. Minimum metric IDs cover wall time, CPU/core-seconds, peak RSS, workers, bytes read/written, persistent/temp bytes, object/pair/tile/configuration counts, throughput, cache hit/miss counts and restart count. Warnings/reasons and capacity status accompany the receipt.

Unavailable measurements remain explicitly UNAVAILABLE; they are never fabricated. Metrics and machine/environment observations are execution evidence and cannot change scientific output identity.

## Source relationship

IROF reuses patterns from SRFD environment/IO profiling and resource contracts without rewriting SRFD method/configuration completeness rules. SRFD-specific science remains inside SRFD.

## Rollback

Fall back to serial/default resource execution under the same experiment identity and source adapters.
