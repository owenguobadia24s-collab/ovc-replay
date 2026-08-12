import "./pvsComponents.css";

export type DataColumn = { key:string; label:string; type?:"text"|"mono"|"number"|"status"; width?:number };
export type DataRecord = Record<string,string|number> & { id:string; state?:"default"|"selected"|"warn" };

export function DataCell({value,type="text"}:{value:string|number;type?:"text"|"mono"|"number"|"status"}) {
  const status = type==="status" ? ` status-${String(value).toLowerCase()}` : "";
  return <td className={`${type}${status}`} data-figma-node="66:37">{value}</td>;
}

export function DataTable({columns,rows,total,state="normal"}:{columns:readonly DataColumn[];rows:readonly DataRecord[];total:number;state?:"normal"|"truncated"|"capacity"}) {
  return <div className="pvs-table" data-figma-node="69:805" data-state={state.toUpperCase()}>
    <table><thead><tr>{columns.map(col=><th key={col.key} style={col.width?{width:col.width}:undefined}>{col.label}</th>)}</tr></thead><tbody>{rows.map(row=><tr key={row.id} className={row.state==="selected"?"is-selected":row.state==="warn"?"is-warn":""}>{columns.map(col=><DataCell key={col.key} value={row[col.key]} type={col.type}/>)}</tr>)}</tbody></table>
    <DenominatorFooter visible={rows.length} total={total}/>
    {state!=="normal"&&<VirtualisationMarker state={state} visible={rows.length} total={total}/>}  
  </div>;
}

export function LedgerRow({id,relation,target,state="PASS"}:{id:string;relation:string;target:string;state?:string}) {
  return <div className="pvs-ledger-row" data-figma-node="72:793"><code>{id}</code><span>{relation}</span><strong data-state={state}>{target}</strong></div>;
}

export function DenominatorFooter({visible,total}:{visible:number;total:number}) {
  return <div className="pvs-denominator" data-figma-node="73:665"><span>Showing 1–{visible} of {total.toLocaleString()}</span><span>universe {total.toLocaleString()} · denominator unchanged</span></div>;
}

export function VirtualisationMarker({state,visible,total}:{state:"truncated"|"capacity";visible:number;total:number}) {
  return <div className={`pvs-virtualisation${state==="capacity"?" is-capacity":""}`} data-figma-node="74:665"><strong>{state==="capacity"?"CAPACITY_EXCEEDED":"TRUNCATED DISPLAY"}</strong><span>rendered {visible.toLocaleString()} / source population {total.toLocaleString()}</span><span>{state==="capacity"?"no silent sampling":"unrendered ≠ missing"}</span></div>;
}
