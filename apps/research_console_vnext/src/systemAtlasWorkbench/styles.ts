import type { StylesheetJson } from "cytoscape";

export const atlasWorkbenchStyles: StylesheetJson = [
  { selector: "node", style: { width: 148, height: 48, shape: "round-rectangle", "background-color": "#111923", "border-color": "#3986a8", "border-width": 1.5, color: "#dce9ef", label: "data(label)", "font-family": "Segoe UI, sans-serif", "font-size": 11, "font-weight": 600, "text-wrap": "wrap", "text-max-width": "132px", "text-valign": "center", "text-halign": "center", "overlay-opacity": 0 } },
  { selector: "node[domain = 'market']", style: { "border-color": "#d79a42" } },
  { selector: "node[domain = 'research']", style: { "border-color": "#51a77d" } },
  { selector: "node[domain = 'development']", style: { "border-color": "#5ea4c7" } },
  { selector: "node[domain = 'governance']", style: { "border-color": "#ae83c9" } },
  { selector: "node[family = 'domain']", style: { shape: "rectangle", width: 118, height: 34, "background-color": "#171b20", "border-width": 2, "font-size": 10 } },
  { selector: "node[family = 'authority']", style: { shape: "diamond", width: 74, height: 74, "background-color": "#191528", "border-color": "#ae83c9" } },
  { selector: "node[family = 'record']", style: { shape: "tag", "background-color": "#101d1a" } },
  { selector: "node[family = 'contract']", style: { shape: "hexagon", "background-color": "#18202a" } },
  { selector: "node[family = 'assurance']", style: { shape: "barrel", "background-color": "#18221c", "border-color": "#65a872" } },
  { selector: "node[state = 'reserved']", style: { "background-color": "#241d12", "border-color": "#d79a42", "border-style": "double", "border-width": 4 } },
  { selector: "node[state = 'historical']", style: { opacity: 0.42, "border-style": "dashed" } },
  { selector: "node[state = 'forbidden']", style: { "background-color": "#271516", "border-color": "#e06465", "border-style": "dashed", "border-width": 3 } },
  { selector: ".query-hidden", style: { display: "none" } },
  { selector: "node:selected", style: { "border-color": "#ffffff", "border-width": 3, "background-color": "#1c3040" } },
  { selector: "edge", style: { width: 1.5, "line-color": "#36515e", "target-arrow-color": "#36515e", "target-arrow-shape": "triangle", "curve-style": "taxi", "taxi-direction": "rightward", "arrow-scale": 0.75, opacity: 0.72 } },
  { selector: "edge[family = 'authority']", style: { "line-color": "#ae83c9", "target-arrow-color": "#ae83c9", "line-style": "dotted", width: 3 } },
  { selector: "edge[family = 'data']", style: { "line-color": "#4b9a78", "target-arrow-color": "#4b9a78" } },
  { selector: "edge[family = 'assurance']", style: { "line-color": "#65a872", "target-arrow-color": "#65a872" } },
  { selector: "edge[state = 'reserved']", style: { "line-color": "#b07b35", "target-arrow-color": "#b07b35", "line-style": "dashed" } },
  { selector: "edge[state = 'historical']", style: { opacity: 0.18, "line-style": "dotted" } },
  { selector: "edge[family = 'prohibition']", style: { "line-color": "#e06465", "target-arrow-color": "#e06465", "target-arrow-shape": "tee", "line-style": "dashed", width: 4 } },
  { selector: ".authority-hidden", style: { display: "none" } }
];
