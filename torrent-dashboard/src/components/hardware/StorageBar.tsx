import React from 'react';

interface StorageBarProps {
  name: string;
  used?: number | null;
  total?: number | null;
  temperature?: number | null;
  usedPercent?: number | null;
}

export default function StorageBar({
  name,
  used,
  total,
  temperature,
  usedPercent,
}: StorageBarProps) {
  const safeUsed = Number.isFinite(Number(used)) ? Number(used) : 0;
  const safeTotal = Number.isFinite(Number(total)) ? Number(total) : 0;
  const computedPercent = Number.isFinite(Number(usedPercent))
    ? Number(usedPercent)
    : safeTotal > 0
      ? (safeUsed / safeTotal) * 100
      : 0;

  const getBarColor = (percent: number) => {
    if (percent < 50) return 'bg-green-500';
    if (percent < 75) return 'bg-yellow-500';
    if (percent < 90) return 'bg-orange-500';
    return 'bg-red-500';
  };

  const getTempColor = (temp: number | undefined) => {
    if (!temp) return 'text-gray-400';
    if (temp < 30) return 'text-blue-400';
    if (temp < 45) return 'text-green-400';
    if (temp < 55) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="rounded-xl border border-white/5 bg-gray-900/60 p-4 shadow-sm shadow-black/20">
      <div className="flex justify-between items-center gap-3">
        <div className="flex-1">
          <h4 className="text-sm font-semibold text-gray-100">{name}</h4>
          <p className="text-xs text-gray-400">
            {safeUsed.toFixed(1)} GB / {safeTotal.toFixed(1)} GB
          </p>
        </div>
        <div className="flex items-center gap-3 ml-2">
          <span className="text-sm font-bold text-gray-100 w-14 text-right">
            {computedPercent.toFixed(1)}%
          </span>
          {temperature !== null && temperature !== undefined && (
            <span className={`text-sm font-semibold ${getTempColor(temperature)}`}>
              {temperature.toFixed(0)}°C
            </span>
          )}
        </div>
      </div>

      <div className="mt-3 w-full bg-gray-800/80 rounded-full h-2.5 overflow-hidden">
        <div
          className={`h-full ${getBarColor(computedPercent)} transition-all duration-500 rounded-full`}
          style={{ width: `${Math.min(computedPercent, 100)}%` }}
        />
      </div>
    </div>
  );
}
