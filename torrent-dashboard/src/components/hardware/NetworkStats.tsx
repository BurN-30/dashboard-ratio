import React from 'react';
import { Upload, Download } from 'lucide-react';
import { NetworkData } from '@/hooks/useHardwareStats';

interface NetworkStatsProps {
  network: NetworkData;
}

export default function NetworkStats({ network }: NetworkStatsProps) {
  const formatSpeed = (speedKbps: number) => {
    if (speedKbps < 1024) return `${speedKbps.toFixed(2)} KB/s`;
    return `${(speedKbps / 1024).toFixed(2)} MB/s`;
  };

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* Upload */}
      <div className="bg-gradient-to-br from-green-900/30 to-green-900/10 border border-green-700/30 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <Upload className="w-5 h-5 text-green-400" />
          <span className="text-sm font-semibold text-gray-300">Upload</span>
        </div>
        <p className="text-2xl font-bold text-green-400">
          {formatSpeed(network.uploadSpeed)}
        </p>
      </div>

      {/* Download */}
      <div className="bg-gradient-to-br from-blue-900/30 to-blue-900/10 border border-blue-700/30 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <Download className="w-5 h-5 text-blue-400" />
          <span className="text-sm font-semibold text-gray-300">Download</span>
        </div>
        <p className="text-2xl font-bold text-blue-400">
          {formatSpeed(network.downloadSpeed)}
        </p>
      </div>
    </div>
  );
}
