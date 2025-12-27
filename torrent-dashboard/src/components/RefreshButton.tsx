'use client';

import { useState } from 'react';
import { RefreshCw } from 'lucide-react';

export default function RefreshButton() {
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleRefresh = async () => {
    if (isLoading) return;
    setIsLoading(true);
    setMessage('');

    try {
      const res = await fetch('/api/refresh', { method: 'POST' });
      const data = await res.json();

      if (!res.ok) {
        setMessage('❌ Erreur: ' + (data.details || data.error || 'Erreur inconnue'));
      } else {
        setMessage('✅ Scraper lancé');
        setTimeout(() => setMessage(''), 3000);
      }
    } catch (error) {
      setMessage('❌ Serveur inaccessible');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        onClick={handleRefresh}
        disabled={isLoading}
        className="flex items-center justify-center w-8 h-8 text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
        title="Actualiser les données"
      >
        <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
      </button>
      {message && (
        <span className="text-xs text-gray-600 dark:text-gray-400 whitespace-nowrap">
          {message}
        </span>
      )}
    </div>
  );
}