"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTheme } from "@/context/ThemeContext";
import { useToast } from "@/context/ToastContext";
import { fetchTorrentStats, fetchTorrentHistory } from "@/lib/api";
import { AllStats, TrackerData, Unit3DStats, SharewoodStats } from "@/types/tracker";
import { ArrowUp, ArrowDown, Coins, ArrowRightLeft, UploadCloud, DownloadCloud, RefreshCw, BarChart2, Clock, LogOut, Sun, Moon } from "lucide-react";
import dynamic from "next/dynamic";
import RefreshButton from "@/components/RefreshButton";
import LastUpdateInfo from "@/components/LastUpdateInfo";

// Dynamically import Chart to avoid SSR issues
const TrackerChart = dynamic(() => import("@/components/charts/TrackerChart"), {
  ssr: false,
});

export default function Home() {
  const [stats, setStats] = useState<AllStats | null>(null);
  const [history, setHistory] = useState<AllStats[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastTimestamp, setLastTimestamp] = useState<number | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const { showToast } = useToast();
  const router = useRouter();

  const handleLogout = async () => {
    await fetch("/api/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  };

  // Fonction pour recharger les données
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

  // Polling pour détecter quand les données changent après refresh
  const startPolling = () => {
    if (isPolling) return;
    setIsPolling(true);
    let attempts = 0;
    const maxAttempts = 15; // 30 secondes (2s * 15)

    const poll = async () => {
      attempts++;
      try {
        const newStats = await fetchTorrentStats();
        if (newStats && newStats._timestamp && newStats._timestamp !== lastTimestamp) {
          // Données ont changé !
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

      // Polling suivant dans 2 secondes
      setTimeout(poll, 2000);
    };

    poll();
  };

  useEffect(() => {
    loadData();

    // Auto-refresh every 5 minutes
    const interval = setInterval(loadData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  // Listener pour quand le refresh button est cliqué
  useEffect(() => {
    const handleRefreshClick = () => {
      startPolling();
    };

    window.addEventListener('refresh-clicked', handleRefreshClick);
    return () => window.removeEventListener('refresh-clicked', handleRefreshClick);
  }, [lastTimestamp]);

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
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-black dark:text-white">
          Tracker Stats
        </h1>
        <div className="flex items-center gap-3">
          <RefreshButton />

          <button
            onClick={toggleTheme}
            className="flex items-center justify-center w-8 h-8 text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            title="Toggle Theme"
          >
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>

          <Link 
            href="/traffic" 
            className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
          >
             <BarChart2 className="w-4 h-4" />
             Details
          </Link>

          <button
            onClick={handleLogout}
            className="flex items-center justify-center w-8 h-8 text-red-500 bg-red-50 dark:bg-red-900/20 rounded-md hover:bg-red-100 dark:hover:bg-red-900/40 transition-colors"
            title="Logout"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
      
      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 md:gap-6 xl:grid-cols-3 2xl:gap-7.5 mb-10">
        {Object.entries(stats)
          .filter(([name]) => name !== "_timestamp")
          .map(([name, data]) => (
            <TrackerCard key={name} name={name} data={data as TrackerData} />
          ))}
      </div>

      {/* Charts */}
      {history && history.length > 0 && (
        <>
          <h2 className="mb-6 text-xl font-bold text-black dark:text-white">
            Ratio History
          </h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
             {Object.keys(stats)
               .filter((name) => name !== "_timestamp")
               .map((name) => (
                <div key={name} className="col-span-1">
                   <TrackerChart trackerName={name} history={history} />
                </div>
             ))}
          </div>
        </>
      )}
      <footer className="mx-auto max-w-screen-2xl p-4 md:p-6 2xl:p-10 mt-auto">
        <LastUpdateInfo />
      </footer>
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
        buffer: u.buffer, // "Tampon"
        points: u.points_bonus, // "Coupon" / "Points Bonus"
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
        buffer: s.buffer, // "Capacité de DL"
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
            <div className="flex items-center gap-2">
                <ArrowRightLeft className="w-4 h-4 text-blue-500" />
                <p className="text-lg font-bold text-black dark:text-white">{stats.buffer}</p>
            </div>
        </div>
        <div className="space-y-1">
            <p className="text-xs text-gray-500 uppercase">Points Bonus</p>
            <div className="flex items-center gap-2">
                <Coins className="w-4 h-4 text-yellow-500" />
                <p className="text-lg font-bold text-brand-500">{stats.points}</p>
            </div>
        </div>
        <div className="space-y-1">
            <p className="text-xs text-gray-500 uppercase">Upload Vol.</p>
            <div className="flex items-center gap-2">
                <ArrowUp className="w-4 h-4 text-success-500" />
                <p className="text-sm font-medium text-black dark:text-white">{stats.upload}</p>
            </div>
        </div>
        <div className="space-y-1">
            <p className="text-xs text-gray-500 uppercase">Download Vol.</p>
            <div className="flex items-center gap-2">
                <ArrowDown className="w-4 h-4 text-error-500" />
                <p className="text-sm font-medium text-black dark:text-white">{stats.download}</p>
            </div>
        </div>
      </div>

      {/* Super Useful Stats */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
        <h5 className="text-sm font-semibold text-gray-500 mb-3">Activity & Seeding</h5>
        <div className="space-y-2">
            <div className="flex justify-between text-sm">
                <span className="text-gray-600 dark:text-gray-400">Torrents Seeding</span>
                <div className="flex items-center gap-2">
                    <UploadCloud className="w-4 h-4 text-success-500" />
                    <span className="font-medium text-black dark:text-white">{stats.seed_count}</span>
                </div>
            </div>
            <div className="flex justify-between text-sm">
                <span className="text-gray-600 dark:text-gray-400">Torrents Downloaded</span>
                <div className="flex items-center gap-2">
                    <DownloadCloud className="w-4 h-4 text-blue-500" />
                    <span className="font-medium text-black dark:text-white">{stats.download_count}</span>
                </div>
            </div>
            <div className="flex justify-between text-sm">
                <span className="text-gray-600 dark:text-gray-400">Total Seed Time</span>
                <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-gray-400" />
                    <span className="font-medium text-black dark:text-white">{stats.seed_time_total}</span>
                </div>
            </div>
            <div className="flex justify-between text-sm">
                <span className="text-gray-600 dark:text-gray-400">Avg Seed Time</span>
                <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-gray-400" />
                    <span className="font-medium text-black dark:text-white">{stats.seed_time_avg}</span>
                </div>
            </div>
        </div>
      </div>
    </div>
  );
}

function StatRow({ label, value, highlight = false, icon: Icon }: { label: string; value: string; highlight?: boolean; icon?: React.ElementType }) {
    return (
        <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600 dark:text-gray-400">{label}</span>
            <div className="flex items-center gap-2">
                {Icon && <Icon className={`w-4 h-4 ${highlight ? "text-brand-500" : "text-gray-400"}`} />}
                <span className={`text-sm font-medium ${highlight ? "text-brand-500 font-bold" : "text-black dark:text-white"}`}>
                    {value}
                </span>
            </div>
        </div>
    );
}
