namespace hwMonitor.Models;

/// <summary>
/// Modèle représentant les statistiques matérielles du système
/// </summary>
public class HardwareStats
{
    // === CPU ===
    public string CpuName { get; set; } = "N/A";
    public float CpuLoad { get; set; } = 0f;
    public float CpuTemp { get; set; } = 0f;
    public float CpuPower { get; set; } = 0f;  // Consommation en Watts
    public float CpuClockSpeed { get; set; } = 0f;  // Fréquence en MHz
    
    // === GPUs (Liste pour iGPU + dGPU) ===
    public List<GpuData> Gpus { get; set; } = new();
    
    // === RAM ===
    public float RamUsed { get; set; } = 0f;
    public float RamTotal { get; set; } = 0f;
    public float RamUsedPercent { get; set; } = 0f;
    
    // === Stockage (Liste pour plusieurs disques) ===
    public List<DriveData> Drives { get; set; } = new();
    
    // === Réseau ===
    public NetworkData Network { get; set; } = new();
    
    public DateTime Timestamp { get; set; } = DateTime.UtcNow;
}

/// <summary>
/// Données d'un GPU (iGPU ou dGPU)
/// </summary>
public class GpuData
{
    public string Name { get; set; } = "N/A";
    public float Load { get; set; } = 0f;  // Charge en %
    public float Temperature { get; set; } = 0f;  // Température en °C
    public float MemoryUsed { get; set; } = 0f;  // Mémoire utilisée en Mo
    public float MemoryTotal { get; set; } = 0f;  // Mémoire totale en Mo
    public float FanSpeed { get; set; } = 0f;  // Vitesse ventilateur en %
    public float Power { get; set; } = 0f;  // Consommation en Watts
}

/// <summary>
/// Données d'un disque dur/SSD
/// </summary>
public class DriveData
{
    public string Name { get; set; } = "N/A";
    public float UsedSpace { get; set; } = 0f;  // Espace utilisé en Go
    public float TotalSpace { get; set; } = 0f;  // Espace total en Go
    public float UsedPercent { get; set; } = 0f;  // Pourcentage d'utilisation
    public float? Temperature { get; set; } = null;  // Température (nullable car pas toujours dispo)
}

/// <summary>
/// Statistiques réseau (Upload/Download)
/// </summary>
public class NetworkData
{
    public float UploadSpeed { get; set; } = 0f;  // Vitesse d'envoi en Ko/s
    public float DownloadSpeed { get; set; } = 0f;  // Vitesse de réception en Ko/s
}