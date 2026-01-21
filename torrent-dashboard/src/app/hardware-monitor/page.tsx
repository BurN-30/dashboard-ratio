'use client';

import React from 'react';
import Navbar from '@/components/Navbar';
import { useHardwareStats } from '@/hooks/useHardwareStats';
import { 
  Cpu, 
  MemoryStick, 
  HardDrive, 
  Wifi, 
  Zap, 
  Server,
  ArrowDown,
  ArrowUp,
  Activity,
  Clock,
  AlertTriangle
} from 'lucide-react';

// Composant barre de progression sécurisé
const ProgressBar = ({ value, color = "bg-blue-500", label, subLabel }: any) => {
  // Sécurité : si value est undefined ou null, on met 0
  const safeValue = value || 0;
  
  return (
    <div className="w-full mb-3">
      <div className="flex justify-between text-xs mb-1">
        <span className="text-gray-400 font-medium">{label}</span>
        <span className="text-gray-200">{subLabel || `${safeValue.toFixed(1)}%`}</span>
      </div>
      <div className="w-full bg-gray-700/50 rounded-full h-2">
        <div 
          className={`h-2 rounded-full transition-all duration-500 ${color}`} 
          style={{ width: `${Math.min(safeValue, 100)}%` }}
        ></div>
      </div>
    </div>
  );
};

// Composant Carte Statistique Rapide
const StatCard = ({ icon: Icon, title, value, subtext, color }: any) => (
  <div className="bg-gray-800/80 border border-gray-700/50 p-4 rounded-xl flex items-center space-x-4 hover:bg-gray-800 transition-colors">
    <div className={`p-3 rounded-lg bg-gray-700/30 ${color}`}>
      <Icon size={24} />
    </div>
    <div>
      <p className="text-gray-400 text-xs uppercase font-bold tracking-wider">{title}</p>
      <h3 className="text-xl font-bold text-white">{value}</h3>
      {subtext && <p className="text-xs text-gray-500">{subtext}</p>}
    </div>
  </div>
);

export default function HardwareMonitor() {
  const { stats, loading, error } = useHardwareStats({
    interval: 2000,
  });

  if (loading && !stats) return <div className="min-h-screen bg-gray-950 flex items-center justify-center text-blue-500 animate-pulse">Initialisation du Nexus...</div>;
  if (error) return <div className="min-h-screen bg-gray-950 flex items-center justify-center text-red-500">Erreur de connexion : {error}</div>;

  // Sécurisation des valeurs principales
  const cpuTemp = stats?.cpuTemp || 0;
  const cpuLoad = stats?.cpuLoad || 0;
  const cpuPower = stats?.cpuPower || 0;
  const cpuClock = stats?.cpuClockSpeed || 0;
  const ramUsedPercent = stats?.ramUsedPercent || 0;
  const ramUsed = stats?.ramUsed || 0;
  const ramTotal = stats?.ramTotal || 0;
  const downloadSpeed = stats?.network?.downloadSpeed || 0;
  const uploadSpeed = stats?.network?.uploadSpeed || 0;
  const cpuFanSpeed = stats?.cpuFanSpeed || 0;

  // Calcul pour l'alerte visuelle (Rouge si > 80°C)
  const isCpuCritical = cpuTemp > 80;

  return (
    <div className="min-h-screen bg-gray-950 text-gray-200 font-sans selection:bg-blue-500/30 pb-10">
      <Navbar />
      
      <div className="max-w-7xl mx-auto px-4 py-8">
        
        {/* === HEADER === */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <Activity className="text-blue-500" /> 
              System Overview
            </h1>
            <p className="text-gray-500 text-sm mt-1 flex items-center gap-2">
               <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
               {stats?.osName || "System Online"}
            </p>
          </div>
          <div className="flex gap-4">
            <div className="px-4 py-2 bg-gray-900 rounded-lg border border-gray-800 text-sm text-gray-400 flex items-center gap-3">
              <Clock size={16} />
              <div>
                <span className="block text-[10px] font-bold text-gray-500 uppercase">Uptime</span>
                <span className="text-white font-mono">{stats?.uptime || "00:00:00"}</span>
              </div>
            </div>
          </div>
        </div>

        {stats && (
          <>
            {/* === KPI CARDS === */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              <StatCard 
                icon={Cpu} 
                title="CPU Load" 
                value={`${cpuLoad.toFixed(1)}%`} 
                subtext={`${cpuTemp.toFixed(0)}°C • ${cpuClock.toFixed(0)} MHz`}
                color={isCpuCritical ? "text-red-500" : "text-blue-400"}
              />
              <StatCard 
                icon={MemoryStick} 
                title="Memory" 
                value={`${ramUsedPercent.toFixed(1)}%`} 
                subtext={`${ramUsed.toFixed(1)} GB / ${ramTotal.toFixed(1)} GB`}
                color="text-purple-400"
              />
              <StatCard 
                icon={Zap} 
                title="Power Draw" 
                value={`${cpuPower.toFixed(1)} W`} 
                subtext="CPU Package Only"
                color="text-yellow-400"
              />
              <StatCard 
                icon={Wifi} 
                title="Network" 
                value={`${downloadSpeed.toFixed(1)} Mb/s`} 
                subtext={`Up: ${uploadSpeed.toFixed(1)} Mb/s`}
                color="text-green-400"
              />
            </div>

            {/* === MAIN GRID === */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              {/* COLONNE 1 & 2 : CPU & GPU */}
              <div className="lg:col-span-2 space-y-6">
                
                {/* CPU PANEL */}
                <div className={`
                    bg-gray-900 border rounded-xl p-6 shadow-xl transition-all duration-500
                    ${isCpuCritical ? 'border-red-500 shadow-[0_0_20px_rgba(239,68,68,0.3)]' : 'border-gray-800'}
                `}>
                  <div className="flex justify-between items-center mb-6">
                    <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                      {isCpuCritical ? <AlertTriangle className="text-red-500 animate-bounce" /> : <Cpu size={20} />}
                      Processor Details
                    </h2>
                    <span className="px-2 py-1 bg-gray-800 text-gray-400 text-xs rounded border border-gray-700">
                        {stats.cpuName || "Unknown CPU"}
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    {/* Visualisation Coeurs */}
                    <div className="space-y-4">
                      {/* Grid dynamique en fonction du nombre de coeurs */}
                      <div 
                        className="grid gap-1 h-32 items-end"
                        style={{
                          gridTemplateColumns: `repeat(${(stats.cpuCoreLoads && stats.cpuCoreLoads.length > 0) ? Math.min(Math.max(stats.cpuCoreLoads.length, 4), 32) : 8}, 1fr)`
                        }}
                      >
                        {(stats.cpuCoreLoads && stats.cpuCoreLoads.length > 0) ? (
                          stats.cpuCoreLoads.map((load, i) => (
                            <div key={i} className="bg-gray-800 rounded-sm relative overflow-hidden group w-full h-full" title={`Core ${i+1}: ${load.toFixed(0)}%`}>
                               <div 
                                  className={`absolute bottom-0 w-full transition-all duration-300 ${load > 90 ? 'bg-red-500' : 'bg-blue-500'}`} 
                                  style={{height: `${load}%`, opacity: 0.8}}
                               ></div>
                            </div>
                          ))
                        ) : (
                          // Message si pas de données détectées
                          <div className="col-span-full h-full flex items-center justify-center bg-gray-900/50 border border-gray-800 rounded">
                            <p className="text-xs text-gray-500">Core details unavailable</p>
                          </div>
                        )}
                      </div>
                      <p className="text-center text-xs text-gray-500">
                        Logical Cores Activity 
                        {stats.cpuCoreLoads && stats.cpuCoreLoads.length > 0 && ` (${stats.cpuCoreLoads.length} Cores detected)`}
                      </p>
                    </div>

                    <div className="flex flex-col justify-center space-y-4">
                      <ProgressBar 
                        label="Total Load" 
                        value={cpuLoad} 
                        color={isCpuCritical ? "bg-red-500" : "bg-blue-600"} 
                      />
                      <ProgressBar 
                        label="Temperature" 
                        value={cpuTemp} 
                        subLabel={`${cpuTemp.toFixed(1)}°C`} 
                        color={cpuTemp > 80 ? "bg-red-500" : cpuTemp > 60 ? "bg-orange-400" : "bg-emerald-500"} 
                      />
                      
                      <div className="grid grid-cols-2 gap-4 mt-2">
                         <div className="bg-gray-800/50 p-2 rounded border border-gray-700/50 text-center">
                            <span className="text-xs text-gray-500 block">Fan Speed</span>
                            <span className="text-white font-mono">{cpuFanSpeed.toFixed(0)} RPM</span>
                         </div>
                         <div className="bg-gray-800/50 p-2 rounded border border-gray-700/50 text-center">
                            <span className="text-xs text-gray-500 block">Power</span>
                            <span className="text-white font-mono">{cpuPower.toFixed(1)} W</span>
                         </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* GPU Section */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {stats.gpus && stats.gpus.length > 0 ? stats.gpus.map((gpu, idx) => (
                    <div key={idx} className="bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-xl relative overflow-hidden group hover:border-purple-500/50 transition-colors">
                      <div className="absolute top-0 right-0 p-3 opacity-5 group-hover:opacity-10 transition-opacity">
                        <Zap size={100} />
                      </div>
                      <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2 relative z-10">
                        <Server size={20} className="text-purple-500" /> GPU {idx + 1}
                      </h2>
                      <div className="relative z-10 space-y-4">
                        <div className="flex justify-between items-end">
                          <span className="text-gray-400 text-xs truncate max-w-[150px]">{gpu.name}</span>
                          <span className="text-2xl font-bold text-white">{(gpu.load || 0).toFixed(0)}%</span>
                        </div>
                        <ProgressBar label="Core Load" value={gpu.load || 0} color="bg-purple-500" />
                        <ProgressBar 
                            label="VRAM Usage" 
                            value={gpu.memoryTotal ? ((gpu.memoryUsed || 0) / gpu.memoryTotal) * 100 : 0} 
                            subLabel={`${(gpu.memoryUsed || 0).toFixed(0)} / ${(gpu.memoryTotal || 0).toFixed(0)} MB`} 
                            color="bg-purple-400/70" 
                        />
                        
                        <div className="grid grid-cols-2 gap-2 mt-4">
                           <div className="bg-gray-800/50 p-2 rounded border border-gray-700/50 text-center">
                              <span className="text-[10px] text-gray-500 block uppercase">Temp</span>
                              <span className="text-white font-mono text-sm">{(gpu.temperature || 0).toFixed(0)}°C</span>
                           </div>
                           <div className="bg-gray-800/50 p-2 rounded border border-gray-700/50 text-center">
                              <span className="text-[10px] text-gray-500 block uppercase">Fan</span>
                              <span className="text-white font-mono text-sm">{(gpu.fanSpeed || 0).toFixed(0)}%</span>
                           </div>
                        </div>
                      </div>
                    </div>
                  )) : (
                    <div className="col-span-2 bg-gray-900/50 border border-gray-800 p-6 rounded-xl text-center text-gray-500">
                      Aucun GPU détecté
                    </div>
                  )}
                </div>
              </div>

              {/* COLONNE 3 : Storage, Processes & Network */}
              <div className="space-y-6">
                
                {/* TOP PROCESSES (Nouveau !) */}
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-xl">
                  <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2 uppercase tracking-wide">
                    <Activity size={16} className="text-pink-500" /> Top Memory Usage
                  </h2>
                  <div className="space-y-3">
                    {stats.topProcesses && stats.topProcesses.length > 0 ? stats.topProcesses.map((proc) => (
                      <div key={proc.id} className="flex justify-between items-center text-xs border-b border-gray-800 pb-2 last:border-0 last:pb-0">
                        <div className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 rounded-full bg-pink-500/50"></div>
                          <span className="text-gray-300 font-mono truncate max-w-[100px]" title={proc.name}>{proc.name}</span>
                        </div>
                        <span className="text-pink-400 font-bold">{(proc.memoryUsedMb || 0).toFixed(0)} MB</span>
                      </div>
                    )) : (
                       <p className="text-xs text-gray-600 italic">Aucune donnée processus...</p>
                    )}
                  </div>
                </div>

                {/* Storage Panel */}
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 h-fit">
                  <h2 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
                    <HardDrive size={20} /> Storage
                  </h2>
                  <div className="space-y-6">
                    {stats.drives && stats.drives.map((drive, idx) => (
                      <div key={idx} className="group">
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-sm font-medium text-gray-300 flex items-center gap-2">
                            <span className="text-gray-600 text-xs bg-gray-800 px-1 rounded">{drive.mount || "DISK"}</span>
                            {drive.name}
                          </span>
                        </div>
                        <div className="flex justify-between text-xs text-gray-500 mb-1">
                             <span>{(drive.usedSpace || 0).toFixed(0)} GB Used</span>
                             <span>{(drive.totalSpace || 0).toFixed(0)} GB Total</span>
                        </div>
                        <div className="w-full bg-gray-800 rounded-full h-2 relative overflow-hidden">
                          <div 
                            className={`h-full rounded-full ${(drive.usedPercent || 0) > 90 ? 'bg-red-500' : 'bg-emerald-500'}`}
                            style={{ width: `${(drive.usedPercent || 0)}%` }}
                          ></div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Network Panel */}
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                  <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <Wifi size={20} /> Network
                  </h2>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg border border-gray-700/30">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-green-500/20 rounded text-green-400"><ArrowDown size={16}/></div>
                        <div>
                          <span className="block text-xs text-gray-500">Download</span>
                          <span className="block text-sm font-mono text-white">{downloadSpeed.toFixed(1)} Mbps</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg border border-gray-700/30">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-blue-500/20 rounded text-blue-400"><ArrowUp size={16}/></div>
                        <div>
                          <span className="block text-xs text-gray-500">Upload</span>
                          <span className="block text-sm font-mono text-white">{uploadSpeed.toFixed(1)} Mbps</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}