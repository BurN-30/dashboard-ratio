import React from 'react';

interface StatRowProps {
  label: string;
  value: string;
  highlight?: boolean;
  icon?: React.ElementType;
}

export default function StatRow({ label, value, highlight = false, icon: Icon }: StatRowProps) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-sm text-gray-600 dark:text-gray-400">{label}</span>
      <div className="flex items-center gap-2">
        {Icon && <Icon className={`w-4 h-4 ${highlight ? "text-brand-500" : "text-gray-400"}`} />}
        <span className={`text-sm font-medium ${highlight ? "text-brand-500 font-bold" : "text-gray-900 dark:text-white"}`}>
          {value}
        </span>
      </div>
    </div>
  );
}
