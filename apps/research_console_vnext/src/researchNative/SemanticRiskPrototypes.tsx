const axes = [
  { name: 'LOCATION', state: 'OBSERVED', evidence: 'SYNTHETIC_FIXTURE', detail: 'ABOVE_RANGE_MID', coverage: 'FULL' },
  { name: 'MOTION', state: 'OBSERVED', evidence: 'SYNTHETIC_FIXTURE', detail: 'UP_IMPULSE_DECELERATING', coverage: 'FULL' },
  { name: 'ORGANISATION', state: 'NOT_EVALUABLE', evidence: 'MISSING_DEPENDENCY', detail: 'DEPENDENCY_WITHHELD', coverage: 'NONE' },
  { name: 'INTERACTION', state: 'OBSERVED', evidence: 'SYNTHETIC_FIXTURE', detail: 'TESTING_PRIOR_HIGH', coverage: 'PARTIAL' },
] as const;

export function MatrixView() {
  return <section className="rnMatrixInstrument" aria-label="C2 MatrixView">
    <div className="rnInstrumentHeader"><div><span className="rnPanelCode">B1</span><strong>C2 MatrixView</strong></div><small>ORTHOGONAL STRUCTURAL EVIDENCE · NO COMPOSITE WINNER</small></div>
    <div className="rnMatrixToolbar"><span>Selected cutoff <b>08:15Z</b></span><span>Parent <b>2H · B</b></span><span>Rows <b>4 / 4</b></span><span>Evidence plane <b>VISIBLE</b></span></div>
    <div className="rnMatrixScroll">
      <table className="rnMatrixTable"><thead><tr><th>Dimension</th><th>Structural state</th><th>Coverage</th><th>Evidence / Missingness</th><th>Exact fixture value</th></tr></thead><tbody>
        {axes.map((axis) => <tr key={axis.name} data-state={axis.state}>
          <th><span className="rnAxisDot" data-state={axis.state}/>{axis.name}</th>
          <td><span className="rnStatePill" data-state={axis.state}>{axis.state}</span></td>
          <td><div className="rnCoverageTrack"><i data-coverage={axis.coverage}/></div><small>{axis.coverage}</small></td>
          <td><strong>{axis.evidence}</strong><small>{axis.state === 'NOT_EVALUABLE' ? 'Required owner is not materialized' : 'Source-bound fixture evidence'}</small></td>
          <td><code>{axis.detail}</code></td>
        </tr>)}
      </tbody></table>
      <div className="rnMatrixPlane"><div className="rnPlaneTitle"><span>STRUCTURAL EVIDENCE PLANE</span><small>Cutoff-relative fixture projection · values remain source-owned</small></div><div className="rnPlaneAxes">{axes.map((axis,index)=><div key={axis.name}><small>{axis.name}</small><div><i style={{width: axis.state === 'NOT_EVALUABLE' ? '18%' : `${54 + index * 9}%`}} data-state={axis.state}/></div><strong>{axis.detail}</strong></div>)}</div></div>
    </div>
    <div className="rnMatrixFooter"><span>Dimension independence preserved</span><span>Denominator 4 structural dimensions</span><span>Frontend calculations: NONE</span></div>
  </section>;
}

export function ProofTimeline() {
  const steps = [
    ['Definition AST', 'EVENT_DEF.FX01', 'DECLARED'],
    ['Bindings', 'C2.LOCATION + C2E.PHASE', 'BOUND'],
    ['Effective time', '08:00Z', 'EFFECTIVE'],
    ['First-valid time', '08:15Z', 'FVT'],
    ['PENDING window', 'dependency firewall intact', 'OPEN'],
  ] as const;
  return <section className="rnProofInstrument" aria-label="C2.5 ProofTimeline">
    <div className="rnInstrumentHeader"><div><span className="rnPanelCode">B2</span><strong>C2.5 ProofTimeline</strong></div><small>DEFINITION ≠ PROOF · EFFECTIVE ≠ FIRST-VALID</small></div>
    <div className="rnProofTrack">{steps.map(([label, value, state], index) => <div className="rnProofStep" key={label}><i data-state={state}/><span>{index + 1}</span><div><small>{label}</small><strong>{value}</strong></div></div>)}</div>
    <div className="rnProofFooter"><span>PENDING until closure / coverage proof</span><span>CENSORED ≠ TERMINATED</span></div>
  </section>;
}

const ast = { type: 'STRUCTURAL_STATEMENT', clauses: ['episode', 'event', 'context?'] };
export function AstRenderer() {
  return <section className="rnAstInstrument" aria-label="C3 AST Renderer">
    <div className="rnMiniHeader"><strong>C3 AST Renderer</strong><span>STANDARD</span></div>
    <div className="rnAstTree"><div className="rnAstRoot">STRUCTURAL_STATEMENT</div><div className="rnAstBranch"><i/>episode <b>required</b></div><div className="rnAstBranch"><i/>event <b>required</b></div><div className="rnAstBranch"><i/>context <b>optional</b></div></div>
    <div className="rnMiniFooter">COMPACT · STANDARD · EXPANDED · AUDIT · AST truth authoritative</div>
    <span className="rnVisuallyHidden">{JSON.stringify(ast)}</span>
  </section>;
}

export function BoundedGraph() {
  return <section className="rnGraphInstrument" aria-label="BoundedGraph">
    <div className="rnMiniHeader"><strong>BoundedGraph</strong><span>120 / 50,000</span></div>
    <div className="rnGraphStage"><svg viewBox="0 0 300 86" role="img" aria-label="Bounded source lineage from C2 through C2E, C2P and C2.5"><line x1="36" y1="43" x2="104" y2="22"/><line x1="36" y1="43" x2="104" y2="64"/><line x1="104" y1="22" x2="178" y2="43"/><line x1="104" y1="64" x2="178" y2="43"/><line x1="178" y1="43" x2="255" y2="43"/><circle cx="36" cy="43" r="8"/><circle cx="104" cy="22" r="7"/><circle cx="104" cy="64" r="7"/><circle cx="178" cy="43" r="8"/><circle cx="255" cy="43" r="8"/></svg><span className="rnGraphLabel rnGraphL1">C2</span><span className="rnGraphLabel rnGraphL2">C2E</span><span className="rnGraphLabel rnGraphL3">C2P</span><span className="rnGraphLabel rnGraphL4">C2.5</span></div>
    <div className="rnGraphMeta"><span>display_projection=true</span><span>expansion_handle=RN-GRAPH-NEXT-001</span></div>
    <details><summary>Accessible ledger alternative</summary><ul><li>C2 → C2E · source-explicit</li><li>C2E → C2P · unavailable</li></ul></details>
  </section>;
}

export function SemanticRiskGallery() {
  return <div className="rnSemanticLayout"><MatrixView/><ProofTimeline/><div className="rnSemanticMiniRail"><AstRenderer/><BoundedGraph/></div></div>;
}
