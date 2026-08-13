import { useQuery } from "@tanstack/react-query";

import { getRepresentationSnapshot } from "../api/client";
import type { WP5AFamilyOutcome, WP5AMethod } from "../api/types";
import "../design/productionTokens.css";
import "./productionConsole.css";
import "./representationWorkbench.css";
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
  kicker: "RESEARCH / WP5A SOURCE-BOUND REPRESENTATIONS",
  title: "SRI, FDI, SRFD and MCARB representation evidence",
  subtitle: "synthetic fixture · non-evidentiary · exact source blobs verified · no first-new real Research source",
  navigatorTitle: "WP5A / METHOD-FIRST",
  selectedObject: "RCN-RN-WP5A",
  objectType: "RepresentationReadSurface",
  source: "WP5A-FIXTURE-BINDINGS-v1",
  generation: "RCN-RN-v0.3",
  population: "7 fixture methods",
  instrument: "GBP/USD",
  clock: "15M / 2H",
  fvt: "FIXTURE / NO MARKET FVT",
  nav: [
    ["Methods", "7"],
    ["Comparability", "5"],
    ["Outcomes", "3"],
    ["Sensitivity", "3"],
    ["MCARB", "3"],
    ["Authority", "NONE"],
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

function MethodRows({ methods }: { methods: WP5AMethod[] }) {
  return (
    <>
      {methods.map((method) => (
        <div
          className={`method-row ${method.status === "NO_STABLE_FAMILY" ? "warn" : ""}`}
          key={method.method_id}
          data-winner={method.winner === null ? "NONE" : "PROHIBITED"}
        >
          <code>{method.method_id}</code>
          <code>{method.basis}</code>
          <code>{method.source_fixture_id}</code>
          <code>{method.status}</code>
          <code>{method.disposition}</code>
          <code>{method.selection_authority}</code>
        </div>
      ))}
    </>
  );
}

function OutcomeRows({ outcomes }: { outcomes: WP5AFamilyOutcome[] }) {
  return (
    <div className="wp5a-outcome-grid">
      {outcomes.map((outcome) => (
        <article key={outcome.outcome} data-outcome-status="LAWFUL_EQUAL_STATUS">
          <small>{outcome.outcome}</small>
          <strong>{outcome.count}</strong>
          <code>{outcome.status}</code>
          <span>{outcome.source_fixture_id}</span>
        </article>
      ))}
    </div>
  );
}

function RepresentationPrimary() {
  const query = useQuery({
    queryKey: ["rcn-rn-wp5a-representation-snapshot"],
    queryFn: getRepresentationSnapshot,
    staleTime: Infinity,
    retry: false,
  });

  const snapshot = query.data?.payload;

  return (
    <main
      className="pc-primary research wp5a-representation-primary"
      data-testid="production-primary-canvas"
      data-rcn-ref="production-primary-canvas"
      data-wp5a-workbenchframe="SOURCE_BOUND"
      data-first-new-real-research-source="false"
    >
      <small className="pc-primary-kicker" style={{ color: domainColor(cfg.domain) }}>
        {cfg.kicker}
      </small>
      <h1>{cfg.title}</h1>
      <p className="pc-primary-subtitle">{cfg.subtitle}</p>

      {query.isPending && (
        <section className="pc-panel wp5a-state">
          <PanelTitle title="WP5A SOURCE PREFLIGHT" note="loading exact fixture identities" />
          <strong>LOADING SOURCE-BOUND FIXTURE PROJECTION</strong>
        </section>
      )}

      {query.isError && (
        <section className="pc-panel wp5a-state error">
          <PanelTitle title="WP5A SOURCE PREFLIGHT" note="fail closed" />
          <strong>NOT MATERIALIZED</strong>
          <code>{query.error instanceof Error ? query.error.message : "UNKNOWN_ERROR"}</code>
        </section>
      )}

      {snapshot && (
        <>
          <section className="pc-panel wp5a-source-preflight">
            <PanelTitle
              title="SOURCE + AUTHORITY PREFLIGHT"
              note="SRI / FDI / SRFD / MCARB · exact repository fixture bindings"
            />
            <div className="wp5a-preflight-grid">
              <p><small>STATUS</small><strong className="good">{snapshot.source_preflight.status}</strong></p>
              <p><small>MODE</small><strong>{snapshot.mode}</strong></p>
              <p><small>EVIDENCE</small><strong>{snapshot.evidence_status}</strong></p>
              <p><small>FIRST NEW REAL SOURCE</small><strong>NO</strong></p>
              <p><small>AUTO BRANCH</small><strong>{snapshot.source_preflight.gate_branch}</strong></p>
              <p><small>RESERVED ESCALATION</small><strong className="warn">{snapshot.source_preflight.operator_escalation_gate}</strong></p>
            </div>
            <div className="frozen">
              <b>FROZEN INPUT</b>
              <span>{snapshot.source_preflight.source_ids.join(" · ")}</span>
              <em>NO METHOD SELECTOR AUTHORITY</em>
            </div>
          </section>

          <div className="pc-research-top">
            <section className="pc-panel pc-methods">
              <PanelTitle
                title="METHOD-FIRST SOURCE EVIDENCE"
                note="source declarations only · frontend scientific calculation PROHIBITED"
              />
              <div className="method-head">
                {["METHOD","BASIS","FIXTURE","STATUS","DISPOSITION","SELECTOR"].map((label) => (
                  <b key={label}>{label}</b>
                ))}
              </div>
              <MethodRows methods={snapshot.methods} />
              <div className="wp5a-null-winner">
                <b>NO DEFAULT WINNER</b>
                <span>all method and comparison winner fields are null</span>
                <code>SELECTOR AUTHORITY {snapshot.presentation_guardrails.selector_authority}</code>
              </div>
            </section>

            <section className="pc-panel pc-sensitivity">
              <PanelTitle
                title="SOURCE-DECLARED SENSITIVITY"
                note="method sensitivity is evidence, not ontological truth"
              />
              {snapshot.sensitivity.map((row) => (
                <div className="wp5a-evidence-row" key={row.source_fixture_id}>
                  <code>{row.source_fixture_id}</code>
                  <strong>{row.status}</strong>
                  <span>{row.expected}</span>
                </div>
              ))}
              <div className="interpret">
                <b>INTERPRETATION</b>
                <span>no invariant core may be a complete result; correspondence ≠ independence</span>
              </div>
            </section>
          </div>

          <section className="pc-panel pc-residual wp5a-outcomes">
            <PanelTitle
              title="RESIDUAL / AMBIGUITY / NO_STABLE_FAMILY"
              note="three equal-status lawful outcomes · no forced assignment"
            />
            <OutcomeRows outcomes={snapshot.family_outcomes} />
            <div className="pc-denominator">
              <span>DENOMINATOR</span>
              <b>
                {snapshot.outcome_denominator.denominator} source-declared outcomes ·
                population {snapshot.population.evaluable_count}/{snapshot.population.denominator} ·
                missing {snapshot.population.missing_count}
              </b>
              <em>truncated {String(snapshot.population.truncated).toUpperCase()}</em>
            </div>
          </section>

          <section className="pc-panel wp5a-mcarb">
            <PanelTitle
              title="MCARB AUXILIARY REPRESENTATION EVIDENCE"
              note="dependence visible · no double credit · complete auxiliary null is lawful"
            />
            {snapshot.mcarb.map((row) => (
              <div className="wp5a-evidence-row" key={row.source_fixture_id}>
                <code>{row.source_fixture_id}</code>
                <strong>{row.status}</strong>
                <span>{row.expected}</span>
              </div>
            ))}
            <div className="wp5a-firewall">
              <b>SCIENTIFIC FIREWALL</b>
              <span>{snapshot.presentation_guardrails.frontend_scientific_calculation}</span>
              <span>VALIDATION {snapshot.presentation_guardrails.validation_consumption}</span>
              <span>WRITES {snapshot.presentation_guardrails.writes}</span>
            </div>
          </section>
        </>
      )}
    </main>
  );
}

export function RepresentationWorkbench() {
  return (
    <div
      className="production-console domain-research"
      aria-label="WP5A fixture-only source-bound representation workbench"
      data-domain={cfg.domain}
      data-figma-manifest="269:2"
      data-pvs-release="RCN-vNext-OPT-B-ESL-PVS-v0.2"
      data-wp5a-authority-effect="NONE"
    >
      <GlobalDomainRail domain={cfg.domain} />
      <ApplicationHeader domain={cfg.domain} />
      <ContextAuthorityStrip cfg={cfg} />
      <WorkbenchNavigator cfg={cfg} />
      <RepresentationPrimary />
      <EvidenceInspector cfg={cfg} />
      <EvidenceDock />
      <StatusBar />
    </div>
  );
}
