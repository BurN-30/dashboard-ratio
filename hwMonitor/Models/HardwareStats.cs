using System.Collections.Generic;

namespace hwMonitor.Models;

public class HardwareStats
{
    public string OsName { get; set; } = string.Empty;
    public string Uptime { get; set; } = string.Empty;

    // === CPU ===
    public string CpuName { get; set; } = string.Empty;
    public float CpuLoad { get; set; } = 0f;          // %
    public float CpuTemp { get; set; } = 0f;          // °C
    public float CpuPower { get; set; } = 0f;         // Watts
    public float CpuClockSpeed { get; set; } = 0f;    // MHz
    public float CpuFanSpeed { get; set; } = 0f;      // RPM (Nouveau !)
    public List<float> CpuCoreLoads { get; set; } = new List<float>();

    // === GPUs ===
    public List<GpuData> Gpus { get; set; } = new List<GpuData>();

    // === RAM ===
    public float RamUsed { get; set; } = 0f;          // GB
    public float RamTotal { get; set; } = 0f;         // GB
    public float RamUsedPercent { get; set; } = 0f;   // %

    // === Stockage ===
    public List<DriveData> Drives { get; set; } = new List<DriveData>();

    // === Réseau ===
    public NetworkData Network { get; set; } = new NetworkData();

    public string Timestamp { get; set; } = string.Empty;
    public List<ProcessData> TopProcesses { get; set; } = new List<ProcessData>();
}

public class GpuData
{
    public string Name { get; set; } = string.Empty;
    public float Load { get; set; } = 0f;             // %
    public float Temperature { get; set; } = 0f;      // °C
    public float MemoryUsed { get; set; } = 0f;       // MB
    public float MemoryTotal { get; set; } = 0f;      // MB
    public float FanSpeed { get; set; } = 0f;         // % ou RPM
    public float Power { get; set; } = 0f;            // Watts
}

public class DriveData
{
    public string Name { get; set; } = string.Empty;
    public string Mount { get; set; } = string.Empty; // Lettre (C:\)
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
    public string Name { get; set; } = string.Empty;
    public int Id { get; set; }
    public float MemoryUsedMb { get; set; }
}