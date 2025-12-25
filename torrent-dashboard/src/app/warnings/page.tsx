"use client";

import React, { useEffect, useState } from "react";
import { fetchTorrentStats } from "@/lib/api";
import { AllStats, TrackerData, Unit3DStats, SharewoodStats } from "@/types/tracker";

export default function WarningsPage() {
  const [stats, setStats] = useState<AllStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      const data = await fetchTorrentStats();
      setStats(data);
      setLoading(false);
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-100 dark:bg-gray-dark">
        <div className="h-16 w-16 animate-spin rounded-full border-4 border-solid border-brand-500 border-t-transparent"></div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-100 dark:bg-gray-dark">
        <p className="text-xl text-error-500">Failed to load data.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-screen-2xl p-4 md:p-6 2xl:p-10">
      <h1 className="mb-6 text-2xl font-bold text-black dark:text-white">
        Warnings & Hit and Run
      </h1>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 md:gap-6 xl:grid-cols-3 2xl:gap-7.5">
        {Object.entries(stats).map(([name, data]) => (
          <WarningCard key={name} name={name} data={data} />
        ))}
      </div>
    </div>
  );
}

function WarningCard({ name, data }: { name: string; data: TrackerData }) {
  const isUnit3D = (data: TrackerData): data is Unit3DStats => {
    return (data as Unit3DStats).warnings_active !== undefined;
  };

  const isSharewood = (data: TrackerData): data is SharewoodStats => {
    return (data as SharewoodStats).vol_upload_final !== undefined;
  };

  let warnings = "0";
  let hitAndRun = "0";

  if (isUnit3D(data)) {
    warnings = data.warnings_active;
    hitAndRun = data.hit_and_run;
  } else if (isSharewood(data)) {
    warnings = data.warnings || "0 / 3";
    hitAndRun = data.hit_and_run;
  }

  // Determine status color
  const hasWarnings = warnings !== "0" && warnings !== "0 / 3";
  const hasHitAndRun = hitAndRun !== "0";
  
  const statusColor = (hasWarnings || hasHitAndRun) ? "text-error-500" : "text-success-500";
  const borderColor = (hasWarnings || hasHitAndRun) ? "border-error-500" : "border-gray-200 dark:border-gray-700";

  return (
    <div className={`rounded-sm border ${borderColor} bg-white py-6 px-7.5 shadow-theme-md dark:bg-gray-dark`}>
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-xl font-bold text-black dark:text-white">
          {name}
        </h4>
        {(hasWarnings || hasHitAndRun) && (
            <span className="inline-flex rounded-full bg-error-500/10 px-3 py-1 text-sm font-medium text-error-500">
                Action Required
            </span>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4">
        <div className="flex items-center justify-between border-b border-gray-200 pb-4 dark:border-gray-700">
            <span className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Active Warnings
            </span>
            <span className={`text-lg font-bold ${warnings !== "0" && warnings !== "0 / 3" ? "text-error-500" : "text-success-500"}`}>
                {warnings}
            </span>
        </div>

        <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Hit & Run Count
            </span>
            <span className={`text-lg font-bold ${hitAndRun !== "0" ? "text-warning-500" : "text-success-500"}`}>
                {hitAndRun}
            </span>
        </div>
      </div>
    </div>
  );
}
