using hwMonitor.Models;

namespace hwMonitor.Services;

/// <summary>
/// Interface définissant le contrat du service de monitoring matériel
/// </summary>
public interface IHardwareMonitorService : IDisposable
{
    /// <summary>
    /// Récupère les statistiques matérielles actuelles
    /// </summary>
    Task<HardwareStats> GetHardwareStatsAsync();
}