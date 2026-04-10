import React, { useCallback } from 'react';
import { ArrowUp, ArrowDown, Coins, ArrowRightLeft, UploadCloud, DownloadCloud, Clock, AlertTriangle } from 'lucide-react';
import { TrackerData, ScrapeMeta } from '@/types/tracker';
import DashboardCard from '@/components/common/DashboardCard';

interface TrackerCardProps {
  name: string;
  data: TrackerData;
  style?: React.CSSProperties;
  scrapeMeta?: ScrapeMeta;
}

function timeAgo(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const hours = Math.floor(diff / 3600000);
  if (hours < 1) return "moins d'1h";
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  return `${days}j`;
}

function isStale(data: TrackerData, scrapeMeta?: ScrapeMeta): boolean {
  if (scrapeMeta) {
    if (scrapeMeta.status !== 'ok') return true;
    if (scrapeMeta.consecutive_failures > 0) return true;
  }
  if (data.scraped_at) {
    const diff = Date.now() - new Date(data.scraped_at).getTime();
    if (diff > 12 * 3600000) return true;
  }
  return false;
}

function staleBannerText(scrapeMeta?: ScrapeMeta): string {
  if (scrapeMeta?.status === 'skipped') return 'Maintenance';
  return 'Service indisponible';
}

function staleReferenceDate(data: TrackerData, scrapeMeta?: ScrapeMeta): string | null {
  if (scrapeMeta?.last_success_at) return scrapeMeta.last_success_at;
  if (data.scraped_at) return data.scraped_at;
  return null;
}

// Username configurable via env var (pas de données personnelles dans le code)
const TRACKER_USER = process.env.NEXT_PUBLIC_TRACKER_USERNAME || '';

// Fragments d'URL construits dynamiquement (pas de lien complet en dur)
const SP = (h: string, p: string): [string, string] => [h, p];
const buildShopMap = (user: string): Record<string, [string, string]> => ({
  'Torr9': SP('torr9.net', '/tokens'),
  'TOS': SP('theoldschool.cc', `/users/${user}/transactions/create`),
  'G3MINI TR4CK3R': SP('gemini-tracker.org', `/users/${user}/transactions/create`),
  'GF-FREE': SP('generation-free.org', `/users/${user}/transactions/create`),
});
const SHOP_MAP = TRACKER_USER ? buildShopMap(TRACKER_USER) : {};

// Max redeem tier par tracker (meilleur ratio points/GB).
// null = pas de redeem connu. Ajuster les valeurs selon les sites.
const MAX_REDEEM: Record<string, number> = {
  'Torr9': 12000,           // TODO: verifier la vraie valeur
  'TOS': 100000,            // TODO: verifier
  'G3MINI TR4CK3R': 100000, // TODO: verifier
  'GF-FREE': 100000,        // TODO: verifier
};

export default function TrackerCard({ name, data, style, scrapeMeta }: TrackerCardProps) {
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
    // Ouvrir sans referrer : on part de about:blank donc pas de Referer header
    // On ne met PAS noopener dans window.open sinon il retourne null
    const w = window.open('about:blank', '_blank');
    if (w) {
      w.opener = null;          // couper le lien retour
      w.location.href = dest;   // naviguer depuis about:blank = pas de referrer
    }
  }, [name]);

  const stats = getStats(data);
  const hasShop = name in SHOP_MAP;
  const stale = isStale(data, scrapeMeta);
  const refDate = staleReferenceDate(data, scrapeMeta);

  return (
    <DashboardCard className={`animate-slide-up${stale ? ' opacity-60' : ''}`} style={style}>
      <div className="flex items-center justify-between mb-6">
        <h4 className="text-xl font-bold text-gray-900 dark:text-white">{name}</h4>
        <span
          className={`px-3 py-1 rounded-full text-sm font-bold ${
            stale
              ? 'bg-gray-200 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
              : parseFloat(stats.ratio) >= 1
                ? 'bg-success-500/10 text-success-500'
                : 'bg-error-500/10 text-error-500'
          }`}
        >
          Ratio: {stats.ratio}
        </span>
      </div>

      {/* Stale banner */}
      {stale && (
        <div className="flex items-start gap-2 rounded-md bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 px-3 py-2 mb-4">
          <AlertTriangle className="w-4 h-4 text-orange-500 mt-0.5 shrink-0" />
          <div className="min-w-0">
            <p className="text-sm font-semibold text-orange-700 dark:text-orange-400">
              {staleBannerText(scrapeMeta)}
            </p>
            {refDate && (
              <p className="text-xs text-orange-600 dark:text-orange-500">
                Dernières données : il y a {timeAgo(refDate)}
              </p>
            )}
          </div>
        </div>
      )}

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
          {(() => {
            const maxRedeem = MAX_REDEEM[name];
            if (!maxRedeem) return null;
            const current = parseFloat((stats.points || '0').replace(/[^\d]/g, '')) || 0;
            const pct = Math.min((current / maxRedeem) * 100, 100);
            const ready = current >= maxRedeem;
            return (
              <div className="mt-1" title={`${current.toLocaleString()} / ${maxRedeem.toLocaleString()} pour redeem max`}>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1">
                  <div
                    className={`h-full rounded-full transition-all ${ready ? 'bg-success-500' : 'bg-yellow-500/70'}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <p className="text-[10px] text-gray-400 mt-0.5 text-right">
                  {ready ? 'redeem dispo' : `/ ${(maxRedeem / 1000).toFixed(0)}k`}
                </p>
              </div>
            );
          })()}
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
