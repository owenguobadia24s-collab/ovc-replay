import { useEffect, useRef } from "react";
import { CandlestickSeries, ColorType, createChart, type UTCTimestamp } from "lightweight-charts";
import type { MarketBar } from "../api/types";
import styles from "./WorkspaceFrame.module.css";

function asUtcTimestamp(value: string): UTCTimestamp { return Math.floor(Date.parse(value) / 1000) as UTCTimestamp; }

export function FixtureChart({ bars, selectedTime, onSelectTime }: { bars: MarketBar[]; selectedTime: string | null; onSelectTime: (value: string) => void }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const container = containerRef.current;
    if (!container || bars.length === 0) return;
    const chart = createChart(container, {
      width: container.clientWidth,
      height: Math.max(220, container.clientHeight),
      layout: { background: { type: ColorType.Solid, color: "#0a1017" }, textColor: "#8897aa", attributionLogo: false },
      grid: { vertLines: { color: "#17202b" }, horzLines: { color: "#17202b" } },
      rightPriceScale: { borderColor: "#263140" }, timeScale: { borderColor: "#263140", timeVisible: true, secondsVisible: false, rightOffset: 2, barSpacing: 9 },
      crosshair: { vertLine: { color: "#2f7df6" }, horzLine: { color: "#56667c" } },
    });
    const series = chart.addSeries(CandlestickSeries, { upColor: "#24c681", downColor: "#ef5b6c", borderVisible: false, wickUpColor: "#24c681", wickDownColor: "#ef5b6c" });
    series.setData(bars.map((bar) => ({ time: asUtcTimestamp(bar.t), open: bar.o, high: bar.h, low: bar.l, close: bar.c })));
    chart.timeScale().fitContent();
    chart.subscribeCrosshairMove((param) => { if (typeof param.time !== "number") return; const target = bars.find((bar) => asUtcTimestamp(bar.t) === param.time); if (target) onSelectTime(target.t); });
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(([entry]) => chart.resize(Math.max(1, Math.round(entry.contentRect.width)), Math.max(220, Math.round(entry.contentRect.height))));
    observer?.observe(container);
    return () => { observer?.disconnect(); chart.remove(); };
  }, [bars, onSelectTime]);
  return <div className={styles.chartWrap} data-testid="primary-canvas"><div ref={containerRef} className={styles.chart}/><div className={styles.chartOverlayBadge}>FIXTURE · DISPLAY ONLY</div><div className={styles.chartSelection}>Selected first-valid time: <strong>{selectedTime ?? "move crosshair over fixture bars"}</strong></div><div className={styles.chartAttribution}>TradingView Lightweight Charts · fixture rendering only</div></div>;
}
