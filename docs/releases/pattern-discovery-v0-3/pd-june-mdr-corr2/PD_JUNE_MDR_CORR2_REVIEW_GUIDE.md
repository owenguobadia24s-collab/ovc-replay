# PD-JUNE-MDR-CORR2 Blinded Review Guide

## Status

`OPERATOR_REVIEW_INPUT_REQUIRED`

The review packet is complete and machine-validated. No model, candidate, trigger or selector has been changed.

## Files

1. `PD_JUNE_MDR_CORR2_BLINDED_REVIEW_INDEX.json` — review index and exact batch hashes.
2. `PD_JUNE_MDR_CORR2_BLINDED_REVIEW_BATCH_01.json` through `BATCH_04.json` — review all 16 cards in batch and card order.
3. `PD_JUNE_MDR_CORR2_BLINDED_REVIEW_RESPONSE.template.json` — complete and return this file.
4. `PD_JUNE_MDR_CORR2_SEALED_ANSWER_KEY.json` — **do not open until the completed response is returned**.
5. `PD_JUNE_MDR_CORR2_CONTROL_LEDGER.json` — deterministic construction evidence; avoid opening before review to preserve the strongest blinding.

A single combined review-input file is also supplied to the operator outside the repository for easier completion. Its cards are exactly bound by the index and four repository batches.

## Review procedure

Review all 16 cards in their listed order.

For each card:

- choose the best trigger classification;
- decide whether the structural description is supported, contradicted or insufficient;
- choose the review disposition;
- record confidence from 1 to 5;
- add contradiction codes and concise notes.

Use `INSUFFICIENT_EVIDENCE` rather than guessing.

Do not change `blind_id` or `card_payload_sha256`.

## Return

Upload the completed response JSON without opening the answer key. CORR2 will then validate and score:

- false-positive controls;
- promoted trigger detection;
- exact trigger-reason agreement;
- structural contradictions;
- repeat disposition agreement;
- Cohen's kappa.

The result returns to `PD-JUNE-MDR-G1`. General reliability remains bounded to the exact June slice.
