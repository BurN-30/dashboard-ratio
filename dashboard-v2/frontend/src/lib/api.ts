/**
 * API Client pour Dashboard V2
 * Se connecte directement au backend FastAPI
 */
import { AllStats } from "@/types/tracker";

// Demo mode: mock data, no backend needed (for Vercel preview)
export const IS_DEMO = process.env.NEXT_PUBLIC_DEMO === 'true';

// URL de l'API (configurable via env)
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Stockage du token JWT (côté client)
let authToken: string | null = null;

/**
 * Configure le token d'authentification
 */
export function setAuthToken(token: string | null) {
  authToken = token;
  if (typeof window !== 'undefined') {
    if (token) {
      localStorage.setItem('auth_token', token);
    } else {
      localStorage.removeItem('auth_token');
    }
  }
}

/**
 * Récupère le token stocké
 */
export function getAuthToken(): string | null {
  if (authToken) return authToken;
  if (typeof window !== 'undefined') {
    authToken = localStorage.getItem('auth_token');
  }
  return authToken;
}

/**
 * Vérifie si l'utilisateur est authentifié
 */
export function isAuthenticated(): boolean {
  return !!getAuthToken();
}

/**
 * Headers communs pour les requêtes authentifiées
 */
function getAuthHeaders(): HeadersInit {
  const token = getAuthToken();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

/**
 * Wrapper fetch avec gestion d'erreurs et auth
 */
async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      ...getAuthHeaders(),
      ...options.headers,
    },
  });

  if (response.status === 401) {
    // Token expiré ou invalide
    setAuthToken(null);
    throw new Error('Session expirée, veuillez vous reconnecter');
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Erreur ${response.status}`);
  }

  return response.json();
}

// ==================== AUTH ====================

export interface LoginResponse {
  success: boolean;
  token: {
    access_token: string;
    token_type: string;
    expires_in: number;
  };
}

/**
 * Authentification
 */
export async function login(password: string, rememberMe: boolean = false): Promise<boolean> {
  if (IS_DEMO) {
    setAuthToken('demo-token');
    return true;
  }
  try {
    const data = await apiFetch<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ password, remember_me: rememberMe }),
    });

    if (data.success && data.token) {
      setAuthToken(data.token.access_token);
      return true;
    }
    return false;
  } catch (error) {
    console.error('Login error:', error);
    return false;
  }
}

/**
 * Déconnexion
 */
export async function logout(): Promise<void> {
  try {
    await apiFetch('/auth/logout', { method: 'POST' });
  } catch (error) {
    // Ignorer les erreurs de logout
  } finally {
    setAuthToken(null);
  }
}

/**
 * Vérifie la validité du token
 */
export async function checkAuth(): Promise<boolean> {
  if (IS_DEMO) return true;
  try {
    await apiFetch('/auth/me');
    return true;
  } catch {
    return false;
  }
}

// ==================== STATS ====================

/**
 * Récupère les stats actuelles de tous les trackers
 */
export async function fetchTorrentStats(): Promise<AllStats | null> {
  if (IS_DEMO) {
    const { DEMO_STATS } = await import('./demo-data');
    return DEMO_STATS;
  }
  try {
    return await apiFetch<AllStats>('/api/stats');
  } catch (error) {
    console.error('Error fetching stats:', error);
    return null;
  }
}

/**
 * Récupère l'historique des stats
 */
export async function fetchTorrentHistory(days: number = 30): Promise<AllStats[] | null> {
  if (IS_DEMO) {
    const { DEMO_HISTORY } = await import('./demo-data');
    return DEMO_HISTORY;
  }
  try {
    return await apiFetch<AllStats[]>(`/api/history?days=${days}`);
  } catch (error) {
    console.error('Error fetching history:', error);
    return null;
  }
}

/**
 * Récupère le résumé du dashboard
 */
export async function fetchDashboardSummary(): Promise<{
  trackers_count: number;
  total_records: number;
  last_update: string | null;
} | null> {
  try {
    return await apiFetch('/api/summary');
  } catch (error) {
    console.error('Error fetching summary:', error);
    return null;
  }
}

// ==================== SCRAPERS ====================

export interface ScraperStatus {
  scraping_in_progress: boolean;
  configured_scrapers: string[];
}

export interface ScrapeResult {
  status: string;
  message: string;
  tracker?: string;
}

/**
 * Récupère le status des scrapers
 */
export async function getScraperStatus(): Promise<ScraperStatus | null> {
  if (IS_DEMO) return { scraping_in_progress: false, configured_scrapers: ['Tracker Alpha', 'Tracker Bravo', 'Tracker Charlie', 'Tracker Delta'] };
  try {
    return await apiFetch<ScraperStatus>('/scrapers/status');
  } catch (error) {
    console.error('Error fetching scraper status:', error);
    return null;
  }
}

/**
 * Lance le scraping de tous les trackers
 */
export async function runAllScrapers(): Promise<ScrapeResult | null> {
  if (IS_DEMO) return { status: 'demo', message: 'Demo mode - scraping disabled' };
  try {
    return await apiFetch<ScrapeResult>('/scrapers/run', { method: 'POST' });
  } catch (error) {
    console.error('Error running scrapers:', error);
    return null;
  }
}

/**
 * Lance le scraping d'un tracker spécifique
 */
export async function runScraper(trackerName: string): Promise<ScrapeResult | null> {
  try {
    return await apiFetch<ScrapeResult>(`/scrapers/run/${trackerName}`, { method: 'POST' });
  } catch (error) {
    console.error(`Error running scraper ${trackerName}:`, error);
    return null;
  }
}

// ==================== HARDWARE ====================

export interface HardwareStats {
  cpu: {
    usage: number;
    temp: number | null;
    frequency: number | null;
    cores: number;
    physical_cores: number;
    name: string;
  };
  ram: {
    used_percent: number;
    used_gb: number;
    total_gb: number;
    available_gb: number;
  };
  gpu: {
    name: string;
    usage: number;
    temp: number;
    memory_used: number;
    memory_total: number;
    memory_percent: number;
  } | null;
  storage: Array<{
    device: string;
    mountpoint: string;
    fstype: string;
    total_gb: number;
    used_gb: number;
    free_gb: number;
    percent: number;
  }>;
  timestamp: string;
  agent_connected: boolean;
}

/**
 * Récupère les stats hardware (REST, snapshot unique)
 */
export async function fetchHardwareStats(): Promise<HardwareStats | null> {
  try {
    return await apiFetch<HardwareStats>('/hardware/stats');
  } catch (error) {
    console.error('Error fetching hardware stats:', error);
    return null;
  }
}

/**
 * Récupère le status de l'agent hardware
 */
export async function getHardwareStatus(): Promise<{
  agent_connected: boolean;
  clients_count: number;
} | null> {
  try {
    // Cet endpoint est public (pas besoin d'auth)
    const response = await fetch(`${API_BASE_URL}/hardware/status`);
    if (!response.ok) return null;
    return response.json();
  } catch (error) {
    console.error('Error fetching hardware status:', error);
    return null;
  }
}

/**
 * Crée une connexion WebSocket pour les stats hardware temps réel
 */
export function createHardwareWebSocket(
  onMessage: (data: HardwareStats) => void,
  onError?: (error: Event) => void,
  onClose?: () => void
): WebSocket | null {
  const wsUrl = API_BASE_URL.replace('http', 'ws') + '/hardware/ws/client';

  try {
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (e) {
        console.error('Error parsing WebSocket message:', e);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      onError?.(error);
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
      onClose?.();
    };

    return ws;
  } catch (error) {
    console.error('Error creating WebSocket:', error);
    return null;
  }
}
