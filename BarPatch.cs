using System.Reflection;
using HarmonyLib;
using Meitou.Modding;
using Meitou.Simulation;

namespace OperatingTables;

/// <summary>
/// The progress bar over a working surgeon, as the game shows one over a character picking a lock: a postfix on the character publish step that
/// fills the snapshot's bar (<c>World.FillInteraction</c>, private, found by name; the bar's setter is internal). A missing member is logged and
/// leaves the bar out.
/// </summary>
static class BarPatch
{
    /// <summary>
    /// The bar's caption.
    /// </summary>
    public const string Caption = "Surgery";

    /// <summary>
    /// The snapshot's <c>Bar</c> setter.
    /// </summary>
    static MethodInfo? s_setBar;

    /// <summary>
    /// Patches the publish step.
    /// </summary>
    public static void Apply(ModContext context)
    {
        var fill = AccessTools.Method(typeof(World), "FillInteraction");
        s_setBar = AccessTools.PropertySetter(typeof(CharacterSnapshot), nameof(CharacterSnapshot.Bar));
        if (fill is null || s_setBar is null)
        {
            context.LogError("the character publish step was not found: no surgery progress bar (the game changed; rebuild the mod)");
            return;
        }

        context.Harmony.Patch(fill, postfix: new HarmonyMethod(typeof(BarPatch), nameof(Postfix)));
    }

    /// <summary>
    /// A surgeon at work gets the bar, its fill the progress through the current amputation.
    /// </summary>
    static void Postfix(CharacterSnapshot s)
    {
        if (SurgerySystem.Progress.TryGetValue(s.Id, out float progress)) s_setBar!.Invoke(s, [new TaskBar(Caption, progress)]);
    }
}
