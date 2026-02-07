import React from 'react';
import { ArrowUp, ArrowDown, Coins, ArrowRightLeft, UploadCloud, DownloadCloud, Clock } from 'lucide-react';
import { TrackerData, Unit3DStats, SharewoodStats } from '@/types/tracker';
import DashboardCard from '@/components/common/DashboardCard';

interface TrackerCardProps {
  name: string;
  data: TrackerData;
  style?: React.CSSProperties;
}

export default function TrackerCard({ name, data, style }: TrackerCardProps) {
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
        download_count: u.count_downloaded,
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
        download_count: s.count_download,
      };
    }
  };

  const stats = getStats(data);

  return (
    <DashboardCard className="animate-slide-up" style={style}>
      <div className="flex items-center justify-between mb-6">
        <h4 className="text-xl font-bold text-gray-900 dark:text-white">{name}</h4>
        <span
          className={`px-3 py-1 rounded-full text-sm font-bold ${
            parseFloat(stats.ratio) >= 1
              ? 'bg-success-500/10 text-success-500'
              : 'bg-error-500/10 text-error-500'
          }`}
        >
          Ratio: {stats.ratio}
        </span>
      </div>

      {/* Primary Stats */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="space-y-1">
          <p className="text-xs text-gray-500 uppercase">Buffer / Capacit&eacute;</p>
          <div className="flex items-center gap-2">
            <ArrowRightLeft className="w-4 h-4 text-blue-500" />
            <p className="text-lg font-bold text-gray-900 dark:text-white">{stats.buffer}</p>
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
            <p className="text-sm font-medium text-gray-900 dark:text-white">{stats.upload}</p>
          </div>
        </div>
        <div className="space-y-1">
          <p className="text-xs text-gray-500 uppercase">Download Vol.</p>
          <div className="flex items-center gap-2">
            <ArrowDown className="w-4 h-4 text-error-500" />
            <p className="text-sm font-medium text-gray-900 dark:text-white">{stats.download}</p>
          </div>
        </div>
      </div>

      {/* Activity & Seeding */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
        <h5 className="text-sm font-semibold text-gray-500 mb-3">Activity & Seeding</h5>
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-400">Torrents Seeding</span>
            <div className="flex items-center gap-2">
              <UploadCloud className="w-4 h-4 text-success-500" />
              <span className="font-medium text-gray-900 dark:text-white">{stats.seed_count}</span>
            </div>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-400">Torrents Downloaded</span>
            <div className="flex items-center gap-2">
              <DownloadCloud className="w-4 h-4 text-blue-500" />
              <span className="font-medium text-gray-900 dark:text-white">{stats.download_count}</span>
            </div>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-400">Total Seed Time</span>
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-gray-400" />
              <span className="font-medium text-gray-900 dark:text-white">{stats.seed_time_total}</span>
            </div>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-400">Avg Seed Time</span>
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-gray-400" />
              <span className="font-medium text-gray-900 dark:text-white">{stats.seed_time_avg}</span>
            </div>
          </div>
        </div>
      </div>
    </DashboardCard>
  );
}
