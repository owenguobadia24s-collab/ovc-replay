import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { AtlasFeasibilityCanvas } from "./AtlasFeasibilityCanvas";
import { layoutAtlasGraph, type AtlasLayoutResult } from "./layout";
import { buildCompoundC2EGraph, buildL1SyntheticGraph } from "./model";
import "./system-atlas-feasibility.css";

const l1Graph = buildL1SyntheticGraph();
const c2eGraph = buildCompoundC2EGraph();

function FeasibilityPage() {
  const [layouts, setLayouts] = useState<{ l1: AtlasLayoutResult; c2e: AtlasLayoutResult }>();
  useEffect(() => {
    let current = true;
    Promise.all([layoutAtlasGraph(l1Graph), layoutAtlasGraph(c2eGraph)]).then(([l1, c2e]) => {
      if (current) setLayouts({ l1, c2e });
    });
    return () => { current = false; };
  }, []);
  return (
    <main className="atlas-feasibility-shell" data-atlas-feasibility="synthetic-only">
      <header className="atlas-feasibility-header">
        <div>
          <p>ATLAS-WP1V · SYNTHETIC_NOT_COURT_RECORD</p>
          <h1>System Atlas visual feasibility</h1>
        </div>
        <dl>
          <div><dt>Renderer</dt><dd>Cytoscape 3.31.2</dd></div>
          <div><dt>Layout</dt><dd>ELK 0.12.0</dd></div>
          <div><dt>Authority</dt><dd>None</dd></div>
        </dl>
      </header>
      <section className="atlas-feasibility-band" aria-labelledby="l1-title">
        <div className="atlas-feasibility-section-title"><h2 id="l1-title">L1 whole-system spine</h2><span>Stable hierarchical geography</span></div>
        {layouts ? <AtlasFeasibilityCanvas graph={l1Graph} layout={layouts.l1} label="Synthetic L1 whole-system Atlas graph" /> : <div className="atlas-feasibility-loading">Computing deterministic layout</div>}
      </section>
      <section className="atlas-feasibility-band" aria-labelledby="c2e-title">
        <div className="atlas-feasibility-section-title"><h2 id="c2e-title">Compound C2E drill</h2><span>Contracts → records → implementation → assurance</span></div>
        {layouts ? <AtlasFeasibilityCanvas graph={c2eGraph} layout={layouts.c2e} label="Synthetic compound C2E Atlas graph" /> : <div className="atlas-feasibility-loading">Computing deterministic layout</div>}
      </section>
      <footer className="atlas-feasibility-legend" aria-label="Visual grammar legend">
        <span className="legend-current">Current</span><span className="legend-reserved">Reserved</span><span className="legend-conflict">Conflict</span><span className="legend-historical">Historical</span><span className="legend-forbidden">Forbidden edge</span>
      </footer>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<StrictMode><FeasibilityPage /></StrictMode>);
