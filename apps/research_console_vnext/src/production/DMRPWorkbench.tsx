import { useQuery } from "@tanstack/react-query";

import { getDMRPSnapshot } from "../api/client";
import "../design/productionTokens.css";
import "./productionConsole.css";
import {
  ApplicationHeader,
  ContextAuthorityStrip,
  EvidenceDock,
  EvidenceInspector,
  GlobalDomainRail,
  StatusBar,
  WorkbenchNavigator,
} from "./PvsShell";
import { domainColor, type RouteConfig } from "./pvsContracts";

const cfg: RouteConfig = {
  domain: "Research",
  kicker: "RESEARCH / WP5B1 DMRP SOURCE-BOUND OPERATIONS",
  title: "Path 1, Path 2, candidate generation and cross-mode evidence",
  subtitle: "source-bound · read-only · owner identities preserved · no candidate repair/ranking/promotion",
  navigatorTitle: "WP5B1 / DMRP",
  selectedObject: "RCN-RN-WP5B1",
  objectType: "DMRPReadSurface",
  source: "WP5B1-DMRP-SOURCE-BINDINGS-v1",
  generation: "RCN-RN-v0.3",
  population: "DMRP owner source surface",
  instrument: "SOURCE BOUND",
  clock: "SOURCE BOUND",
  fvt: "OWNER RECORDED",
  nav: [
    ["Path 1", "DISCOVERY"],
    ["Path 2", "FORMALISATION"],
    ["Candidate", "OWNER"],
    ["Cross-mode", "OWNER"],
    ["Negative", "OWNER"],
    ["Authority", "READ ONLY"],
  ],
};

function PanelTitle({ title, note }: { title: string; note: string }) {
  return (
    <div className="pc-panel-title">
      <b>{title}</b>
      {note && <small>{note}</small>}
    </div>
  );
}

function show(value: unknown): string {
  return value === null || value === undefined || value === "" ? "NOT MATERIALIZED" : String(value);
}

function DMRPPrimary() {
  const query = useQuery({
    queryKey: ["rcn-rn-wp5b1-dmrp-snapshot"],
    queryFn: getDMRPSnapshot,
    staleTime: Infinity,
    retry: false,
  });
  const snapshot = query.data?.payload;
  const real = snapshot?.mode === "REAL_SOURCE_READ_ONLY";

  return (
    <main
      className="pc-primary research"
      data-testid="production-primary-canvas"
      data-rcn-ref="production-primary-canvas"
      data-wp5b1-workbenchframe="SOURCE_BOUND"
      data-first-new-real-research-source={snapshot ? String(Boolean(snapshot.source_preflight?.first_new_real_research_source)) : "unknown"}
    >
      <small className="pc-primary-kicker" style={{ color: domainColor(cfg.domain) }}>
        {cfg.kicker}
      </small>
      <h1>{cfg.title}</h1>
      <p className="pc-primary-subtitle">{cfg.subtitle}</p>

      {query.isPending && (
        <section className="pc-panel">
          <PanelTitle title="DMRP SOURCE PREFLIGHT" note="loading exact owner-bound source identities" />
          <strong>LOADING SOURCE-BOUND DMRP PROJECTION</strong>
        </section>
      )}

      {query.isError && (
        <section className="pc-panel">
          <PanelTitle title="DMRP SOURCE PREFLIGHT" note="fail closed" />
          <strong>NOT MATERIALIZED</strong>
          <code>{query.error instanceof Error ? query.error.message : "UNKNOWN_ERROR"}</code>
        </section>
      )}

      {snapshot && (
        <>
          <section className="pc-panel">
            <PanelTitle title="SOURCE + AUTHORITY PREFLIGHT" note={real ? "DMRP owner court records · exact Git blob binding" : "DMRP owner fixtures · exact Git blob binding"} />
            <div className="wp5a-preflight-grid">
              <p><small>STATUS</small><strong className="good">{snapshot.source_preflight.status}</strong></p>
              <p><small>MODE</small><strong>{snapshot.mode}</strong></p>
              <p><small>EVIDENCE</small><strong>{snapshot.evidence_status}</strong></p>
              <p><small>FIRST NEW REAL SOURCE</small><strong>{snapshot.source_preflight.first_new_real_research_source ? "YES — DMRP ONLY" : "NO"}</strong></p>
              <p><small>FIXTURE FALLBACK</small><strong>{show(snapshot.source_preflight.fixture_fallback ?? "FIXTURE MODE")}</strong></p>
              <p><small>RESERVED/APPROVED GATE</small><strong className="warn">{show(snapshot.source_preflight.gate_id ?? snapshot.source_preflight.operator_escalation_gate)}</strong></p>
            </div>
          </section>

          <div className="pc-research-top">
            <section className="pc-panel">
              <PanelTitle title="PATH 1 / EMPIRICAL DISCOVERY" note="source-owned research mode and owner state" />
              <div className="wp5a-evidence-row"><code>{show(snapshot.path1.study_id)}</code><strong>{show(snapshot.path1.research_mode)}</strong><span>{show(snapshot.path1.research_role)}</span></div>
              <div className="wp5a-evidence-row"><code>{show(snapshot.path1.cycle_id)}</code><strong>{show(snapshot.path1.question_id)}</strong><span>{show(snapshot.path1.validation_access_state)}</span></div>
            </section>

            <section className="pc-panel">
              <PanelTitle title="PATH 2 / THEORY FORMALISATION" note="distinct provenance · no identity collapse" />
              <div className="wp5a-evidence-row"><code>{show(snapshot.path2.training_id)}</code><strong>{show(snapshot.path2.guided_formalisation_id)}</strong><span>{show(snapshot.path2.ready_intake_id)}</span></div>
              <div className="wp5a-evidence-row"><code>{show(snapshot.path2.divergent_intake_id)}</code><strong className="warn">{show(snapshot.path2.divergent_disposition)}</strong><span>OWNER BINDING {show(snapshot.path2.real_source_authority)}</span></div>
            </section>
          </div>

          <section className="pc-panel">
            <PanelTitle title="RESEARCH CANDIDATE GENERATION" note="owner identity only · no repair or promotion" />
            <div className="wp5a-preflight-grid">
              <p><small>AVAILABILITY</small><strong>{show(snapshot.candidate_generation.availability)}</strong></p>
              <p><small>SERIES</small><strong>{show(snapshot.candidate_generation.series_id)}</strong></p>
              <p><small>GENERATION</small><strong>{show(snapshot.candidate_generation.generation)}</strong></p>
              <p><small>ORIGIN</small><strong>{show(snapshot.candidate_generation.origin_mode)}</strong></p>
              <p><small>POPULATION</small><strong>{show(snapshot.candidate_generation.population_id)}</strong></p>
              {Object.entries(snapshot.candidate_generation.membership ?? {}).map(([status, count]) => (
                <p key={status}><small>{status}</small><strong>{String(count)}</strong></p>
              ))}
            </div>
          </section>

          <section className="pc-panel">
            <PanelTitle title="CROSS-MODE CORRESPONDENCE" note="correspondence is not independence" />
            {(snapshot.cross_mode ?? []).map((row: any) => (
              <div className="wp5a-evidence-row" key={row.relation_id} data-identity-merge={String(row.identity_merge)}>
                <code>{row.relation_id}</code>
                <strong>{row.correspondence}</strong>
                <span>INDEPENDENCE {row.independence} · MERGE NO · WINNER NONE · RANKING NONE</span>
              </div>
            ))}
            {(snapshot.cross_mode ?? []).length === 0 && (
              <div className="wp5a-evidence-row"><code>NO BOUND RELATION</code><strong>INDEPENDENCE UNKNOWN</strong><span>missing exposure does not imply independence</span></div>
            )}
          </section>

          <section className="pc-panel pc-residual">
            <PanelTitle title="NEGATIVE / DIVERGENT EVIDENCE" note="retained when owner-bound; absence is not inferred as a scientific negative" />
            {(snapshot.negative_divergent_evidence ?? []).map((row: any) => (
              <div className="wp5a-evidence-row" key={row.evidence_id}>
                <code>{row.evidence_id}</code><strong>{row.status}</strong><span>{row.mode} · count {row.count}</span>
              </div>
            ))}
            {(snapshot.negative_divergent_evidence ?? []).length === 0 && (
              <div className="wp5a-evidence-row"><code>NO BOUND OWNER RECORD</code><strong>UNRESOLVED</strong><span>do not infer absence</span></div>
            )}
            <div className="wp5a-firewall">
              <b>SCIENTIFIC FIREWALL</b>
              <span>CANDIDATE CONSTRUCTION {snapshot.presentation_guardrails.candidate_construction}</span>
              <span>IDENTITY MERGE {snapshot.presentation_guardrails.candidate_identity_merge}</span>
              <span>PATH WINNER NONE · RANKING {snapshot.presentation_guardrails.ranking}</span>
              <span>VALIDATION {snapshot.presentation_guardrails.validation_consumption}</span>
              <span>WRITES {snapshot.presentation_guardrails.writes}</span>
              <span>SOURCE TRANSITIVITY {show(snapshot.presentation_guardrails.source_admission_transitivity ?? "PROHIBITED")}</span>
            </div>
          </section>
        </>
      )}
    </main>
  );
}

export function DMRPWorkbench() {
  return (
    <div
      className="production-console domain-research"
      aria-label="WP5B1 source-bound DMRP workbench"
      data-domain={cfg.domain}
      data-wp5b1-authority-effect="NONE"
    >
      <GlobalDomainRail domain={cfg.domain} />
      <ApplicationHeader domain={cfg.domain} />
      <ContextAuthorityStrip cfg={cfg} />
      <WorkbenchNavigator cfg={cfg} />
      <DMRPPrimary />
      <EvidenceInspector cfg={cfg} />
      <EvidenceDock />
      <StatusBar />
    </div>
  );
}
