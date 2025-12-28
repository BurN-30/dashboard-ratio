'use client';

import React from 'react';
import { useHardwareStats } from '@/hooks/useHardwareStats';
import { Zap, AlertCircle, RefreshCw } from 'lucide-react';
import CircularGauge from './CircularGauge';

/**
 * Widget compact pour afficher un aperçu des stats hardware
 * Parfait pour l'intégrer dans le dashboard principal
 */
export default function HardwareMonitorWidget() {
  const { stats, loading, error, manualRefresh } = useHardwareStats({
    interval: 5000, // Refresh moins souvent sur la page principale
  });

  if (error) {
    return (
      <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
        <div className="flex items-center gap-2 text-red-400">
          <AlertCircle className="w-4 h-4" />
          <span className="text-sm">Hardware Monitor unavailable</span>
        </div>
      </div>
    );
  }

  if (loading || !stats) {
    return (
      <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
        <div className="flex items-center justify-center">
          <RefreshCw className="w-4 h-4 animate-spin text-blue-400" />
          <span className="ml-2 text-sm text-gray-400">Loading...</span>
        </div>
      </div>
    );
  }

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
    <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Zap className="w-5 h-5 text-yellow-400" />
          <h3 className="text-lg font-bold text-gray-100">Hardware</h3>
        </div>
        <button
          onClick={manualRefresh}
          className="p-1 hover:bg-gray-700 rounded transition-colors"
        >
          <RefreshCw className="w-4 h-4 text-gray-400" />
        </button>
      </div>

      {/* CPU & RAM Gauges */}
      <div className="grid grid-cols-2 gap-4">
        {/* CPU */}
        <div className="flex flex-col items-center">
          <div className="mb-2" style={{ width: '80px', height: '80px' }}>
            <svg viewBox="0 0 100 100" className="w-full h-full">
              <defs>
                <linearGradient id="cpuGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#4ade80" />
                  <stop offset="100%" stopColor="#16a34a" />
                </linearGradient>
              </defs>
              <circle
                cx="50"
                cy="50"
                r="40"
                fill="none"
                stroke="rgba(255, 255, 255, 0.1)"
                strokeWidth="3"
              />
              <circle
                cx="50"
                cy="50"
                r="40"
                fill="none"
                stroke="url(#cpuGrad)"
                strokeWidth="3"
                strokeDasharray={`${(stats.cpuLoad / 100) * 251.3} 251.3`}
                strokeLinecap="round"
                className="transform -rotate-90 origin-center"
                style={{ transformOrigin: '50px 50px' }}
              />
              <text
                x="50"
                y="55"
                textAnchor="middle"
                fontSize="18"
                fontWeight="bold"
                fill="#4ade80"
              >
                {stats.cpuLoad.toFixed(0)}%
              </text>
            </svg>
          </div>
          <p className="text-xs text-gray-400 text-center truncate w-full">CPU</p>
          <p className="text-xs text-gray-500 text-center truncate w-full">
            {stats.cpuName.substring(0, 15)}...
          </p>
        </div>

        {/* RAM */}
        <div className="flex flex-col items-center">
          <div className="mb-2" style={{ width: '80px', height: '80px' }}>
            <svg viewBox="0 0 100 100" className="w-full h-full">
              <defs>
                <linearGradient id="ramGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#60a5fa" />
                  <stop offset="100%" stopColor="#2563eb" />
                </linearGradient>
              </defs>
              <circle
                cx="50"
                cy="50"
                r="40"
                fill="none"
                stroke="rgba(255, 255, 255, 0.1)"
                strokeWidth="3"
              />
              <circle
                cx="50"
                cy="50"
                r="40"
                fill="none"
                stroke="url(#ramGrad)"
                strokeWidth="3"
                strokeDasharray={`${(stats.ramUsedPercent / 100) * 251.3} 251.3`}
                strokeLinecap="round"
                className="transform -rotate-90 origin-center"
                style={{ transformOrigin: '50px 50px' }}
              />
              <text
                x="50"
                y="55"
                textAnchor="middle"
                fontSize="18"
                fontWeight="bold"
                fill="#60a5fa"
              >
                {stats.ramUsedPercent.toFixed(0)}%
              </text>
            </svg>
          </div>
          <p className="text-xs text-gray-400 text-center">RAM</p>
          <p className="text-xs text-gray-500 text-center">
            {stats.ramUsed.toFixed(1)}/{stats.ramTotal.toFixed(1)} GB
          </p>
        </div>
      </div>

      {/* Storage Preview */}
      {stats.drives.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-700 space-y-2">
          <p className="text-xs font-semibold text-gray-400">Storage</p>
          {stats.drives.slice(0, 2).map((drive, idx) => (
            <div key={idx} className="space-y-1">
              <div className="flex justify-between items-center">
                <p className="text-xs text-gray-400 truncate flex-1">
                  {drive.name.substring(0, 20)}...
                </p>
                <p className="text-xs text-gray-300 ml-2">
                  {drive.usedPercent.toFixed(0)}%
                </p>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-1 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-orange-500 to-red-500 transition-all duration-300"
                  style={{ width: `${Math.min(drive.usedPercent, 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Network Summary */}
      {stats.network && (
        <div className="mt-4 pt-4 border-t border-gray-700 grid grid-cols-2 gap-2 text-xs">
          <div>
            <p className="text-gray-500">↓ Download</p>
            <p className="text-green-400 font-semibold">
              {(stats.network.downloadSpeed / 1024).toFixed(2)} MB/s
            </p>
          </div>
          <div>
            <p className="text-gray-500">↑ Upload</p>
            <p className="text-blue-400 font-semibold">
              {(stats.network.uploadSpeed / 1024).toFixed(2)} MB/s
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
