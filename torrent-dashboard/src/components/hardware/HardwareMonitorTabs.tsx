'use client';

import React, { useState } from 'react';
import { useHardwareStats } from '@/hooks/useHardwareStats';
import {
  RefreshCw,
  AlertCircle,
  Clock,
  Zap,
  Cpu,
  Database,
} from 'lucide-react';
import CircularGauge from '@/components/hardware/CircularGauge';
import StorageBar from '@/components/hardware/StorageBar';
import GpuCard from '@/components/hardware/GpuCard';
import NetworkStats from '@/components/hardware/NetworkStats';

type TabType = 'overview' | 'cpu' | 'storage' | 'gpu' | 'network';

const TABS: { id: TabType; label: string; icon: React.ReactNode }[] = [
  { id: 'overview', label: 'Overview', icon: <Zap className="w-4 h-4" /> },
  { id: 'cpu', label: 'Processor', icon: <Cpu className="w-4 h-4" /> },
  { id: 'storage', label: 'Storage', icon: <Database className="w-4 h-4" /> },
  { id: 'gpu', label: 'Graphics', icon: <Zap className="w-4 h-4" /> },
  { id: 'network', label: 'Network', icon: <Database className="w-4 h-4" /> },
];

export default function HardwareMonitorTabs() {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const { stats, loading, error, isPolling, togglePolling, manualRefresh } =
    useHardwareStats({
      interval: 2000,
      apiUrl:
        process.env.NEXT_PUBLIC_HWMONITOR_API ||
        'http://localhost:5056/api/stats',
    });

  const getCpuColor = (load: number) => {
    if (load < 30) return 'green';
    if (load < 60) return 'blue';
    if (load < 80) return 'orange';
    return 'red';
  };

  const getRamColor = (percent: number) => {
    if (percent < 50) return 'green';
    if (percent < 75) return 'blue';
    if (percent < 90) return 'orange';
    return 'red';
  };

  return (
    <div className="min-h-screen bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white flex items-center gap-2">
              <Zap className="w-8 h-8 text-yellow-400" />
              Hardware Monitor
            </h1>
            <p className="text-gray-400 mt-2">
              Real-time system monitoring and performance metrics
            </p>
          </div>

          <div className="flex items-center gap-3">
            {stats && (
              <div className="text-right text-sm text-gray-400">
                <div className="flex items-center gap-1 justify-end mb-1">
                  <Clock className="w-4 h-4" />
                  Last update
                </div>
                <p className="text-xs text-gray-500">
                  {new Date(stats.timestamp).toLocaleTimeString()}
                </p>
              </div>
            )}

            <button
              onClick={togglePolling}
              className={`px-4 py-2 rounded-lg font-semibold text-sm transition-all ${
                isPolling
                  ? 'bg-green-600 hover:bg-green-700 text-white'
                  : 'bg-gray-700 hover:bg-gray-600 text-gray-200'
              }`}
            >
              {isPolling ? '● Auto' : '○ Manual'}
            </button>

            <button
              onClick={manualRefresh}
              disabled={loading}
              aria-label="Refresh"
              className="p-2 hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
            >
              <RefreshCw
                className={`w-5 h-5 text-gray-300 ${
                  loading ? 'animate-spin' : ''
                }`}
              />
            </button>
          </div>
        </div>

        {/* Error state */}
        {error && (
          <div className="mb-6 p-4 bg-red-900/20 border border-red-700/50 rounded-lg flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <div>
              <p className="text-red-400 font-semibold">Connection Error</p>
              <p className="text-red-300 text-sm">{error}</p>
            </div>
          </div>
        )}

        {/* Loading state */}
        {loading && !stats && (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin">
              <RefreshCw className="w-8 h-8 text-blue-400" />
            </div>
          </div>
        )}

        {stats && (
          <>
            {/* Tab Navigation */}
            <div className="mb-8 border-b border-gray-700">
              <div className="flex gap-2 overflow-x-auto">
                {TABS.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`px-4 py-3 font-medium text-sm transition-all border-b-2 flex items-center gap-2 whitespace-nowrap ${
                      activeTab === tab.id
                        ? 'border-blue-500 text-blue-400'
                        : 'border-transparent text-gray-400 hover:text-gray-300'
                    }`}
                  >
                    {tab.icon}
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Tab Content */}
            <div className="animate-fadeIn">
              {/* Overview Tab */}
              {activeTab === 'overview' && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                  {/* CPU Gauge */}
                  <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-6 flex flex-col items-center">
                    <CircularGauge
                      label={stats.cpuName}
                      value={stats.cpuLoad}
                      size="md"
                      color={getCpuColor(stats.cpuLoad)}
                    />
                  </div>

                  {/* CPU Stats */}
                  <div className="space-y-3">
                    <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
                      <p className="text-xs text-gray-400 mb-1">Temperature</p>
                      <p
                        className={`text-2xl font-bold ${
                          stats.cpuTemp === 0
                            ? 'text-gray-400'
                            : stats.cpuTemp < 50
                            ? 'text-green-400'
                            : stats.cpuTemp < 80
                            ? 'text-yellow-400'
                            : 'text-red-400'
                        }`}
                      >
                        {stats.cpuTemp === 0
                          ? 'N/A'
                          : `${stats.cpuTemp.toFixed(1)}°C`}
                      </p>
                    </div>

                    <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
                      <p className="text-xs text-gray-400 mb-1">Power Draw</p>
                      <p
                        className={`text-2xl font-bold ${
                          stats.cpuPower === 0 ? 'text-gray-400' : 'text-yellow-400'
                        }`}
                      >
                        {stats.cpuPower === 0
                          ? 'N/A'
                          : `${stats.cpuPower.toFixed(1)}W`}
                      </p>
                    </div>

                    <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
                      <p className="text-xs text-gray-400 mb-1">Clock Speed</p>
                      <p
                        className={`text-2xl font-bold ${
                          stats.cpuClockSpeed === 0
                            ? 'text-gray-400'
                            : 'text-purple-400'
                        }`}
                      >
                        {stats.cpuClockSpeed === 0
                          ? 'N/A'
                          : `${(stats.cpuClockSpeed / 1000).toFixed(2)} GHz`}
                      </p>
                    </div>
                  </div>

                  {/* RAM Gauge */}
                  <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-6 flex flex-col items-center">
                    <CircularGauge
                      label="Memory Usage"
                      value={stats.ramUsedPercent}
                      size="md"
                      color={getRamColor(stats.ramUsedPercent)}
                    />
                  </div>

                  {/* RAM Details */}
                  <div className="space-y-3">
                    <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
                      <p className="text-xs text-gray-400 mb-1">Used</p>
                      <p className="text-2xl font-bold text-cyan-400">
                        {stats.ramUsed.toFixed(1)} GB
                      </p>
                    </div>

                    <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
                      <p className="text-xs text-gray-400 mb-1">Total</p>
                      <p className="text-2xl font-bold text-gray-300">
                        {stats.ramTotal.toFixed(1)} GB
                      </p>
                    </div>

                    <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
                      <p className="text-xs text-gray-400 mb-1">Available</p>
                      <p className="text-2xl font-bold text-green-400">
                        {(stats.ramTotal - stats.ramUsed).toFixed(1)} GB
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* CPU Tab */}
              {activeTab === 'cpu' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-6 flex flex-col items-center">
                    <CircularGauge
                      label={stats.cpuName}
                      value={stats.cpuLoad}
                      size="lg"
                      color={getCpuColor(stats.cpuLoad)}
                    />
                  </div>

                  <div className="space-y-4">
                    <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
                      <p className="text-sm text-gray-400 mb-2">CPU Temperature</p>
                      <p
                        className={`text-3xl font-bold ${
                          stats.cpuTemp === 0
                            ? 'text-gray-400'
                            : stats.cpuTemp < 50
                            ? 'text-green-400'
                            : stats.cpuTemp < 80
                            ? 'text-yellow-400'
                            : 'text-red-400'
                        }`}
                      >
                        {stats.cpuTemp === 0 ? 'N/A' : `${stats.cpuTemp.toFixed(1)}°C`}
                      </p>
                    </div>

                    <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
                      <p className="text-sm text-gray-400 mb-2">Power Consumption</p>
                      <p
                        className={`text-3xl font-bold ${
                          stats.cpuPower === 0 ? 'text-gray-400' : 'text-yellow-400'
                        }`}
                      >
                        {stats.cpuPower === 0 ? 'N/A' : `${stats.cpuPower.toFixed(1)}W`}
                      </p>
                    </div>

                    <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
                      <p className="text-sm text-gray-400 mb-2">Clock Speed</p>
                      <p
                        className={`text-3xl font-bold ${
                          stats.cpuClockSpeed === 0
                            ? 'text-gray-400'
                            : 'text-purple-400'
                        }`}
                      >
                        {stats.cpuClockSpeed === 0
                          ? 'N/A'
                          : `${(stats.cpuClockSpeed / 1000).toFixed(2)} GHz`}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Storage Tab */}
              {activeTab === 'storage' && (
                <div className="space-y-4">
                  {stats.drives.length > 0 ? (
                    stats.drives.map((drive, idx) => (
                      <StorageBar key={idx} {...drive} />
                    ))
                  ) : (
                    <div className="text-gray-400">No storage data available</div>
                  )}
                </div>
              )}

              {/* GPU Tab */}
              {activeTab === 'gpu' && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {stats.gpus.length > 0 ? (
                    stats.gpus.map((gpu, idx) => (
                      <GpuCard key={idx} gpu={gpu} />
                    ))
                  ) : (
                    <div className="text-gray-400">No GPU data available</div>
                  )}
                </div>
              )}

              {/* Network Tab */}
              {activeTab === 'network' && <NetworkStats network={stats.network} />}
            </div>
          </>
        )}
      </div>

      <style jsx>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .animate-fadeIn {
          animation: fadeIn 0.3s ease-out;
        }
      `}</style>
    </div>
  );
}
