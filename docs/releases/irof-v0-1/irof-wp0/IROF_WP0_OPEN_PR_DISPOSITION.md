# IROF-WP0 — Open PR Disposition

Initial baseline: `07d078101daf9645dafa2dea23999f9d1d688133`.  
Reconciled main: `c09613495556d0f88496208a31824dc968d89930`.

Open pull requests are proposals/evidence until merged to main. IROF may inspect them for compatibility and fixture lessons but may not treat their branch state as authority.

- **#488** — current IROF-WP0 packet.
- **#487** — SRFD owner-programme resilience proposal. It preserves the consumed v0.6 token and does not itself grant IROF real-run authority.
- **#479** — historical C2E blocked June pre-run evidence. Its old proposed run path is superseded by the later merged binding decision; it is not a PASS authority source.
- **#433** — SRFD consumed-run capacity blocker; intentionally unmerged blocker evidence.
- **#422 / #413** — historical SRFD blocker/preflight evidence; not current executable authority.
- **#418** — historical/draft full-stack synthetic rehearsal. Useful fixture scenarios only; DO NOT IMPORT or merge through IROF.
- **#211** — inactive shadow proposal, no authority.
- **#202** — separate historical programme PR, no IROF authority.

**Merged during WP0:** PR **#485** merged as `c09613495556d0f88496208a31824dc968d89930`. It authorises only C2E replacement-object preparation after a population-unit mismatch; the old token is invalidated unconsumed and WP6 execution remains denied pending a fresh exact C2E2-G6-RUN-AUTH decision. IROF therefore continues to fail closed for real C2E execution.

The disposition is intentionally conservative: proposal branch code may be studied, but only merged court-record contracts and separately valid owner-programme decisions can satisfy an IROF `AuthorityBinding`.
