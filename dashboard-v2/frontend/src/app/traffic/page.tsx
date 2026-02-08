"use client";

import React, { useEffect, useState } from "react";
import { fetchTorrentStats } from "@/lib/api";
import { AllStats, TrackerData, Unit3DStats, SharewoodStats } from "@/types/tracker";
import { ArrowUp, ArrowDown, ArrowRightLeft, UploadCloud, DownloadCloud, Coins, AlertTriangle, Clock, HardDrive, FileCheck, Percent } from "lucide-react";
import DashboardShell from "@/components/common/DashboardShell";
import DashboardCard from "@/components/common/DashboardCard";
import SkeletonCard from "@/components/common/SkeletonCard";
import StatRow from "@/components/common/StatRow";

export default function TrafficPage() {
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
      <DashboardShell>
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Traffic & Seeding Stats</h1>
        </div>
        <div className="grid grid-cols-1 gap-6">
          {[...Array(3)].map((_, i) => (
            <SkeletonCard key={i} variant="list" />
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

  return (
    <DashboardShell>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Traffic & Seeding Stats
        </h1>
      </div>
      <div className="grid grid-cols-1 gap-6">
        {Object.entries(stats)
          .filter(([name]) => name !== "_timestamp")
          .map(([name, data], index) => (
          <TrafficCard key={name} name={name} data={data as TrackerData} style={{ animationDelay: `${index * 80}ms` }} />
        ))}
      </div>
    </DashboardShell>
  );
}

function TrafficCard({ name, data, style }: { name: string; data: TrackerData; style?: React.CSSProperties }) {
  const isUnit3D = (data: TrackerData): data is Unit3DStats => {
    return (data as Unit3DStats).real_ratio !== undefined;
  };

  return (
    <DashboardCard className="animate-slide-up" style={style}>
      <h2 className="mb-4 text-xl font-bold text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-700 pb-2">
        {name}
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Column 1: Traffic Volume */}
        <div>
          <h3 className="mb-3 text-sm font-semibold text-gray-500 uppercase tracking-wider">Traffic Volume</h3>
          <div className="space-y-2">
            <StatRow label="Upload (Total)" value={data.vol_upload} icon={ArrowUp} highlight />
            <StatRow label="Download (Total)" value={data.vol_download} icon={ArrowDown} />
            <StatRow label="Buffer" value={data.buffer} icon={ArrowRightLeft} />
            {isUnit3D(data) && <StatRow label="Real Ratio" value={data.real_ratio} icon={Percent} />}
            <StatRow label="Ratio" value={data.ratio} icon={Percent} highlight />
          </div>
        </div>

        {/* Column 2: Torrent Counts */}
        <div>
          <h3 className="mb-3 text-sm font-semibold text-gray-500 uppercase tracking-wider">Torrent Counts</h3>
          <div className="space-y-2">
            <StatRow label="Seeding" value={data.count_seed} icon={UploadCloud} />
            <StatRow label="Leeching" value={data.count_leech} icon={DownloadCloud} />
            <StatRow label="Downloaded" value={data.count_downloaded} icon={FileCheck} />
          </div>
        </div>

        {/* Column 3: Seeding Stats */}
        <div>
          <h3 className="mb-3 text-sm font-semibold text-gray-500 uppercase tracking-wider">Seeding Performance</h3>
          <div className="space-y-2">
            <StatRow label="Total Seed Time" value={data.seed_time_total} icon={Clock} />
            <StatRow label="Avg Seed Time" value={data.seed_time_avg} icon={Clock} />
            {isUnit3D(data) && <StatRow label="Seeding Size" value={data.seed_size} icon={HardDrive} />}
            <StatRow label="Points" value={data.points_bonus} icon={Coins} highlight />
            <StatRow label="FL Tokens" value={data.fl_tokens} icon={Coins} />
          </div>
        </div>

        {/* Column 4: Account Health */}
        <div>
          <h3 className="mb-3 text-sm font-semibold text-gray-500 uppercase tracking-wider">Account Health</h3>
          <div className="space-y-2">
            <StatRow label="Active Warnings" value={data.warnings_active || "0"} highlight={data.warnings_active !== "0" && data.warnings_active !== undefined} icon={AlertTriangle} />
            <StatRow label="Hit & Run" value={data.hit_and_run} icon={AlertTriangle} />
          </div>
        </div>
      </div>

      {/* Extra Details for Unit3D */}
      {isUnit3D(data) && (
        <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
          <h3 className="mb-3 text-sm font-semibold text-gray-500 uppercase tracking-wider">Detailed Transfer Stats</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <StatRow label="Torrent Uploaded" value={data.torrent_uploader || "0"} />
              <StatRow label="Torrent Uploaded (Credited)" value={data.torrent_uploader_credited || "0"} />
            </div>
            <div className="space-y-1">
              <StatRow label="Torrent Downloaded" value={data.torrent_downloader || "0"} />
            </div>
          </div>
        </div>
      )}
    </DashboardCard>
  );
}
