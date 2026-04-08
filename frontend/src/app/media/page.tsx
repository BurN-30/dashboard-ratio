'use client';

import React, { useEffect, useState, useCallback } from 'react';
import DashboardShell from '@/components/common/DashboardShell';
import DashboardCard from '@/components/common/DashboardCard';
import { fetchMediaOverview } from '@/lib/api';
import { MediaOverview } from '@/types/media';
import {
  Film,
  Tv,
  Play,
  HardDrive,
  Download,
  Calendar,
  Users,
  Wifi,
  RefreshCw,
  AlertCircle,
  MonitorPlay,
  Clapperboard,
} from 'lucide-react';

function KpiCard({ icon: Icon, title, value, subtext, color }: {
  icon: React.ElementType;
  title: string;
  value: string;
  subtext?: string;
  color: string;
}) {
  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-white/[0.03] p-4 flex items-center space-x-4 hover:border-gray-300 dark:hover:border-gray-600 transition-all">
      <div className={`p-3 rounded-lg bg-gray-100 dark:bg-gray-700/30 ${color}`}>
        <Icon size={22} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-gray-500 dark:text-gray-400 text-xs uppercase font-bold tracking-wider truncate">{title}</p>
        <h3 className="text-xl font-bold text-gray-900 dark:text-white">{value}</h3>
        {subtext && <p className="text-xs text-gray-400 dark:text-gray-500 truncate">{subtext}</p>}
      </div>
    </div>
  );
}

function ServiceUnavailable({ name }: { name: string }) {
  return (
    <div className="flex items-center gap-3 p-4 text-gray-400 dark:text-gray-500">
      <AlertCircle size={20} />
      <span>{name} indisponible</span>
    </div>
  );
}

export default function MediaPage() {
  const [data, setData] = useState<MediaOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    const result = await fetchMediaOverview();
    setData(result);
    setLoading(false);
    setRefreshing(false);
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(() => loadData(), 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  if (loading) {
    return (
      <DashboardShell>
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <Film className="w-12 h-12 text-purple-500 animate-pulse mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">Chargement des services media...</p>
          </div>
        </div>
      </DashboardShell>
    );
  }

  const plex = data?.plex;
  const radarr = data?.radarr;
  const sonarr = data?.sonarr;
  const tautulli = data?.tautulli;

  // Compute totals from Plex libraries
  const movieCount = plex?.libraries.filter(l => l.type === 'movie').reduce((sum, l) => sum + l.count, 0) ?? 0;
  const showCount = plex?.libraries.filter(l => l.type === 'show').reduce((sum, l) => sum + l.count, 0) ?? 0;

  return (
    <DashboardShell>
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Film className="text-purple-500" />
            Media Center
          </h1>
          <p className="text-gray-500 text-sm mt-1 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            Mise a jour auto toutes les 30s
          </p>
        </div>
        <button
          onClick={() => loadData(true)}
          disabled={refreshing}
          className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 text-sm hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
        >
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          Rafraichir
        </button>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KpiCard
          icon={Clapperboard}
          title="Films"
          value={movieCount.toLocaleString()}
          subtext={radarr ? `${radarr.monitored} surveilles` : undefined}
          color="text-blue-400"
        />
        <KpiCard
          icon={Tv}
          title="Series"
          value={showCount.toLocaleString()}
          subtext={sonarr ? `${sonarr.total_episodes.toLocaleString()} episodes` : undefined}
          color="text-purple-400"
        />
        <KpiCard
          icon={Play}
          title="Streams actifs"
          value={String(plex?.active_streams ?? 0)}
          subtext={tautulli ? `${tautulli.total_bandwidth_mbps} Mbps` : undefined}
          color="text-green-400"
        />
        <KpiCard
          icon={Download}
          title="En queue"
          value={String((radarr?.queue_count ?? 0) + (sonarr?.queue_count ?? 0))}
          subtext={`${radarr?.queue_count ?? 0} films, ${sonarr?.queue_count ?? 0} series`}
          color="text-orange-400"
        />
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Column 1-2 */}
        <div className="lg:col-span-2 space-y-6">

          {/* Plex Libraries */}
          <DashboardCard>
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2 uppercase tracking-wide">
              <MonitorPlay size={16} className="text-yellow-500" /> Bibliotheques Plex
            </h2>
            {plex ? (
              <div className="space-y-3">
                {plex.libraries.map((lib) => (
                  <div key={lib.title} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                    <div className="flex items-center gap-3">
                      {lib.type === 'movie' ? <Film size={16} className="text-blue-400" /> : <Tv size={16} className="text-purple-400" />}
                      <span className="text-sm text-gray-700 dark:text-gray-300">{lib.title}</span>
                    </div>
                    <span className="font-mono text-sm font-bold text-gray-900 dark:text-white">{lib.count.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            ) : (
              <ServiceUnavailable name="Plex" />
            )}
          </DashboardCard>

          {/* Radarr */}
          <DashboardCard>
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2 uppercase tracking-wide">
              <Clapperboard size={16} className="text-blue-500" /> Radarr
            </h2>
            {radarr ? (
              <>
                <div className="grid grid-cols-3 gap-3 mb-4">
                  <div className="bg-gray-50 dark:bg-gray-800/50 p-3 rounded-lg text-center">
                    <span className="text-xs text-gray-500 block">Total</span>
                    <span className="font-bold text-gray-900 dark:text-white">{radarr.total_movies}</span>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800/50 p-3 rounded-lg text-center">
                    <span className="text-xs text-gray-500 block">Surveilles</span>
                    <span className="font-bold text-blue-400">{radarr.monitored}</span>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800/50 p-3 rounded-lg text-center">
                    <span className="text-xs text-gray-500 block">Queue</span>
                    <span className="font-bold text-orange-400">{radarr.queue_count}</span>
                  </div>
                </div>
                {/* Disk Space */}
                {radarr.disk_space.length > 0 && (
                  <div className="space-y-2">
                    {radarr.disk_space.map((disk) => (
                      <div key={disk.path}>
                        <div className="flex justify-between text-xs text-gray-500 mb-1">
                          <span className="flex items-center gap-1"><HardDrive size={12} /> {disk.path}</span>
                          <span>{disk.free_gb} GB libres / {disk.total_gb} GB</span>
                        </div>
                        <div className="w-full bg-gray-200 dark:bg-gray-800 rounded-full h-2">
                          <div
                            className={`h-full rounded-full transition-all ${
                              disk.total_gb > 0 && (disk.total_gb - disk.free_gb) / disk.total_gb > 0.9
                                ? 'bg-red-500'
                                : 'bg-blue-500'
                            }`}
                            style={{ width: disk.total_gb > 0 ? `${((disk.total_gb - disk.free_gb) / disk.total_gb) * 100}%` : '0%' }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <ServiceUnavailable name="Radarr" />
            )}
          </DashboardCard>

          {/* Sonarr */}
          <DashboardCard>
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2 uppercase tracking-wide">
              <Tv size={16} className="text-purple-500" /> Sonarr
            </h2>
            {sonarr ? (
              <>
                <div className="grid grid-cols-4 gap-3 mb-4">
                  <div className="bg-gray-50 dark:bg-gray-800/50 p-3 rounded-lg text-center">
                    <span className="text-xs text-gray-500 block">Series</span>
                    <span className="font-bold text-gray-900 dark:text-white">{sonarr.total_series}</span>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800/50 p-3 rounded-lg text-center">
                    <span className="text-xs text-gray-500 block">Surveillees</span>
                    <span className="font-bold text-purple-400">{sonarr.monitored}</span>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800/50 p-3 rounded-lg text-center">
                    <span className="text-xs text-gray-500 block">Episodes</span>
                    <span className="font-bold text-gray-900 dark:text-white">{sonarr.total_episodes.toLocaleString()}</span>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800/50 p-3 rounded-lg text-center">
                    <span className="text-xs text-gray-500 block">Queue</span>
                    <span className="font-bold text-orange-400">{sonarr.queue_count}</span>
                  </div>
                </div>
                {/* Upcoming */}
                {sonarr.upcoming.length > 0 && (
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1">
                      <Calendar size={12} /> Prochains episodes
                    </p>
                    <div className="space-y-2">
                      {sonarr.upcoming.map((ep, i) => (
                        <div key={i} className="flex justify-between items-center text-sm py-1.5 border-b border-gray-100 dark:border-gray-800 last:border-0">
                          <div className="min-w-0">
                            <span className="text-gray-700 dark:text-gray-300">{ep.series}</span>
                            <span className="text-gray-400 dark:text-gray-500 ml-2 text-xs">S{String(ep.season).padStart(2, '0')}E{String(ep.episode).padStart(2, '0')}</span>
                          </div>
                          <span className="text-xs text-gray-400 ml-2 whitespace-nowrap">{ep.air_date}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <ServiceUnavailable name="Sonarr" />
            )}
          </DashboardCard>
        </div>

        {/* Column 3: Tautulli + Upcoming Movies */}
        <div className="space-y-6">

          {/* Tautulli - Active Sessions */}
          <DashboardCard>
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2 uppercase tracking-wide">
              <Users size={16} className="text-green-500" /> Activite en cours
            </h2>
            {tautulli ? (
              <>
                <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg mb-3">
                  <div className="flex items-center gap-2">
                    <Play size={14} className="text-green-400" />
                    <span className="text-sm text-gray-700 dark:text-gray-300">Streams actifs</span>
                  </div>
                  <span className="font-bold text-gray-900 dark:text-white">{tautulli.stream_count}</span>
                </div>
                {tautulli.total_bandwidth_mbps > 0 && (
                  <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg mb-3">
                    <div className="flex items-center gap-2">
                      <Wifi size={14} className="text-blue-400" />
                      <span className="text-sm text-gray-700 dark:text-gray-300">Bande passante</span>
                    </div>
                    <span className="font-mono text-sm text-gray-900 dark:text-white">{tautulli.total_bandwidth_mbps} Mbps</span>
                  </div>
                )}
                {tautulli.sessions.length > 0 && (
                  <div className="mt-3 space-y-2">
                    <p className="text-xs text-gray-400 uppercase tracking-wider">Sessions</p>
                    {tautulli.sessions.map((s, i) => (
                      <div key={i} className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                        <div className="flex justify-between items-start">
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{s.title}</p>
                            <p className="text-xs text-gray-400">{s.user} - {s.player}</p>
                          </div>
                          <span className={`text-xs px-2 py-0.5 rounded-full ${
                            s.state === 'playing' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                          }`}>
                            {s.state === 'playing' ? 'Lecture' : 'Pause'}
                          </span>
                        </div>
                        <div className="mt-2 w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                          <div className="h-full rounded-full bg-purple-500" style={{ width: `${s.progress}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                {tautulli.sessions.length === 0 && tautulli.stream_count === 0 && (
                  <p className="text-sm text-gray-400 dark:text-gray-500 text-center py-4">Aucun stream en cours</p>
                )}
              </>
            ) : (
              <ServiceUnavailable name="Tautulli" />
            )}
          </DashboardCard>

          {/* Most Watched */}
          {tautulli && tautulli.most_watched.length > 0 && (
            <DashboardCard>
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2 uppercase tracking-wide">
                <Film size={16} className="text-pink-500" /> Les plus regardes
              </h2>
              <div className="space-y-2">
                {tautulli.most_watched.map((item, i) => (
                  <div key={i} className="flex justify-between items-center text-sm py-1.5 border-b border-gray-100 dark:border-gray-800 last:border-0">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-gray-400 text-xs w-4">{i + 1}</span>
                      <span className="text-gray-700 dark:text-gray-300 truncate">{item.title}</span>
                    </div>
                    <span className="text-pink-400 font-mono text-xs ml-2">{item.total_plays}x</span>
                  </div>
                ))}
              </div>
            </DashboardCard>
          )}

          {/* Upcoming Movies */}
          {radarr && radarr.upcoming.length > 0 && (
            <DashboardCard>
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2 uppercase tracking-wide">
                <Calendar size={16} className="text-blue-500" /> Films a venir
              </h2>
              <div className="space-y-2">
                {radarr.upcoming.map((movie, i) => (
                  <div key={i} className="flex justify-between items-center text-sm py-1.5 border-b border-gray-100 dark:border-gray-800 last:border-0">
                    <span className="text-gray-700 dark:text-gray-300 truncate">{movie.title}</span>
                    <span className="text-xs text-gray-400 ml-2">{movie.year}</span>
                  </div>
                ))}
              </div>
            </DashboardCard>
          )}
        </div>
      </div>
    </DashboardShell>
  );
}
