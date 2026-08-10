import { useMemo, useState, type MouseEvent } from "react";
import type { MarketBar } from "../api/types";
import styles from "./WorkspaceFrame.module.css";

const SCENE_W = 805;
const SCENE_H = 322;
const PLOT_LEFT = 8;
const PLOT_RIGHT = 746;
const PLOT_TOP = 12;
const PLOT_BOTTOM = 246;
const NAV_TOP = 278;
const NAV_BOTTOM = 318;

type SceneBar = MarketBar & { visual_reference_only?: boolean };
type MarkerKind = "birth" | "mutation" | "transition" | "censor" | "conflict" | "terminate";
type Marker = { index: number; value: number; kind: MarkerKind; label: string };

function formatPrice(value?: number): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(5) : "—";
}

function interpolateAnchors(anchors: Array<[number, number]>, count: number): number[] {
  const out: number[] = [];
  for (let i = 0; i < count; i += 1) {
    const rightIndex = anchors.findIndex(([idx]) => idx >= i);
    if (rightIndex <= 0) {
      out.push(anchors[0][1]);
      continue;
    }
    const [ri, rv] = anchors[rightIndex];
    const [li, lv] = anchors[rightIndex - 1];
    const t = ri === li ? 0 : (i - li) / (ri - li);
    out.push(lv + (rv - lv) * t);
  }
  return out;
}

function buildReferenceSceneBars(): SceneBar[] {
  const count = 72;
  const closeBase = interpolateAnchors([
    [0, 1.27945], [6, 1.28010], [12, 1.28155], [18, 1.28075], [26, 1.28135],
    [34, 1.28155], [40, 1.28255], [47, 1.28225], [54, 1.28292], [61, 1.28055],
    [65, 1.28085], [69, 1.28172], [71, 1.28155],
  ], count);
  const start = Date.parse("2026-07-23T09:00:00Z");
  let previous = closeBase[0] - 0.00012;
  return closeBase.map((base, index) => {
    const micro = Math.sin(index * 1.67) * 0.000105 + Math.sin(index * 0.51) * 0.000055;
    const close = base + micro;
    const open = index === 0 ? previous : previous + Math.sin(index * 0.93) * 0.000055;
    const high = Math.max(open, close) + 0.000095 + Math.abs(Math.sin(index * 0.71)) * 0.000075;
    const low = Math.min(open, close) - 0.00009 - Math.abs(Math.cos(index * 0.63)) * 0.00007;
    previous = close;
    return {
      t: new Date(start + index * 225_000).toISOString().replace(".000Z", "Z"),
      o: Number(open.toFixed(5)), h: Number(high.toFixed(5)), l: Number(low.toFixed(5)), c: Number(close.toFixed(5)),
      visual_reference_only: true,
    };
  });
}

function movingAverage(values: number[], radius = 2): number[] {
  return values.map((_, index) => {
    const start = Math.max(0, index - radius);
    const end = Math.min(values.length, index + radius + 1);
    const slice = values.slice(start, end);
    return slice.reduce((sum, value) => sum + value, 0) / slice.length;
  });
}

function xFor(index: number, count: number): number {
  return PLOT_LEFT + (index / Math.max(1, count - 1)) * (PLOT_RIGHT - PLOT_LEFT);
}

function yFor(value: number, min: number, max: number): number {
  return PLOT_TOP + ((max - value) / Math.max(0.000001, max - min)) * (PLOT_BOTTOM - PLOT_TOP);
}

function pathFrom(values: Array<number | null>, min: number, max: number): string {
  let drawing = false;
  return values.map((value, index) => {
    if (value === null) { drawing = false; return ""; }
    const command = drawing ? "L" : "M";
    drawing = true;
    return `${command}${xFor(index, values.length).toFixed(2)},${yFor(value, min, max).toFixed(2)}`;
  }).filter(Boolean).join(" ");
}

function areaPath(upper: Array<number | null>, lower: Array<number | null>, min: number, max: number): string {
  const valid = upper.map((value, index) => value === null || lower[index] === null ? null : index).filter((value): value is number => value !== null);
  if (valid.length < 2) return "";
  const start = valid[0];
  const end = valid[valid.length - 1];
  const top = valid.map((index, offset) => `${offset === 0 ? "M" : "L"}${xFor(index, upper.length).toFixed(2)},${yFor(upper[index] as number, min, max).toFixed(2)}`).join(" ");
  const bottom = valid.slice().reverse().map((index) => `L${xFor(index, lower.length).toFixed(2)},${yFor(lower[index] as number, min, max).toFixed(2)}`).join(" ");
  return start <= end ? `${top} ${bottom} Z` : "";
}

function referenceOverlays(count: number) {
  const green = interpolateAnchors([[0,1.27985],[8,1.28040],[13,1.28185],[24,1.28172],[31,1.28210],[40,1.28212],[48,1.28270],[55,1.28345],[60,1.28255],[64,1.28220],[68,1.28250],[71,1.28235]], count)
    .map((value, index) => value + Math.sin(index * 0.62) * 0.000055);
  const greenLower = green.map((value, index) => value - (index < 56 ? 0.00048 : 0.00042));
  const orangeRaw = interpolateAnchors([[0,1.27910],[10,1.27940],[20,1.28035],[30,1.28095],[39,1.28110],[47,1.28172],[55,1.28265]], count);
  const orange = orangeRaw.map((value, index) => index > 56 ? null : value + Math.sin(index * 0.44) * 0.000055);
  const blueRaw = interpolateAnchors([[0,1.27872],[10,1.27902],[18,1.27970],[27,1.28015],[38,1.28085],[47,1.28155],[54,1.28198],[58,1.28155],[61,1.27955],[64,1.27872]], count);
  const blue = blueRaw.map((value, index) => index > 64 ? null : value + Math.sin(index * 0.57) * 0.000045);
  const greyRaw = interpolateAnchors([[0,1.27865],[60,1.27865],[63,1.27875],[66,1.27945],[69,1.27965],[71,1.27950]], count);
  const grey = greyRaw.map((value, index) => index < 62 ? null : value + Math.sin(index * 0.8) * 0.00005);
  return { green, greenLower, orange, blue, grey };
}

function genericOverlays(sceneBars: SceneBar[]) {
  const closes = sceneBars.map((bar) => bar.c);
  const smooth = movingAverage(closes, 2);
  const range = Math.max(...sceneBars.map((bar) => bar.h)) - Math.min(...sceneBars.map((bar) => bar.l));
  return {
    green: smooth.map((value) => value + range * 0.09),
    greenLower: smooth.map((value) => value - range * 0.03),
    orange: smooth.map((value, index) => index > sceneBars.length * 0.76 ? null : value - range * 0.11),
    blue: smooth.map((value, index) => index > sceneBars.length * 0.84 ? null : value - range * 0.19),
    grey: smooth.map((value, index) => index < sceneBars.length * 0.76 ? null : value - range * 0.23),
  };
}

export function FixtureChart({ bars, selectedTime, onSelectTime, referenceMode = false }: {
  bars: MarketBar[];
  selectedTime: string | null;
  onSelectTime: (value: string) => void;
  referenceMode?: boolean;
}) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const sceneBars = useMemo<SceneBar[]>(() => referenceMode ? buildReferenceSceneBars() : bars, [bars, referenceMode]);
  const min = referenceMode ? 1.2780 : Math.min(...sceneBars.map((bar) => bar.l), 1) - 0.00015;
  const max = referenceMode ? 1.2840 : Math.max(...sceneBars.map((bar) => bar.h), 1) + 0.00015;
  const overlays = useMemo(() => referenceMode ? referenceOverlays(sceneBars.length) : genericOverlays(sceneBars), [referenceMode, sceneBars]);
  const detailIndex = hoveredIndex ?? Math.max(0, sceneBars.findIndex((bar) => bar.t === selectedTime));
  const detailBar = sceneBars[detailIndex] ?? sceneBars.at(-1);
  const markers: Marker[] = referenceMode ? [
    { index: 12, value: 1.28208, kind: "birth", label: "B" },
    { index: 40, value: 1.28325, kind: "mutation", label: "M" },
    { index: 49, value: 1.28280, kind: "transition", label: "↗" },
    { index: 53, value: 1.28322, kind: "censor", label: "⊘" },
    { index: 61, value: 1.28035, kind: "conflict", label: "ϟ" },
    { index: 64, value: 1.27935, kind: "terminate", label: "■" },
  ] : [];
  const timeLabels = referenceMode ? ["09:00","09:30","10:00","10:30","11:00","11:30","12:00","12:30","13:00"] : sceneBars.filter((_, index) => index % Math.max(1, Math.floor(sceneBars.length / 7)) === 0).map((bar) => bar.t.slice(11,16));
  const yTicks = referenceMode ? [1.284,1.283,1.282,1.281,1.280,1.279,1.278] : Array.from({length:6},(_,i)=>max-(i/5)*(max-min));

  const onMove = (event: MouseEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * SCENE_W;
    const normalized = Math.max(0, Math.min(1, (x - PLOT_LEFT) / (PLOT_RIGHT - PLOT_LEFT)));
    const index = Math.round(normalized * Math.max(0, sceneBars.length - 1));
    setHoveredIndex(index);
    const target = sceneBars[index];
    if (target) onSelectTime(target.t);
  };

  return <div className={styles.chartWrap} data-testid="primary-canvas" data-chart-role="ovc-reference-scene" data-chart-dynamics="wp3g" data-renderer="ovc-svg-scene">
    <svg className="wp3g-scene" data-testid="reference-scene" viewBox={`0 0 ${SCENE_W} ${SCENE_H}`} preserveAspectRatio="none" onMouseMove={onMove} onMouseLeave={() => setHoveredIndex(null)} aria-label="OVC fixture-only reference chart scene">
      <defs>
        <linearGradient id="wp3g-green-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#35c879" stopOpacity="0.22"/><stop offset="100%" stopColor="#35c879" stopOpacity="0.035"/></linearGradient>
        <linearGradient id="wp3g-nav-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#355fc0" stopOpacity="0.28"/><stop offset="100%" stopColor="#20396f" stopOpacity="0.05"/></linearGradient>
        <filter id="wp3g-soft-glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="1.4" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
        <clipPath id="wp3g-plot-clip"><rect x={PLOT_LEFT} y={PLOT_TOP} width={PLOT_RIGHT-PLOT_LEFT} height={PLOT_BOTTOM-PLOT_TOP}/></clipPath>
      </defs>
      <rect width={SCENE_W} height={SCENE_H} className="wp3g-scene-bg"/>
      <g className="wp3g-grid">
        {yTicks.map((value) => <g key={`y-${value}`}><line x1={PLOT_LEFT} x2={PLOT_RIGHT} y1={yFor(value,min,max)} y2={yFor(value,min,max)}/><text x={797} y={yFor(value,min,max)+3} textAnchor="end">{value.toFixed(5)}</text></g>)}
        {timeLabels.map((label,index) => { const x=PLOT_LEFT+(index/Math.max(1,timeLabels.length-1))*(PLOT_RIGHT-PLOT_LEFT); return <g key={`${label}-${index}`}><line x1={x} x2={x} y1={PLOT_TOP} y2={PLOT_BOTTOM}/><text x={x} y={263} textAnchor={index===0?"start":index===timeLabels.length-1?"end":"middle"}>{label}</text></g>; })}
      </g>
      <g clipPath="url(#wp3g-plot-clip)">
        <path className="wp3g-green-area" d={areaPath(overlays.green, overlays.greenLower, min, max)}/>
        <path className="wp3g-green-line" d={pathFrom(overlays.green, min, max)}/>
        <path className="wp3g-orange-line" d={pathFrom(overlays.orange, min, max)}/>
        <path className="wp3g-blue-line" d={pathFrom(overlays.blue, min, max)}/>
        <path className="wp3g-grey-line" d={pathFrom(overlays.grey, min, max)}/>
        <g className="wp3g-candles">{sceneBars.map((bar,index) => {
          const x=xFor(index,sceneBars.length); const yo=yFor(bar.o,min,max); const yc=yFor(bar.c,min,max); const yh=yFor(bar.h,min,max); const yl=yFor(bar.l,min,max); const up=bar.c>=bar.o; const bodyY=Math.min(yo,yc); const bodyH=Math.max(1.8,Math.abs(yc-yo));
          return <g key={`${bar.t}-${index}`} data-up={up}><line className="wp3g-wick" x1={x} x2={x} y1={yh} y2={yl}/><rect className="wp3g-body" x={x-2.55} y={bodyY} width={5.1} height={bodyH} rx={0.35}/></g>;
        })}</g>
        {markers.map((marker) => { const x=xFor(marker.index,sceneBars.length); const y=yFor(marker.value,min,max); return <g key={`${marker.kind}-${marker.index}`} className={`wp3g-marker wp3g-marker-${marker.kind}`} transform={`translate(${x} ${y})`}><circle r={marker.kind==="terminate"?0:10}/><text y={3.5} textAnchor="middle">{marker.label}</text></g>; })}
        {hoveredIndex !== null ? <line className="wp3g-crosshair" x1={xFor(hoveredIndex,sceneBars.length)} x2={xFor(hoveredIndex,sceneBars.length)} y1={PLOT_TOP} y2={PLOT_BOTTOM}/> : null}
      </g>
      <g className="wp3g-current-price"><line x1={PLOT_LEFT} x2={PLOT_RIGHT} y1={yFor(sceneBars.at(-1)?.c ?? min,min,max)} y2={yFor(sceneBars.at(-1)?.c ?? min,min,max)}/><rect x={748} y={yFor(sceneBars.at(-1)?.c ?? min,min,max)-9} width={54} height={18} rx={2}/><text x={775} y={yFor(sceneBars.at(-1)?.c ?? min,min,max)+3} textAnchor="middle">{formatPrice(sceneBars.at(-1)?.c)}</text></g>
      <g className="wp3g-navigator">
        <rect x={34} y={NAV_TOP} width={744} height={NAV_BOTTOM-NAV_TOP}/>
        <path className="wp3g-nav-area" d={`${pathFrom(sceneBars.map((bar)=>bar.c), min, max).replaceAll(String(PLOT_TOP),String(NAV_TOP))}`}/>
        <polyline points={sceneBars.map((bar,index)=>`${34+(index/Math.max(1,sceneBars.length-1))*744},${NAV_TOP+24-((bar.c-min)/(max-min))*18}`).join(" ")} />
        <rect className="wp3g-nav-selection" x={205} y={NAV_TOP+4} width={540} height={NAV_BOTTOM-NAV_TOP-8}/><rect className="wp3g-nav-handle" x={202} y={NAV_TOP+3} width={6} height={NAV_BOTTOM-NAV_TOP-6}/><rect className="wp3g-nav-handle" x={742} y={NAV_TOP+3} width={6} height={NAV_BOTTOM-NAV_TOP-6}/>
      </g>
    </svg>
    <div className="wp3g-accessible-detail" data-testid="chart-detail-hud">O {formatPrice(detailBar?.o)} H {formatPrice(detailBar?.h)} L {formatPrice(detailBar?.l)} C {formatPrice(detailBar?.c)}</div>
    <span className="wp3g-accessible-detail" data-testid="chart-bar-count">{sceneBars.length}</span>
    <span className="wp3g-reference-label">{referenceMode ? "VISUAL REFERENCE FIXTURE · PRESENTATION ONLY" : "SYNTHETIC FIXTURE · PRESENTATION ONLY"}</span>
  </div>;
}
