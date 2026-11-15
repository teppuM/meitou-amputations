using System.Numerics;
using System.Reflection;
using HarmonyLib;
using Meitou.Game.Ui;
using Meitou.Modding;
using Meitou.Simulation;

namespace OperatingTables;

/// <summary>
/// The "Surgery..." row and its menu. The row goes on the right-click menu of the player's own character lying on an Operating Table or a Skeleton
/// Operating Bed while another character is selected (a postfix on <c>Meitou.Game.Ui.ContextMenuWindow.Verbs</c>, internal, found by name). It opens
/// the mod's menu in its place, drawn as the game draws its right-click menu, in the HUD's overlay slot: the patient's name, then Left Arm, Right Arm,
/// Left Leg, Right Leg (one limb per operation). A row whose limb is gone (stumps or prosthetics) has grey text and cannot be clicked;
/// a click elsewhere closes the menu. A row gives the nearest selected character other than the patient the operation.
/// </summary>
sealed class SurgeryMenu : IUiExtension
{
    #region The right-click row

    /// <summary>
    /// The row's caption.
    /// </summary>
    public const string Caption = "Surgery...";

    /// <summary>
    /// The right-click menu's player interface field (a captured primary-constructor parameter, so found by type), its selection read, its cursor
    /// and its session (for the world's beds).
    /// </summary>
    static FieldInfo? s_player, s_mouse, s_session;

    /// <summary>
    /// The player interface's selection read, <c>SelectedIds()</c>.
    /// </summary>
    static MethodInfo? s_selectedIds;

    /// <summary>
    /// The session's <c>CurrentSnapshot</c>.
    /// </summary>
    static PropertyInfo? s_snapshot;

    /// <summary>
    /// How near a bed's spot a character lying in it is, at most.
    /// </summary>
    const float BedNear = 40;

    /// <summary>
    /// Patches the right-click menu's verb list; a missing member is logged and leaves the menu alone.
    /// </summary>
    public static void Apply(ModContext context)
    {
        var window = AccessTools.TypeByName("Meitou.Game.Ui.ContextMenuWindow");
        var verbs = window is null ? null : AccessTools.Method(window, "Verbs", [typeof(CharacterSnapshot)]);
        s_player = window?.GetFields(BindingFlags.Instance | BindingFlags.NonPublic).FirstOrDefault(f => f.FieldType.Name == "PlayerInterface");
        s_selectedIds = s_player is null ? null : AccessTools.Method(s_player.FieldType, "SelectedIds");
        s_mouse = s_player is null ? null : AccessTools.Field(s_player.FieldType, "Mouse");
        s_session = s_player is null ? null : AccessTools.Field(s_player.FieldType, "Session");
        s_snapshot = s_session is null ? null : AccessTools.Property(s_session.FieldType, "CurrentSnapshot");
        if (verbs is null || s_selectedIds is null || s_snapshot is null)
        {
            context.LogError("the right-click menu was not found: no Surgery row (the game changed; rebuild the mod)");
            return;
        }

        context.Harmony.Patch(verbs, postfix: new HarmonyMethod(typeof(SurgeryMenu), nameof(Postfix)));
    }

    /// <summary>
    /// Adds the row to the player's own character lying on one of the mod's tables, while a character other than it is selected.
    /// </summary>
    static void Postfix(object __instance, CharacterSnapshot target, List<(string, Action)> __result)
    {
        if (!target.IsPlayer || !target.InBed || target.Body is { Dead: true }) return;
        var player = s_player?.GetValue(__instance);
        if (player is null || s_selectedIds?.Invoke(player, null) is not IReadOnlyList<CharacterId> selection) return;
        if (!selection.Any(id => id != target.Id) || !OnTable(player, target)) return;

        var at = s_mouse?.GetValue(player) is Vector2 mouse ? mouse : default;
        __result.Add((Caption, () => Show([.. selection.Where(id => id != target.Id)], target, at)));
    }

    /// <summary>
    /// Whether <paramref name="target"/> lies on one of the mod's tables: the nearest bed spot to it is one.
    /// </summary>
    static bool OnTable(object player, CharacterSnapshot target)
    {
        if (s_session?.GetValue(player) is not { } session || s_snapshot?.GetValue(session) is not WorldSnapshot snapshot) return false;
        var bed = snapshot.Beds.MinBy(b => Vector3.DistanceSquared(b.Position, target.Position));
        return bed is not null && Vector3.Distance(bed.Position, target.Position) <= BedNear
            && bed.Record is SurgerySystem.TableRecord or SurgerySystem.SkeletonBedRecord;
    }

    #endregion

    #region The menu

    /// <summary>
    /// The rows: caption and the limb slots it cuts (bit k for limb slot k: 0 left arm, 1 right arm, 2 left leg, 3 right leg).
    /// </summary>
    internal static readonly (string Caption, int Limbs)[] Rows =
    [
        ("Left Arm", 1), ("Right Arm", 2), ("Left Leg", 4), ("Right Leg", 8),
    ];

    /// <summary>
    /// The right-click menu's text colour, and a gone row's (the game dims only a disabled button's background, and these have none).
    /// </summary>
    static readonly Vector4 Ink = new(0.86f, 0.82f, 0.71f, 1), Gone = new(0.45f, 0.43f, 0.4f, 1);

    /// <summary>
    /// An open menu: the surgeons to choose from, the patient, its name, the limbs it still has (bits as in <see cref="Rows"/>), and where the
    /// right-click menu was.
    /// </summary>
    sealed record Open(IReadOnlyList<CharacterId> Surgeons, CharacterId Patient, string Title, int Present, Vector2 At, Vector3 PatientAt,
        IReadOnlyList<Vector3> SurgeonsAt);

    /// <summary>
    /// The open menu, null when closed. Set and read on the interface's thread.
    /// </summary>
    static Open? s_open;

    /// <summary>
    /// The extension's id (its registrations' prefix).
    /// </summary>
    public string Id => "operating-tables";

    /// <summary>
    /// Opens the menu for <paramref name="patient"/> in place of the right-click menu that was at <paramref name="at"/>.
    /// </summary>
    static void Show(IReadOnlyList<CharacterId> surgeons, CharacterSnapshot patient, Vector2 at) =>
        s_open = new(surgeons, patient.Id, patient.Name, Present(patient.LimbBits), at, patient.Position, []);

    /// <summary>
    /// The limbs that can still be cut off: each limb slot whose state (2 bits of <paramref name="limbBits"/>) is the original (0) or crushed (3),
    /// not a stump (1) or a prosthetic (2).
    /// </summary>
    static int Present(int limbBits)
    {
        int present = 0;
        for (int k = 0; k < 4; k++)
            if (((limbBits >> (2 * k)) & 3) is 0 or 3) present |= 1 << k;
        return present;
    }

    /// <summary>
    /// Registers the styles, the two actions (a row picked, a click outside) and the menu's contribution to the overlay.
    /// </summary>
    public void Register(UiRegistration registration)
    {
        string panel = registration.RegisterStyle("panel", new UiStyle
        {
            Skin = "Kenshi_FloatingPanelSkin", Background = new(0.1f, 0.09f, 0.08f, 0.94f), Text = Ink,
        });
        string title = registration.RegisterStyle("title", new UiStyle { Text = Ink, TextAlign = "Center", FontName = "Kenshi_StandardFont_Medium" });
        var buttonStyle = new UiStyle { Skin = "Kenshi_Button1Skin", Text = Ink, TextAlign = "Center", FontName = "Kenshi_PaintedTextFont_Medium" };
        string button = registration.RegisterStyle("button", buttonStyle);
        string gone = registration.RegisterStyle("gone", buttonStyle with { Text = Gone });
        string backdrop = registration.RegisterStyle("backdrop", new UiStyle());
        string pick = registration.RegisterAction("pick", c => Pick(c.Argument));
        string close = registration.RegisterAction("close", _ => s_open = null);
        var ids = new Ids(registration.Key("backdrop"), registration.Key("menu"), registration.Key("title"),
            [.. Rows.Select((_, i) => registration.Key($"row-{i}"))]);

        registration.Contribute(UiSlots.Overlay, frame => Build(frame, ids, new(panel, title, button, gone, backdrop, pick, close)), order: 1000);
    }

    /// <summary>
    /// The node ids.
    /// </summary>
    sealed record Ids(string Backdrop, string Menu, string Title, string[] Rows);

    /// <summary>
    /// The style and action keys.
    /// </summary>
    sealed record Keys(string Panel, string Title, string Button, string Gone, string Backdrop, string Pick, string Close);

    /// <summary>
    /// The menu as the game lays its right-click menu out (an eighth of the screen wide, the title 47.3 % of a 0.0685-screen row pair, one option per
    /// row, beside the cursor and kept on screen), over a clear panel that closes it on a click elsewhere; nothing while closed.
    /// </summary>
    static UiNode Build(UiFrameContext frame, Ids ids, Keys keys)
    {
        if (s_open is not { } open) return new UiNode(ids.Backdrop) { Visible = false };

        var view = frame.Viewport;
        float w = MathF.Max(200, view.Width * 0.125f), full = MathF.Max(64, view.Height * 0.0685185f);
        float titleH = full * 0.472973f, optionH = full - titleH, h = titleH + optionH * Rows.Length + 6;
        float x = Math.Clamp(open.At.X + 12, 0, Math.Max(0, view.Width - w)), y = Math.Clamp(open.At.Y, 0, Math.Max(0, view.Height - h));

        var menu = new UiNode(ids.Menu) { Placement = new(w, h, x, y), Style = keys.Panel };
        menu.Children.Add(new UiNode(ids.Title, UiNodeKind.Label) { Placement = new(w - 12, titleH, 6, 2), Style = keys.Title, Text = open.Title });
        for (int i = 0; i < Rows.Length; i++)
        {
            bool available = (Rows[i].Limbs & open.Present) != 0;
            menu.Children.Add(new UiNode(ids.Rows[i], UiNodeKind.Button)
            {
                Placement = new(w * (1 - 2 * 0.0208333f), optionH * 0.897436f, w * 0.0208333f, titleH + i * optionH + optionH * 0.0512821f),
                Style = available ? keys.Button : keys.Gone,
                Text = Rows[i].Caption,
                Action = keys.Pick,
                Argument = i.ToString(System.Globalization.CultureInfo.InvariantCulture),
                Enabled = available,
            });
        }

        var root = new UiNode(ids.Backdrop) { Style = keys.Backdrop, Action = keys.Close };
        root.Children.Add(menu);
        return root;
    }

    /// <summary>
    /// A row picked: the menu closes and the first selected character other than the patient gets the operation.
    /// </summary>
    static void Pick(string argument)
    {
        var open = s_open;
        s_open = null;
        if (open is null || !int.TryParse(argument, out int i) || i < 0 || i >= Rows.Length || open.Surgeons.Count == 0) return;
        if (OperatingTablesMod.Context is not { } context) return;

        context.Enqueue(new SurgeryOrder(open.Surgeons[0], open.Patient) { Tick = context.Tick, Limbs = Rows[i].Limbs });
    }

    #endregion
}
