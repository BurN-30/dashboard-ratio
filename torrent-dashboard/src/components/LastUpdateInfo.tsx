'use client';

import { useEffect, useState } from 'react';
import { Clock } from 'lucide-react';

export default function LastUpdateInfo() {
  const [lastUpdate, setLastUpdate] = useState<string>('');
  const [error, setError] = useState(false);

  useEffect(() => {
    async function getLastUpdate() {
      try {
        const res = await fetch('/api/stats', { cache: 'no-store' });
        if (!res.ok) {
          console.error('Failed to fetch stats:', res.status);
          setError(true);
          return;
        }
        
        const data = await res.json();
        
        // Si les stats contiennent un timestamp, l'utiliser
        if (data._timestamp) {
          setError(false);
          // Convertir secondes Unix en millisecondes
          const timestamp = new Date(data._timestamp * 1000);
          setLastUpdate(timestamp.toLocaleString('fr-FR', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
          }));
        } else {
          console.warn('No _timestamp in stats data');
        }
      } catch (error) {
        console.error('Failed to fetch update time:', error);
        setError(true);
      }
    }

    getLastUpdate();
    // Refresh every 30 seconds
    const interval = setInterval(getLastUpdate, 30 * 1000);
    return () => clearInterval(interval);
  }, []);

  if (error) {
    return (
      <div className="flex items-center justify-center gap-2 text-xs text-red-500 dark:text-red-400 pt-4 border-t border-gray-200 dark:border-gray-700">
        <Clock className="w-3 h-3" />
        <span>Impossible de récupérer la date de mise à jour</span>
      </div>
    );
  }

  if (!lastUpdate) {
    return (
      <div className="flex items-center justify-center gap-2 text-xs text-gray-500 dark:text-gray-400 pt-4 border-t border-gray-200 dark:border-gray-700">
        <Clock className="w-3 h-3 animate-spin" />
        <span>Chargement...</span>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center gap-2 text-xs text-gray-500 dark:text-gray-400 pt-4 border-t border-gray-200 dark:border-gray-700">
      <Clock className="w-3 h-3" />
      <span>Dernière mise à jour : {lastUpdate}</span>
    </div>
  );
}
