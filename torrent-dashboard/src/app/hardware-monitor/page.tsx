'use client';

import React, { useEffect, useState } from 'react';
import Navbar from '@/components/Navbar';
import { useHardwareStats } from '@/hooks/useHardwareStats';
import CircularGauge from '@/components/hardware/CircularGauge';
import StorageBar from '@/components/hardware/StorageBar';
import GpuCard from '@/components/hardware/GpuCard';

export default function HardwareMonitor() {
  const { stats, loading, error } = useHardwareStats({
    interval: 2000,
    apiUrl: process.env.NEXT_PUBLIC_HWMONITOR_API || '/api/hardware/stats',
  });

  return (
    <div className="min-h-screen bg-gray-900 text-gray-200">
      <Navbar />
      <div className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">Hardware Monitor</h1>
        {error && <p className="text-red-500">Error: {error}</p>}
        {loading && <p>Loading...</p>}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* CPU & RAM */}
            <div className="bg-gray-800 p-4 rounded-lg shadow">
              <h2 className="text-xl font-semibold mb-4">CPU & RAM</h2>
              <CircularGauge label="CPU Load" value={stats.cpuLoad} />
              <CircularGauge label="RAM Usage" value={stats.ramUsedPercent} />
            </div>

            {/* GPU */}
            <div className="bg-gray-800 p-4 rounded-lg shadow">
              <h2 className="text-xl font-semibold mb-4">GPU</h2>
              {stats.gpus.map((gpu, idx) => (
                <GpuCard key={idx} gpu={gpu} />
              ))}
            </div>

            {/* Storage */}
            <div className="bg-gray-800 p-4 rounded-lg shadow">
              <h2 className="text-xl font-semibold mb-4">Storage</h2>
              {stats.drives.map((drive, idx) => (
                <StorageBar key={idx} {...drive} />
              ))}
            </div>

            {/* Network */}
            <div className="bg-gray-800 p-4 rounded-lg shadow">
              <h2 className="text-xl font-semibold mb-4">Network</h2>
              <p>Upload: {stats.network.uploadSpeed} Mbps</p>
              <p>Download: {stats.network.downloadSpeed} Mbps</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
