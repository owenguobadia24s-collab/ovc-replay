import type { ReactNode } from "react";
import { DenominatorFooter } from "./PvsData";
import "./pvsComponents.css";
import "./pvsInstruments.css";

export type MatrixEvidenceState="POSITIVE"|"NEGATIVE"|"MIXED"|"NO_EVIDENCE"|"MISSING"|"NOT_EVALUABLE";
export type MatrixDatum={dimension:string;state:string;evidence:MatrixEvidenceState;detail:string};
export function MatrixView({rows,total=rows.length}:{rows:readonly MatrixDatum[];total?:number}) {
  return <section className="pvs-instrument pvs-matrix-view" data-figma-node="70:736" aria-label="MatrixView"><header><strong>STRUCTURAL EVIDENCE MATRIX</strong><small>orthogonal evidence · no composite winner</small></header><div className="pvs-matrix-rows">{rows.map(row=><div key={row.dimension} className="pvs-matrix-row" data-evidence={row.evidence}><b>{row.dimension}</b><code>{row.state}</code><span>{row.evidence}</span><small>{row.detail}</small></div>)}</div><DenominatorFooter visible={rows.length} total={total}/></section>;
}

export type ProofStage={id:string;kind:"DEFINITION"|"BINDING"|"EFFECTIVE"|"FVT"|"DEPENDENCY"|"TRUTH";value:string;state:"DECLARED"|"BOUND"|"OPEN"|"PASS"|"CENSORED"|"LOCKED"};
export function ProofTimeline({stages}:{stages:readonly ProofStage[]}) {
  return <section className="pvs-instrument pvs-proof" data-figma-node="89:325" aria-label="ProofTimeline"><header><strong>C2.5 PROOF TIMELINE</strong><small>definition ≠ proof · bindings before truth · effective ≠ FVT</small></header><ol>{stages.map(stage=><li key={stage.id} data-kind={stage.kind} data-state={stage.state}><i/><span><small>{stage.kind}</small><strong>{stage.value}</strong></span><code>{stage.state}</code></li>)}</ol><footer>PENDING remains open · CENSORED ≠ TERMINATED · dependency firewall preserved</footer></section>;
}

export type AstNodeModel={id:string;type:string;label:string;cardinality?:string;optional?:boolean;children?:readonly AstNodeModel[]};
function AstNodeView({node}:{node:AstNodeModel}) {return <li><div className="pvs-ast-node" data-figma-node="86:203"><small>{node.type}</small><strong>{node.label}</strong><code>{node.id}</code><span>{node.optional?"OPTIONAL":node.cardinality??"REQUIRED"}</span></div>{node.children?.length?<ul>{node.children.map(child=><AstNodeView key={child.id} node={child}/>)}</ul>:null}</li>;}
export function AstRenderer({root,profile="STANDARD",error}:{root:AstNodeModel;profile?:"COMPACT"|"STANDARD"|"EXPANDED"|"AUDIT";error?:string}) {
  return <section className="pvs-instrument pvs-ast" data-figma-node="90:416" data-profile={profile} aria-label="C3 AST Renderer"><header><strong>C3 AST RENDERER</strong><small>{profile} · one authoritative AST; profile is presentation only</small></header>{error?<div className="pvs-render-error" role="status">RENDERER ERROR · {error} · AST payload remains authoritative</div>:<ul className="pvs-ast-tree"><AstNodeView node={root}/></ul>}{profile==="AUDIT"&&<pre>{JSON.stringify(root,null,2)}</pre>}</section>;
}

export type GraphNodeModel={id:string;role:"primary"|"related"|"candidate"|"context"|"dependency"|"evidence"|"supersession";label:string};
export type GraphEdgeModel={id:string;source:string;target:string;sourcePort?:string;targetPort?:string;direction:"DIRECTED"|"UNDIRECTED";plane:string};
export function BoundedGraph({nodes,edges,totalNodes,totalEdges,truncated=false,selectedId}:{nodes:readonly GraphNodeModel[];edges:readonly GraphEdgeModel[];totalNodes:number;totalEdges:number;truncated?:boolean;selectedId?:string}) {
  return <section className="pvs-instrument pvs-bounded-graph" data-figma-node="81:525" aria-label="BoundedGraph"><header><strong>BOUNDED GRAPH</strong><small>display_projection=true · connectivity ≠ entailment</small></header><div className="pvs-graph-budget"><span>LOADED <b>{nodes.length} / {totalNodes.toLocaleString()}</b></span><span>EDGES <b>{edges.length} / {totalEdges.toLocaleString()}</b></span><span>{truncated?"TRUNCATED · expansion token required":"WITHIN BUDGET"}</span></div><div className="pvs-graph-plane" role="img" aria-label="Typed bounded graph projection">{nodes.map((node,index)=><div key={node.id} className={`pvs-graph-node role-${node.role}${node.id===selectedId?" is-selected":""}`} style={{left:`${8+(index%5)*19}%`,top:`${18+Math.floor(index/5)*38}%`}}><small>{node.role}</small><strong>{node.label}</strong><code>{node.id}</code></div>)}</div><details><summary>Accessible ledger alternative</summary><table><thead><tr><th>Edge ID</th><th>Source / port</th><th>Direction</th><th>Target / port</th><th>Plane</th></tr></thead><tbody>{edges.map(edge=><tr key={edge.id}><td><code>{edge.id}</code></td><td>{edge.source}{edge.sourcePort?` / ${edge.sourcePort}`:""}</td><td>{edge.direction}</td><td>{edge.target}{edge.targetPort?` / ${edge.targetPort}`:""}</td><td>{edge.plane}</td></tr>)}</tbody></table></details>{truncated&&<footer className="pvs-capacity-note">Projection truncated explicitly; source population unchanged. No silent sampling.</footer>}</section>;
}

export function InstrumentPanel({title,note,children}:{title:string;note:string;children:ReactNode}) {return <section className="pvs-instrument" data-figma-node="54:293"><header><strong>{title}</strong><small>{note}</small></header>{children}</section>;}
