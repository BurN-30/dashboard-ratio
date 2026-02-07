'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { LayoutDashboard, Cpu, Database, BarChart2, Sun, Moon, LogOut } from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';
import { useAuth } from '@/context/AuthContext';
import { logout } from '@/lib/api';

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const { theme, toggleTheme } = useTheme();
  const { logout: authLogout } = useAuth();

  const navItems = [
    { name: 'Torrents', href: '/', icon: Database },
    { name: 'Details', href: '/traffic', icon: BarChart2 },
    { name: 'Hardware', href: '/hardware-monitor', icon: Cpu },
  ];

  const handleLogout = async () => {
    await logout();
    authLogout();
    router.push('/login');
  };

  return (
    <nav className="sticky top-0 z-50 w-full border-b border-gray-200 bg-white/80 backdrop-blur-md dark:border-gray-800 dark:bg-gray-950/80">
      <div className="max-w-screen-2xl mx-auto px-4 h-16 flex justify-between items-center">

        {/* Logo / Branding */}
        <div className="flex items-center gap-3 group cursor-default">
          <div className="p-2 bg-brand-100 dark:bg-blue-600/20 rounded-lg group-hover:bg-brand-200 dark:group-hover:bg-blue-600/30 transition-colors">
            <LayoutDashboard className="w-6 h-6 text-brand-500 dark:text-blue-500" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900 dark:text-white tracking-wide">Nexus<span className="text-brand-500 dark:text-blue-500">Dash</span></h1>
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
        <ul className="flex items-center gap-1 bg-gray-100/80 dark:bg-gray-900/50 p-1 rounded-full border border-gray-200/50 dark:border-gray-800/50">
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
                      ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-theme-xs border border-gray-200 dark:border-gray-700'
                      : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-200/50 dark:hover:bg-gray-800/50'
                    }
                  `}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-brand-500 dark:text-blue-400' : 'text-gray-400 dark:text-gray-500'}`} />
                  {item.name}
                </Link>
              </li>
            );
          })}
        </ul>

        {/* Actions: theme toggle + logout */}
        <div className="flex items-center gap-2">
          <button
            onClick={toggleTheme}
            className="flex items-center justify-center w-9 h-9 text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            title="Toggle Theme"
          >
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
          <button
            onClick={handleLogout}
            className="flex items-center justify-center w-9 h-9 text-red-500 bg-red-50 dark:bg-red-900/20 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/40 transition-colors"
            title="Logout"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>

      </div>
    </nav>
  );
}
