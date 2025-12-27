'use client';

import { useState } from 'react';
import { RefreshCw } from 'lucide-react'; // Assure-toi d'avoir lucide-react ou une autre icône

export default function RefreshButton() {
  const [isLoading, setIsLoading] = useState(false);

  const handleRefresh = async () => {
    if (isLoading) return;
    setIsLoading(true);

    try {
      const res = await fetch('/api/refresh', { method: 'POST' });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.details || 'Erreur inconnue');
      }

      alert("Scraper lancé ! Les données se mettront à jour d'ici quelques secondes.");
      // Optionnel : Recharger la page après un délai pour voir les nouvelles stats
      // setTimeout(() => window.location.reload(), 5000); 

    } catch (error) {
      alert("Erreur lors du lancement : " + String(error));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <button
      onClick={handleRefresh}
      disabled={isLoading}
      className={`flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-all ${
        isLoading ? 'opacity-50 cursor-not-allowed' : ''
      }`}
    >
      <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
      {isLoading ? 'Lancement...' : 'Actualiser les données'}
    </button>
  );
}