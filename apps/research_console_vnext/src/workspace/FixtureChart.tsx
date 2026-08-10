import { useEffect, useMemo, useRef, useState } from "react";
import { CandlestickSeries, ColorType, createChart, type UTCTimestamp } from "lightweight-charts";
import type { MarketBar } from "../api/types";
import styles from "./WorkspaceFrame.module.css";

function asUtcTimestamp(value: string): UTCTimestamp { return Math.floor(Date.parse(value) / 1000) as UTCTimestamp; }
function formatPrice(value?: number): string { return typeof value === "number" && Number.isFinite(value) ? value.toFixed(5) : "—"; }
function shortStamp(value?: string): string { return value ? value.replace("T", " ").replace("Z", " UTC") : "—"; }

function navigatorPath(bars: MarketBar[], low: number, high: number): string {
  if (bars.length < 2 || high <= low) return "";
  return bars.map((bar, index) => {
    const x = (index / (bars.length - 1)) * 1000;
    const y = 27 - ((bar.c - low) / (high - low)) * 21;
    return `${index === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
  }).join(" ");
}

type EnvelopePoint = {
  x: number;
  high: number;
  bodyHigh: number;
  mid: number;
  close: number;
  bodyLow: number;
  low: number;
};

type OverlayGeometry = {
  width: number;
  height: number;
  outer: string;
  body: string;
  high: string;
  mid: string;
  close: string;
  low: string;
};

function pointPath(points: EnvelopePoint[], key: keyof Omit<EnvelopePoint, "x">): string {
  return points.map((point, index) => `${index === 0 ? "M" : "L"}${point.x.toFixed(2)},${point[key].toFixed(2)}`).join(" ");
}

function ribbonPath(points: EnvelopePoint[], upper: "high" | "bodyHigh", lower: "low" | "bodyLow"): string {
  if (points.length < 2) return "";
  const forward = points.map((point, index) => `${index === 0 ? "M" : "L"}${point.x.toFixed(2)},${point[upper].toFixed(2)}`).join(" ");
  const reverse = points.slice().reverse().map((point) => `L${point.x.toFixed(2)},${point[lower].toFixed(2)}`).join(" ");
  return `${forward} ${reverse} Z`;
}

export function FixtureChart({ bars, selectedTime, onSelectTime }: { bars: MarketBar[]; selectedTime: string | null; onSelectTime: (value: string) => void }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [hoveredTime, setHoveredTime] = useState<string | null>(null);
  const [overlayGeometry, setOverlayGeometry] = useState<OverlayGeometry | null>(null);
  const sessionHigh = useMemo(() => bars.length ? Math.max(...bars.map((bar) => bar.h)) : undefined, [bars]);
  const sessionLow = useMemo(() => bars.length ? Math.min(...bars.map((bar) => bar.l)) : undefined, [bars]);
  const detailBar = useMemo(() => bars.find((bar) => bar.t === hoveredTime) ?? bars.find((bar) => bar.t === selectedTime) ?? bars.at(-1), [bars, hoveredTime, selectedTime]);
  const direction = detailBar && detailBar.c >= detailBar.o ? "up" : "down";
  const change = detailBar ? detailBar.c - detailBar.o : undefined;
  const navigator = useMemo(() => sessionHigh === undefined || sessionLow === undefined ? "" : navigatorPath(bars, sessionLow, sessionHigh), [bars, sessionHigh, sessionLow]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || bars.length === 0) return;
    let disposed = false;
    let frame = 0;
    setOverlayGeometry(null);

    const chart = createChart(container, {
      width: container.clientWidth,
      height: Math.max(220, container.clientHeight),
      layout: {
        background: { type: ColorType.Solid, color: "#070c12" },
        textColor: "#93a2b5",
        fontSize: 10,
        fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: "#14202a", style: 1 },
        horzLines: { color: "#172631", style: 1 },
      },
      rightPriceScale: {
        borderColor: "#2a394b",
        scaleMargins: { top: 0.08, bottom: 0.12 },
      },
      timeScale: {
        borderColor: "#2a394b",
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 2.1,
        barSpacing: 9.2,
        minBarSpacing: 5.5,
      },
      crosshair: {
        vertLine: { color: "#357ff7", width: 1, style: 2, labelBackgroundColor: "#1b4f92" },
        horzLine: { color: "#60748c", width: 1, style: 2, labelBackgroundColor: "#27384d" },
      },
    });
    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#10cf82",
      downColor: "#ff4d61",
      borderVisible: true,
      borderUpColor: "#42efa9",
      borderDownColor: "#ff7180",
      wickUpColor: "#5af2b2",
      wickDownColor: "#ff7a88",
      priceLineVisible: true,
      priceLineColor: "#4b9cff",
      priceLineStyle: 2,
      priceLineWidth: 1,
      lastValueVisible: true,
      priceFormat: { type: "price", precision: 5, minMove: 0.00001 },
    });
    series.setData(bars.map((bar) => ({ time: asUtcTimestamp(bar.t), open: bar.o, high: bar.h, low: bar.l, close: bar.c })));
    if (sessionHigh !== undefined) series.createPriceLine({ price: sessionHigh, color: "#33455a", lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: "" });
    if (sessionLow !== undefined) series.createPriceLine({ price: sessionLow, color: "#33455a", lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: "" });
    chart.timeScale().fitContent();

    const computeOverlay = () => {
      if (disposed) return;
      const points = bars.flatMap((bar): EnvelopePoint[] => {
        const x = chart.timeScale().timeToCoordinate(asUtcTimestamp(bar.t));
        const high = series.priceToCoordinate(bar.h);
        const bodyHigh = series.priceToCoordinate(Math.max(bar.o, bar.c));
        const mid = series.priceToCoordinate((bar.h + bar.l) / 2);
        const close = series.priceToCoordinate(bar.c);
        const bodyLow = series.priceToCoordinate(Math.min(bar.o, bar.c));
        const low = series.priceToCoordinate(bar.l);
        if ([x, high, bodyHigh, mid, close, bodyLow, low].some((value) => value === null)) return [];
        return [{ x: Number(x), high: Number(high), bodyHigh: Number(bodyHigh), mid: Number(mid), close: Number(close), bodyLow: Number(bodyLow), low: Number(low) }];
      });
      if (points.length < 2) return;
      setOverlayGeometry({
        width: Math.max(1, container.clientWidth),
        height: Math.max(220, container.clientHeight),
        outer: ribbonPath(points, "high", "low"),
        body: ribbonPath(points, "bodyHigh", "bodyLow"),
        high: pointPath(points, "high"),
        mid: pointPath(points, "mid"),
        close: pointPath(points, "close"),
        low: pointPath(points, "low"),
      });
    };
    const scheduleOverlay = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(computeOverlay);
    };
    scheduleOverlay();
    chart.timeScale().subscribeVisibleLogicalRangeChange(scheduleOverlay);

    chart.subscribeCrosshairMove((param) => {
      if (typeof param.time !== "number") { setHoveredTime(null); return; }
      const target = bars.find((bar) => asUtcTimestamp(bar.t) === param.time);
      if (target) { setHoveredTime(target.t); onSelectTime(target.t); }
    });
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(([entry]) => {
      chart.resize(Math.max(1, Math.round(entry.contentRect.width)), Math.max(220, Math.round(entry.contentRect.height)));
      scheduleOverlay();
    });
    observer?.observe(container);
    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(scheduleOverlay);
      observer?.disconnect();
      chart.remove();
    };
  }, [bars, onSelectTime, sessionHigh, sessionLow]);

  return <div className={styles.chartWrap} data-testid="primary-canvas" data-chart-role="reference-locked-fixture" data-chart-dynamics="wp3f">
    <div ref={containerRef} className={styles.chart} data-chart-layer="canvas"/>
    {overlayGeometry ? <svg
      data-chart-layer="reference-overlay"
      data-presentation-only="true"
      data-coordinate-binding="lightweight-chart-api"
      viewBox={`0 0 ${overlayGeometry.width} ${overlayGeometry.height}`}
      preserveAspectRatio="none"
      aria-label="Fixture OHLC price-following coverage envelope; presentation only"
    >
      <title>Fixture-only OHLC envelope. Geometry is bound to the chart's actual time and price coordinates and is derived directly from synthetic source bars. It carries no structural or predictive authority.</title>
      <defs>
        <linearGradient id="wp3f-envelope-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#36dc8e" stopOpacity="0.22"/>
          <stop offset="48%" stopColor="#1ead71" stopOpacity="0.12"/>
          <stop offset="100%" stopColor="#159d69" stopOpacity="0.055"/>
        </linearGradient>
        <linearGradient id="wp3f-body-fill" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#2ba5ff" stopOpacity="0.035"/>
          <stop offset="55%" stopColor="#48e6a2" stopOpacity="0.10"/>
          <stop offset="100%" stopColor="#2ba5ff" stopOpacity="0.035"/>
        </linearGradient>
      </defs>
      <path className="wp3f-envelope-halo" d={overlayGeometry.outer}/>
      <path className="wp3f-envelope-fill" data-testid="wp3f-envelope-fill" d={overlayGeometry.outer}/>
      <path className="wp3f-body-ribbon" d={overlayGeometry.body}/>
      <path className="wp3f-envelope-high" d={overlayGeometry.high}/>
      <path className="wp3f-flow-glow" d={overlayGeometry.close}/>
      <path className="wp3f-flow-line" d={overlayGeometry.close}/>
      <path className="wp3f-envelope-mid" d={overlayGeometry.mid}/>
      <path className="wp3f-envelope-low" d={overlayGeometry.low}/>
    </svg> : null}
    <div data-chart-layer="hud" data-testid="chart-detail-hud">
      <strong>{shortStamp(detailBar?.t)}</strong><i/><span>O <strong>{formatPrice(detailBar?.o)}</strong></span><span>H <strong>{formatPrice(detailBar?.h)}</strong></span><span>L <strong>{formatPrice(detailBar?.l)}</strong></span><span>C <strong>{formatPrice(detailBar?.c)}</strong></span><b data-direction={direction}>{change === undefined ? "—" : `${change >= 0 ? "+" : ""}${change.toFixed(5)}`}</b>
    </div>
    <div data-chart-layer="range"><span>FIXTURE HIGH <strong>{formatPrice(sessionHigh)}</strong></span><span>LOW <strong>{formatPrice(sessionLow)}</strong></span></div>
    <div data-chart-layer="badge">OHLC PRICE-FOLLOWING ENVELOPE · FIXTURE PRESENTATION ONLY</div>
    {navigator ? <div data-chart-layer="navigator" aria-label="Fixture price range navigator; presentation only" data-presentation-only="true"><svg viewBox="0 0 1000 32" preserveAspectRatio="none"><defs><linearGradient id="wp3f-nav-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#3f79df" stopOpacity="0.23"/><stop offset="100%" stopColor="#163a7a" stopOpacity="0.03"/></linearGradient></defs><path className="navigator-area" d={`${navigator} L1000,31 L0,31 Z`}/><path className="navigator-line" d={navigator}/></svg><i className="navigator-selection"/><b className="navigator-handle navigator-handle-left"/><b className="navigator-handle navigator-handle-right"/></div> : null}
    <div data-chart-layer="footer">
      <span>SELECTED <strong>{selectedTime ? shortStamp(selectedTime) : "move crosshair over fixture bars"}</strong></span>
      <span>BARS <strong data-testid="chart-bar-count">{bars.length}</strong></span>
      <span>MODE <strong>FIRST-VALID FIXTURE</strong></span>
      <span>CURRENT <strong>{formatPrice(bars.at(-1)?.c)}</strong></span>
    </div>
  </div>;
}
