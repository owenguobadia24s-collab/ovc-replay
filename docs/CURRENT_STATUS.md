# Current status

Snapshot date: 2026-07-19.

## Authority chain

| Boundary | Authority | Important limitation |
| --- | --- | --- |
| OPT-A discovery | `OPT-A.GBPUSD.2026H1.v1` | Research data only |
| OPT-A validation | `OPT-A.GBPUSD.2025.v1` | 2025 is now consumed evidence |
| OPT-B relevance | `B-REF-0.2-STRUCTURAL-ONLY` | No time-to-live retirement |
| OPT-B state | `B-STATE-0.3b-FRONTIER-ACTIVE-RESEARCH` | Descriptive state only |
| OPT-C outcomes | `OPT-C-MEASURE-0.1.1` | 1–12h measured; 24h coverage-only; 48h blocked |
| OPT-D review | `OPT-D-REVIEW-0.1` | Frozen descriptive hypotheses |
| OPT-D validation | `OPT-D-VALIDATE-0.1` | Untouched validation completed on 2025 |
| Robustness | `OPT-D-ROBUSTNESS-0.1` | Review complete; blockers retained |
| Paper playbook | `PAPER-PLAYBOOK-GATE-0.1` | 0 pass, 0 defer, 202 block |

## What changed semantically

The original persistent acceptance state occupied most bars. `B-STATE-0.3`
split state into parallel axes, `0.3a` moved maintained acceptance into a
numeric relation inventory, and ratified `0.3b` made outward accepted-frontier
advances the primary acceptance event. This prevents acceptance from suppressing
displacement, compression, interaction, or quality evidence.

## What is complete

- Strict no-fill provider ingestion and sealed authority releases.
- Reference-level construction, structural retirement, and seven OPT-B terms.
- Ratified parallel-axis/frontier state representation.
- Strict forward-path coverage, censoring, and neutral measurement.
- Semantic sanity checks and overlap-aware cohorts.
- Cluster-balanced contrasts, repeated stories, and evidence review.
- Frozen 2025 holdout validation and robustness review.

## Next research gate

`OPT-D-REFINE-0.2` is the next valid build. It should analyze the 202 blocked
candidates, distinguish structural failure from support/concentration failure,
write new hypotheses without retroactively changing 2025 outcomes, and reserve
a genuinely new validation period before reopening the paper gate.

Execution authority remains `NONE`.
