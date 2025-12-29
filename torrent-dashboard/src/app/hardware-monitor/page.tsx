'use client';

import React from 'react';
import Navbar from '@/components/Navbar'; // On garde la nav pour circuler
import { useHardwareStats } from '@/hooks/useHardwareStats';
import { 
  Cpu, 
  MemoryStick, 
  HardDrive, 
  Wifi, 
  Zap, 
  Server,
  Activity,
  ArrowUp,
  ArrowDown,
  Thermometer,
  Wind
} from 'lucide-react';

// === COMPOSANTS STYLE "TORRENT DASHBOARD" ===

// Carte standard (Fond blanc en light, Gris foncé en dark)
const DashboardCard = ({ title, icon: Icon, children, className = "" }: any) => (
  <div className={`rounded-sm border border-gray-200 bg-white p-6 shadow-theme-md dark:border-gray-700 dark:bg-gray-800 ${className}`}>
    <div className="flex items-center justify-between mb-4">
      <h4 className="text-xl font-bold text-black dark:text-white flex items-center gap-2">
        {Icon && <Icon className="w-5 h-5 text-brand-500" />}
        {title}
      </h4>
    </div>
    {children}
  </div>
);

// Ligne de stat simple
const StatRow = ({ label, value, subValue, icon: Icon, alert = false }: any) => (
  <div className="flex justify-between items-center py-2 border-b border-gray-100 dark:border-gray-700 last:border-0">
    <span className="text-sm text-gray-600 dark:text-gray-400 flex items-center gap-2">
      {Icon && <Icon className="w-4 h-4 text-gray-400" />}
      {label}
    </span>
    <div className="text-right">
      <div className={`text-sm font-bold ${alert ? "text-red-500 animate-pulse" : "text-black dark:text-white"}`}>
        {value}
      </div>
      {subValue && <div className="text-xs text-gray-500">{subValue}</div>}
    </div>
  </div>
);

// Barre de progression simple
const ProgressBar = ({ value, max = 100, color = "bg-blue-500", label }: any) => {
  const percent = Math.min((value / max) * 100, 100);
  return (
    <div className="mb-3">
      <div className="flex justify-between text-xs mb-1">
        <span className="text-gray-500 font-medium">{label}</span>
        <span className="text-black dark:text-white font-bold">{value.toFixed(0)}%</span>
      </div>
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
        <div 
          className={`h-2.5 rounded-full transition-all duration-500 ${color}`} 
          style={{ width: `${percent}%` }}
        ></div>
      </div>
    </div>
  );
};

export default function HardwareMonitor() {
  const { stats, loading, error } = useHardwareStats({ interval: 2000 });

  if (loading && !stats) return <div className="flex h-screen items-center justify-center bg-gray-100 dark:bg-gray-900"><div className="animate-spin h-10 w-10 border-4 border-blue-500 border-t-transparent rounded-full"></div></div>;
  if (error) return <div className="flex h-screen items-center justify-center text-red-500">Erreur: {error}</div>;

  // Sécurisation des données
  const safeStats = stats || {
    cpuName: 'N/A', cpuLoad: 0, cpuTemp: 0, cpuPower: 0, cpuFanSpeed: 0,
    ramUsedPercent: 0, ramUsed: 0, ramTotal: 0,
    network: { downloadSpeed: 0, uploadSpeed: 0 },
    gpus: [], drives: [], topProcesses: [],
    osName: '', uptime: ''
  };

  const isCpuHot = safeStats.cpuTemp > 80;

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 text-gray-600 dark:text-gray-300">
      <Navbar />

      <div className="mx-auto max-w-screen-2xl p-4 md:p-6 2xl:p-10">
        
        {/* HEADER */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-black dark:text-white">Hardware Monitor</h1>
            <p className="text-sm text-gray-500 mt-1">
              {safeStats.osName} • Uptime: {safeStats.uptime}
            </p>
          </div>
        </div>

        {/* GRILLE PRINCIPALE */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3 2xl:gap-7.5">
          
          {/* 1. CPU CARD */}
          <DashboardCard title="Processeur" icon={Cpu} className={isCpuHot ? "border-red-500 dark:border-red-500" : ""}>
            <div className="mb-4">
              <span className="text-xs bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded text-gray-500">
                {safeStats.cpuName}
              </span>
            </div>
            
            <ProgressBar label="Charge Totale" value={safeStats.cpuLoad} color={isCpuHot ? "bg-red-500" : "bg-blue-500"} />
            
            <div className="mt-4 space-y-1">
              <StatRow label="Température" value={`${safeStats.cpuTemp.toFixed(1)}°C`} icon={Thermometer} alert={isCpuHot} />
              <StatRow label="Ventilateur" value={`${safeStats.cpuFanSpeed.toFixed(0)} RPM`} icon={Wind} />
              <StatRow label="Consommation" value={`${safeStats.cpuPower.toFixed(1)} W`} icon={Zap} />
            </div>
          </DashboardCard>

          {/* 2. RAM CARD */}
          <DashboardCard title="Mémoire RAM" icon={MemoryStick}>
            <div className="mb-6 text-center">
              <div className="text-3xl font-bold text-black dark:text-white mb-1">
                {safeStats.ramUsedPercent.toFixed(1)}%
              </div>
              <p className="text-sm text-gray-500">
                {safeStats.ramUsed.toFixed(1)} Go / {safeStats.ramTotal.toFixed(1)} Go
              </p>
            </div>
            <ProgressBar label="Utilisation" value={safeStats.ramUsedPercent} color="bg-purple-500" />
            
            {/* Top Process List inside RAM Card */}
            <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700">
              <h5 className="text-sm font-semibold mb-3 flex items-center gap-2">
                <Activity size={14} /> Top Consommateurs
              </h5>
              <div className="space-y-2">
                {safeStats.topProcesses && safeStats.topProcesses.length > 0 ? (
                   safeStats.topProcesses.slice(0, 3).map((proc: any) => (
                    <div key={proc.id} className="flex justify-between text-xs">
                      <span className="text-gray-600 dark:text-gray-400 truncate w-32">{proc.name}</span>
                      <span className="font-mono font-bold text-purple-500">{proc.memoryUsedMb.toFixed(0)} Mo</span>
                    </div>
                   ))
                ) : <span className="text-xs text-gray-400">Chargement...</span>}
              </div>
            </div>
          </DashboardCard>

          {/* 3. NETWORK CARD */}
          <DashboardCard title="Réseau" icon={Wifi}>
            <div className="grid grid-cols-2 gap-4 text-center mb-6">
              <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <ArrowDown className="w-6 h-6 text-green-500 mx-auto mb-2" />
                <div className="text-xl font-bold text-black dark:text-white">
                  {safeStats.network.downloadSpeed.toFixed(1)}
                </div>
                <div className="text-xs text-gray-500">Mbps Down</div>
              </div>
              <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <ArrowUp className="w-6 h-6 text-blue-500 mx-auto mb-2" />
                <div className="text-xl font-bold text-black dark:text-white">
                  {safeStats.network.uploadSpeed.toFixed(1)}
                </div>
                <div className="text-xs text-gray-500">Mbps Up</div>
              </div>
            </div>
            <div className="text-xs text-center text-gray-400">
              Surveillance en temps réel
            </div>
          </DashboardCard>

          {/* 4. GPU CARDS (Mapping dynamique) */}
          {safeStats.gpus.map((gpu: any, idx: number) => (
            <DashboardCard key={idx} title={`GPU ${idx + 1}`} icon={Server}>
              <div className="mb-4">
                 <span className="text-xs bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded text-gray-500 truncate block">
                  {gpu.name}
                </span>
              </div>
              <ProgressBar label="Charge Core" value={gpu.load || 0} color="bg-orange-500" />
              
              <div className="mt-2 space-y-1">
                 <StatRow label="Température" value={`${(gpu.temperature || 0).toFixed(0)}°C`} icon={Thermometer} />
                 <StatRow label="Ventilateur" value={`${(gpu.fanSpeed || 0).toFixed(0)}%`} icon={Wind} />
                 <StatRow 
                    label="VRAM" 
                    value={`${(gpu.memoryUsed || 0).toFixed(0)} Mo`} 
                    subValue={`sur ${(gpu.memoryTotal || 0).toFixed(0)} Mo`} 
                 />
              </div>
            </DashboardCard>
          ))}

          {/* 5. STORAGE CARD */}
          <DashboardCard title="Stockage" icon={HardDrive}>
            <div className="space-y-4">
              {safeStats.drives.map((drive: any, idx: number) => (
                <div key={idx}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="font-bold text-gray-700 dark:text-gray-300">{drive.mount || "Disk"}</span>
                    <span className="text-gray-500">
                      {(drive.usedSpace || 0).toFixed(0)} Go / {(drive.totalSpace || 0).toFixed(0)} Go
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full ${drive.usedPercent > 90 ? 'bg-red-500' : 'bg-green-500'}`} 
                      style={{ width: `${drive.usedPercent || 0}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </DashboardCard>

        </div>
      </div>
    </div>
  );
}