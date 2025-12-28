'use client';

import React, { useEffect, useState } from 'react';
import { useHardwareStats } from '@/hooks/useHardwareStats';
import { RefreshCw, AlertCircle, Clock, Zap, Cpu, Database } from 'lucide-react';
import CircularGauge from '@/components/hardware/CircularGauge';
import StorageBar from '@/components/hardware/StorageBar';
import GpuCard from '@/components/hardware/GpuCard';
import NetworkStats from '@/components/hardware/NetworkStats';

export default function HardwareMonitor() {
  const { stats, loading, error, isPolling, togglePolling, manualRefresh } = useHardwareStats({
    interval: 2000, // Refresh every 2 seconds
    apiUrl: process.env.NEXT_PUBLIC_HWMONITOR_API || 'http://localhost:5056/api/stats',
  });

  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  // Determine CPU color based on load
  const getCpuColor = (load: number) => {
    if (load < 30) return 'green';
    if (load < 60) return 'blue';
    if (load < 80) return 'orange';
    return 'red';
  };

  // Determine RAM color based on percentage
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
            <p className="text-gray-400 mt-2">Real-time system monitoring and performance metrics</p>
          </div>

          <div className="flex items-center gap-3">
            {/* Last update */}
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

            {/* Polling toggle */}
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

            {/* Refresh button */}
            <button
              onClick={manualRefresh}
              disabled={loading}
              className="p-2 hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
            >
              <RefreshCw
                className={`w-5 h-5 text-gray-300 ${loading ? 'animate-spin' : ''}`}
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

        {/* Main content */}
        {stats && (
          <div className="space-y-8">
            {/* CPU & RAM Section */}
            <section>
              <h2 className="text-xl font-bold text-gray-100 mb-6 flex items-center gap-2">
                <Cpu className="w-6 h-6 text-blue-400" />
                Processor & Memory
              </h2>

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

                {/* CPU Stats Cards */}
                <div className="space-y-3">
                  {/* Temperature */}
                  <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
                    <p className="text-xs text-gray-400 mb-1">Temperature</p>
                    <p className={`text-2xl font-bold ${
                      stats.cpuTemp === 0
                        ? 'text-gray-400'
                        : stats.cpuTemp < 50
                        ? 'text-green-400'
                        : stats.cpuTemp < 80
                        ? 'text-yellow-400'
                        : 'text-red-400'
                    }`}>
                      {stats.cpuTemp === 0 ? 'N/A' : `${stats.cpuTemp.toFixed(1)}°C`}
                    </p>
                  </div>

                  {/* Power */}
                  <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
                    <p className="text-xs text-gray-400 mb-1">Power Draw</p>
                    <p className={`text-2xl font-bold ${
                      stats.cpuPower === 0 ? 'text-gray-400' : 'text-yellow-400'
                    }`}>
                      {stats.cpuPower === 0 ? 'N/A' : `${stats.cpuPower.toFixed(1)}W`}
                    </p>
                  </div>

                  {/* Clock */}
                  <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
                    <p className="text-xs text-gray-400 mb-1">Clock Speed</p>
                    <p className={`text-2xl font-bold ${
                      stats.cpuClockSpeed === 0 ? 'text-gray-400' : 'text-purple-400'
                    }`}>
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
            </section>

            {/* GPUs Section */}
            {stats.gpus.length > 0 && (
              <section>
                <h2 className="text-xl font-bold text-gray-100 mb-6 flex items-center gap-2">
                  <Zap className="w-6 h-6 text-blue-400" />
                  Graphics Processors ({stats.gpus.length})
                </h2>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {stats.gpus.map((gpu, idx) => (
                    <GpuCard key={idx} gpu={gpu} />
                  ))}
                </div>
              </section>
            )}

            {/* Storage Section */}
            {stats.drives.length > 0 && (
              <section>
                <h2 className="text-xl font-bold text-gray-100 mb-6 flex items-center gap-2">
                  <Database className="w-6 h-6 text-blue-400" />
                  Storage Drives ({stats.drives.length})
                </h2>

                <div className="space-y-4">
                  {stats.drives.map((drive, idx) => (
                    <StorageBar key={idx} {...drive} />
                  ))}
                </div>
              </section>
            )}

            {/* Network Section */}
            <section>
              <h2 className="text-xl font-bold text-gray-100 mb-6 flex items-center gap-2">
                <Database className="w-6 h-6 text-blue-400" />
                Network
              </h2>

              <NetworkStats network={stats.network} />
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
