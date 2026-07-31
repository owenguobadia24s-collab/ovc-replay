# PD-JUNE-MDR-CORR2 Post-Unblinding Comparison

- Frozen response SHA-256: `1fb60b05b0a85cc95074bb2867b67f1debbdd2310ca5e98a3af2ba0b934e9a8d`
- Bounded result: `DEFER_OR_BLOCK_EXACT_JUNE_CONTROLLED_REPEAT_REVIEW`
- General reliability: `NOT_ESTABLISHED_SINGLE_GAPPED_JUNE_SLICE`

## Metrics

- `card_count`: 16
- `control_count`: 10
- `control_determinate_count`: 4
- `control_true_negative_count`: 4
- `control_false_positive_count`: 0
- `promoted_count`: 6
- `promoted_determinate_count`: 4
- `promoted_trigger_detected_count`: 4
- `promoted_exact_reason_agreement_count`: 3
- `promoted_structural_contradiction_count`: 0
- `prior_repeat_disposition_agreement_count`: 0
- `prior_repeat_disposition_count`: 6
- `prior_repeat_disposition_kappa`: -0.125

## Acceptance

- `all_cards_completed`: PASS
- `at_least_8_determinate_controls`: FAIL
- `no_control_false_positives`: PASS
- `at_least_5_promoted_triggers_detected`: FAIL
- `at_least_4_exact_trigger_reasons`: FAIL
- `no_promoted_structural_contradictions`: PASS
- `at_least_4_of_6_disposition_agreement`: FAIL
- `disposition_kappa_at_least_0_40`: FAIL

## Card comparison

| Card | Class | Expected trigger | Review trigger | Trigger match | Prior disposition | Review disposition | Disposition match |
|---|---|---|---|---:|---|---|---:|
| 001 | NEGATIVE_CONTROL | NO_TRIGGER | INSUFFICIENT_EVIDENCE | No | — | DEFER_PILOT_OBJECT | — |
| 002 | NEGATIVE_CONTROL | NO_TRIGGER | NO_TRIGGER | Yes | — | WORKFLOW_ACCEPTED | — |
| 003 | PROMOTED_CANDIDATE | LONG_PERSISTENCE | INSUFFICIENT_EVIDENCE | No | WORKFLOW_ACCEPTED | DEFER_PILOT_OBJECT | No |
| 004 | NEGATIVE_CONTROL | NO_TRIGGER | INSUFFICIENT_EVIDENCE | No | — | DEFER_PILOT_OBJECT | — |
| 005 | PROMOTED_CANDIDATE | LONG_PERSISTENCE | INSUFFICIENT_EVIDENCE | No | WORKFLOW_ACCEPTED | DEFER_PILOT_OBJECT | No |
| 006 | NEGATIVE_CONTROL | NO_TRIGGER | NO_TRIGGER | Yes | — | WORKFLOW_ACCEPTED | — |
| 007 | PROMOTED_CANDIDATE | BREACH_ACTIVE | BREACH_ACTIVE | Yes | REJECT_PILOT_OBJECT | DEFER_PILOT_OBJECT | No |
| 008 | NEGATIVE_CONTROL | NO_TRIGGER | INSUFFICIENT_EVIDENCE | No | — | DEFER_PILOT_OBJECT | — |
| 009 | NEGATIVE_CONTROL | NO_TRIGGER | NO_TRIGGER | Yes | — | WORKFLOW_ACCEPTED | — |
| 010 | NEGATIVE_CONTROL | NO_TRIGGER | INSUFFICIENT_EVIDENCE | No | — | DEFER_PILOT_OBJECT | — |
| 011 | PROMOTED_CANDIDATE | BREACH_ACTIVE | BREACH_ACTIVE | Yes | WORKFLOW_ACCEPTED | DEFER_PILOT_OBJECT | No |
| 012 | NEGATIVE_CONTROL | NO_TRIGGER | INSUFFICIENT_EVIDENCE | No | — | DEFER_PILOT_OBJECT | — |
| 013 | NEGATIVE_CONTROL | NO_TRIGGER | NO_TRIGGER | Yes | — | WORKFLOW_ACCEPTED | — |
| 014 | PROMOTED_CANDIDATE | LONG_PERSISTENCE | BREACH_ACTIVE | No | REJECT_PILOT_OBJECT | WORKFLOW_ACCEPTED | No |
| 015 | NEGATIVE_CONTROL | NO_TRIGGER | INSUFFICIENT_EVIDENCE | No | — | DEFER_PILOT_OBJECT | — |
| 016 | PROMOTED_CANDIDATE | BREACH_ACTIVE | BREACH_ACTIVE | Yes | WORKFLOW_ACCEPTED | DEFER_PILOT_OBJECT | No |
