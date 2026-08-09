import { useEffect, useMemo, useRef, useState } from "react";
import { CandlestickSeries, ColorType, createChart, type UTCTimestamp } from "lightweight-charts";
import type { MarketBar } from "../api/types";
import styles from "./WorkspaceFrame.module.css";

function asUtcTimestamp(value: string): UTCTimestamp { return Math.floor(Date.parse(value) / 1000) as UTCTimestamp; }
function formatPrice(value?: number): string { return typeof value === "number" && Number.isFinite(value) ? value.toFixed(5) : "—"; }
function shortStamp(value?: string): string { return value ? value.replace("T", " ").replace("Z", " UTC") : "—"; }

function tracePath(bars: MarketBar[], valueOf: (bar: MarketBar) => number, low: number, high: number): string {
  if (bars.length < 2 || high <= low) return "";
  return bars.map((bar, index) => {
    const x = (index / (bars.length - 1)) * 1000;
    const y = 405 - ((valueOf(bar) - low) / (high - low)) * 375;
    return `${index === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
  }).join(" ");
}

function navigatorPath(bars: MarketBar[], low: number, high: number): string {
  if (bars.length < 2 || high <= low) return "";
  return bars.map((bar, index) => {
    const x = (index / (bars.length - 1)) * 1000;
    const y = 27 - ((bar.c - low) / (high - low)) * 21;
    return `${index === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
  }).join(" ");
}

export function FixtureChart({ bars, selectedTime, onSelectTime }: { bars: MarketBar[]; selectedTime: string | null; onSelectTime: (value: string) => void }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [hoveredTime, setHoveredTime] = useState<string | null>(null);
  const sessionHigh = useMemo(() => bars.length ? Math.max(...bars.map((bar) => bar.h)) : undefined, [bars]);
  const sessionLow = useMemo(() => bars.length ? Math.min(...bars.map((bar) => bar.l)) : undefined, [bars]);
  const detailBar = useMemo(() => bars.find((bar) => bar.t === hoveredTime) ?? bars.find((bar) => bar.t === selectedTime) ?? bars.at(-1), [bars, hoveredTime, selectedTime]);
  const direction = detailBar && detailBar.c >= detailBar.o ? "up" : "down";
  const change = detailBar ? detailBar.c - detailBar.o : undefined;
  const referenceTraces = useMemo(() => {
    if (sessionHigh === undefined || sessionLow === undefined || bars.length < 2) return null;
    const high = tracePath(bars, (bar) => bar.h, sessionLow, sessionHigh);
    const mid = tracePath(bars, (bar) => (bar.h + bar.l) / 2, sessionLow, sessionHigh);
    const low = tracePath(bars, (bar) => bar.l, sessionLow, sessionHigh);
    const lowReverse = bars.slice().reverse().map((bar, reverseIndex) => {
      const index = bars.length - 1 - reverseIndex;
      const x = (index / (bars.length - 1)) * 1000;
      const y = 405 - ((bar.l - sessionLow) / (sessionHigh - sessionLow)) * 375;
      return `L${x.toFixed(2)},${y.toFixed(2)}`;
    }).join(" ");
    return { high, mid, low, fill: `${high} ${lowReverse} Z`, navigator: navigatorPath(bars, sessionLow, sessionHigh) };
  }, [bars, sessionHigh, sessionLow]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || bars.length === 0) return;
    const chart = createChart(container, {
      width: container.clientWidth,
      height: Math.max(220, container.clientHeight),
      layout: {
        background: { type: ColorType.Solid, color: "#080d13" },
        textColor: "#8998ab",
        fontSize: 10,
        fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: "#16212c", style: 1 },
        horzLines: { color: "#17232e", style: 1 },
      },
      rightPriceScale: {
        borderColor: "#263446",
        scaleMargins: { top: 0.08, bottom: 0.12 },
      },
      timeScale: {
        borderColor: "#263446",
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 2.5,
        barSpacing: 8,
        minBarSpacing: 5,
      },
      crosshair: {
        vertLine: { color: "#2f7df6", width: 1, style: 2, labelBackgroundColor: "#1b4f92" },
        horzLine: { color: "#53647a", width: 1, style: 2, labelBackgroundColor: "#253347" },
      },
    });
    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#18c27d",
      downColor: "#ef5364",
      borderVisible: true,
      borderUpColor: "#37d79a",
      borderDownColor: "#ff7080",
      wickUpColor: "#36d69a",
      wickDownColor: "#ff6f7f",
      priceLineVisible: true,
      priceLineColor: "#438bda",
      priceLineStyle: 2,
      priceLineWidth: 1,
      lastValueVisible: true,
      priceFormat: { type: "price", precision: 5, minMove: 0.00001 },
    });
    series.setData(bars.map((bar) => ({ time: asUtcTimestamp(bar.t), open: bar.o, high: bar.h, low: bar.l, close: bar.c })));
    if (sessionHigh !== undefined) series.createPriceLine({ price: sessionHigh, color: "#2a3a4e", lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: "" });
    if (sessionLow !== undefined) series.createPriceLine({ price: sessionLow, color: "#2a3a4e", lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: "" });
    chart.timeScale().fitContent();
    chart.subscribeCrosshairMove((param) => {
      if (typeof param.time !== "number") { setHoveredTime(null); return; }
      const target = bars.find((bar) => asUtcTimestamp(bar.t) === param.time);
      if (target) { setHoveredTime(target.t); onSelectTime(target.t); }
    });
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(([entry]) => chart.resize(Math.max(1, Math.round(entry.contentRect.width)), Math.max(220, Math.round(entry.contentRect.height))));
    observer?.observe(container);
    return () => { observer?.disconnect(); chart.remove(); };
  }, [bars, onSelectTime, sessionHigh, sessionLow]);

  return <div className={styles.chartWrap} data-testid="primary-canvas" data-chart-role="reference-locked-fixture">
    <div ref={containerRef} className={styles.chart} data-chart-layer="canvas"/>
    {referenceTraces ? <svg data-chart-layer="reference-overlay" viewBox="0 0 1000 420" preserveAspectRatio="none" aria-label="Fixture OHLC high midpoint low reference traces; presentation only" data-presentation-only="true">
      <title>Fixture-only OHLC reference traces. High, midpoint and low are derived directly from the synthetic source bars and carry no structural or predictive authority.</title>
      <path className="ref-fill" d={referenceTraces.fill}/>
      <path className="ref-high" d={referenceTraces.high}/>
      <path className="ref-mid" d={referenceTraces.mid}/>
      <path className="ref-low" d={referenceTraces.low}/>
    </svg> : null}
    <div data-chart-layer="hud" data-testid="chart-detail-hud">
      <strong>{shortStamp(detailBar?.t)}</strong><i/><span>O <strong>{formatPrice(detailBar?.o)}</strong></span><span>H <strong>{formatPrice(detailBar?.h)}</strong></span><span>L <strong>{formatPrice(detailBar?.l)}</strong></span><span>C <strong>{formatPrice(detailBar?.c)}</strong></span><b data-direction={direction}>{change === undefined ? "—" : `${change >= 0 ? "+" : ""}${change.toFixed(5)}`}</b>
    </div>
    <div data-chart-layer="range"><span>FIXTURE HIGH <strong>{formatPrice(sessionHigh)}</strong></span><span>LOW <strong>{formatPrice(sessionLow)}</strong></span></div>
    <div data-chart-layer="badge">OHLC H / HL2 / L TRACES · FIXTURE PRESENTATION ONLY</div>
    {referenceTraces ? <div data-chart-layer="navigator" aria-label="Fixture price range navigator; presentation only" data-presentation-only="true"><svg viewBox="0 0 1000 32" preserveAspectRatio="none"><path d={referenceTraces.navigator}/></svg><i className="navigator-selection"/><b className="navigator-handle navigator-handle-left"/><b className="navigator-handle navigator-handle-right"/></div> : null}
    <div data-chart-layer="footer">
      <span>SELECTED <strong>{selectedTime ? shortStamp(selectedTime) : "move crosshair over fixture bars"}</strong></span>
      <span>BARS <strong data-testid="chart-bar-count">{bars.length}</strong></span>
      <span>MODE <strong>FIRST-VALID FIXTURE</strong></span>
      <span>CURRENT <strong>{formatPrice(bars.at(-1)?.c)}</strong></span>
    </div>
  </div>;
}
