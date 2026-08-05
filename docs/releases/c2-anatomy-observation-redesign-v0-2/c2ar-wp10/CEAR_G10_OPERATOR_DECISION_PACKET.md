# CEAR-G10 Operator Decision Packet

**Status:** `GATE_READY`  
**PR:** `#319`  
**Main baseline:** `8ff30900da9af11a2defe612fa6b1f0e86fb7a5f`  
**Pre-packet head:** `5e70d3cd50c74f3f9a1c1500f3cb0091c3698ad6`

## Recommended multipart decision

- Method: **PASS** as inactive, noncanonical shadow research method.
- Functional candidates: **PASS all 14** as inactive research candidates.
- Rule candidates: **PASS all 14** as inactive research candidates.
- Legacy mappings: **DEFER both**; no lawful vNext opportunity-ID crosswalk exists.
- Research consumers: **PASS read-only shadow research only**.

Overall recommendation: **PASS**, with both legacy mapping slots independently **DEFERRED**.

## Evidence

- Drive file: `1xffbDKFIGEK8MLNH-eh3UdhBueASHTU4`
- Size: `214,135` bytes
- Raw SHA-256: `6228282d2fc19542877e12add9d922040eac49ed345488e2dd33cedcf3cb4944`
- Internal content SHA-256: `4a21f3db44f8a6587ff863bb24fc6fe213f73ea9cf47d9d6cd69ba2e82b16fc2`
- Binding SHA-256: `126a703b89bfef8fc60a4beb1248b20b424621334c8fff254c122555e44663f8`
- Logical population SHA-256: `3f1089e3a4eefe94147c8c2f912e77899e4ed21fe8b3b8b85993e47bf7151ee7`
- Population: 33,320 requested; 27,996 computable; 1,638 censored; 3,686 not evaluable.
- Two clean runs, determinism and checkpoint/restart: **PASS**.

## Candidate surface

| Rule | Core | Source | Matches | Controls | Weeks |
|---|---|---:|---:|---:|---:|
| `0acd2769f75cff12a0f0e835` | `16859d1bfef47da02cc661c1` | 1,920 | 10,659 | 1,920/1,920 | 5 |
| `1863494da8e1614cba3cf183` | `d84a4ff786e481f11540e180` | 907 | 793 | 895/907 | 5 |
| `2349dcfd483fc8c58bdd0201` | `94c38c6eb0c857834e455c9e` | 428 | 1,728 | 428/428 | 5 |
| `38d3990bee1dde8d8bece49e` | `c3bcf05c5c0ed35424de24f2` | 1,160 | 2,671 | 1,160/1,160 | 5 |
| `58b1a4913dd2b424d0ee96bb` | `b6c7b83a4d65f8bd6dc45a25` | 2 | 2 | 2/2 | 2 |
| `86454a838779ebcf777d9b3e` | `786ce54507b084963244eeae` | 92 | 165 | 92/92 | 5 |
| `96906508e07dd315ea23b592` | `56a50355d6977b5833edcb0a` | 36 | 45 | 36/36 | 5 |
| `9c1eb77722719c990ea3fac2` | `543e8dc008834e2b89b7a70c` | 1,298 | 1,954 | 1,298/1,298 | 5 |
| `a60845024f1244e51aabb28d` | `1a74fef350834438db47af9a` | 96 | 473 | 96/96 | 5 |
| `b2599cfe9e190f1cd45a779b` | `84b737ff760b07fe7d3a0775` | 10 | 8 | 10/10 | 3 |
| `b5af87038319d59d331d365e` | `d5097fe99f4a13121684a0ad` | 3,932 | 3,865 | 1,549/3,932 | 5 |
| `c6cbe3a6347a73c89e3eb2ca` | `c2b8dcb2b2c0debbb9d5e4da` | 22 | 204 | 22/22 | 5 |
| `d139b408441476c06491c0a1` | `9ace10b2dc812f32454599ef` | 2 | 2 | 2/2 | 2 |
| `f86431d28f7b90acd678373a` | `79b7d1a60244146d40e7cc6c` | 329 | 906 | 329/329 | 5 |

All candidates have exact lineage, independent recurrence, complete registered-population evaluation, preserved counterexamples and explicit control accounting. PASS retains research objects only; it grants no semantic, event, episode, outcome, selector or active authority.

## Nonblocking warnings

1. Incomplete exact-stratum control coverage: `C2.RULE.CANDIDATE.1863494da8e1614cba3cf183` and `C2.RULE.CANDIDATE.b5af87038319d59d331d365e`. Unmatched requests and reasons remain explicit; no fallback was used.
2. No candidate matched `2H_A_L` in this June population; no 2H claim or authority is inferred.
3. Both legacy mappings remain not evaluable and are recommended `DEFER`.

## Explicitly excluded

Selector activation, semantic/event/episode/outcome promotion, numeric threshold/parameter/family/model promotion, canonical/R2 publication, new release identity, Validation, C2E/C2.5/C3, probability, risk, exposure, trading, execution and agent writes remain denied.

## Exact recommended command

```text
OVC APPROVE CEAR-G10 METHOD=PASS FUNCTIONAL_CANDIDATES=PASS_ALL RULE_CANDIDATES=PASS_ALL LEGACY_MAPPINGS=DEFER RESEARCH_CONSUMER=PASS_READ_ONLY_SHADOW
```

After approval: record the decision, rerun exact-head assurance, squash-merge PR #319 if eligible, record the merge receipt, and continue to WP11 integrated shadow closeout.

## Rollback

Leave PR 319 unmerged or close it while retaining branch and external evidence. After approval but before merge, revert the decision commit to restore method, candidate and consumer permissions to none.

