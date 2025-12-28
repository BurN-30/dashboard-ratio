using LibreHardwareMonitor.Hardware;
using hwMonitor.Models;
using hwMonitor.Visitors;

namespace hwMonitor.Services;

/// <summary>
/// Service principal de monitoring matériel utilisant LibreHardwareMonitor
/// IMPORTANT : Nécessite des droits Administrateur pour accéder aux capteurs matériels
/// </summary>
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
            // Initialisation de l'objet Computer avec tous les composants nécessaires
            _computer = new Computer
            {
                IsCpuEnabled = true,         // Surveillance CPU
                IsGpuEnabled = true,         // Surveillance GPU (iGPU + dGPU)
                IsMemoryEnabled = true,      // Surveillance RAM
                IsStorageEnabled = true,     // Surveillance Stockage (tous les disques)
                IsNetworkEnabled = true,     // Surveillance Réseau (Upload/Download)
                IsControllerEnabled = true,  // Contrôleurs (pour ventilateurs/RGB)
                IsMotherboardEnabled = true  // Carte mère (voltages, ventilateurs)
            };

            _computer.Open();
        }
        catch (Exception ex)
        {
            // Initialisation avec une instance vide si erreur (nécessite admin)
            _computer = null;
            Console.Error.WriteLine($"⚠️ Erreur lors de l'initialisation des capteurs matériels: {ex.Message}");
            Console.Error.WriteLine("💡 Assurez-vous que l'application s'exécute en mode Administrateur.");
        }
    }

    /// <summary>
    /// Récupère les statistiques matérielles en temps réel
    /// Optimisé pour être léger et rapide
    /// </summary>
    public async Task<HardwareStats> GetHardwareStatsAsync()
    {
        var stats = new HardwareStats();

        // Si Computer n'a pas pu être initialisé, retourner des stats vides
        if (_computer == null)
        {
            return stats;
        }

        await _semaphore.WaitAsync();
        try
        {
            // Mise à jour des capteurs (opération légère)
            _computer.Accept(_updateVisitor);

            // Collecte des données de manière optimisée
            foreach (var hardware in _computer.Hardware)
            {
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
                }
            }

            return stats;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"Erreur lors de la lecture des capteurs: {ex.Message}");
            return stats;
        }
        finally
        {
            _semaphore.Release();
        }
    }

    /// <summary>
    /// Extrait les statistiques CPU (charge, température, puissance, fréquence)
    /// </summary>
    private void ExtractCpuStats(IHardware hardware, HardwareStats stats)
    {
        stats.CpuName = hardware.Name ?? "CPU Unknown";

        foreach (var sensor in hardware.Sensors)
        {
            if (sensor.Value.HasValue)
            {
                // Charge CPU totale
                if (sensor.SensorType == SensorType.Load && sensor.Name.Contains("Total", StringComparison.OrdinalIgnoreCase))
                {
                    stats.CpuLoad = sensor.Value.Value;
                }
                
                // Température CPU (Package ou Average)
                if (sensor.SensorType == SensorType.Temperature && 
                    (sensor.Name.Contains("Package", StringComparison.OrdinalIgnoreCase) || 
                     sensor.Name.Contains("Average", StringComparison.OrdinalIgnoreCase) ||
                     sensor.Name.Contains("Tctl", StringComparison.OrdinalIgnoreCase)))  // AMD Ryzen
                {
                    stats.CpuTemp = sensor.Value.Value;
                }
                
                // Consommation électrique (Watts)
                if (sensor.SensorType == SensorType.Power && 
                    (sensor.Name.Contains("Package", StringComparison.OrdinalIgnoreCase) ||
                     sensor.Name.Contains("CPU", StringComparison.OrdinalIgnoreCase)))
                {
                    stats.CpuPower = sensor.Value.Value;
                }
                
                // Fréquence (Clock Speed en MHz)
                if (sensor.SensorType == SensorType.Clock && 
                    sensor.Name.Contains("Core", StringComparison.OrdinalIgnoreCase))
                {
                    // Prendre la fréquence moyenne ou max
                    if (stats.CpuClockSpeed == 0 || sensor.Value.Value > stats.CpuClockSpeed)
                    {
                        stats.CpuClockSpeed = sensor.Value.Value;
                    }
                }
            }
        }
    }

    /// <summary>
    /// Extrait les statistiques GPU (supporte multi-GPU : iGPU + dGPU)
    /// </summary>
    private void ExtractGpuStats(IHardware hardware, HardwareStats stats)
    {
        var gpuData = new GpuData
        {
            Name = hardware.Name ?? "GPU Unknown"
        };

        foreach (var sensor in hardware.Sensors)
        {
            if (sensor.Value.HasValue)
            {
                // Charge GPU (Core)
                if (sensor.SensorType == SensorType.Load && 
                    (sensor.Name.Contains("Core", StringComparison.OrdinalIgnoreCase) ||
                     sensor.Name.Contains("GPU", StringComparison.OrdinalIgnoreCase)))
                {
                    gpuData.Load = sensor.Value.Value;
                }
                
                // Température GPU
                if (sensor.SensorType == SensorType.Temperature && 
                    (sensor.Name.Contains("Core", StringComparison.OrdinalIgnoreCase) ||
                     sensor.Name.Contains("GPU", StringComparison.OrdinalIgnoreCase)))
                {
                    gpuData.Temperature = sensor.Value.Value;
                }
                
                // Mémoire GPU utilisée
                if (sensor.SensorType == SensorType.SmallData && 
                    sensor.Name.Contains("Used", StringComparison.OrdinalIgnoreCase))
                {
                    gpuData.MemoryUsed = sensor.Value.Value;
                }
                
                // Mémoire GPU totale
                if (sensor.SensorType == SensorType.SmallData && 
                    sensor.Name.Contains("Total", StringComparison.OrdinalIgnoreCase))
                {
                    gpuData.MemoryTotal = sensor.Value.Value;
                }
                
                // Vitesse ventilateur GPU
                if (sensor.SensorType == SensorType.Control && 
                    sensor.Name.Contains("Fan", StringComparison.OrdinalIgnoreCase))
                {
                    gpuData.FanSpeed = sensor.Value.Value;
                }
                
                // Consommation GPU (Watts)
                if (sensor.SensorType == SensorType.Power && 
                    (sensor.Name.Contains("GPU", StringComparison.OrdinalIgnoreCase) ||
                     sensor.Name.Contains("Total", StringComparison.OrdinalIgnoreCase)))
                {
                    gpuData.Power = sensor.Value.Value;
                }
            }
        }
        
        // Ajouter le GPU à la liste
        stats.Gpus.Add(gpuData);
    }

    /// <summary>
    /// Extrait les statistiques RAM (utilisée/totale)
    /// </summary>
    private void ExtractMemoryStats(IHardware hardware, HardwareStats stats)
    {
        foreach (var sensor in hardware.Sensors)
        {
            if (sensor.Value.HasValue)
            {
                // RAM utilisée
                if (sensor.SensorType == SensorType.Data && 
                    sensor.Name.Contains("Used", StringComparison.OrdinalIgnoreCase))
                {
                    stats.RamUsed = sensor.Value.Value;
                }
                
                // RAM disponible (pour calculer le total)
                if (sensor.SensorType == SensorType.Data && 
                    sensor.Name.Contains("Available", StringComparison.OrdinalIgnoreCase))
                {
                    stats.RamTotal = stats.RamUsed + sensor.Value.Value;
                }
                
                // Pourcentage d'utilisation RAM
                if (sensor.SensorType == SensorType.Load && 
                    sensor.Name.Contains("Memory", StringComparison.OrdinalIgnoreCase))
                {
                    stats.RamUsedPercent = sensor.Value.Value;
                }
            }
        }
    }

    /// <summary>
    /// Extrait les statistiques de stockage (supporte multi-disques : SSD + HDD)
    /// </summary>
    private void ExtractStorageStats(IHardware hardware, HardwareStats stats)
    {
        var driveData = new DriveData
        {
            Name = hardware.Name ?? "Drive Unknown"
        };

        foreach (var sensor in hardware.Sensors)
        {
            if (sensor.Value.HasValue)
            {
                // Pourcentage d'utilisation
                if (sensor.SensorType == SensorType.Load && 
                    sensor.Name.Contains("Used Space", StringComparison.OrdinalIgnoreCase))
                {
                    driveData.UsedPercent = sensor.Value.Value;
                }
                
                // Espace utilisé et total (en Go)
                if (sensor.SensorType == SensorType.Data)
                {
                    if (sensor.Name.Contains("Used", StringComparison.OrdinalIgnoreCase))
                    {
                        driveData.UsedSpace = sensor.Value.Value;
                    }
                    if (sensor.Name.Contains("Total", StringComparison.OrdinalIgnoreCase))
                    {
                        driveData.TotalSpace = sensor.Value.Value;
                    }
                }
                
                // Température du disque (peut être null)
                if (sensor.SensorType == SensorType.Temperature)
                {
                    driveData.Temperature = sensor.Value.Value;
                }
            }
        }
        
        // Ajouter le disque à la liste
        stats.Drives.Add(driveData);
    }

    /// <summary>
    /// Extrait les statistiques réseau (Upload/Download en Ko/s)
    /// </summary>
    private void ExtractNetworkStats(IHardware hardware, HardwareStats stats)
    {
        foreach (var sensor in hardware.Sensors)
        {
            if (sensor.Value.HasValue)
            {
                // Vitesse d'envoi (Upload)
                if (sensor.SensorType == SensorType.Throughput && 
                    sensor.Name.Contains("Upload", StringComparison.OrdinalIgnoreCase))
                {
                    // Conversion de bytes/s vers Ko/s
                    stats.Network.UploadSpeed += sensor.Value.Value / 1024f;
                }
                
                // Vitesse de réception (Download)
                if (sensor.SensorType == SensorType.Throughput && 
                    sensor.Name.Contains("Download", StringComparison.OrdinalIgnoreCase))
                {
                    // Conversion de bytes/s vers Ko/s
                    stats.Network.DownloadSpeed += sensor.Value.Value / 1024f;
                }
            }
        }
    }

    /// <summary>
    /// Libère les ressources du Computer
    /// </summary>
    public void Dispose()
    {
        try
        {
            _semaphore?.Dispose();
            _computer?.Close();
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"Erreur lors de la fermeture des ressources: {ex.Message}");
        }
    }
}