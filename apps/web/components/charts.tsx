"use client";

import dynamic from "next/dynamic";
import type { EChartsOption } from "echarts";
import { ablationData, taskHeatmap } from "../lib/demo-data";
import type { CategoryScore, Run } from "../lib/types";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });
const ink = "#272932";
const muted = "#777b86";
const violet = "#7255d9";
const cyan = "#00a6a6";

function Chart({ option, label, className = "chart" }: { option: EChartsOption; label: string; className?: string }) {
  return <div role="img" aria-label={label}><ReactECharts option={option} className={className} opts={{ renderer: "svg" }} /></div>;
}

export function CategoryChart({ categories }: { categories: CategoryScore[] }) {
  const option: EChartsOption = {
    animationDuration: 350,
    grid: { left: 78, right: 36, top: 12, bottom: 28 },
    xAxis: { type: "value", min: 0, max: 100, axisLabel: { color: muted }, splitLine: { lineStyle: { color: "#e7e7e3" } } },
    yAxis: { type: "category", inverse: true, data: categories.map((row) => row.category), axisLabel: { color: ink }, axisLine: { show: false }, axisTick: { show: false } },
    tooltip: { trigger: "axis", formatter: (items: unknown) => { const first = (items as Array<{ name: string; value: number }>)[0]; return `${first.name}<br><strong>${first.value.toFixed(1)}</strong> / 100`; } },
    series: [{ type: "bar", data: categories.map((row) => ({ value: row.score, itemStyle: { color: row.category === "safety" ? cyan : violet, borderRadius: [0, 5, 5, 0] } })), barWidth: 14 }],
  };
  return <Chart option={option} label="Category scores from zero to one hundred" />;
}

export function ReliabilityChart({ run }: { run: Run }) {
  const summary = run.summary!;
  const ks = Object.keys(summary.pass_at_k);
  const option: EChartsOption = {
    grid: { left: 48, right: 20, top: 34, bottom: 38 }, legend: { top: 0, textStyle: { color: muted } },
    xAxis: { type: "category", data: ks.map((k) => `k=${k}`), axisLine: { lineStyle: { color: "#d4d5d2" } } },
    yAxis: { type: "value", min: 0, max: 1, axisLabel: { formatter: (value: number) => `${Math.round(value * 100)}%`, color: muted }, splitLine: { lineStyle: { color: "#e7e7e3" } } },
    tooltip: { trigger: "axis", valueFormatter: (value) => `${(Number(value) * 100).toFixed(1)}%` },
    series: [
      { name: "pass@k", type: "line", smooth: true, symbolSize: 8, lineStyle: { color: cyan, width: 3 }, itemStyle: { color: cyan }, data: ks.map((k) => summary.pass_at_k[k]) },
      { name: "strict passᵏ", type: "line", smooth: true, symbolSize: 8, lineStyle: { color: violet, width: 3 }, itemStyle: { color: violet }, data: ks.map((k) => summary.pass_power_k[k]) },
    ],
  };
  return <Chart option={option} label="Reliability curves for pass at k and strict pass to the power k" />;
}

export function HeatmapChart() {
  const option: EChartsOption = {
    grid: { left: 68, right: 18, top: 12, bottom: 42 },
    xAxis: { type: "category", data: ["Output", "Tools", "Grounding", "Memory", "Robustness", "Security"], axisLabel: { color: muted, rotate: 22 }, splitArea: { show: true } },
    yAxis: { type: "category", data: ["Base", "Perturbed", "Ablated"], axisLabel: { color: muted }, splitArea: { show: true } },
    visualMap: { min: 50, max: 100, calculable: false, orient: "horizontal", left: "center", bottom: -2, inRange: { color: ["#efe7fc", "#9f8adb", "#00a6a6"] }, textStyle: { color: muted } },
    tooltip: { position: "top", formatter: (item: unknown) => { const data = (item as { data: number[] }).data; return `${data[2]} / 100`; } },
    series: [{ type: "heatmap", data: taskHeatmap, label: { show: true, color: ink, fontSize: 10 }, emphasis: { itemStyle: { shadowBlur: 10, shadowColor: "rgba(0,0,0,.2)" } } }],
  };
  return <Chart option={option} label="Task-pack performance heatmap across base, perturbed, and ablated variants" />;
}

export function ParetoChart({ runs }: { runs: Run[] }) {
  const points = runs.filter((run) => run.summary?.quality_index !== null).map((run) => ({ name: run.agent?.name, value: [run.summary!.latency_p50_ms, run.summary!.quality_index] }));
  const option: EChartsOption = {
    grid: { left: 54, right: 25, top: 18, bottom: 45 },
    xAxis: { type: "value", name: "p50 latency (ms)", nameLocation: "middle", nameGap: 30, axisLabel: { color: muted }, splitLine: { lineStyle: { color: "#e7e7e3" } } },
    yAxis: { type: "value", name: "Quality", min: 50, max: 100, axisLabel: { color: muted }, splitLine: { lineStyle: { color: "#e7e7e3" } } },
    tooltip: { formatter: (item: unknown) => { const point = item as { name: string; value: number[] }; return `${point.name}<br>${point.value[1]} quality · ${point.value[0]} ms`; } },
    series: [{ type: "scatter", symbolSize: 19, data: points, itemStyle: { color: cyan, borderColor: "#fff", borderWidth: 3 }, label: { show: true, position: "top", formatter: "{b}", color: ink } }],
  };
  return <Chart option={option} label="Cost and quality Pareto chart using latency as the efficiency dimension" />;
}

export function AblationChart() {
  const option: EChartsOption = {
    grid: { left: 172, right: 36, top: 14, bottom: 32 },
    xAxis: { type: "value", min: -25, max: 5, axisLabel: { formatter: "{value} pp", color: muted }, splitLine: { lineStyle: { color: "#e7e7e3" } } },
    yAxis: { type: "category", inverse: true, data: ablationData.map((row) => row.name), axisLabel: { color: ink, fontSize: 11 }, axisLine: { show: false }, axisTick: { show: false } },
    tooltip: { formatter: (item: unknown) => { const point = item as { dataIndex: number }; const row = ablationData[point.dataIndex]; return `${row.name}<br><strong>${row.delta} pp</strong><br>95% CI ${row.low} to ${row.high}`; } },
    series: [{ type: "scatter", symbolSize: 13, data: ablationData.map((row, index) => [row.delta, index]), itemStyle: { color: violet }, markLine: { silent: true, symbol: "none", data: [{ xAxis: 0 }], lineStyle: { color: "#9b9da4", type: "dashed" } } }],
  };
  return <Chart option={option} label="Ablation quality deltas with values listed in the accompanying table" />;
}
