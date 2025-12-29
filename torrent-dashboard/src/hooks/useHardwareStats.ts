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
  apiUrl?: string;
  historyLength?: number; // Nouveau : combien de points on garde en mémoire
}

export function useHardwareStats(options: UseHardwareStatsOptions = {}) {
  const {
    interval = 2000,
    apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://submedial-bloodlike-sarah.ngrok-free.dev/hardware-proxy',
    historyLength = 30, // On garde les 30 dernières mesures par défaut
  } = options;

  const [stats, setStats] = useState<HardwareStats | null>(null);
  const [history, setHistory] = useState<HardwareStats[]>([]); // Pour les graphiques
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(true); // Par défaut on veut que ça tourne

  // Ref pour annuler la requête si le composant est démonté
  const abortControllerRef = useRef<AbortController | null>(null);

  const fetchStats = useCallback(async () => {
    // Annuler la requête précédente si elle est encore en cours
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    // Nouveau contrôleur pour cette requête
    abortControllerRef.current = new AbortController();

    try {
      const headers: HeadersInit = {
        'ngrok-skip-browser-warning': 'true',
        'Content-Type': 'application/json',
      };
      
      const token = process.env.NEXT_PUBLIC_HWMONITOR_TOKEN;
      if (token) {
        headers['X-Api-Key'] = token;
      }

      const response = await fetch(apiUrl, { 
        headers,
        signal: abortControllerRef.current.signal // Lier le signal d'annulation
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status} - ${response.statusText}`);
      }

      const data: HardwareStats = await response.json();
      
      // Mise à jour des stats actuelles
      setStats(data);
      setError(null);

      // Mise à jour de l'historique (FIFO: First In First Out)
      setHistory(prev => {
        const newHistory = [...prev, data];
        if (newHistory.length > historyLength) {
          return newHistory.slice(newHistory.length - historyLength);
        }
        return newHistory;
      });

    } catch (err: any) {
      if (err.name === 'AbortError') {
        // Ignorer l'erreur si c'est juste une annulation volontaire
        return;
      }
      console.error('Hardware stats fetch error:', err);
      // On ne met pas forcément error en state bloquant pour éviter de flasher l'écran 
      // si une seule requête échoue (micro-coupure), sauf si on a pas de stats du tout.
      if (!stats) setError(err instanceof Error ? err.message : 'Connection failed');
    } finally {
      setLoading(false);
    }
  }, [apiUrl, historyLength, stats]); // stats ajouté aux dépendances pour la logique d'erreur conditionnelle

  // Initial fetch
  useEffect(() => {
    fetchStats();
    return () => {
      // Cleanup au démontage
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); 

  // Auto-polling
  useEffect(() => {
    if (!isPolling) return;

    const intervalId = setInterval(fetchStats, interval);
    return () => clearInterval(intervalId);
  }, [isPolling, interval, fetchStats]);

  const togglePolling = useCallback(() => setIsPolling(prev => !prev), []);
  
  // Fonction pour vider l'historique si besoin
  const clearHistory = useCallback(() => setHistory([]), []);

  return {
    stats,
    history, // <-- La data clé pour tes sparklines
    loading,
    error,
    isPolling,
    togglePolling,
    manualRefresh: fetchStats,
    clearHistory
  };
}