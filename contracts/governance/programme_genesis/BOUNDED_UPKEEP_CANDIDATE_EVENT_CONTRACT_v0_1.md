# Programme Genesis Bounded Upkeep Candidate-Event Contract v0.1

## Authority

This contract implements the disabled `PG-WP6` candidate-event collector authorised by the accepted `PG-G6` decision. It does not activate automatic upkeep. Activation remains operator-required at `PG-G7`.

The current authority is limited to deterministic validation, in-memory preview, schemas, registries, tests, QA and gate preparation. Repository writes by the collector remain disabled.

## Purpose

The collector converts an explicit, source-linked programme-health or synchronisation finding into an unapproved candidate event for later human-governed review. A candidate event is evidence that a material change may need recording. It is not a programme event, decision, correction, approval or authority grant.

## Candidate invariants

Every candidate event must:

- refer to an already known programme identity;
- bind a source path and SHA-256;
- carry an explicit finding identity and first-valid time;
- use an allowlisted candidate event type;
- have deterministic identity independent of runtime ordering;
- use status `CANDIDATE_UNAPPROVED`;
- use `authority_effect: NONE`;
- target only a dedicated branch beginning `upkeep/pg-candidate-events/`;
- remain below the configured per-run limit;
- preserve all source uncertainty and never repair programme-owned state.

## Permanent prohibitions

The collector cannot:

- create or admit a programme;
- create an accepted Programme Event;
- approve, ratify, merge, publish or write `main`;
- alter programme-owned state;
- infer authority, acceptance or completion;
- activate admission enforcement or the Control Plane route;
- change market data, formulas, thresholds, selectors, models, semantics, releases or Validation state;
- grant agent-write, probability, risk, exposure, trading or execution authority.

Candidate payloads containing decision, approval, authority-grant, merge, publication, programme-creation, selector, risk or execution fields fail closed.

## Disabled-state behaviour

Before `PG-G7=PASS`:

- deterministic preview is permitted;
- persistence is denied;
- the registry must have `enabled: false`;
- no activation decision may be present;
- attempts to persist a candidate raise a blocking error before any file is created.

Code availability, passing tests and a merged disabled implementation do not grant upkeep authority.

## Future activation boundary

A future `PG-G7` PASS may authorise append-only candidate files only on a dedicated candidate branch. Even after activation, the collector may not create programmes, approve candidates, merge pull requests or write `main`. Every candidate remains unapproved until a separate accepted human decision converts it into a lawful Programme Event.

## Rollback

Disable the registry, discard preview outputs and stop candidate generation. Preserve source findings, candidate hashes, tests, gate packets and decisions. Never delete or rewrite accepted programme records.
