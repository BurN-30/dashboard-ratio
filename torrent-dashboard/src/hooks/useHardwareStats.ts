import { useState, useEffect, useCallback, useRef } from 'react';

// === NOUVELLES INTERFACES ===
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

export interface HardwareStats {
  // Infos Système
  osName: string;
  uptime: string;
  
  // CPU
  cpuName: string;
  cpuLoad: number;
  cpuTemp: number;
  cpuPower: number;
  cpuClockSpeed: number;
  cpuFanSpeed: number;
  cpuCoreLoads: number[]; // <--- Ajouté
  
  // Listes
  gpus: GpuData[];
  topProcesses: ProcessData[]; // <--- On a ajouté ça
  
  // RAM
  ramUsed: number;
  ramTotal: number;
  ramUsedPercent: number;
  
  // Autres
  drives: DriveData[];
  network: NetworkData;
  timestamp: string;
}

interface UseHardwareStatsOptions {
  interval?: number;
  url?: string;
  historyLength?: number;
}

export function useHardwareStats(options: UseHardwareStatsOptions = {}) {
  const {
    interval = 2000,
    url = '/hardware.json', // URL par défaut (à la racine du site)
    historyLength = 30,
  } = options;

  const [stats, setStats] = useState<HardwareStats | null>(null);
  const [history, setHistory] = useState<{ time: string; cpu: number; ram: number }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Utiliser useRef pour garder la dernière valeur sans déclencher de re-render
  const latestStatsRef = useRef<HardwareStats | null>(null);

  const fetchStats = useCallback(async () => {
    try {
      // Ajout d'un timestamp pour éviter le cache du navigateur
      const cacheBuster = `?t=${new Date().getTime()}`;
      const response = await fetch(`${url}${cacheBuster}`);
      
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      
      const data: HardwareStats = await response.json();
      
      // Mise à jour si les données ont changé (basique)
      if (JSON.stringify(data) !== JSON.stringify(latestStatsRef.current)) {
        latestStatsRef.current = data;
        setStats(data);
        setError(null);

        // Mise à jour de l'historique pour les graphiques
        setHistory(prev => {
          const now = new Date();
          const timeStr = now.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
          const newPoint = {
            time: timeStr,
            cpu: data.cpuLoad,
            ram: data.ramUsedPercent
          };
          const newHistory = [...prev, newPoint];
          return newHistory.slice(-historyLength);
        });
      }
    } catch (err) {
      console.error('Error fetching hardware stats:', err);
      // On ne set pas l'erreur immédiatement pour éviter le clignotement si un fetch rate
      // setError('Impossible de joindre le moniteur');
    } finally {
      setLoading(false);
    }
  }, [url, historyLength]);

  useEffect(() => {
    fetchStats();
    const timer = setInterval(fetchStats, interval);
    return () => clearInterval(timer);
  }, [fetchStats, interval]);

  return { stats, history, error, loading };
}