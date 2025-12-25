"use client";

import React, { useEffect, useState } from "react";
import { fetchTorrentStats, fetchTorrentHistory } from "@/lib/api";
import { AllStats, TrackerData, Unit3DStats, SharewoodStats } from "@/types/tracker";
import dynamic from "next/dynamic";

// Dynamically import Chart to avoid SSR issues
const TrackerChart = dynamic(() => import("@/components/charts/TrackerChart"), {
  ssr: false,
});

export default function Home() {
  const [stats, setStats] = useState<AllStats | null>(null);
  const [history, setHistory] = useState<AllStats[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      const [currentData, historyData] = await Promise.all([
        fetchTorrentStats(),
        fetchTorrentHistory(),
      ]);
      setStats(currentData);
      setHistory(historyData);
      setLoading(false);
    }
    loadData();

    // Auto-refresh every 5 minutes
    const interval = setInterval(loadData, 5 * 60 * 1000);
    return () => clearInterval(interval);
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
        Tracker Stats
      </h1>
      
      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 md:gap-6 xl:grid-cols-3 2xl:gap-7.5 mb-10">
        {Object.entries(stats).map(([name, data]) => (
          <TrackerCard key={name} name={name} data={data} />
        ))}
      </div>

      {/* Charts */}
      {history && history.length > 0 && (
        <>
          <h2 className="mb-6 text-xl font-bold text-black dark:text-white">
            Ratio History
          </h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
             {Object.keys(stats).map((name) => (
                <div key={name} className="col-span-1">
                   <TrackerChart trackerName={name} history={history} />
                </div>
             ))}
          </div>
        </>
      )}
    </div>
  );
}

function TrackerCard({ name, data }: { name: string; data: TrackerData }) {
  // Helper to unify data access
  const getStats = (d: TrackerData) => {
    const isUnit3D = (d as Unit3DStats).warnings_active !== undefined;
    
    if (isUnit3D) {
      const u = d as Unit3DStats;
      return {
        ratio: u.ratio,
        seed_count: u.count_seed,
        buffer: u.buffer, // "Tampon"
        points: u.points_bonus, // "Coupon" / "Points Bonus"
        upload: u.vol_upload,
        download: u.vol_download,
        seed_time_total: u.seed_time_total,
        seed_time_avg: u.seed_time_avg,
        download_count: u.count_downloaded,
        upload_count: u.count_up_total || u.count_up_non_anon || "0"
      };
    } else {
      const s = d as SharewoodStats;
      return {
        ratio: s.ratio,
        seed_count: s.count_seed,
        buffer: s.buffer, // "Capacité de DL"
        points: s.points_bonus,
        upload: s.vol_upload,
        download: s.vol_download,
        seed_time_total: s.time_seed_total,
        seed_time_avg: s.time_seed_avg,
        download_count: s.count_download,
        upload_count: s.count_upload
      };
    }
  };

  const stats = getStats(data);

  return (
    <div className="rounded-sm border border-gray-200 bg-white p-6 shadow-theme-md dark:border-gray-700 dark:bg-gray-dark">
      <div className="flex items-center justify-between mb-6">
        <h4 className="text-xl font-bold text-black dark:text-white">
          {name}
        </h4>
        <span className={`px-3 py-1 rounded-full text-sm font-bold ${parseFloat(stats.ratio) >= 1 ? 'bg-success-500/10 text-success-500' : 'bg-error-500/10 text-error-500'}`}>
            Ratio: {stats.ratio}
        </span>
      </div>

      {/* Primary Stats */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="space-y-1">
            <p className="text-xs text-gray-500 uppercase">Buffer / Capacité</p>
            <p className="text-lg font-bold text-black dark:text-white">{stats.buffer}</p>
        </div>
        <div className="space-y-1">
            <p className="text-xs text-gray-500 uppercase">Points Bonus</p>
            <p className="text-lg font-bold text-brand-500">{stats.points}</p>
        </div>
        <div className="space-y-1">
            <p className="text-xs text-gray-500 uppercase">Upload Vol.</p>
            <p className="text-sm font-medium text-black dark:text-white">{stats.upload}</p>
        </div>
        <div className="space-y-1">
            <p className="text-xs text-gray-500 uppercase">Download Vol.</p>
            <p className="text-sm font-medium text-black dark:text-white">{stats.download}</p>
        </div>
      </div>

      {/* Super Useful Stats */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
        <h5 className="text-sm font-semibold text-gray-500 mb-3">Activity & Seeding</h5>
        <div className="space-y-2">
            <div className="flex justify-between text-sm">
                <span className="text-gray-600 dark:text-gray-400">Torrents Seeding</span>
                <span className="font-medium text-black dark:text-white">{stats.seed_count}</span>
            </div>
            <div className="flex justify-between text-sm">
                <span className="text-gray-600 dark:text-gray-400">Torrents Downloaded</span>
                <span className="font-medium text-black dark:text-white">{stats.download_count}</span>
            </div>
            <div className="flex justify-between text-sm">
                <span className="text-gray-600 dark:text-gray-400">Total Seed Time</span>
                <span className="font-medium text-black dark:text-white">{stats.seed_time_total}</span>
            </div>
            <div className="flex justify-between text-sm">
                <span className="text-gray-600 dark:text-gray-400">Avg Seed Time</span>
                <span className="font-medium text-black dark:text-white">{stats.seed_time_avg}</span>
            </div>
        </div>
      </div>
    </div>
  );
}
