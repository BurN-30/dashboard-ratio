"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useToast } from "@/context/ToastContext";
import { useAuth } from "@/context/AuthContext";
import { fetchTorrentStats, fetchTorrentHistory } from "@/lib/api";
import { AllStats, TrackerData } from "@/types/tracker";
import dynamic from "next/dynamic";
import RefreshButton from "@/components/RefreshButton";
import LastUpdateInfo from "@/components/LastUpdateInfo";
import DashboardShell from "@/components/common/DashboardShell";
import SkeletonCard from "@/components/common/SkeletonCard";
import TrackerCard from "@/components/tracker/TrackerCard";

const TrackerChart = dynamic(() => import("@/components/charts/TrackerChart"), {
  ssr: false,
});

export default function Home() {
  const [stats, setStats] = useState<AllStats | null>(null);
  const [history, setHistory] = useState<AllStats[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastTimestamp, setLastTimestamp] = useState<number | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const { showToast } = useToast();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, authLoading, router]);

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
    const handleRefreshComplete = () => {
      loadData();
      showToast('Données mises à jour !', 'success', 3000);
    };

    window.addEventListener('refresh-complete', handleRefreshComplete);
    return () => window.removeEventListener('refresh-complete', handleRefreshComplete);
  }, [showToast]);

  if (authLoading) return null;
  if (!isAuthenticated) return null;

  if (loading) {
    return (
      <DashboardShell>
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Tracker Stats</h1>
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 md:gap-6 xl:grid-cols-3 2xl:gap-7.5">
          {[...Array(5)].map((_, i) => (
            <SkeletonCard key={i} variant="stat" />
          ))}
        </div>
      </DashboardShell>
    );
  }

  if (!stats) {
    return (
      <DashboardShell>
        <div className="flex h-64 items-center justify-center">
          <p className="text-xl text-error-500">Failed to load data.</p>
        </div>
      </DashboardShell>
    );
  }

  const trackerEntries = Object.entries(stats).filter(([name]) => name !== "_timestamp");

  return (
    <DashboardShell footer={<LastUpdateInfo />}>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Tracker Stats</h1>
        <RefreshButton />
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 md:gap-6 xl:grid-cols-3 2xl:gap-7.5 mb-10">
        {trackerEntries.map(([name, data], index) => (
          <TrackerCard
            key={name}
            name={name}
            data={data as TrackerData}
            style={{ animationDelay: `${index * 80}ms` }}
          />
        ))}
      </div>

      {/* Charts */}
      {history && history.length > 0 && (
        <>
          <h2 className="mb-6 text-xl font-bold text-gray-900 dark:text-white">
            Ratio History
          </h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {trackerEntries.map(([name]) => (
              <div key={name} className="col-span-1">
                <TrackerChart trackerName={name} history={history} />
              </div>
            ))}
          </div>
        </>
      )}
    </DashboardShell>
  );
}
