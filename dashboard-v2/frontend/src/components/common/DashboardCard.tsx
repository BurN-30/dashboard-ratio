import React from 'react';

interface DashboardCardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  headerRight?: React.ReactNode;
  noPadding?: boolean;
  style?: React.CSSProperties;
}

export default function DashboardCard({ children, className = '', title, headerRight, noPadding, style }: DashboardCardProps) {
  return (
    <div className={`rounded-xl border border-gray-200 bg-white shadow-theme-sm dark:border-gray-800 dark:bg-white/[0.03] ${className}`} style={style}>
      {(title || headerRight) && (
        <div className="flex items-center justify-between px-6 pt-5 pb-0">
          {title && <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h3>}
          {headerRight && <div>{headerRight}</div>}
        </div>
      )}
      <div className={noPadding ? '' : 'p-6'}>{children}</div>
    </div>
  );
}
