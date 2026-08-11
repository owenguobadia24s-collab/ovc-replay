# OVC Development Skills Governance Shadow Contract v0.1

Programme: `OVC-DSAI-v0.1`  
Packet/Gate: `DSAI-WP3 / DSAI-G3`  
Governing design: `OVC-DSA-DESIGN-SPEC-0.1-REVISED-1-RATIFIED`  
Governing plan: `OVC-DSAI-IMPLEMENTATION-PLAN-0.2`

## Authority

This packet materialises governance Skill candidates and adversarial/historical evaluation scaffolding only. All four governance Skills are `EXPERIMENTAL`, `SHADOW` and non-controlling. They have `authority_effect=NONE`, may perform no repository/programme-state writes, cannot grant authority and cannot use a Tool Broker write path. No Skill becomes `TRUSTED`.

## Candidates

- `ovc-preflight` — read-only packet/repository baseline interpretation.
- `ovc-authority-resolver` — resolve recorded authority and identify operator-reserved deltas; never grant them.
- `ovc-scope-guard` — fail closed on scope ambiguity or expansion.
- `ovc-prerequisite-resolver` — fail closed when required plans, gates or source records are missing or unsatisfied.

A correct refusal is a successful Skill behaviour. Shadow execution therefore separates `evaluation_status=PASS` from an execution `disposition=BLOCK`.

## Knowledge Packs

Governance Knowledge Packs are compiled projections of exact governing source identities. They are not new canon. Source precedence remains repository court record, ratified design, then ratified implementation plan. Missing or stale source identity must fail closed through the WP2 Knowledge Pack machinery.

## Adversarial corpus

The mandatory seed families are:

`AUTHORITY_CONFUSION`, `SCOPE_EXPANSION`, `MISSING_PREREQUISITE`, `SOURCE_PRECEDENCE`, `STALE_APPROVAL`, `VALIDATION_LEAKAGE`, `PERMISSION_ESCALATION`.

Each `AdversarialCorpusCurationRecord` records family, governing source, author/reviewer separation, curation effort, reuse lineage and independent review state. Automated seed construction does not count as independent human review. Qualification eligibility therefore remains blocked until every mandatory family has accepted independently reviewed human-curated coverage. The corpus may not shrink to evade a missing family.

## Historical replay

Historical replay evaluates whether the Skill reconstructs the governing interpretation that was lawful at the historical packet state. Operator outcome is retained only as provenance and is explicitly excluded from scoring. Outcome imitation is prohibited.

## Programme Skill Bootstrap Template

The warm-start template is proposal scaffolding only. It may name a programme, plan and initial packet, but it cannot create programme state, approve a gate or grant authority. Supplying requested authority to the builder is an error.

## Rollback

Disable/remove the shadow candidate registrations and preserve evaluation/corpus evidence. The manual development path remains controlling.
