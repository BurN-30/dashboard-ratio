import React from 'react';

interface SkeletonCardProps {
  variant?: 'stat' | 'chart' | 'list';
}

export default function SkeletonCard({ variant = 'stat' }: SkeletonCardProps) {
  const base = 'rounded-xl border border-gray-200 bg-white shadow-theme-sm dark:border-gray-800 dark:bg-white/[0.03] animate-pulse';

  if (variant === 'chart') {
    return (
      <div className={`${base} p-6`}>
        <div className="h-4 w-1/3 rounded bg-gray-200 dark:bg-gray-700 mb-4" />
        <div className="h-64 rounded bg-gray-100 dark:bg-gray-800" />
      </div>
    );
  }

  if (variant === 'list') {
    return (
      <div className={`${base} p-6`}>
        <div className="h-4 w-1/4 rounded bg-gray-200 dark:bg-gray-700 mb-4" />
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex justify-between">
              <div className="h-3 w-1/3 rounded bg-gray-100 dark:bg-gray-800" />
              <div className="h-3 w-1/5 rounded bg-gray-100 dark:bg-gray-800" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // stat variant
  return (
    <div className={`${base} p-6`}>
      <div className="flex items-center justify-between mb-6">
        <div className="h-5 w-1/3 rounded bg-gray-200 dark:bg-gray-700" />
        <div className="h-6 w-20 rounded-full bg-gray-100 dark:bg-gray-800" />
      </div>
      <div className="grid grid-cols-2 gap-4 mb-6">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="space-y-2">
            <div className="h-3 w-2/3 rounded bg-gray-100 dark:bg-gray-800" />
            <div className="h-5 w-1/2 rounded bg-gray-200 dark:bg-gray-700" />
          </div>
        ))}
      </div>
      <div className="border-t border-gray-200 dark:border-gray-700 pt-4 space-y-3">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="flex justify-between">
            <div className="h-3 w-1/3 rounded bg-gray-100 dark:bg-gray-800" />
            <div className="h-3 w-1/5 rounded bg-gray-100 dark:bg-gray-800" />
          </div>
        ))}
      </div>
    </div>
  );
}
