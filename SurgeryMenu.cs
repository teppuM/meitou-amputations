using System.Numerics;
using Meitou.Game.Ui;
using Meitou.Simulation;

namespace OperatingTables;

/// <summary>
/// The "Amputate..." row and its menu. The row goes on the right-click menu of the player's own character lying on an Operating Table or a Skeleton
/// Operating Bed while another character is selected (the game's right-click row hook, <c>AddCharacterMenuVerbs</c>). It opens the mod's menu in
/// its place, drawn as the game draws its right-click menu, in the HUD's overlay slot: the patient's name, then Left Arm, Right Arm, Left Leg, Right
/// Leg (one limb per operation). A row whose limb is gone (stumps or prosthetics) has grey text and cannot be clicked; a click elsewhere closes the
/// menu. A row gives the first selected character other than the patient the operation.
/// </summary>
sealed class SurgeryMenu : IUiExtension
{
    #region The right-click row

    /// <summary>
    /// The row's caption.
    /// </summary>
    public const string Caption = "Amputate...";

    /// <summary>
    /// No rows: the plain right click stays.
    /// </summary>
    static readonly UiMenuVerb[] None = [];

    /// <summary>
    /// The row, for the player's own living character lying on one of the mod's tables (as the surgery system last published), while a character
    /// other than it is selected. Runs whenever the game asks for the menu, so it only reads the snapshot and the published set.
    /// </summary>
    static IEnumerable<UiMenuVerb> Verbs(UiMenuContext context)
    {
        var target = context.Target;
        if (!target.IsPlayer || !target.InBed || target.Body is { Dead: true } || !SurgerySystem.OnTables.Contains(target.Id)) return None;
        if (!context.Selected.Any(id => id != target.Id)) return None;

        return [new UiMenuVerb(Caption, () => Show([.. context.Selected.Where(id => id != target.Id)], target, context))];
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
    sealed record Open(IReadOnlyList<CharacterId> Surgeons, CharacterId Patient, string Title, int Present, Vector2 At, UiMenuContext Menu);

    /// <summary>
    /// The open menu, null when closed. Set and read on the interface's thread.
    /// </summary>
    static Open? s_open;

    /// <summary>
    /// The extension's id (its registrations' prefix).
    /// </summary>
    public string Id => "operating-tables";

    /// <summary>
    /// Opens the menu for <paramref name="patient"/> in place of the right-click menu <paramref name="menu"/> was built for (at its cursor).
    /// </summary>
    static void Show(IReadOnlyList<CharacterId> surgeons, CharacterSnapshot patient, UiMenuContext menu) =>
        s_open = new(surgeons, patient.Id, patient.Name, Present(patient.LimbBits), menu.Cursor, menu);

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
    /// Registers the right-click row, the styles, the two actions (a row picked, a click outside) and the menu's contribution to the overlay.
    /// </summary>
    public void Register(UiRegistration registration)
    {
        registration.AddCharacterMenuVerbs(Verbs);
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

        open.Menu.Enqueue(new SurgeryOrder(open.Surgeons[0], open.Patient) { Tick = open.Menu.Tick, Limbs = Rows[i].Limbs });
    }

    #endregion
}
