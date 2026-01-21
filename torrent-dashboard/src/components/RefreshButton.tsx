'use client';

import { useState, useRef } from 'react';
import { RefreshCw } from 'lucide-react';
import { useToast } from '@/context/ToastContext';

export default function RefreshButton() {
  const [isLoading, setIsLoading] = useState(false);
  const { showToast } = useToast();

  // Stocker le dernier timestamp connu pour comparaison
  const lastTimestampRef = useRef<number | null>(null);

  // Vérifier si on est en production (déployé sur Vercel)
  const isProduction = process.env.NODE_ENV === 'production' && typeof window !== 'undefined' && !window.location.hostname.includes('localhost');

  const getCurrentTimestamp = async () => {
    try {
      const res = await fetch('/api/stats', { cache: 'no-store' });
      if (!res.ok) return null;
      const data = await res.json();
      return data._timestamp || null;
    } catch {
      return null;
    }
  };

  const handleRefresh = async () => {
    if (isLoading) return;
    setIsLoading(true);

    // Récupérer le timestamp actuel avant refresh
    if (lastTimestampRef.current === null) {
      lastTimestampRef.current = await getCurrentTimestamp();
    }

    // Notification immédiate : scraper en cours
    showToast('Scraper en cours...', 'success', 5000);
    window.dispatchEvent(new Event('refresh-clicked'));

    try {
      const res = await fetch('/api/refresh', { method: 'POST' });
      const data = await res.json();

      if (!res.ok) {
        showToast(
          data.details || data.error || 'Erreur lors du lancement',
          'error',
          5000
        );
        setIsLoading(false);
        return;
      }

      // Attendre que le timestamp change (max 15s)
      let tries = 0;
      const maxTries = 30; // 30 x 500ms = 15s
      let newTimestamp = null;
      while (tries < maxTries) {
        newTimestamp = await getCurrentTimestamp();
        if (
          newTimestamp &&
          lastTimestampRef.current &&
          newTimestamp !== lastTimestampRef.current
        ) {
          break;
        }
        await new Promise((r) => setTimeout(r, 500));
        tries++;
      }
      lastTimestampRef.current = newTimestamp;

      showToast('Mise à jour terminée !', 'success', 4000);
    } catch (error) {
      showToast(
        'Serveur inaccessible — vérifiez votre PC',
        'error',
        5000
      );
    } finally {
      setIsLoading(false);
    }
  };

  // Si en production et que la config n'est pas définie, ne pas afficher le bouton
  if (isProduction && (!process.env.NEXT_PUBLIC_SCRAPER_ENABLED)) {
    return null;
  }

  return (
    <button
      onClick={handleRefresh}
      disabled={isLoading}
      className="flex items-center justify-center w-8 h-8 text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
      title="Actualiser les données (déclenche le scraper)"
    >
      <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
    </button>
  );
}