'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, Cpu, Database, Activity } from 'lucide-react';

export default function Navbar() {
  const pathname = usePathname();

  const navItems = [
    { name: 'Torrents', href: '/', icon: Database },
    { name: 'Hardware', href: '/hardware-monitor', icon: Cpu },
  ];

  return (
    <nav className="sticky top-0 z-50 w-full border-b border-gray-800 bg-gray-950/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 h-16 flex justify-between items-center">
        
        {/* Logo / Branding */}
        <div className="flex items-center gap-3 group cursor-default">
          <div className="p-2 bg-blue-600/20 rounded-lg group-hover:bg-blue-600/30 transition-colors">
            <LayoutDashboard className="w-6 h-6 text-blue-500" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white tracking-wide">Nexus<span className="text-blue-500">Dash</span></h1>
            <div className="flex items-center gap-1.5">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
              </span>
              <span className="text-[10px] text-gray-500 uppercase tracking-wider font-medium">System Online</span>
            </div>
          </div>
        </div>

        {/* Navigation Links */}
        <ul className="flex items-center gap-1 bg-gray-900/50 p-1 rounded-full border border-gray-800/50">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;

            return (
              <li key={item.href}>
                <Link 
                  href={item.href}
                  className={`
                    flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all duration-200
                    ${isActive 
                      ? 'bg-gray-800 text-white shadow-lg border border-gray-700' 
                      : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
                    }
                  `}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-blue-400' : 'text-gray-500 group-hover:text-gray-300'}`} />
                  {item.name}
                </Link>
              </li>
            );
          })}
        </ul>

        {/* Action Rapide (Optionnel, ex: Settings ou Logout) */}
        <div className="hidden md:flex items-center gap-4">
          <button className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors">
             <Activity className="w-5 h-5" />
          </button>
        </div>

      </div>
    </nav>
  );
}
