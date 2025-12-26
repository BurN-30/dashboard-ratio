"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { fetchTorrentStats } from "@/lib/api";
import { AllStats, TrackerData, Unit3DStats, SharewoodStats } from "@/types/tracker";
import { ArrowLeft, ArrowUp, ArrowDown, ArrowRightLeft, UploadCloud, DownloadCloud, Coins, AlertTriangle, Clock, HardDrive, FileCheck, Percent } from "lucide-react";

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
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-black dark:text-white">
          Traffic & Seeding Stats
        </h1>
        <Link
          href="/"
          className="flex items-center gap-2 rounded-md bg-gray-100 px-4 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </Link>
      </div>
      <div className="grid grid-cols-1 gap-6">
        {Object.entries(stats)
          .filter(([name]) => name !== "_timestamp")
          .map(([name, data]) => (
          <TrafficCard key={name} name={name} data={data as TrackerData} />
        ))}
      </div>
    </div>
  );
}

function TrafficCard({ name, data }: { name: string; data: TrackerData }) {
  const isUnit3D = (data: TrackerData): data is Unit3DStats => {
    return (data as Unit3DStats).real_ratio !== undefined;
  };

  return (
    <div className="rounded-sm border border-gray-200 bg-white p-6 shadow-theme-md dark:border-gray-700 dark:bg-gray-dark">
      <h2 className="mb-4 text-xl font-bold text-black dark:text-white border-b border-gray-200 dark:border-gray-700 pb-2">
        {name}
      </h2>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Column 1: Traffic Volume */}
        <div>
            <h3 className="mb-3 text-sm font-semibold text-gray-500 uppercase tracking-wider">Traffic Volume</h3>
            <div className="space-y-2">
                {isUnit3D(data) ? (
                    <>
                        <StatRow label="Upload (Total)" value={data.vol_upload} icon={ArrowUp} highlight />
                        <StatRow label="Download (Total)" value={data.vol_download} icon={ArrowDown} />
                        <StatRow label="Buffer" value={data.buffer} icon={ArrowRightLeft} />
                        <StatRow label="Real Ratio" value={data.real_ratio} icon={Percent} />
                        <StatRow label="Ratio" value={data.ratio} icon={Percent} highlight />
                    </>
                ) : (
                    <>
                        <StatRow label="Upload" value={(data as SharewoodStats).vol_upload} icon={ArrowUp} highlight />
                        <StatRow label="Download" value={(data as SharewoodStats).vol_download} icon={ArrowDown} />
                        <StatRow label="Buffer" value={(data as SharewoodStats).buffer} icon={ArrowRightLeft} />
                        <StatRow label="Ratio" value={(data as SharewoodStats).ratio} icon={Percent} highlight />
                    </>
                )}
            </div>
        </div>

        {/* Column 2: Torrent Counts */}
        <div>
            <h3 className="mb-3 text-sm font-semibold text-gray-500 uppercase tracking-wider">Torrent Counts</h3>
            <div className="space-y-2">
                {isUnit3D(data) ? (
                    <>
                        <StatRow label="Seeding" value={data.count_seed} icon={UploadCloud} />
                        <StatRow label="Leeching" value={data.count_leech} icon={DownloadCloud} />
                        <StatRow label="Downloaded" value={data.count_downloaded} icon={FileCheck} />
                    </>
                ) : (
                    <>
                        <StatRow label="Seeding" value={(data as SharewoodStats).count_seed} icon={UploadCloud} />
                        <StatRow label="Leeching" value={(data as SharewoodStats).count_leech} icon={DownloadCloud} />
                        <StatRow label="Downloads" value={(data as SharewoodStats).count_download} icon={FileCheck} />
                    </>
                )}
            </div>
        </div>

        {/* Column 3: Seeding Stats */}
        <div>
            <h3 className="mb-3 text-sm font-semibold text-gray-500 uppercase tracking-wider">Seeding Performance</h3>
            <div className="space-y-2">
                {isUnit3D(data) ? (
                    <>
                        <StatRow label="Total Seed Time" value={data.seed_time_total} icon={Clock} />
                        <StatRow label="Avg Seed Time" value={data.seed_time_avg} icon={Clock} />
                        <StatRow label="Seeding Size" value={data.seed_size} icon={HardDrive} />
                        <StatRow label="Points" value={data.points_bonus} icon={Coins} highlight />
                        <StatRow label="FL Tokens" value={data.fl_tokens} icon={Coins} />
                    </>
                ) : (
                    <>
                        <StatRow label="Total Seed Time" value={(data as SharewoodStats).time_seed_total} icon={Clock} />
                        <StatRow label="Avg Seed Time" value={(data as SharewoodStats).time_seed_avg} icon={Clock} />
                        <StatRow label="Bonus Points" value={(data as SharewoodStats).points_bonus} icon={Coins} highlight />
                        <StatRow label="FL Tokens" value={(data as SharewoodStats).fl_tokens} icon={Coins} />
                    </>
                )}
            </div>
        </div>

        {/* Column 4: Account Health */}
        <div>
            <h3 className="mb-3 text-sm font-semibold text-gray-500 uppercase tracking-wider">Account Health</h3>
            <div className="space-y-2">
                {isUnit3D(data) ? (
                    <>
                        <StatRow label="Active Warnings" value={data.warnings_active} highlight={data.warnings_active !== "0"} icon={AlertTriangle} />
                        <StatRow label="Hit & Run (Total)" value={data.hit_and_run} icon={AlertTriangle} />
                    </>
                ) : (
                    <>
                        <StatRow 
                            label="Warnings / H&R" 
                            value={`${(data as SharewoodStats).warnings_active || "0"} / ${(data as SharewoodStats).warnings_limit || "3"} (${(data as SharewoodStats).hit_and_run} H&R)`} 
                            highlight={(data as SharewoodStats).warnings_active !== "0"} 
                            icon={AlertTriangle}
                        />
                    </>
                )}
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
