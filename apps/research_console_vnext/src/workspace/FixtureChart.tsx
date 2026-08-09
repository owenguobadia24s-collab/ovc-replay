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
      layout: { background: { type: ColorType.Solid, color: "#0a1018" }, textColor: "#8e9bb0" },
      grid: { vertLines: { color: "#172235" }, horzLines: { color: "#172235" } },
      rightPriceScale: { borderColor: "#253044" }, timeScale: { borderColor: "#253044", timeVisible: true, secondsVisible: false },
      crosshair: { vertLine: { color: "#6d8cff" }, horzLine: { color: "#44516a" } },
    });
    const series = chart.addSeries(CandlestickSeries, { upColor: "#42c994", downColor: "#e06b78", borderVisible: false, wickUpColor: "#42c994", wickDownColor: "#e06b78" });
    series.setData(bars.map((bar) => ({ time: asUtcTimestamp(bar.t), open: bar.o, high: bar.h, low: bar.l, close: bar.c })));
    chart.timeScale().fitContent();
    chart.subscribeCrosshairMove((param) => {
      if (typeof param.time !== "number") return;
      const target = bars.find((bar) => asUtcTimestamp(bar.t) === param.time);
      if (target) onSelectTime(target.t);
    });
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(([entry]) => chart.resize(Math.max(1, Math.round(entry.contentRect.width)), Math.max(220, Math.round(entry.contentRect.height))));
    observer?.observe(container);
    return () => { observer?.disconnect(); chart.remove(); };
  }, [bars, onSelectTime]);
  return <div className={styles.chartWrap} data-testid="primary-canvas"><div ref={containerRef} className={styles.chart}/><div className={styles.chartSelection}>Selected first-valid time: <strong>{selectedTime ?? "move crosshair over fixture bars"}</strong></div><div className={styles.chartAttribution}>Chart rendering: <a href="https://www.tradingview.com/" target="_blank" rel="noreferrer">TradingView Lightweight Charts</a> · fixture-only</div></div>;
}
