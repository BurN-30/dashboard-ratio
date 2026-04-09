"use client";

import React, { useCallback, useEffect, useState } from "react";
import { ApexOptions } from "apexcharts";
import ReactApexChart from "react-apexcharts";
import { useTheme } from "@/context/ThemeContext";
import DashboardCard from "@/components/common/DashboardCard";
import { fetchHardwareHistory, HardwareHistoryEntry } from "@/lib/api";
import { History, RefreshCw } from "lucide-react";

const TIME_RANGES = [
  { label: "1h", hours: 1 },
  { label: "6h", hours: 6 },
  { label: "24h", hours: 24 },
  { label: "7d", hours: 168 },
  { label: "30d", hours: 720 },
] as const;

type Metric = "cpu" | "ram" | "gpu" | "temp";

const METRICS: { key: Metric; label: string; color: string; unit: string }[] = [
  { key: "cpu", label: "CPU %", color: "#3b82f6", unit: "%" },
  { key: "ram", label: "RAM %", color: "#a855f7", unit: "%" },
  { key: "gpu", label: "GPU %", color: "#10b981", unit: "%" },
  { key: "temp", label: "CPU Temp", color: "#f97316", unit: "°C" },
];

export default function HardwareHistoryChart() {
  const { theme } = useTheme();
  const [hours, setHours] = useState(24);
  const [data, setData] = useState<HardwareHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [visibleMetrics, setVisibleMetrics] = useState<Set<Metric>>(
    new Set(["cpu", "ram"])
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const result = await fetchHardwareHistory(hours);
    if (result) {
      setData(result);
    } else {
      setError("Impossible de charger l'historique");
    }
    setLoading(false);
  }, [hours]);

  useEffect(() => {
    load();
  }, [load]);

  const toggleMetric = (m: Metric) => {
    setVisibleMetrics((prev) => {
      const next = new Set(prev);
      if (next.has(m)) {
        if (next.size > 1) next.delete(m);
      } else {
        next.add(m);
      }
      return next;
    });
  };

  const activeMetrics = METRICS.filter((m) => visibleMetrics.has(m.key));
  const tempOnly =
    visibleMetrics.size === 1 && visibleMetrics.has("temp");

  const series = activeMetrics.map((m) => ({
    name: m.label,
    data: data.map((entry) => {
      const ts = new Date(entry.recorded_at).getTime();
      let val = 0;
      switch (m.key) {
        case "cpu":
          val = entry.cpu?.usage ?? 0;
          break;
        case "ram":
          val = entry.ram?.used_percent ?? 0;
          break;
        case "gpu":
          val = entry.gpu?.usage ?? 0;
          break;
        case "temp":
          val = entry.cpu?.temp ?? 0;
          break;
      }
      return { x: ts, y: Math.round(val * 10) / 10 };
    }),
  }));

  const options: ApexOptions = {
    theme: { mode: theme },
    chart: {
      type: "area",
      height: 320,
      background: "transparent",
      fontFamily: "Outfit, sans-serif",
      toolbar: { show: false },
      zoom: { enabled: true },
      animations: { enabled: data.length < 200 },
    },
    colors: activeMetrics.map((m) => m.color),
    stroke: { width: 2, curve: "smooth" },
    fill: {
      type: "gradient",
      gradient: { opacityFrom: 0.25, opacityTo: 0.05, stops: [0, 100] },
    },
    grid: {
      borderColor: theme === "dark" ? "#374151" : "#E2E8F0",
      xaxis: { lines: { show: false } },
      yaxis: { lines: { show: true } },
    },
    dataLabels: { enabled: false },
    xaxis: {
      type: "datetime",
      axisBorder: { show: false },
      axisTicks: { show: false },
      labels: {
        style: { colors: theme === "dark" ? "#9CA3AF" : "#64748B" },
        datetimeFormatter: {
          hour: "HH:mm",
          day: "dd MMM",
        },
      },
    },
    yaxis: {
      labels: {
        style: { colors: theme === "dark" ? "#9CA3AF" : "#64748B" },
        formatter: (val) => (tempOnly ? `${val}°C` : `${val}%`),
      },
      min: 0,
      max: tempOnly ? undefined : 100,
    },
    tooltip: {
      x: { format: "dd MMM yyyy HH:mm" },
      theme: theme,
    },
    legend: { show: false },
    responsive: [
      {
        breakpoint: 768,
        options: { chart: { height: 250 } },
      },
    ],
  };

  const isLastSelected = (m: Metric) =>
    visibleMetrics.size === 1 && visibleMetrics.has(m);

  const controls = (
    <div className="flex items-center gap-2 flex-wrap">
      {/* Time range selector */}
      <div className="flex items-center bg-gray-100 dark:bg-gray-800 rounded-md p-0.5">
        {TIME_RANGES.map((r) => (
          <button
            key={r.hours}
            onClick={() => setHours(r.hours)}
            className={`px-2.5 py-1 text-xs font-medium rounded transition-colors ${
              hours === r.hours
                ? "bg-white dark:bg-gray-700 shadow-sm text-gray-900 dark:text-white"
                : "text-gray-500 hover:text-gray-900 dark:hover:text-white"
            }`}
          >
            {r.label}
          </button>
        ))}
      </div>

      {/* Metric toggles */}
      <div className="flex items-center gap-1">
        {METRICS.map((m) => (
          <button
            key={m.key}
            onClick={() => toggleMetric(m.key)}
            disabled={isLastSelected(m.key)}
            aria-pressed={visibleMetrics.has(m.key)}
            aria-label={`Toggle ${m.label}`}
            className={`px-2 py-1 text-xs font-medium rounded border transition-colors ${
              isLastSelected(m.key)
                ? "opacity-60 cursor-not-allowed border-current text-white"
                : visibleMetrics.has(m.key)
                  ? "border-current text-white"
                  : "border-gray-300 dark:border-gray-600 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            }`}
            style={
              visibleMetrics.has(m.key)
                ? { backgroundColor: m.color, borderColor: m.color }
                : undefined
            }
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Refresh */}
      <button
        onClick={load}
        disabled={loading}
        className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded transition-colors"
        title="Rafraîchir"
        aria-label="Rafraîchir l'historique"
      >
        <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
      </button>
    </div>
  );

  return (
    <DashboardCard
      title="Hardware History"
      headerRight={controls}
      noPadding
    >
      <div className="px-5 pb-4 pt-1">
        {error ? (
          <div className="h-[320px] flex items-center justify-center">
            <div className="text-center text-gray-400">
              <p className="text-sm">{error}</p>
              <p className="text-xs mt-1">
                L'agent doit être connecté pour collecter des données.
              </p>
            </div>
          </div>
        ) : data.length === 0 && loading ? (
          <div className="h-[320px] flex items-center justify-center">
            <div className="text-center text-gray-400">
              <History className="w-8 h-8 mx-auto mb-2 animate-pulse" />
              <p className="text-sm">Chargement de l'historique...</p>
            </div>
          </div>
        ) : data.length === 0 ? (
          <div className="h-[320px] flex items-center justify-center">
            <div className="text-center text-gray-400">
              <History className="w-8 h-8 mx-auto mb-2" />
              <p className="text-sm">Aucune donnée sur cette période</p>
              <p className="text-xs mt-1">
                Les snapshots sont enregistrés toutes les 60 secondes.
              </p>
            </div>
          </div>
        ) : (
          <div className="-ml-3">
            <ReactApexChart
              options={options}
              series={series}
              type="area"
              height={320}
            />
          </div>
        )}
        {data.length > 0 && (
          <p className="text-[10px] text-gray-400 text-right mt-1">
            {data.length} points
          </p>
        )}
      </div>
    </DashboardCard>
  );
}
