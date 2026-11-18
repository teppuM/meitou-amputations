using Meitou.Modding;
using Meitou.Simulation;

namespace OperatingTables;

/// <summary>
/// The mod's entry: registers the operations, the "Amputate..." right-click row and its menu. The Operating Table, the Skeleton Operating Bed and
/// their research come from the mod's data file (OperatingTables.mod).
/// </summary>
public sealed class OperatingTablesMod : IMod
{
    /// <summary>
    /// Registers the operation system (after every standard system), the menu row and the menu.
    /// </summary>
    public void Initialize(ModContext context)
    {
        context.AddSystem("surgery", SurgerySystem.Create, SystemAnchor.End);
        context.AddUi(new SurgeryMenu());
        context.AddDebugCommand("Operating Tables: first selected operates on the second (limb 1, 2, 4 or 8)", Operate, hasField: true);
        context.AddDebugCommand("Operating Tables: selected lie on the nearest table", d =>
        {
            d.Enqueue(new LieOnTable(d.Selected) { Tick = d.Tick });
            return "sent to the nearest table";
        });
    }

    /// <summary>
    /// The debug row: the first selected character operates on the second, cutting the limb the field names (1 left arm, 2 right arm, 4 left leg, 8 right leg; empty: the left arm).
    /// </summary>
    static string Operate(DebugCommandContext d)
    {
        if (d.Selected.Count < 2) return "select the surgeon, then the patient";
        int limbs = 1;
        if (d.Field.Length > 0 && (!int.TryParse(d.Field, out limbs) || limbs is < 1 or > 15)) return "type the limb: 1 left arm, 2 right arm, 4 left leg, 8 right leg (empty: left arm)";
        d.Enqueue(new SurgeryOrder(d.Selected[0], d.Selected[1]) { Tick = d.Tick, Limbs = limbs });
        return "operation ordered";
    }
}
