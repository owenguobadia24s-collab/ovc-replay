# OVC Paper-Playbook Gate Contract v0.1

**Contract ID:** `PAPER-PLAYBOOK-GATE-0.1`  
**Scope:** authority gate after untouched OPT-D validation and robustness review  
**Live execution authority:** `NONE`

## Decisions

- `PASS`: the frozen hypothesis may be translated into a separately reviewed, non-live paper-playbook specification.
- `DEFER`: evidence is evaluable only after more data or a preregistered robustness question is resolved.
- `BLOCK`: a ratified failure condition or integrity failure prohibits paper-playbook translation.

## Mandatory checks

A hypothesis can receive `PASS` only when all of the following hold:

1. definition and lineage integrity pass;
2. strict complete-path censoring handling passes;
3. antecedent coverage is evaluable;
4. the exact frozen story structurally reappears;
5. no preregistered counter-story alert is present; and
6. reappearance survives every leave-one-calendar-month-out deletion.

Definition drift, censoring-rule failure, structural non-reappearance or a counter-story alert is a `BLOCK`. Insufficient antecedent coverage or otherwise clean but month-sensitive recurrence is a `DEFER`.

The robustness condition is one-way conservative: it can defer a candidate that otherwise clears untouched validation, but it cannot rescue a candidate that failed a frozen condition.

## Authority boundary

`PASS` does not itself create a playbook, trading signal or order authority. A later paper-playbook document must separately specify triggers, invalidation, observation timing, costs, risk limits and abort conditions. No live execution is authorized by this gate.
