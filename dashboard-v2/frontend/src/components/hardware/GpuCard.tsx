import React from 'react';
import { Zap, Thermometer, MemoryStick } from 'lucide-react';
import { GpuData } from '@/hooks/useHardwareStats';

interface GpuCardProps {
  gpu: GpuData;
}

export default function GpuCard({ gpu }: GpuCardProps) {
  const getTempColor = (temp: number) => {
    if (temp === 0) return 'text-gray-400';
    if (temp < 50) return 'text-green-400';
    if (temp < 70) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getLoadColor = (load: number) => {
    if (load === 0) return 'text-gray-400';
    if (load < 50) return 'text-green-400';
    if (load < 75) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4 space-y-3">
      {/* GPU Name */}
      <h4 className="text-sm font-semibold text-gray-200 truncate">{gpu.name}</h4>

      {/* Load Bar */}
      <div className="space-y-1">
        <div className="flex justify-between items-center">
          <span className="text-xs text-gray-400">Load</span>
          <span className={`text-sm font-bold ${getLoadColor(gpu.load)}`}>
            {gpu.load.toFixed(1)}%
          </span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-1.5 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-300"
            style={{ width: `${Math.min(gpu.load, 100)}%` }}
          />
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-2 pt-2 text-xs">
        {/* Temperature */}
        <div className="flex items-center gap-2 bg-gray-900/50 rounded p-2">
          <Thermometer className={`w-4 h-4 ${getTempColor(gpu.temperature)}`} />
          <div>
            <p className="text-gray-500">Temp</p>
            <p className={`font-semibold ${getTempColor(gpu.temperature)}`}>
              {gpu.temperature === 0 ? 'N/A' : `${gpu.temperature.toFixed(0)}°C`}
            </p>
          </div>
        </div>

        {/* Power */}
        <div className="flex items-center gap-2 bg-gray-900/50 rounded p-2">
          <Zap className="w-4 h-4 text-yellow-400" />
          <div>
            <p className="text-gray-500">Power</p>
            <p className={`font-semibold ${gpu.power === 0 ? 'text-gray-400' : 'text-yellow-400'}`}>
              {gpu.power === 0 ? 'N/A' : `${gpu.power.toFixed(1)}W`}
            </p>
          </div>
        </div>

        {/* Memory */}
        <div className="flex items-center gap-2 bg-gray-900/50 rounded p-2 col-span-2">
          <MemoryStick className="w-4 h-4 text-purple-400" />
          <div>
            <p className="text-gray-500">VRAM</p>
            <p className={`font-semibold ${gpu.memoryTotal === 0 ? 'text-gray-400' : 'text-purple-400'}`}>
              {gpu.memoryTotal === 0
                ? 'N/A'
                : `${gpu.memoryUsed.toFixed(0)} / ${gpu.memoryTotal.toFixed(0)} MB`}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
