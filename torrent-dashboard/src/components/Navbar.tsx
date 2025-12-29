import React from 'react';
import Link from 'next/link';
import { Home, Cpu, Database } from 'lucide-react';

const Navbar = () => {
  return (
    <nav className="bg-gray-800 text-gray-200 shadow-lg">
      <div className="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
        <h1 className="text-xl font-bold text-white">Dashboard</h1>
        <ul className="flex gap-6">
          <li>
            <Link href="/">
              <a className="flex items-center gap-2 hover:text-yellow-400">
                <Home className="w-5 h-5" />
                Home
              </a>
            </Link>
          </li>
          <li>
            <Link href="/hardware-monitor">
              <a className="flex items-center gap-2 hover:text-yellow-400">
                <Cpu className="w-5 h-5" />
                Hardware Monitor
              </a>
            </Link>
          </li>
          <li>
            <Link href="/torrent-dashboard">
              <a className="flex items-center gap-2 hover:text-yellow-400">
                <Database className="w-5 h-5" />
                Torrent Dashboard
              </a>
            </Link>
          </li>
        </ul>
      </div>
    </nav>
  );
};

export default Navbar;