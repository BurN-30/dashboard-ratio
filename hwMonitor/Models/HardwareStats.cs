namespace hwMonitor.Models;

public class HardwareStats
{

    public string OsName { get; set; } = "Unknown OS";
    public string Uptime { get; set; } = "00:00:00"; // Format string pour l'affichage direct
    // === CPU ===
    public string CpuName { get; set; } = "N/A";
    public float CpuLoad { get; set; } = 0f;          // %
    public float CpuTemp { get; set; } = 0f;          // °C
    public float CpuPower { get; set; } = 0f;         // Watts
    public float CpuClockSpeed { get; set; } = 0f;    // MHz
    public float CpuFanSpeed { get; set; } = 0f;      // RPM (Nouveau !)

    // === GPUs ===
    public List<GpuData> Gpus { get; set; } = new();

    // === RAM ===
    public float RamUsed { get; set; } = 0f;          // GB
    public float RamTotal { get; set; } = 0f;         // GB
    public float RamUsedPercent { get; set; } = 0f;   // %

    // === Stockage ===
    public List<DriveData> Drives { get; set; } = new();

    // === Réseau ===
    public NetworkData Network { get; set; } = new();

    public DateTime Timestamp { get; set; } = DateTime.UtcNow;
    public List<ProcessData> TopProcesses { get; set; } = new();
}
public class GpuData
{
    public string Name { get; set; } = "N/A";
    public float Load { get; set; } = 0f;             // %
    public float Temperature { get; set; } = 0f;      // °C
    public float MemoryUsed { get; set; } = 0f;       // MB
    public float MemoryTotal { get; set; } = 0f;      // MB
    public float FanSpeed { get; set; } = 0f;         // % ou RPM
    public float Power { get; set; } = 0f;            // Watts
}

public class DriveData
{
    public string Name { get; set; } = "N/A";
    public string Mount { get; set; } = "";           // Lettre (C:\)
    public float UsedSpace { get; set; } = 0f;        // GB
    public float TotalSpace { get; set; } = 0f;       // GB
    public float UsedPercent { get; set; } = 0f;      // %
    public float? Temperature { get; set; } = null;   // °C
}

public class NetworkData
{
    public float UploadSpeed { get; set; } = 0f;      // Mbps (Megabits/s)
    public float DownloadSpeed { get; set; } = 0f;    // Mbps (Megabits/s)
}

public class ProcessData
{
    public string Name { get; set; }
    public int Id { get; set; }
    public float MemoryUsedMb { get; set; }
}