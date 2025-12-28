using LibreHardwareMonitor.Hardware;

namespace hwMonitor.Visitors;

/// <summary>
/// Visiteur nécessaire pour mettre à jour les valeurs des capteurs matériels
/// Implémentation requise par LibreHardwareMonitor
/// </summary>
public class UpdateVisitor : IVisitor
{
    public void VisitComputer(IComputer computer)
    {
        computer.Traverse(this);
    }

    public void VisitHardware(IHardware hardware)
    {
        hardware.Update();
        foreach (IHardware subHardware in hardware.SubHardware)
        {
            subHardware.Accept(this);
        }
    }

    public void VisitSensor(ISensor sensor) { }

    public void VisitParameter(IParameter parameter) { }
}