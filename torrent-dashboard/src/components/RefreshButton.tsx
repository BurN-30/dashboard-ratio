'use client';

import { useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { useToast } from '@/context/ToastContext';

export default function RefreshButton() {
  const [isLoading, setIsLoading] = useState(false);
  const { showToast } = useToast();

  const handleRefresh = async () => {
    if (isLoading) return;
    setIsLoading(true);

    // Notification immédiate : scraper en cours
    showToast('Scraper en cours...', 'success', 5000);
    
    // Trigger polling sur la page
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
      }
      // Si succès, on affiche "lancé" — les données seront à jour dans la page parent
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

  return (
    <button
      onClick={handleRefresh}
      disabled={isLoading}
      className="flex items-center justify-center w-8 h-8 text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
      title="Actualiser les données"
    >
      <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
    </button>
  );
}