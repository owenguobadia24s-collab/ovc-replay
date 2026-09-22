# PMM-DFA bounded Laboratory bootstrap/replay supplement v0.1

This add-only custody supplement references the already-governed PMM-DFA bootstrap and operator-approved **R1T Generation 1**. It is **not** a second freeze or a new candidate generation, and does not change `records/research_operations/pmm_dfa/CURRENT_STATE_POINTER.json`.

## Verified Laboratory artifact
- PMM programme-first Laboratory directory: `/Google Drive/OVC Labratory/01_PROGRAMMES/PMM/05_REPRODUCIBILITY/`.
- ZIP: [OVC_PMM_DFA_Bounded_Laboratory_Bootstrap_and_Replay_Supplement_v0_1.zip](https://drive.google.com/file/d/1tVDoEtYTLqaMIjg1HY09A4GbWj6Purr_/view); **25,602,250 bytes**; SHA-256 `4017f0e19af38f7a7f38517dd269e18d45bc95bcfd8598c6e47b73082c7b2e9a`.
- [Custody and QA receipt](https://drive.google.com/file/d/1kzPd7nceMBKiFabMOGDop_ynhO7PyLPA/view); SHA-256 `5ee855f63768c82f2a15539bc514970146ee5b5276d48404eca7d96fd7123d59`.
- Both exact remote raw-byte SHA-256s matched their local creation bytes. Catalogue rows **1248–1249**, RoutingEvents **1086–1087** verified.

## Content and reproducibility
The ZIP contains 37 SHA-256-bound payload files (39,476,699 uncompressed payload bytes): available historical PMM R0/R1/R2/R4 archives; OPGS R2 exact reference compiler; R2R FULL5/HAC/PAM recovery harnesses and COMP033 membership; R3A census; exact R4 selected 2015 source; inherited PMM-DFA formal synthesis; bounded R1A blinded working evidence; a synthetic-only six-candidate R1T reference checker, synthetic fixture, unit tests, inheritance and gap registries. `registries/PAYLOAD_SHA256_MANIFEST_v0_1.json` inside the ZIP lists all 37 file hashes and external dependencies. The large R2R FULL5 array and PEH R7 reproducibility pack retain their pre-existing, independently filed custody; neither was duplicated.

Extract the ZIP and run in Python 3.11 or newer:

```sh
python machinery/verify_bundle.py --root .
python -m unittest discover -s tests -v
python machinery/synthetic_r1t.py --synthetic-fixture tests/synthetic_stream.jsonl --output ./synthetic_output.json
```

Observed QA: 37/37 internal SHA checks passed, five synthetic conformance tests passed, and both uploaded archive and receipt passed exact remote readback. The **seven explicit empirical reconstruction gaps** are recorded in `registries/EVIDENCE_INHERITANCE_AND_GAPS_v0_1.json`; the synthetic R1T checker is **not** the frozen real-source execution compiler and does not independently reproduce all DFA R1A–R1T empirical claims.

## Existing repository authority (unchanged)
- Governing bootstrap: `docs/programmes/pmm-dfa-v0-1/bootstrap/`.
- Existing frozen definition: `docs/programmes/pmm-dfa-v0-1/r1t/generation-1/PMM_DFA_R1T_GENERATION_1_FREEZE_MANIFEST_v0_1.json`.
- Frozen identity: `rcg:2ff95fa8e4cbd1038b11edd12b38cc993b23c09569a691b5fd162a478b1066d4`.
- Current programme state: `records/research_operations/pmm_dfa/PMM_DFA_PROGRAMME_STATE_v0_5.json`, **BLOCKED** because no eligible filed untouched same-lineage protected Development source is bound.
- Protected Development and Validation remain locked/unconsumed. No Atlas accession, scientific promotion, new provider intake, predictive/probability, exposure, risk or trading authority.

Rollback is append-only: correct new custody references by forward-superseding the supplement, never rewriting the frozen candidate, historical source evidence, gate records or programme state.
