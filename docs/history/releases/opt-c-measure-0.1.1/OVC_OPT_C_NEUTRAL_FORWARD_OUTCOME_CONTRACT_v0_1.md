# OVC OPT-C Neutral Forward-Outcome Contract v0.1

**Contract ID:** `OPT-C-OUTCOME-0.1`  
**Status:** `RATIFIED FOR CONTRACT AND EVENT-LEDGER BUILD`  
**B-STATE authority:** `B-STATE-0.3b-FRONTIER-ACTIVE-RESEARCH`

## Unit of observation

One anchor row represents one eligible event bar on one canonical clock. All
simultaneous acceptance, displacement, compression and interaction evidence is
stored as components of that row. Compound evidence is not duplicated into
separate outcome observations.

Eligible components are:

- ratified frontier-advance acceptance events;
- displacement onset, refresh, direction change and confirmed exit;
- compression onset, refresh and confirmed exit;
- reclaim, rejection and breach/response interaction components.

Quality changes and one-bar event-to-`NONE` transitions do not independently
create outcome anchors. Axis transitions remain linked audit metadata.

## Anchor

- Anchor time: qualifying event bar close in UTC.
- Anchor price: bid close of that event-clock bar.
- Event clock: canonical 15M detail or canonical 2H spine.
- Direction: `UP`, `DOWN`, `MIXED` or `NONE`, derived from all event components.
- Eligibility is decided entirely from information lawful at the anchor close.

## Forward path authority

The canonical 15M OPT-A series is the path authority for both event clocks.
The exact path for horizon `H` is the sequence of accepted 15M bars whose open
times begin at the anchor and whose closes end at `anchor + H`.

Every expected 15M interval must exist. A missing anchor-start bar, internal gap,
missing endpoint or end-of-release truncation censors that horizon. No lower or
higher resolution may repair the path.

## Horizons

`1h, 2h, 4h, 8h, 12h, 24h, 48h`.

## Neutral measurements

For each complete horizon, OPT-C may record:

- endpoint return in raw price and pips;
- maximum upward and downward excursion;
- time to maximum and minimum;
- first-extreme ordering;
- close position within the forward range;
- raw and event-direction-normalized excursion;
- accepted-frontier retest, hold or loss;
- continuation beyond the event extreme;
- reversal through the opposite frontier;
- subsequent ratified B-STATE record and transition lineage.

Direction-normalized fields describe relative movement only. They cannot be
named or interpreted as profit, loss, win, trade or execution performance.

## Cross-clock and overlap rules

Cross-clock context uses only the latest already-closed state record. Future 2H
context is prohibited. Context older than its clock interval is explicitly stale.

Events on the same bar are compound in one anchor. Events on different bars or
clocks remain separate observations. Same-time cross-clock groups and later
forward-window overlap flags prevent an independence assumption.

## Censoring and leakage controls

- Gaps are never bridged.
- Events near the source boundary remain in the ledger but incomplete horizons
  are censored.
- Event eligibility and direction are frozen before any outcome is measured.
- Outcome values cannot alter OPT-B classification, relevance or event inclusion.
- Thresholds cannot be selected using the measured H1 outcomes.

## Authority boundary

OPT-C produces descriptive forward measurements. It grants no edge,
recommendation, risk, production or execution authority.
