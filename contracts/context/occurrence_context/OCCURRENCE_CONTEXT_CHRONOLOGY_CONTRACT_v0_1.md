# OccurrenceContext Chronology Contract v0.1

For every context record:

`context_first_valid_time = max(anchor_first_valid_time, all populated dependency first_valid_times, all required registry availability/effectivity times, own_derivation_confirmation_time)`.

Occurrence/effective start, session start, episode birth and other onset coordinates never backdate causal availability. A registry revision may be used only at/after its own governed availability; rebuilding an older occurrence with a newer registry creates a successor context record.

A populated dependency with first-valid time after a proposed context first-valid time MUST fail with `OC_TIME_BACKDATE_DENIED`. Missing required chronology produces `NOT_EVALUABLE` or stronger. Retrospective classifications must be explicitly marked and are forbidden from causal representation/event use under the base pack.

C2E elapsed duration/count/phase fields require a lawful first-valid C2E anchor/snapshot. Censoring must never be relabelled completion.