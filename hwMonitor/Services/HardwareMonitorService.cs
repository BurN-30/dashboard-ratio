using LibreHardwareMonitor.Hardware;
using hwMonitor.Models;
using hwMonitor.Visitors;
using System.Text.RegularExpressions;

namespace hwMonitor.Services;

public class HardwareMonitorService : IHardwareMonitorService
{
    private Computer? _computer;
    private readonly UpdateVisitor _updateVisitor;
    private readonly SemaphoreSlim _semaphore = new(1, 1);

    public HardwareMonitorService()
    {
        _updateVisitor = new UpdateVisitor();
        
        try
        {
            _computer = new Computer
            {
                IsCpuEnabled = true,
                IsGpuEnabled = true,
                IsMemoryEnabled = true,
                IsStorageEnabled = true,
                IsNetworkEnabled = true,
                IsControllerEnabled = true,  // Important pour certains contrôleurs de ventilo
                IsMotherboardEnabled = true  // CRUCIAL pour les ventilateurs CPU (SuperIO)
            };

            _computer.Open();
        }
        catch (Exception ex)
        {
            _computer = null;
            Console.Error.WriteLine($"⚠️ Erreur init HardwareMonitor: {ex.Message}");
        }
    }

    public async Task<HardwareStats> GetHardwareStatsAsync()
    {
        var stats = new HardwareStats();

        if (_computer == null) return stats;

        await _semaphore.WaitAsync();
        try
        {
            _computer.Accept(_updateVisitor);

            foreach (var hardware in _computer.Hardware)
            {
                // On passe hardware ET stats pour remplir l'objet
                switch (hardware.HardwareType)
                {
                    case HardwareType.Cpu:
                        ExtractCpuStats(hardware, stats);
                        break;
                    
                    case HardwareType.GpuNvidia:
                    case HardwareType.GpuAmd:
                        ExtractGpuStats(hardware, stats);
                        break;
                    
                    case HardwareType.Memory:
                        ExtractMemoryStats(hardware, stats);
                        break;
                    
                    case HardwareType.Storage:
                        ExtractStorageStats(hardware, stats);
                        break;
                    
                    case HardwareType.Network:
                        ExtractNetworkStats(hardware, stats);
                        break;

                    // NOUVEAU : On scanne la carte mère pour trouver les ventilateurs
                    case HardwareType.Motherboard:
                    case HardwareType.SuperIO:
                        ExtractMotherboardStats(hardware, stats);
                        break;
                }
            }

            // === AJOUT : Infos Système ===
            // Récupération de l'OS
            stats.OsName = System.Runtime.InteropServices.RuntimeInformation.OSDescription;

            // Récupération de l'Uptime
            var uptimeSpan = TimeSpan.FromMilliseconds(Environment.TickCount64);
            stats.Uptime = $"{uptimeSpan.Days}j {uptimeSpan.Hours}h {uptimeSpan.Minutes}m";

            // Ajout du Timestamp pour le suivi frontend
            stats.Timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");

            ExtractTopProcesses(stats);
            
            return stats;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"Erreur lecture capteurs: {ex.Message}");
            return stats;
        }
        finally
        {
            _semaphore.Release();
        }
    }

    private void ExtractCpuStats(IHardware hardware, HardwareStats stats)
    {
        stats.CpuName = hardware.Name;
        // Reset list to avoid duplicates if called multiple times on same object (though strictly new object is created each time)
        stats.CpuCoreLoads = new List<float>();

        // Temporary list to sort cores if needed, though usually they come in order
        var coreLoads = new Dictionary<string, float>();

        foreach (var sensor in hardware.Sensors)
        {
            if (!sensor.Value.HasValue) continue;

            if (sensor.SensorType == SensorType.Load)
            {
                if (sensor.Name.Contains("Total"))
                {
                    stats.CpuLoad = sensor.Value.Value;
                }
                // Accept "Core", "CPU #", or "Thread" (for logical cores)
                else if (sensor.Name.Contains("Core") || sensor.Name.Contains("CPU #") || sensor.Name.Contains("Thread"))
                {
                    coreLoads[sensor.Name] = sensor.Value.Value;
                }
            }
                
            // Ajout de "Tdie" et "Tctl" pour Ryzen
            if (sensor.SensorType == SensorType.Temperature && 
               (sensor.Name.Contains("Package") || sensor.Name.Contains("Average") || sensor.Name.Contains("Tdie")))
                stats.CpuTemp = Math.Max(stats.CpuTemp, sensor.Value.Value); // On prend la plus haute trouvée
                
            if (sensor.SensorType == SensorType.Power && sensor.Name.Contains("Package"))
                stats.CpuPower = sensor.Value.Value;
                
            if (sensor.SensorType == SensorType.Clock)
                stats.CpuClockSpeed = Math.Max(stats.CpuClockSpeed, sensor.Value.Value); // On prend le coeur le plus rapide
        }

        // Debug logging to help troubleshoot missing cores
        if (coreLoads.Count == 0)
        {
            Console.WriteLine($"[Warning] No CPU Cores detected for {hardware.Name}. Found sensors:");
            foreach (var s in hardware.Sensors)
                if (s.SensorType == SensorType.Load)
                    Console.WriteLine($" - {s.Name}: {s.Value}%");
        }

        // Sort dynamically using Regex for "Natural Sort" (e.g. Core #2 before Core #10)
        var sortedCores = coreLoads
            .OrderBy(kvp => 
            {
                // Match the first sequence of digits in the name
                var match = Regex.Match(kvp.Key, @"\d+");
                if (match.Success && int.TryParse(match.Value, out int number))
                {
                    return number;
                }
                return int.MaxValue;
            })
            .ThenBy(kvp => kvp.Key); // Stable fallback

        foreach (var kvp in sortedCores)
        {
            stats.CpuCoreLoads.Add(kvp.Value);
        }
    }

    // NOUVEAU : Extraction récursive pour trouver les ventilateurs sur la Carte Mère / SuperIO
    private void ExtractMotherboardStats(IHardware hardware, HardwareStats stats)
    {
        // D'abord, regarder les capteurs directs de ce composant
        foreach (var sensor in hardware.Sensors)
        {
            if (sensor.SensorType == SensorType.Fan && sensor.Value.HasValue)
            {
                // Essayer de deviner si c'est le ventilateur CPU
                if (sensor.Name.Contains("CPU", StringComparison.OrdinalIgnoreCase) || 
                    sensor.Name.Contains("Fan #1", StringComparison.OrdinalIgnoreCase)) // Souvent Fan #1 est le CPU
                {
                    stats.CpuFanSpeed = sensor.Value.Value;
                }
            }
        }

        // Ensuite, regarder dans les sous-composants (SuperIO est souvent DANS Motherboard)
        foreach (var subHardware in hardware.SubHardware)
        {
            subHardware.Update(); // Important : Mettre à jour les sous-composants
            ExtractMotherboardStats(subHardware, stats);
        }
    }

    private void ExtractGpuStats(IHardware hardware, HardwareStats stats)
    {
        var gpu = new GpuData { Name = hardware.Name };

        foreach (var sensor in hardware.Sensors)
        {
            if (!sensor.Value.HasValue) continue;

            if (sensor.SensorType == SensorType.Load && sensor.Name.Contains("Core"))
                gpu.Load = sensor.Value.Value;

            if (sensor.SensorType == SensorType.Temperature && sensor.Name.Contains("Core"))
                gpu.Temperature = sensor.Value.Value;

            if (sensor.SensorType == SensorType.SmallData || sensor.SensorType == SensorType.Data)
            {
                if (sensor.Name.Contains("Used") && sensor.Name.Contains("Memory")) gpu.MemoryUsed = sensor.Value.Value;
                if (sensor.Name.Contains("Total") && sensor.Name.Contains("Memory")) gpu.MemoryTotal = sensor.Value.Value;
            }

            if (sensor.SensorType == SensorType.Fan)
                gpu.FanSpeed = sensor.Value.Value;

            if (sensor.SensorType == SensorType.Power)
                gpu.Power = sensor.Value.Value;
        }
        stats.Gpus.Add(gpu);
    }

    private void ExtractMemoryStats(IHardware hardware, HardwareStats stats)
    {
        foreach (var sensor in hardware.Sensors)
        {
            if (!sensor.Value.HasValue) continue;

            if (sensor.SensorType == SensorType.Data && sensor.Name.Contains("Used"))
                stats.RamUsed = sensor.Value.Value;

            if (sensor.SensorType == SensorType.Data && sensor.Name.Contains("Available"))
                stats.RamTotal = stats.RamUsed + sensor.Value.Value;
                
            if (sensor.SensorType == SensorType.Load && sensor.Name.Contains("Memory"))
                stats.RamUsedPercent = sensor.Value.Value;
        }
    }

    private void ExtractStorageStats(IHardware hardware, HardwareStats stats)
    {
        // Ignorer les disques amovibles ou virtuels vides si nécessaire
        var drive = new DriveData { Name = hardware.Name };
        
        // Essayer d'extraire la lettre de lecteur du nom (ex: "C: Samsung SSD") si dispo, sinon logique plus complexe requise
        // Ici on simplifie. LibreHardwareMonitor ne donne pas toujours la lettre de lecteur facilement via sensor.
        
        foreach (var sensor in hardware.Sensors)
        {
            if (!sensor.Value.HasValue) continue;

            if (sensor.SensorType == SensorType.Load && sensor.Name.Contains("Used Space"))
                drive.UsedPercent = sensor.Value.Value;

            if (sensor.SensorType == SensorType.Data && sensor.Name.Contains("Used")) // En GB
                drive.UsedSpace = sensor.Value.Value;
            
            if (sensor.SensorType == SensorType.Data && sensor.Name.Contains("Total")) // En GB
                drive.TotalSpace = sensor.Value.Value;

            if (sensor.SensorType == SensorType.Temperature)
                drive.Temperature = sensor.Value.Value;
        }
        
        // On n'ajoute que si on a des données pertinentes
        if (drive.TotalSpace > 0)
            stats.Drives.Add(drive);
    }

    private void ExtractNetworkStats(IHardware hardware, HardwareStats stats)
    {
        foreach (var sensor in hardware.Sensors)
        {
            if (!sensor.Value.HasValue) continue;

            // Conversion Bytes/s -> Mbps (Megabits par seconde)
            // Formule : (Bytes * 8) / 1,000,000
            // Ou plus simple : (Bytes / 1024 / 1024) * 8
            
            float valueInMbps = (sensor.Value.Value * 8.0f) / 1_000_000.0f;

            if (sensor.Name.Contains("Upload"))
                stats.Network.UploadSpeed += valueInMbps;

            if (sensor.Name.Contains("Download"))
                stats.Network.DownloadSpeed += valueInMbps;
        }
    }

    public void Dispose()
    {
        _semaphore?.Dispose();
        _computer?.Close();
    }

    private void ExtractTopProcesses(HardwareStats stats)
    {
        try 
        {
            // On récupère tous les processus, on trie par mémoire, et on prend les 5 premiers
            var processes = System.Diagnostics.Process.GetProcesses()
                .OrderByDescending(p => p.WorkingSet64) // Trie par mémoire utilisée
                .Take(5) // On garde le Top 5
                .Select(p => new ProcessData {
                    Name = p.ProcessName,
                    Id = p.Id,
                    MemoryUsedMb = p.WorkingSet64 / 1024f / 1024f // Conversion en MB
                })
                .ToList();

            stats.TopProcesses = processes;
        }
        catch 
        {
            // Si erreur (droits admin manquants par ex), on laisse vide
        }
    }
}