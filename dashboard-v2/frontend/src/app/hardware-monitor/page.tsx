'use client';

import React from 'react';
import { useHardwareStats } from '@/hooks/useHardwareStats';
import DashboardShell from '@/components/common/DashboardShell';
import DashboardCard from '@/components/common/DashboardCard';
import KpiCard from '@/components/hardware/KpiCard';
import ProgressBar from '@/components/hardware/ProgressBar';
import {
  Cpu,
  MemoryStick,
  HardDrive,
  Wifi,
  Zap,
  Server,
  ArrowDown,
  ArrowUp,
  Activity,
  Clock,
  Thermometer,
  Fan,
  TrendingUp
} from 'lucide-react';

// CPU History SVG chart
const CpuChart = ({ history }: { history: { time: string; cpu: number; ram: number }[] }) => {
  if (history.length < 2) {
    return (
      <div className="h-32 flex items-center justify-center text-gray-400 dark:text-gray-500 text-sm">
        Collecte des données...
      </div>
    );
  }

  const width = 100;
  const height = 100;
  const padding = 5;
  const maxValue = 100;

  const points = history.map((point, index) => {
    const x = padding + (index / (history.length - 1)) * (width - 2 * padding);
    const y = height - padding - (point.cpu / maxValue) * (height - 2 * padding);
    return `${x},${y}`;
  }).join(' ');

  const areaPoints = `${padding},${height - padding} ${points} ${width - padding},${height - padding}`;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-32" preserveAspectRatio="none">
      {[25, 50, 75].map(v => (
        <line
          key={v}
          x1={padding}
          y1={height - padding - (v / maxValue) * (height - 2 * padding)}
          x2={width - padding}
          y2={height - padding - (v / maxValue) * (height - 2 * padding)}
          className="stroke-gray-200 dark:stroke-gray-700"
          strokeWidth="0.3"
          strokeDasharray="2,2"
        />
      ))}
      <polygon points={areaPoints} fill="url(#cpuGradient)" opacity="0.3" />
      <polyline
        points={points}
        fill="none"
        stroke="#3b82f6"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {history.length > 0 && (
        <circle
          cx={width - padding}
          cy={height - padding - (history[history.length - 1].cpu / maxValue) * (height - 2 * padding)}
          r="2"
          fill="#3b82f6"
        />
      )}
      <defs>
        <linearGradient id="cpuGradient" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#3b82f6" />
          <stop offset="100%" stopColor="#1e3a5f" stopOpacity="0" />
        </linearGradient>
      </defs>
    </svg>
  );
};

export default function HardwareMonitor() {
  const { stats, history, loading, error } = useHardwareStats({
    interval: 2000,
    historyLength: 60,
  });

  if (loading && !stats) {
    return (
      <DashboardShell>
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <Activity className="w-12 h-12 text-blue-500 animate-pulse mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">Connexion au moniteur...</p>
          </div>
        </div>
      </DashboardShell>
    );
  }

  if (error) {
    return (
      <DashboardShell>
        <div className="flex items-center justify-center h-64">
          <div className="text-center text-red-500 dark:text-red-400">
            <p className="text-xl mb-2">Erreur de connexion</p>
            <p className="text-sm text-gray-500">{error}</p>
          </div>
        </div>
      </DashboardShell>
    );
  }

  const cpuTemp = stats?.cpuTemp || 0;
  const cpuLoad = stats?.cpuLoad || 0;
  const cpuPower = stats?.cpuPower || 0;
  const cpuClock = stats?.cpuClockSpeed || 0;
  const cpuFanSpeed = stats?.cpuFanSpeed || 0;
  const cpuCoreLoads = stats?.cpuCoreLoads || [];
  const ramUsedPercent = stats?.ramUsedPercent || 0;
  const ramUsed = stats?.ramUsed || 0;
  const ramTotal = stats?.ramTotal || 0;
  const downloadSpeed = stats?.network?.downloadSpeed || 0;
  const uploadSpeed = stats?.network?.uploadSpeed || 0;
  const drives = stats?.drives || [];
  const gpus = stats?.gpus || [];
  const processes = stats?.topProcesses || [];
  const isCpuCritical = cpuTemp > 80;

  return (
    <DashboardShell>
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Activity className="text-blue-500" />
            Hardware Monitor
          </h1>
          <p className="text-gray-500 text-sm mt-1 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            {stats?.osName || "System Online"}
          </p>
        </div>
        <div className="flex gap-3">
          <div className="px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 text-sm flex items-center gap-2">
            <Clock size={14} className="text-gray-400 dark:text-gray-500" />
            <span className="text-gray-900 dark:text-white font-mono">{stats?.uptime || "00:00:00"}</span>
          </div>
        </div>
      </div>

      {stats && (
        <>
          {/* KPI Cards Row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <KpiCard
              icon={Cpu}
              title="CPU"
              value={`${cpuLoad.toFixed(0)}%`}
              subtext={cpuTemp > 0 ? `${cpuTemp.toFixed(0)}°C` : undefined}
              color={isCpuCritical ? "text-red-500" : "text-blue-400"}
              alert={isCpuCritical}
              style={{ animationDelay: '0ms' }}
            />
            <KpiCard
              icon={MemoryStick}
              title="RAM"
              value={`${ramUsedPercent.toFixed(0)}%`}
              subtext={`${ramUsed.toFixed(1)} / ${ramTotal.toFixed(1)} GB`}
              color="text-purple-400"
              style={{ animationDelay: '80ms' }}
            />
            <KpiCard
              icon={Wifi}
              title="Download"
              value={`${downloadSpeed.toFixed(1)}`}
              subtext="Mbps"
              color="text-green-400"
              style={{ animationDelay: '160ms' }}
            />
            <KpiCard
              icon={Wifi}
              title="Upload"
              value={`${uploadSpeed.toFixed(1)}`}
              subtext="Mbps"
              color="text-cyan-400"
              style={{ animationDelay: '240ms' }}
            />
          </div>

          {/* Main Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

            {/* Column 1-2: CPU & GPU */}
            <div className="lg:col-span-2 space-y-6">

              {/* CPU Panel */}
              <DashboardCard className={isCpuCritical ? '!border-red-500' : ''}>
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                      <Cpu size={20} className="text-blue-400" />
                      Processor
                    </h2>
                    <p className="text-xs text-gray-500 mt-1">{stats.cpuName}</p>
                  </div>
                  <div className="text-right">
                    <span className="text-3xl font-bold text-gray-900 dark:text-white">{cpuLoad.toFixed(0)}%</span>
                    {cpuClock > 0 && (
                      <p className="text-xs text-gray-500">{(cpuClock / 1000).toFixed(2)} GHz</p>
                    )}
                  </div>
                </div>

                {/* CPU History Chart */}
                <div className="mb-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
                      <TrendingUp size={12} /> CPU Usage History
                    </span>
                    <span className="text-xs text-gray-400 dark:text-gray-500">Last 2 min</span>
                  </div>
                  <CpuChart history={history} />
                </div>

                {/* Core Loads */}
                {cpuCoreLoads.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Core Activity ({cpuCoreLoads.length} cores)</p>
                    <div className="grid gap-1" style={{ gridTemplateColumns: `repeat(${Math.min(cpuCoreLoads.length, 12)}, 1fr)` }}>
                      {cpuCoreLoads.map((load, i) => (
                        <div key={i} className="relative" title={`Core ${i}: ${load.toFixed(0)}%`}>
                          <div className="h-8 bg-gray-100 dark:bg-gray-800 rounded overflow-hidden">
                            <div
                              className={`w-full transition-all duration-300 ${load > 90 ? 'bg-red-500' : load > 70 ? 'bg-orange-500' : 'bg-blue-500'}`}
                              style={{ height: `${load}%`, marginTop: `${100 - load}%` }}
                            />
                          </div>
                          <span className="absolute bottom-0 left-1/2 -translate-x-1/2 text-[8px] text-gray-400 dark:text-gray-500">{i}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* CPU Stats Row */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="bg-gray-50 dark:bg-gray-800/50 p-3 rounded-lg text-center">
                    <Thermometer size={16} className="mx-auto mb-1 text-orange-400" />
                    <span className="text-xs text-gray-500 block">Temp</span>
                    <span className={`font-bold ${cpuTemp > 80 ? 'text-red-400' : cpuTemp > 65 ? 'text-orange-400' : cpuTemp > 0 ? 'text-green-400' : 'text-gray-400'}`}>
                      {cpuTemp > 0 ? `${cpuTemp.toFixed(0)}°C` : 'N/A'}
                    </span>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800/50 p-3 rounded-lg text-center">
                    <Zap size={16} className="mx-auto mb-1 text-yellow-400" />
                    <span className="text-xs text-gray-500 block">Power</span>
                    <span className={`font-bold ${cpuPower > 0 ? 'text-yellow-400' : 'text-gray-400'}`}>
                      {cpuPower > 0 ? `${cpuPower.toFixed(0)}W` : 'N/A'}
                    </span>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800/50 p-3 rounded-lg text-center">
                    <Fan size={16} className="mx-auto mb-1 text-cyan-400" />
                    <span className="text-xs text-gray-500 block">Fan</span>
                    <span className={`font-bold ${cpuFanSpeed > 0 ? 'text-cyan-400' : 'text-gray-400'}`}>
                      {cpuFanSpeed > 0 ? `${cpuFanSpeed} RPM` : 'N/A'}
                    </span>
                  </div>
                </div>
              </DashboardCard>

              {/* GPU Panel */}
              {gpus.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {gpus.map((gpu, idx) => (
                    <DashboardCard key={idx}>
                      <div className="flex justify-between items-start mb-4">
                        <div className="min-w-0 flex-1">
                          <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                            <Server size={16} className="text-purple-400 flex-shrink-0" />
                            GPU
                          </h3>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 truncate" title={gpu.name}>{gpu.name}</p>
                        </div>
                        <span className="text-2xl font-bold text-gray-900 dark:text-white ml-2">{gpu.load.toFixed(0)}%</span>
                      </div>

                      <ProgressBar label="Core Load" value={gpu.load} color="bg-purple-500" />
                      <ProgressBar
                        label="VRAM"
                        value={gpu.memoryTotal > 0 ? (gpu.memoryUsed / gpu.memoryTotal) * 100 : 0}
                        subLabel={`${gpu.memoryUsed.toFixed(0)} / ${gpu.memoryTotal.toFixed(0)} MB`}
                        color="bg-purple-400/70"
                      />

                      <div className="grid grid-cols-3 gap-2 mt-3">
                        <div className="bg-gray-50 dark:bg-gray-800/50 p-2 rounded text-center">
                          <span className="text-[10px] text-gray-500 block">Temp</span>
                          <span className="text-sm font-bold text-orange-400">{gpu.temperature > 0 ? `${gpu.temperature}°C` : 'N/A'}</span>
                        </div>
                        <div className="bg-gray-50 dark:bg-gray-800/50 p-2 rounded text-center">
                          <span className="text-[10px] text-gray-500 block">Power</span>
                          <span className="text-sm font-bold text-yellow-400">{gpu.power > 0 ? `${gpu.power.toFixed(0)}W` : 'N/A'}</span>
                        </div>
                        <div className="bg-gray-50 dark:bg-gray-800/50 p-2 rounded text-center">
                          <span className="text-[10px] text-gray-500 block">Fan</span>
                          <span className="text-sm font-bold text-cyan-400">{gpu.fanSpeed > 0 ? `${gpu.fanSpeed}%` : 'N/A'}</span>
                        </div>
                      </div>
                    </DashboardCard>
                  ))}
                </div>
              ) : (
                <DashboardCard className="text-center">
                  <Server size={24} className="mx-auto mb-2 text-gray-400 opacity-50" />
                  <p className="text-gray-500">Aucun GPU détecté</p>
                </DashboardCard>
              )}
            </div>

            {/* Column 3: Processes, Storage, Network */}
            <div className="space-y-6">

              {/* Top Processes */}
              <DashboardCard>
                <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2 uppercase tracking-wide">
                  <Activity size={16} className="text-pink-500" /> Top Memory
                </h2>
                <div className="space-y-2">
                  {processes.length > 0 ? processes.map((proc, i) => (
                    <div key={proc.id} className="flex justify-between items-center text-sm py-1 border-b border-gray-100 dark:border-gray-800 last:border-0">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-gray-400 text-xs w-4">{i + 1}</span>
                        <span className="text-gray-700 dark:text-gray-300 truncate" title={proc.name}>{proc.name}</span>
                      </div>
                      <span className="text-pink-400 font-mono text-xs ml-2">{proc.memoryUsedMb.toFixed(0)} MB</span>
                    </div>
                  )) : (
                    <p className="text-xs text-gray-400 italic">Aucune donnée</p>
                  )}
                </div>
              </DashboardCard>

              {/* Storage */}
              <DashboardCard>
                <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2 uppercase tracking-wide">
                  <HardDrive size={16} className="text-emerald-500" /> Storage
                </h2>
                <div className="space-y-4">
                  {drives.map((drive, idx) => (
                    <div key={idx}>
                      <div className="flex justify-between items-center mb-1">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="text-xs text-gray-500 bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded">{drive.mount}</span>
                          <span className="text-sm text-gray-700 dark:text-gray-300 truncate" title={drive.name}>{drive.name}</span>
                        </div>
                      </div>
                      <div className="flex justify-between text-xs text-gray-500 mb-1">
                        <span>{drive.usedSpace.toFixed(0)} GB</span>
                        <span>{drive.totalSpace.toFixed(0)} GB</span>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-800 rounded-full h-2">
                        <div
                          className={`h-full rounded-full transition-all ${drive.usedPercent > 90 ? 'bg-red-500' : drive.usedPercent > 75 ? 'bg-orange-500' : 'bg-emerald-500'}`}
                          style={{ width: `${drive.usedPercent}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </DashboardCard>

              {/* Network */}
              <DashboardCard>
                <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2 uppercase tracking-wide">
                  <Wifi size={16} className="text-blue-500" /> Network
                </h2>
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <ArrowDown className="text-green-400" size={18} />
                      <div>
                        <span className="text-xs text-gray-500 block">Download</span>
                        <span className="font-mono text-gray-900 dark:text-white">{downloadSpeed.toFixed(2)} Mbps</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <ArrowUp className="text-blue-400" size={18} />
                      <div>
                        <span className="text-xs text-gray-500 block">Upload</span>
                        <span className="font-mono text-gray-900 dark:text-white">{uploadSpeed.toFixed(2)} Mbps</span>
                      </div>
                    </div>
                  </div>
                </div>
              </DashboardCard>

            </div>
          </div>
        </>
      )}
    </DashboardShell>
  );
}
