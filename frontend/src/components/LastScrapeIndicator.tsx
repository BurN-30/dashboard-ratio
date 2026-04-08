'use client';

import { useEffect, useState } from 'react';
import { Clock } from 'lucide-react';

interface LastScrapeIndicatorProps {
  timestamp: number | null; // Unix seconds
}

function formatRelative(ts: number): string {
  const diff = Math.floor(Date.now() / 1000) - ts;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function formatExact(ts: number): string {
  return new Date(ts * 1000).toLocaleString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function LastScrapeIndicator({ timestamp }: LastScrapeIndicatorProps) {
  const [relative, setRelative] = useState('');

  useEffect(() => {
    if (!timestamp) return;
    setRelative(formatRelative(timestamp));
    const interval = setInterval(() => setRelative(formatRelative(timestamp)), 30_000);
    return () => clearInterval(interval);
  }, [timestamp]);

  if (!timestamp || !relative) return null;

  return (
    <div
      className="flex items-center gap-1.5 text-xs text-gray-400 dark:text-gray-500 cursor-default"
      title={`Last scrape: ${formatExact(timestamp)}`}
    >
      <Clock className="w-3 h-3" />
      <span>{relative}</span>
    </div>
  );
}
