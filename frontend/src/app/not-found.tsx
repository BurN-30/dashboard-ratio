import Link from "next/link";
import React from "react";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-6 bg-gray-50 dark:bg-gray-900">
      <div className="text-center max-w-md">
        <h1 className="text-6xl font-bold text-brand-500 mb-4">404</h1>
        <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-3">
          Page introuvable
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mb-8">
          La page que vous cherchez n&apos;existe pas ou a &eacute;t&eacute; d&eacute;plac&eacute;e.
        </p>
        <Link
          href="/"
          className="inline-flex items-center justify-center rounded-lg bg-brand-500 px-5 py-3 text-sm font-medium text-white hover:bg-opacity-90 transition-colors"
        >
          Retour au dashboard
        </Link>
      </div>
      <p className="absolute bottom-6 text-xs text-gray-500 dark:text-gray-400">
        &copy; {new Date().getFullYear()} TrackBoard
      </p>
    </div>
  );
}
