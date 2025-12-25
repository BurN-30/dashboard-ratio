"use client";

import React, { useEffect, useState } from "react";
import { fetchTorrentStats } from "@/lib/api";
import { AllStats, TrackerData, Unit3DStats, SharewoodStats } from "@/types/tracker";

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
      <h1 className="mb-6 text-2xl font-bold text-black dark:text-white">
        Traffic & Seeding Stats
      </h1>
      <div className="grid grid-cols-1 gap-6">
        {Object.entries(stats).map(([name, data]) => (
          <TrafficCard key={name} name={name} data={data} />
        ))}
      </div>
    </div>
  );
}

function TrafficCard({ name, data }: { name: string; data: TrackerData }) {
  const isUnit3D = (data: TrackerData): data is Unit3DStats => {
    return (data as Unit3DStats).warnings_active !== undefined;
  };

  return (
    <div className="rounded-sm border border-gray-200 bg-white p-6 shadow-theme-md dark:border-gray-700 dark:bg-gray-dark">
      <h2 className="mb-4 text-xl font-bold text-black dark:text-white border-b border-gray-200 dark:border-gray-700 pb-2">
        {name}
      </h2>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Column 1: Traffic Volume */}
        <div>
            <h3 className="mb-3 text-sm font-semibold text-gray-500 uppercase tracking-wider">Traffic Volume</h3>
            <div className="space-y-2">
                {isUnit3D(data) ? (
                    <>
                        <StatRow label="Upload (Total)" value={data.vol_upload} />
                        <StatRow label="Download (Total)" value={data.vol_download} />
                        <StatRow label="Buffer" value={data.buffer} />
                        <StatRow label="Real Ratio" value={data.real_ratio} />
                        <StatRow label="Ratio" value={data.ratio} highlight />
                    </>
                ) : (
                    <>
                        <StatRow label="Upload" value={(data as SharewoodStats).vol_upload_final} />
                        <StatRow label="Download" value={(data as SharewoodStats).vol_download} />
                        <StatRow label="Ratio" value={(data as SharewoodStats).ratio} highlight />
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
                        <StatRow label="Seeding" value={data.count_seed} />
                        <StatRow label="Leeching" value={data.count_leech} />
                        <StatRow label="Downloaded" value={data.count_downloaded} />
                        <StatRow label="Uploaded (Non-Anon)" value={data.count_up_non_anon || "0"} />
                        <StatRow label="Uploaded (Anon)" value={data.count_up_anon || "0"} />
                    </>
                ) : (
                    <>
                        <StatRow label="Seeding" value={(data as SharewoodStats).count_seed} />
                        <StatRow label="Leeching" value={(data as SharewoodStats).count_leech} />
                        <StatRow label="Uploads" value={(data as SharewoodStats).count_upload} />
                        <StatRow label="Downloads" value={(data as SharewoodStats).count_download} />
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
                        <StatRow label="Total Seed Time" value={data.seed_time_total} />
                        <StatRow label="Avg Seed Time" value={data.seed_time_avg} />
                        <StatRow label="Seeding Size" value={data.seed_size} />
                        <StatRow label="Points" value={data.points} />
                    </>
                ) : (
                    <>
                        <StatRow label="Total Seed Time" value={(data as SharewoodStats).time_seed_total} />
                        <StatRow label="Avg Seed Time" value={(data as SharewoodStats).time_seed_avg} />
                        <StatRow label="Bonus Points" value={(data as SharewoodStats).points_bonus} />
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
                    <StatRow label="Torrent Downloaded (Credited)" value={data.torrent_downloader_credited || "0"} />
                    <StatRow label="Torrent Downloaded (Refunded)" value={data.torrent_downloader_refunded || "0"} />
                </div>
            </div>
        </div>
      )}
    </div>
  );
}

function StatRow({ label, value, highlight = false }: { label: string; value: string; highlight?: boolean }) {
    return (
        <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600 dark:text-gray-400">{label}</span>
            <span className={`text-sm font-medium ${highlight ? "text-brand-500 font-bold" : "text-black dark:text-white"}`}>
                {value}
            </span>
        </div>
    );
}
