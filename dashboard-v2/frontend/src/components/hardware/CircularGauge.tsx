import React from 'react';

interface CircularGaugeProps {
  label: string;
  value: number;
  max?: number;
  unit?: string;
  size?: 'sm' | 'md' | 'lg';
  color?: 'green' | 'blue' | 'red' | 'orange';
}

const textSizeMap = {
  sm: 'text-2xl',
  md: 'text-3xl',
  lg: 'text-4xl',
} as const;

export default function CircularGauge({
  label,
  value,
  max = 100,
  unit = '%',
  size = 'md',
  color = 'green',
}: CircularGaugeProps) {
  const percentage = Math.min((value / max) * 100, 100);

  const sizeMap = {
    sm: { size: 100, strokeWidth: 6 },
    md: { size: 140, strokeWidth: 7 },
    lg: { size: 180, strokeWidth: 8 },
  };

  const colorMap = {
    green: 'text-green-400',
    blue: 'text-blue-400',
    red: 'text-red-400',
    orange: 'text-orange-400',
  };

  const stopColors = {
    green: ['#4ade80', '#16a34a'],
    blue: ['#60a5fa', '#2563eb'],
    red: ['#f87171', '#dc2626'],
    orange: ['#fb923c', '#ea580c'],
  };

  const { size: svgSize, strokeWidth } = sizeMap[size];
  const textClass = textSizeMap[size];
  const textColor = colorMap[color];
  const [stopStart, stopEnd] = stopColors[color];

  const radius = svgSize / 2 - strokeWidth;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percentage / 100) * circumference;

  return (
    <div className="flex flex-col items-center justify-center">
      <div className="relative" style={{ width: svgSize, height: svgSize }}>
        <svg width={svgSize} height={svgSize} className="transform -rotate-90">
          {/* Background circle */}
          <circle
            cx={svgSize / 2}
            cy={svgSize / 2}
            r={radius}
            fill="none"
            className="stroke-gray-200 dark:stroke-white/10"
            strokeWidth={strokeWidth}
          />
          {/* Progress circle with gradient */}
          <defs>
            <linearGradient id={`gradient-${label}`} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={stopStart} />
              <stop offset="100%" stopColor={stopEnd} />
            </linearGradient>
          </defs>
          <circle
            cx={svgSize / 2}
            cy={svgSize / 2}
            r={radius}
            fill="none"
            stroke={`url(#gradient-${label})`}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-300"
          />
        </svg>

        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`${textClass} font-bold ${textColor}`}>
            {value.toFixed(1)}
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400">{unit}</span>
        </div>
      </div>

      {/* Label */}
      <p className="mt-4 text-sm font-semibold text-gray-600 dark:text-gray-300 text-center">{label}</p>
    </div>
  );
}
