import { useState, useEffect, useCallback } from 'react';

export interface GpuData {
  name: string;
  load: number;
  temperature: number;
  memoryUsed: number;
  memoryTotal: number;
  fanSpeed: number;
  power: number;
}

export interface DriveData {
  name: string;
  usedSpace: number;
  totalSpace: number;
  usedPercent: number;
  temperature: number | null;
}

export interface NetworkData {
  uploadSpeed: number;
  downloadSpeed: number;
}

export interface HardwareStats {
  cpuName: string;
  cpuLoad: number;
  cpuTemp: number;
  cpuPower: number;
  cpuClockSpeed: number;
  gpus: GpuData[];
  ramUsed: number;
  ramTotal: number;
  ramUsedPercent: number;
  drives: DriveData[];
  network: NetworkData;
  timestamp: string;
}

interface UseHardwareStatsOptions {
  interval?: number; // milliseconds, default 2000
  apiUrl?: string;
}

export function useHardwareStats(options: UseHardwareStatsOptions = {}) {
  const {
    interval = 2000,
    // Utilise la variable d'environnement ou le proxy local par défaut
    apiUrl = process.env.NEXT_PUBLIC_NGROK_URL 
      ? `${process.env.NEXT_PUBLIC_NGROK_URL}/hardware-proxy` 
      : '/api/hardware/stats',
  } = options;

  const [stats, setStats] = useState<HardwareStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);

  const fetchStats = useCallback(async () => {
    try {
      const headers: HeadersInit = {
        'ngrok-skip-browser-warning': 'true',
      };
      const token = process.env.NEXT_PUBLIC_HWMONITOR_TOKEN;
      if (token) {
        headers['X-Api-Key'] = token;
      }

      const response = await fetch(apiUrl, { headers });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      setStats(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch hardware stats');
      console.error('Hardware stats fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [apiUrl]);

  // Initial fetch
  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  // Auto-polling
  useEffect(() => {
    if (!isPolling) return;

    const intervalId = setInterval(fetchStats, interval);
    return () => clearInterval(intervalId);
  }, [isPolling, interval, fetchStats]);

  const togglePolling = useCallback(() => {
    setIsPolling(prev => !prev);
  }, []);

  const manualRefresh = useCallback(async () => {
    await fetchStats();
  }, [fetchStats]);

  return {
    stats,
    loading,
    error,
    isPolling,
    togglePolling,
    manualRefresh,
  };
}
