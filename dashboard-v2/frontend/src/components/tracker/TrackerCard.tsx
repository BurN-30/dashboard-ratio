import React, { useCallback } from 'react';
import { ArrowUp, ArrowDown, Coins, ArrowRightLeft, UploadCloud, DownloadCloud, Clock } from 'lucide-react';
import { TrackerData, Unit3DStats, SharewoodStats } from '@/types/tracker';
import DashboardCard from '@/components/common/DashboardCard';

interface TrackerCardProps {
  name: string;
  data: TrackerData;
  style?: React.CSSProperties;
}

// Fragments d'URL construits dynamiquement (pas de lien complet en dur)
const SP = (h: string, p: string): [string, string] => [h, p];
const SHOP_MAP: Record<string, [string, string]> = {
  'Sharewood': SP('www.sharewood.tv', '/bonus/your-username'),
  'Torr9': SP('torr9.xyz', '/tokens'),
  'TOS': SP('theoldschool.cc', '/users/your-username/transactions/create'),
  'GF-FREE': SP('generation-free.org', '/users/your-username/transactions/create'),
  'G3MINI TR4CK3R': SP('gemini-tracker.org', '/users/your-username/transactions/create'),
};

export default function TrackerCard({ name, data, style }: TrackerCardProps) {
  const getStats = (d: TrackerData) => {
    return {
      ratio: d.ratio,
      seed_count: d.count_seed,
      buffer: d.buffer,
      points: d.points_bonus,
      upload: d.vol_upload,
      download: d.vol_download,
      seed_time_total: d.seed_time_total,
      seed_time_avg: d.seed_time_avg,
      download_count: d.count_downloaded,
    };
  };

  const openShop = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const parts = SHOP_MAP[name];
    if (!parts) return;
    // Construire l'URL au moment du clic uniquement
    const dest = ['https:/', parts[0], ...parts[1].split('/')].filter(Boolean).join('/');
    // Ouvrir sans referrer ni lien tracable
    const w = window.open('about:blank', '_blank', 'noopener,noreferrer');
    if (w) {
      w.opener = null;
      w.location.href = dest;
    }
  }, [name]);

  const stats = getStats(data);
  const hasShop = name in SHOP_MAP;

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
          <div
            className={`flex items-center gap-2 ${hasShop ? 'cursor-pointer group' : ''}`}
            onClick={hasShop ? openShop : undefined}
            role={hasShop ? 'button' : undefined}
            tabIndex={hasShop ? 0 : undefined}
          >
            <Coins className={`w-4 h-4 text-yellow-500 ${hasShop ? 'group-hover:text-yellow-400 transition-colors' : ''}`} />
            <p className={`text-lg font-bold text-brand-500 ${hasShop ? 'group-hover:underline' : ''}`}>{stats.points}</p>
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
          {stats.seed_time_avg && stats.seed_time_avg !== '0' && (
          <div className="flex justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-400">Avg Seed Time</span>
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-gray-400" />
              <span className="font-medium text-gray-900 dark:text-white">{stats.seed_time_avg}</span>
            </div>
          </div>
          )}
        </div>
      </div>
    </DashboardCard>
  );
}
