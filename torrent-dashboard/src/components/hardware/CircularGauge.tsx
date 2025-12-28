import React from 'react';

interface CircularGaugeProps {
  label: string;
  value: number;
  max?: number;
  unit?: string;
  size?: 'sm' | 'md' | 'lg';
  color?: 'green' | 'blue' | 'red' | 'orange';
}

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
    sm: { size: 100, strokeWidth: 6, textSize: 24 },
    md: { size: 140, strokeWidth: 7, textSize: 32 },
    lg: { size: 180, strokeWidth: 8, textSize: 40 },
  };

  const colorMap = {
    green: { gradient: 'from-green-400 to-green-600', text: 'text-green-400' },
    blue: { gradient: 'from-blue-400 to-blue-600', text: 'text-blue-400' },
    red: { gradient: 'from-red-400 to-red-600', text: 'text-red-400' },
    orange: { gradient: 'from-orange-400 to-orange-600', text: 'text-orange-400' },
  };

  const { size: svgSize, strokeWidth, textSize } = sizeMap[size];
  const { gradient, text } = colorMap[color];
  
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
            stroke="rgba(255, 255, 255, 0.1)"
            strokeWidth={strokeWidth}
          />
          {/* Progress circle with gradient */}
          <defs>
            <linearGradient id={`gradient-${label}`} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={color === 'green' ? '#4ade80' : color === 'blue' ? '#60a5fa' : color === 'red' ? '#f87171' : '#fb923c'} />
              <stop offset="100%" stopColor={color === 'green' ? '#16a34a' : color === 'blue' ? '#2563eb' : color === 'red' ? '#dc2626' : '#ea580c'} />
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
          <span className={`text-${textSize} font-bold ${text}`}>
            {value.toFixed(1)}
          </span>
          <span className="text-xs text-gray-400">{unit}</span>
        </div>
      </div>

      {/* Label */}
      <p className="mt-4 text-sm font-semibold text-gray-300 text-center">{label}</p>
    </div>
  );
}
