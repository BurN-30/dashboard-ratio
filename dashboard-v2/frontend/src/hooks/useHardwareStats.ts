import { useState, useEffect, useCallback, useRef } from 'react';
import { IS_DEMO } from '@/lib/api';

// === INTERFACES ===
export interface ProcessData {
  name: string;
  id: number;
  memoryUsedMb: number;
}

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
  mount: string;
  usedSpace: number;
  totalSpace: number;
  usedPercent: number;
  temperature: number | null;
}

export interface NetworkData {
  uploadSpeed: number;
  downloadSpeed: number;
}

export interface DiskTempData {
  name: string;
  temp: number;
}

export interface HardwareStats {
  osName: string;
  uptime: string;
  cpuName: string;
  cpuLoad: number;
  cpuTemp: number;
  cpuPower: number;
  cpuClockSpeed: number;
  cpuFanSpeed: number;
  cpuCoreLoads: number[];
  gpus: GpuData[];
  topProcesses: ProcessData[];
  ramUsed: number;
  ramTotal: number;
  ramUsedPercent: number;
  drives: DriveData[];
  diskTemps: DiskTempData[];
  network: NetworkData;
  timestamp: string;
}

interface UseHardwareStatsOptions {
  interval?: number;
  historyLength?: number;
}

// Transformer les données de l'agent V2 vers le format frontend
function transformAgentData(data: any): HardwareStats {
  const cpu = data.cpu || {};
  const ram = data.ram || {};
  const gpu = data.gpu;
  const storage = data.storage || [];
  const network = data.network || {};
  const processes = data.processes || [];

  return {
    osName: data.os || 'Unknown OS',
    uptime: data.uptime || '00:00:00',
    cpuName: cpu.name || 'Unknown CPU',
    cpuLoad: cpu.usage || 0,
    cpuTemp: cpu.temp || 0,
    cpuPower: cpu.power || 0,
    cpuClockSpeed: cpu.frequency || 0,
    cpuFanSpeed: cpu.fan_speed || 0,
    cpuCoreLoads: cpu.core_usage || [],
    gpus: gpu ? [{
      name: gpu.name || 'Unknown GPU',
      load: gpu.usage || 0,
      temperature: gpu.temp || 0,
      memoryUsed: gpu.memory_used || 0,
      memoryTotal: gpu.memory_total || 0,
      fanSpeed: gpu.fan_speed || 0,
      power: gpu.power || 0,
    }] : [],
    topProcesses: processes.map((p: any) => ({
      name: p.name || 'Unknown',
      id: p.id || 0,
      memoryUsedMb: p.memory_mb || 0,
    })),
    ramUsed: ram.used_gb || 0,
    ramTotal: ram.total_gb || 0,
    ramUsedPercent: ram.used_percent || 0,
    drives: storage.map((drive: any) => ({
      name: drive.name || 'Local Disk',
      mount: drive.device || drive.mountpoint || '',
      usedSpace: drive.used_gb || 0,
      totalSpace: drive.total_gb || 0,
      usedPercent: drive.percent || 0,
      temperature: null,
    })),
    diskTemps: (data.disk_temps || []).map((dt: any) => ({
      name: dt.name || '',
      temp: dt.temp || 0,
    })),
    network: {
      uploadSpeed: network.upload_speed || 0,
      downloadSpeed: network.download_speed || 0,
    },
    timestamp: data.timestamp || new Date().toISOString(),
  };
}

function generateDemoHwStats(): HardwareStats {
  const rnd = (min: number, max: number) => min + Math.random() * (max - min);
  return {
    osName: 'Windows 11 Pro 24H2',
    uptime: '3j 14h 22min',
    cpuName: 'AMD Ryzen 7 5800X 8-Core',
    cpuLoad: rnd(25, 75),
    cpuTemp: rnd(42, 68),
    cpuPower: rnd(35, 95),
    cpuClockSpeed: rnd(3600, 4700),
    cpuFanSpeed: rnd(800, 1400),
    cpuCoreLoads: Array.from({ length: 16 }, () => rnd(5, 95)),
    gpus: [{
      name: 'NVIDIA GeForce RTX 3070',
      load: rnd(10, 60),
      temperature: rnd(38, 72),
      memoryUsed: rnd(1200, 4800),
      memoryTotal: 8192,
      fanSpeed: rnd(30, 65),
      power: rnd(40, 180),
    }],
    topProcesses: [
      { name: 'chrome.exe', id: 1234, memoryUsedMb: rnd(800, 1600) },
      { name: 'firefox.exe', id: 2345, memoryUsedMb: rnd(400, 900) },
      { name: 'code.exe', id: 3456, memoryUsedMb: rnd(300, 700) },
      { name: 'discord.exe', id: 4567, memoryUsedMb: rnd(200, 500) },
      { name: 'steam.exe', id: 5678, memoryUsedMb: rnd(100, 350) },
    ],
    ramUsed: 21.3,
    ramTotal: 32.0,
    ramUsedPercent: 66.6,
    drives: [
      { name: 'Samsung 980 PRO', mount: 'C:', usedSpace: 287, totalSpace: 476, usedPercent: 60.3, temperature: null },
      { name: 'WD Black SN850X', mount: 'D:', usedSpace: 1245, totalSpace: 1907, usedPercent: 65.3, temperature: null },
    ],
    diskTemps: [
      { name: 'Samsung 980 PRO', temp: 41 },
      { name: 'WD Black SN850X', temp: 38 },
    ],
    network: { uploadSpeed: rnd(5, 55), downloadSpeed: rnd(2, 120) },
    timestamp: new Date().toISOString(),
  };
}

export function useHardwareStats(options: UseHardwareStatsOptions = {}) {
  const {
    interval = 2000,
    historyLength = 30,
  } = options;

  const [stats, setStats] = useState<HardwareStats | null>(null);
  const [history, setHistory] = useState<{ time: string; cpu: number; ram: number }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [isPolling, setIsPolling] = useState(true);

  const latestStatsRef = useRef<HardwareStats | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Demo mode: generate fake data on interval
  useEffect(() => {
    if (!IS_DEMO) return;
    setLoading(false);
    const tick = () => {
      const data = generateDemoHwStats();
      setStats(data);
      setHistory(prev => {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        return [...prev, { time: timeStr, cpu: data.cpuLoad, ram: data.ramUsedPercent }].slice(-historyLength);
      });
    };
    tick();
    const id = setInterval(tick, interval);
    return () => clearInterval(id);
  }, [IS_DEMO, interval, historyLength]);

  useEffect(() => {
    if (IS_DEMO) return;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const apiHost = process.env.NEXT_PUBLIC_API_URL?.replace(/^https?:\/\//, '') || window.location.host;
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') || '' : '';
    const wsUrl = `${protocol}//${apiHost}/hardware/ws/client?token=${encodeURIComponent(token)}`;

    console.log('[HW Stats] Connecting to WebSocket:', wsUrl.replace(/token=[^&]+/, 'token=***'));

    const connect = () => {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[HW Stats] WebSocket connected');
        setError(null);
        setLoading(false);
      };

      ws.onmessage = (event) => {
        try {
          const rawData = JSON.parse(event.data);
          const data = transformAgentData(rawData);

          latestStatsRef.current = data;
          setStats(data);
          setError(null);

          setHistory(prev => {
            const now = new Date();
            const timeStr = now.toLocaleTimeString('fr-FR', {
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit'
            });
            const newPoint = {
              time: timeStr,
              cpu: data.cpuLoad,
              ram: data.ramUsedPercent
            };
            const newHistory = [...prev, newPoint];
            return newHistory.slice(-historyLength);
          });
        } catch (err) {
          console.error('[HW Stats] Error parsing message:', err);
        }
      };

      ws.onerror = (err) => {
        console.error('[HW Stats] WebSocket error:', err);
      };

      ws.onclose = () => {
        console.log('[HW Stats] WebSocket closed, reconnecting in 5s...');
        setTimeout(() => {
          if (isPolling) {
            connect();
          }
        }, 5000);
      };
    };

    if (isPolling && !IS_DEMO) {
      connect();
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [isPolling, historyLength]);

  const fetchStats = useCallback(async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || `${window.location.protocol}//${window.location.host}`;
      const response = await fetch(`${apiUrl}/hardware/stats`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token') || ''}`,
        },
      });

      if (!response.ok) {
        throw new Error(response.status === 401 ? 'Non authentifié' : 'Erreur serveur');
      }

      const rawData = await response.json();
      const data = transformAgentData(rawData);

      if (JSON.stringify(data) !== JSON.stringify(latestStatsRef.current)) {
        latestStatsRef.current = data;
        setStats(data);
        setError(null);
      }
    } catch (err: any) {
      console.error('[HW Stats] Fetch error:', err);
      setError(err.message || 'Erreur de connexion');
    } finally {
      setLoading(false);
    }
  }, []);

  const togglePolling = () => setIsPolling((prev) => !prev);
  const manualRefresh = () => fetchStats();

  return { stats, history, error, loading, isPolling, togglePolling, manualRefresh };
}
