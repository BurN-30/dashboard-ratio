"use client";

import React, { useState, useEffect } from 'react';
import { RefreshCw } from 'lucide-react';
import { runAllScrapers, getScraperStatus } from '@/lib/api';

interface RefreshButtonProps {
  onRefreshStarted?: () => void;
  onRefreshComplete?: () => void;
}

export default function RefreshButton({ onRefreshStarted, onRefreshComplete }: RefreshButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  // Vérifier le status au montage
  useEffect(() => {
    const checkStatus = async () => {
      const result = await getScraperStatus();
      if (result?.scraping_in_progress) {
        setIsLoading(true);
        setStatus('Scraping en cours...');
        startPolling();
      }
    };
    checkStatus();
  }, []);

  // Polling pour détecter la fin du scraping
  const startPolling = () => {
    const poll = async () => {
      const result = await getScraperStatus();
      if (result && !result.scraping_in_progress) {
        setIsLoading(false);
        setStatus('Terminé !');
        onRefreshComplete?.();
        // Émettre un événement pour que la page principale recharge les données
        window.dispatchEvent(new CustomEvent('refresh-complete'));
        setTimeout(() => setStatus(null), 3000);
        return;
      }
      // Continuer le polling
      setTimeout(poll, 2000);
    };
    setTimeout(poll, 2000);
  };

  const handleClick = async () => {
    if (isLoading) return;

    setIsLoading(true);
    setStatus('Lancement...');
    onRefreshStarted?.();

    try {
      const result = await runAllScrapers();

      if (result?.status === 'busy') {
        setStatus('Scraping déjà en cours');
      } else if (result?.status === 'started') {
        setStatus('Scraping lancé');
        startPolling();
      } else {
        setStatus('Erreur');
        setIsLoading(false);
        setTimeout(() => setStatus(null), 3000);
      }
    } catch (error) {
      console.error('Error triggering refresh:', error);
      setStatus('Erreur de connexion');
      setIsLoading(false);
      setTimeout(() => setStatus(null), 3000);
    }
  };

  return (
    <div className="flex items-center gap-2">
      {status && (
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {status}
        </span>
      )}
      <button
        onClick={handleClick}
        disabled={isLoading}
        className={`
          flex items-center justify-center w-8 h-8
          text-gray-600 dark:text-gray-400
          bg-gray-100 dark:bg-gray-800
          rounded-md transition-all
          ${isLoading
            ? 'cursor-not-allowed opacity-50'
            : 'hover:bg-gray-200 dark:hover:bg-gray-700'}
        `}
        title={isLoading ? 'Scraping en cours...' : 'Rafraîchir les données'}
      >
        <RefreshCw
          className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`}
        />
      </button>
    </div>
  );
}
