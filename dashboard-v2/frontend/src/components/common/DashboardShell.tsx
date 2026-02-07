'use client';

import React from 'react';
import Navbar from '@/components/Navbar';

interface DashboardShellProps {
  children: React.ReactNode;
  footer?: React.ReactNode;
}

export default function DashboardShell({ children, footer }: DashboardShellProps) {
  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="max-w-screen-2xl mx-auto p-4 md:p-6">
        {children}
      </main>
      {footer && (
        <footer className="max-w-screen-2xl mx-auto px-4 md:px-6 pb-6">
          {footer}
        </footer>
      )}
    </div>
  );
}
