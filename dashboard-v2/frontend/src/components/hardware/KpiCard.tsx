import React from 'react';

interface KpiCardProps {
  icon: React.ElementType;
  title: string;
  value: string;
  subtext?: string;
  color: string;
  alert?: boolean;
  style?: React.CSSProperties;
}

export default function KpiCard({ icon: Icon, title, value, subtext, color, alert, style }: KpiCardProps) {
  return (
    <div
      className={`rounded-xl border bg-white dark:bg-white/[0.03] p-4 flex items-center space-x-4 transition-all animate-slide-up ${
        alert
          ? 'border-red-500/50 shadow-lg'
          : 'border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-600'
      }`}
      style={style}
    >
      <div className={`p-3 rounded-lg bg-gray-100 dark:bg-gray-700/30 ${color}`}>
        <Icon size={22} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-gray-500 dark:text-gray-400 text-xs uppercase font-bold tracking-wider truncate">{title}</p>
        <h3 className="text-xl font-bold text-gray-900 dark:text-white">{value}</h3>
        {subtext && <p className="text-xs text-gray-400 dark:text-gray-500 truncate">{subtext}</p>}
      </div>
    </div>
  );
}
