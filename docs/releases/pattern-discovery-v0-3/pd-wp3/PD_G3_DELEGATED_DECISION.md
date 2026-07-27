# PD-G3 — Delegated Decision

## Decision

`PASS`

## Authority source

The approved OVC continuous-development plan delegates PASS decisions where the entire authority delta remains `AUTO-EXECUTABLE`, acceptance checks pass, QA recommends PASS, rollback exists and no operator-reserved capability is activated.

PD-G3 accepts only derived fingerprints, similarity computation and provisional, non-semantic cluster versions. It grants no model, family, archetype, episode, selector, release, evidence-write, probability, exposure or execution authority.

## Candidate and evidence

- Plan version: `0.3`.
- Baseline main: `ff9f8a9604d352bb37777e04282cd0641e5f38b8`.
- Branch: `build/pd-wp3-fingerprint-clustering`.
- Pull request: `#94`.
- Dedicated workflow `30264050530`: PASS.
- Canonical workflow `30264050496`: PASS.
- QA result: `PASS_PD_G3_AUTO_RATIFIABLE`.

## Accepted delta

- deterministic completed-window fingerprints;
- frozen composite distance and robust scaling;
- hard structural partitions;
- exact deterministic PAM;
- immutable provisional ClusterVersions, medoids, dispersion, outliers and lineage.

## Retained prohibitions

Live processing, active novelty ranking, semantic naming, archetype or family promotion, C2E/C3, evidence writes, selector/release/R2 mutation, Validation, probability, exposure, trading, execution and agent authority remain prohibited.

## Rollback

Revert the bounded squash merge or rebuild all derived fingerprints and cluster artifacts. Accepted upstream and canonical market/evidence authority remains unchanged.

## Next packet

Release `PD-WP4` from the post-merge main tip. PD-WP4 may implement the simple UI and evidence-bridge candidate, but actual canonical evidence-write activation remains operator-reserved.
