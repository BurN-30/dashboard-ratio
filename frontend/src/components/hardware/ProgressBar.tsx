import React from 'react';

interface ProgressBarProps {
  value: number;
  color?: string;
  label: string;
  subLabel?: string;
}

export default function ProgressBar({ value, color = "bg-blue-500", label, subLabel }: ProgressBarProps) {
  const safeValue = value || 0;

  return (
    <div className="w-full mb-3">
      <div className="flex justify-between text-xs mb-1">
        <span className="text-gray-500 dark:text-gray-400 font-medium">{label}</span>
        <span className="text-gray-700 dark:text-gray-200">{subLabel || `${safeValue.toFixed(1)}%`}</span>
      </div>
      <div className="w-full bg-gray-200 dark:bg-gray-700/50 rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all duration-300 ${color}`}
          style={{ width: `${Math.min(safeValue, 100)}%` }}
        />
      </div>
    </div>
  );
}
