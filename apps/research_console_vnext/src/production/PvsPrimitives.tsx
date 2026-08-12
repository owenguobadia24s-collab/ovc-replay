import type { ButtonHTMLAttributes, ReactNode } from "react";
import "./pvsComponents.css";

export type PvsTone = "neutral" | "investigate" | "research" | "evidence" | "control" | "pass" | "warn" | "error" | "residual" | "null";

export function ObjectBadge({label,value,tone="neutral"}:{label:string;value:string;tone?:PvsTone}) {
  return <span className={`pvs-badge tone-${tone}`} data-figma-node="22:45"><small>{label}</small><strong>{value}</strong></span>;
}

export function TypedObjectLink({type,id,selected=false}:{type:string;id:string;selected?:boolean}) {
  return <span className={`pvs-object-link${selected?" is-selected":""}`} data-figma-node="21:29" data-selection-state={selected?"SELECTED":"DEFAULT"}><small>{type}</small><code>{id}</code></span>;
}

export function StatusBadge({kind,label}:{kind:"available"|"authorised"|"active"|"pass"|"warn"|"error"|"locked";label:string}) {
  return <span className={`pvs-status pvs-status-${kind}`} data-figma-node="20:77"><i aria-hidden="true"/><strong>{label}</strong></span>;
}

export function AuthorityTriadView({available,authorised,active}:{available:boolean;authorised:boolean;active:boolean}) {
  const values = [["AVAILABLE",available],["AUTHORISED",authorised],["ACTIVE",active]] as const;
  return <div className="pvs-authority-triad" data-figma-node="23:85" aria-label="Independent authority state">{values.map(([label,value])=><div key={label} data-state={value?"YES":"NO"}><small>{label}</small><strong>{value?"YES":"NO"}</strong></div>)}</div>;
}

export function DegradedState({kind,why,impact,unaffected="identity, authority and evidence trace"}:{kind:string;why:string;impact:string;unaffected?:string}) {
  return <section className="pvs-degraded" data-figma-node="91:221" role="status"><small>{kind}</small><strong>FAIL-HONEST DEGRADED STATE</strong><p>Why: {why}</p><p>Impact: {impact}</p><p>Unaffected: {unaffected}</p></section>;
}

type IconButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>,"children"> & {label:string;icon:ReactNode;size?:24|28|32;styleKind?:"ghost"|"outline"};
export function IconButton({label,icon,size=24,styleKind="ghost",disabled,...props}:IconButtonProps) {
  return <button {...props} type="button" className={`pvs-icon-button pvs-icon-${size} pvs-icon-${styleKind}`} aria-label={label} disabled={disabled} data-figma-node="24:125" data-navigation-only="true">{icon}</button>;
}

export function PvsButton({children,emphasis="quiet",disabled=false}:{children:ReactNode;emphasis?:"quiet"|"emphasis";disabled?:boolean}) {
  return <button type="button" className={`pvs-button pvs-button-${emphasis}`} disabled={disabled} data-navigation-only="true" data-figma-node={emphasis==="emphasis"?"26:145":"27:165"}>{children}</button>;
}

export function SearchField({value="",placeholder="Search…"}:{value?:string;placeholder?:string}) {
  return <label className="pvs-field pvs-search" data-figma-node="29:165"><span aria-hidden="true">⌕</span><input aria-label={placeholder} value={value} placeholder={placeholder} readOnly/></label>;
}

export function SelectField({label,value,locked=false}:{label:string;value:string;locked?:boolean}) {
  return <label className={`pvs-field pvs-select${locked?" is-locked":""}`} data-figma-node="30:175"><small>{label}</small><span>{value}</span><b>{locked?"LOCKED":"⌄"}</b></label>;
}

export function FilterChip({label,count,selected=false}:{label:string;count?:number;selected?:boolean}) {
  return <button type="button" className={`pvs-chip${selected?" is-selected":""}`} data-figma-node="31:219" data-navigation-only="true"><span>{label}</span>{count!==undefined&&<code>{count}</code>}</button>;
}

export function SegmentedControl<T extends string>({label,options,value}:{label:string;options:readonly T[];value:T}) {
  return <div className="pvs-segmented" data-figma-node="34:197" role="group" aria-label={label}>{options.map(option=><button type="button" key={option} className={option===value?"is-selected":""} aria-pressed={option===value} data-navigation-only="true">{option}</button>)}</div>;
}

export function DensityControl({value="Analytical"}:{value?:"Focus"|"Analytical"|"Dense"}) {
  return <div data-figma-node="37:202"><SegmentedControl label="Display density" options={["Focus","Analytical","Dense"] as const} value={value}/></div>;
}
