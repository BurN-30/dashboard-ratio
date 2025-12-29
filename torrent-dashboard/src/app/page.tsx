"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useToast } from "@/context/ToastContext";
import { fetchTorrentStats, fetchTorrentHistory } from "@/lib/api";
import { AllStats, TrackerData, Unit3DStats, SharewoodStats } from "@/types/tracker";
import { ArrowUp, ArrowDown, Coins, ArrowRightLeft, UploadCloud, DownloadCloud, Clock, Activity } from "lucide-react";
import dynamic from "next/dynamic";
import RefreshButton from "@/components/RefreshButton";
import LastUpdateInfo from "@/components/LastUpdateInfo";
import Navbar from "@/components/Navbar";

// Dynamically import Chart to avoid SSR issues
const TrackerChart = dynamic(() => import("@/components/charts/TrackerChart"), {
  ssr: false,
});

// === COMPOSANTS STYLE "DASHBOARD" (Identiques à HardwareMonitor) ===

const DashboardCard = ({ title, icon: Icon, children, className = "" }: any) => (
  <div className={`rounded-sm border border-gray-200 bg-white p-6 shadow-theme-md dark:border-gray-700 dark:bg-gray-800 ${className}`}>
    <div className="flex items-center justify-between mb-4">
      <h4 className="text-xl font-bold text-black dark:text-white flex items-center gap-2">
        {Icon && <Icon className="w-5 h-5 text-brand-500" />}
        {title}
      </h4>
    </div>
    {children}
  </div>
);

const StatRow = ({ label, value, subValue, icon: Icon, highlight = false }: any) => (
  <div className="flex justify-between items-center py-2 border-b border-gray-100 dark:border-gray-700 last:border-0">
    <span className="text-sm text-gray-600 dark:text-gray-400 flex items-center gap-2">
      {Icon && <Icon className="w-4 h-4 text-gray-400" />}
      {label}
    </span>
    <div className="text-right">
      <div className={`text-sm font-medium ${highlight ? "text-brand-500 font-bold" : "text-black dark:text-white"}`}>
        {value}
      </div>
      {subValue && <div className="text-xs text-gray-500">{subValue}</div>}
    </div>
  </div>
);

// === MAIN PAGE ===

export default function Home() {
  const [stats, setStats] = useState<AllStats | null>(null);
  const [history, setHistory] = useState<AllStats[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastTimestamp, setLastTimestamp] = useState<number | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const { showToast } = useToast();

  const loadData = async () => {
    const [currentData, historyData] = await Promise.all([
      fetchTorrentStats(),
      fetchTorrentHistory(),
    ]);
    setStats(currentData);
    setHistory(historyData);
    if (currentData && currentData._timestamp) {
      setLastTimestamp(currentData._timestamp);
    }
    setLoading(false);
  };

  const startPolling = useCallback(() => {
    if (isPolling) return;
    setIsPolling(true);
    let attempts = 0;
    const maxAttempts = 15;

    const poll = async () => {
      attempts++;
      try {
        const newStats = await fetchTorrentStats();
        if (newStats && newStats._timestamp && newStats._timestamp !== lastTimestamp) {
          setStats(newStats);
          setLastTimestamp(newStats._timestamp);
          setIsPolling(false);
          showToast('Données mises à jour !', 'success', 4000);
          return;
        }
      } catch (error) {
        console.error('Polling error:', error);
      }

      if (attempts >= maxAttempts) {
        setIsPolling(false);
        showToast('Timeout — scraper peut encore être en cours', 'error', 3000);
        return;
      }
      setTimeout(poll, 2000);
    };
    poll();
  }, [isPolling, lastTimestamp, showToast]);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleRefreshClick = () => {
      startPolling();
    };
    window.addEventListener('refresh-clicked', handleRefreshClick);
    return () => window.removeEventListener('refresh-clicked', handleRefreshClick);
  }, [startPolling]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-100 dark:bg-gray-900">
        <div className="h-16 w-16 animate-spin rounded-full border-4 border-solid border-brand-500 border-t-transparent"></div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-100 dark:bg-gray-900">
        <p className="text-xl text-error-500">Failed to load data.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 text-gray-600 dark:text-gray-300 transition-colors duration-300">
      <Navbar />
      <main className="mx-auto max-w-screen-2xl p-4 md:p-6 2xl:p-10">
        
        {/* Header Section */}
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-black dark:text-white">
            Tracker Stats
          </h1>
          <div className="flex items-center gap-3">
            <RefreshButton />
          </div>
        </div>
        
        {/* Stats Cards Grid */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 md:gap-6 xl:grid-cols-3 2xl:gap-7.5 mb-10">
          {Object.entries(stats)
            .filter(([name]) => name !== "_timestamp")
            .map(([name, data]) => (
              <TrackerCard key={name} name={name} data={data as TrackerData} />
            ))}
        </div>

        {/* Charts Grid */}
        {history && history.length > 0 && (
          <>
            <h2 className="mb-6 text-xl font-bold text-black dark:text-white">
              Ratio History
            </h2>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3 2xl:gap-7.5">
               {Object.keys(stats)
                 .filter((name) => name !== "_timestamp")
                 .map((name) => (
                  <DashboardCard key={name} title={`History - ${name}`} icon={Activity}>
                     <div className="mt-2">
                        <TrackerChart trackerName={name} history={history} />
                     </div>
                  </DashboardCard>
               ))}
            </div>
          </>
        )}
        
        <footer className="mx-auto max-w-screen-2xl p-4 md:p-6 2xl:p-10 mt-auto">
          <LastUpdateInfo />
        </footer>
      </main>
    </div>
  );
}

function TrackerCard({ name, data }: { name: string; data: TrackerData }) {
  // Helper to unify data access
  const getStats = (d: TrackerData) => {
    const isSharewood = name === 'Sharewood';
    if (!isSharewood) {
      const u = d as Unit3DStats;
      return {
        ratio: u.ratio,
        seed_count: u.count_seed,
        buffer: u.buffer,
        points: u.points_bonus,
        upload: u.vol_upload,
        download: u.vol_download,
        seed_time_total: u.seed_time_total,
        seed_time_avg: u.seed_time_avg,
        download_count: u.count_downloaded
      };
    } else {
      const s = d as SharewoodStats;
      return {
        ratio: s.ratio,
        seed_count: s.count_seed,
        buffer: s.buffer,
        points: s.points_bonus,
        upload: s.vol_upload,
        download: s.vol_download,
        seed_time_total: s.time_seed_total,
        seed_time_avg: s.time_seed_avg,
        download_count: s.count_download
      };
    }
  };

  const stats = getStats(data);
  const ratio = Number(stats.ratio) || 0;

  return (
    <DashboardCard title={name}>
      {/* Badge Ratio - Positionné absolute ou intégré dans le header si nécessaire, ici en haut */}
      <div className="mb-6 -mt-10 flex justify-end">
         <span className={`px-3 py-1 rounded-full text-sm font-bold ${ratio >= 1 ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'}`}>
            Ratio: {ratio.toFixed(2)}
        </span>
      </div>

      {/* Primary Stats Grid */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="space-y-1">
            <p className="text-xs text-gray-500 uppercase font-semibold">Buffer</p>
            <div className="flex items-center gap-2">
                <ArrowRightLeft className="w-4 h-4 text-blue-500" />
                <p className="text-lg font-bold text-black dark:text-white">{stats.buffer}</p>
            </div>
        </div>
        <div className="space-y-1">
            <p className="text-xs text-gray-500 uppercase font-semibold">Points</p>
            <div className="flex items-center gap-2">
                <Coins className="w-4 h-4 text-yellow-500" />
                <p className="text-lg font-bold text-brand-500">{stats.points}</p>
            </div>
        </div>
        <div className="space-y-1">
            <p className="text-xs text-gray-500 uppercase font-semibold">Upload</p>
            <div className="flex items-center gap-2">
                <ArrowUp className="w-4 h-4 text-green-500" />
                <p className="text-sm font-medium text-black dark:text-white">{stats.upload}</p>
            </div>
        </div>
        <div className="space-y-1">
            <p className="text-xs text-gray-500 uppercase font-semibold">Download</p>
            <div className="flex items-center gap-2">
                <ArrowDown className="w-4 h-4 text-red-500" />
                <p className="text-sm font-medium text-black dark:text-white">{stats.download}</p>
            </div>
        </div>
      </div>

      {/* List Stats style HardwareMonitor */}
      <div className="border-t border-gray-100 dark:border-gray-700 pt-2">
        <h5 className="text-sm font-semibold text-gray-500 mb-2 mt-2">Activity</h5>
        <div className="space-y-0">
             <StatRow 
                label="Seeding" 
                value={stats.seed_count} 
                icon={UploadCloud} 
             />
             <StatRow 
                label="Downloaded" 
                value={stats.download_count} 
                icon={DownloadCloud} 
             />
             <StatRow 
                label="Total Time" 
                value={stats.seed_time_total} 
                icon={Clock} 
             />
             <StatRow 
                label="Avg Time" 
                value={stats.seed_time_avg} 
                icon={Clock} 
             />
        </div>
      </div>
    </DashboardCard>
  );
}