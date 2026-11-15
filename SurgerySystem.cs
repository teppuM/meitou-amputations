using System.Numerics;
using Meitou.Data.Gameplay.Ai;
using Meitou.Data.Gameplay.Bodies;
using Meitou.Simulation;
using Meitou.Simulation.Ai;
using Meitou.Simulation.Bodies;
using Meitou.Simulation.Locks;
using Meitou.Simulation.Movement;
using Meitou.Simulation.Player;

namespace OperatingTables;

/// <summary>
/// An operation: <paramref name="Surgeon"/> cuts the limbs <see cref="Limbs"/> off <paramref name="Patient"/>, who lies on an Operating Table or a
/// Skeleton Operating Bed. Bits as in <see cref="SurgeryMenu.Rows"/>: bit k for limb slot k (0 left arm, 1 right arm, 2 left leg, 3 right leg).
/// </summary>
public sealed record SurgeryOrder(CharacterId Surgeon, CharacterId Patient) : OrderCommand
{
    /// <summary>
    /// The limbs to cut off.
    /// </summary>
    public int Limbs { get; init; }
}

/// <summary>
/// The debug menu's test row: each of <paramref name="Characters"/> is ordered into the nearest of the mod's tables (within 200 units).
/// </summary>
public sealed record LieOnTable(IReadOnlyList<CharacterId> Characters) : OrderCommand;

/// <summary>
/// Operations: the surgeon walks to the patient's table and works on one limb at a time with the medic clip, <see cref="OperateSeconds"/> each. Each
/// amputation turns the limb into a stump, drops the cut-off limb as the game's own cut does, and takes a share of the patient's blood (oil for a
/// skeleton) set by the surgeon's skill: First Aid on the Operating Table, Robotics on the Skeleton Operating Bed. The share falls from
/// <see cref="CostAtZero"/> at skill 0 to <see cref="CostAtFull"/> at 100; a botch, likelier the less skilled the surgeon, multiplies it by
/// <see cref="BotchMultiplier"/>. The cost replaces the game's own limb-loss bleeding: the surgeon closes the stump, so no wound is left. The
/// surgeon gains skill experience per limb, the patient toughness as for any lost limb. Another order or Stop ends it; an operation under way is
/// not saved.
/// </summary>
public sealed class SurgerySystem : ITickSystem, IOrderOwner, ITaskOwner, ITaskHandler
{
    #region Setup

    /// <summary>
    /// The order's task row: a mod number, outside the game's own rows (never saved, as the order is not).
    /// </summary>
    public const TaskType Row = (TaskType)1181;

    /// <summary>
    /// The clip the surgeon works in.
    /// </summary>
    public const string Clip = "medic";

    /// <summary>
    /// The two tables' BUILDING records (the mod's data file).
    /// </summary>
    public const string TableRecord = "1-OperatingTables.mod", SkeletonBedRecord = "2-OperatingTables.mod";

    /// <summary>
    /// The share of the patient's blood capacity one amputation costs at surgeon skill 0 and 100, the botch chance at the two, and what a botch
    /// multiplies the cost by.
    /// </summary>
    public const float CostAtZero = 0.6f, CostAtFull = 0.2f, BotchAtZero = 0.9f, BotchAtFull = 0.05f, BotchMultiplier = 2.5f;

    /// <summary>
    /// How long one amputation takes, seconds.
    /// </summary>
    public const float OperateSeconds = 6;

    /// <summary>
    /// The surgeon's skill experience per amputation (a per-event factor, as the game's XP events use).
    /// </summary>
    public const float SkillXpFactor = 20;

    /// <summary>
    /// How near the patient the surgeon must stand, and how far beside it the walk aims; walks tried before giving up.
    /// </summary>
    public const float Reach = 20, StandOff = 10;

    /// <summary>
    /// Walks tried before the surgeon gives up on reaching the table.
    /// </summary>
    public const int MaxWalks = 3;

    /// <summary>
    /// The operations under way, in the order they began.
    /// </summary>
    readonly List<Operation> _operations = [];

    /// <summary>
    /// The world's game constants and body options (for the patient's blood capacity), and the experience rules.
    /// </summary>
    readonly XpService _xp;

    /// <summary>
    /// The limbs of the order being started (<see cref="IOrderOwner.Start"/> hands them to the task's start, which makes the operation).
    /// </summary>
    int _startLimbs;

    /// <summary>
    /// Set while the walk hands over to the work, so the walk's end does not drop the operation.
    /// </summary>
    bool _switching;

    /// <summary>
    /// One operation.
    /// </summary>
    sealed class Operation
    {
        public CharacterId Surgeon;
        public CharacterId Patient;
        public int Limbs;
        public bool Working;
        public float Time;
        public int Walks;
        public Vector2 Goal;
        public Vector3 Stand;
    }

    SurgerySystem(XpService xp) => _xp = xp;

    /// <summary>
    /// The factory the mod registers.
    /// </summary>
    public static ITickSystem Create(SystemBuildContext context) =>
        new SurgerySystem(new XpService(context.Data.Bodies.Constants, context.Data.BodyOptions));

    /// <summary>
    /// Registers the row's act-out with this system.
    /// </summary>
    public void RegisterTasks(TaskHandlers tasks) => tasks.Register(Row, this);

    #endregion

    #region Who may operate on whom

    /// <summary>
    /// The table <paramref name="patient"/> lies on, when it is one of the mod's: the Operating Table for a flesh patient, the Skeleton Operating
    /// Bed for a robot one; null otherwise (not in a bed, an ordinary bed, or the other kind's table).
    /// </summary>
    static Fixture? TableOf(World world, CharacterCold? patient)
    {
        if (patient is not { InSomething: HeldState.Bed, InWhat: { } bedId, Race: { } race, Medical.Dead: false }) return null;
        if (world.Fixtures.Find(bedId) is not { } bed) return null;
        return bed.RecordId == (race.IsRobot ? SkeletonBedRecord : TableRecord) ? bed : null;
    }

    /// <summary>
    /// A character who can operate: the player's, awake, hands free, not carried or caged.
    /// </summary>
    static bool CanOperate(CharacterCold? s) =>
        s is { IsPlayer: true, Medical.Incapacitated: false, Stats: not null, Race: not null } && s.Carrying.IsNone && s.CarriedBy.IsNone
        && !s.IsImprisoned;

    /// <summary>
    /// The skill an operation on <paramref name="patient"/> uses: Robotics on a skeleton, First Aid (Medic) on anyone else.
    /// </summary>
    static StatsEnumerated SkillFor(CharacterCold patient) => patient.Race!.IsRobot ? StatsEnumerated.Robotics : StatsEnumerated.Medic;

    #endregion

    #region Orders

    /// <summary>
    /// Takes the tick's operation orders.
    /// </summary>
    public void Inputs(World world, IReadOnlyList<SimCommand> commands)
    {
        foreach (var command in commands)
        {
            if (command is SurgeryOrder order) Begin(world, order);
            if (command is LieOnTable lie) SendToTables(world, lie);
        }
    }

    /// <summary>
    /// The test row: each character gets the game's own bed order for the nearest of the mod's tables within 200 units.
    /// </summary>
    static void SendToTables(World world, LieOnTable lie)
    {
        foreach (var id in lie.Characters)
        {
            if (!world.Characters.TryResolveNext(id, out int c)) continue;
            var at = world.Characters.Next[c].Position;
            var bed = world.Fixtures.All
                .Where(f => f.RecordId is TableRecord or SkeletonBedRecord && Vector3.Distance(f.Position, at) < 200)
                .MinBy(f => Vector3.Distance(f.Position, at));
            if (bed is not null) world.Defer(new UseBedOrder([id], bed.Id) { Tick = world.Tick + 1 });
        }
    }

    /// <summary>
    /// Gives the order to the surgeon when the patient lies on the right table; else the surgeon says why not.
    /// </summary>
    void Begin(World world, SurgeryOrder order)
    {
        var table = world.Characters;
        if (!table.TryResolveNext(order.Surgeon, out int s) || !table.TryResolveNext(order.Patient, out int p) || s == p) return;
        if (TableOf(world, table.Cold(p)) is null)
        {
            world.Bark(order.Surgeon, table.Cold(p)!.Race?.IsRobot == true ? "A skeleton needs the Skeleton Operating Bed." : "They need to be on an Operating Table.");
            return;
        }

        var entry = new OrderEntry(Row, this) { Target = order.Patient, Detail = order.Limbs };
        if (PlayerOrders.CanRun(world, s, entry).CanRun) PlayerOrders.Give(world, s, entry, order.Queued);
    }

    /// <summary>
    /// The order runs while the patient lies on the right table (else it leaves the queue) and the surgeon is fit (else it waits).
    /// </summary>
    OrderCheck IOrderOwner.CanRun(World world, int slot, OrderEntry order)
    {
        var table = world.Characters;
        if (!table.TryResolveNext(order.Target, out int p) || TableOf(world, table.Cold(p)) is null) return OrderCheck.Gone;
        return CanOperate(table.Cold(slot)) ? OrderCheck.Run : OrderCheck.Blocked();
    }

    /// <summary>
    /// Starts the walk to the patient (the order's limbs go with it).
    /// </summary>
    void IOrderOwner.Start(World world, int slot, OrderEntry order)
    {
        _startLimbs = order.Detail is int limbs ? limbs : 0;
        TaskStart.Start(world, slot, new TaskRequest(CharacterTask.GoTo, Row, TaskSource.Order) { Target = order.Target });
        _startLimbs = 0;
    }

    /// <summary>
    /// A running operation stops when the patient leaves the table.
    /// </summary>
    bool IOrderOwner.StillHolds(World world, int slot, OrderEntry order) =>
        world.Characters.TryResolveNext(order.Target, out int p) && TableOf(world, world.Characters.Cold(p)) is not null;

    /// <summary>
    /// Never saved: a loaded game has no operation under way.
    /// </summary>
    int IOrderOwner.SaveKind(OrderEntry order) => -1;

    #endregion

    #region Task

    /// <summary>
    /// The walk's start makes the operation and sets off; the work's start stands the surgeon still with the clip.
    /// </summary>
    void ITaskHandler.Start(World world, int slot, in TaskRequest request)
    {
        var table = world.Characters;
        if (request.Task == CharacterTask.Idle)
        {
            MovementSystem.Stop(table, slot);
            table.Cold(slot)!.ActionClip = Clip;
            return;
        }

        var surgeon = table.IdOf(slot);
        _operations.RemoveAll(o => o.Surgeon == surgeon);
        var op = new Operation { Surgeon = surgeon, Patient = request.Target, Limbs = _startLimbs };
        _operations.Add(op);
        if (table.TryResolveNext(request.Target, out int p)) Walk(world, slot, p, op);
    }

    /// <summary>
    /// Another order, Stop, or the end: the operation goes and the clip with it (not while the walk hands over to the work).
    /// </summary>
    void ITaskHandler.End(World world, int slot, CharacterTask task, TaskEnd reason)
    {
        if (_switching) return;
        Drop(world.Characters, slot);
    }

    /// <summary>
    /// The task is done once its operation is gone.
    /// </summary>
    bool ITaskHandler.Done(World world, int slot, CharacterTask task)
    {
        var surgeon = world.Characters.IdOf(slot);
        return world.Characters.Next[slot].Task != (byte)task || !_operations.Exists(o => o.Surgeon == surgeon);
    }

    /// <summary>
    /// Forgets the slot's operation and clears its clip.
    /// </summary>
    void Drop(CharacterTable table, int slot)
    {
        var surgeon = table.IdOf(slot);
        _operations.RemoveAll(o => o.Surgeon == surgeon);
        if (table.Cold(slot) is { } c && c.ActionClip == Clip) c.ActionClip = null;
    }

    /// <summary>
    /// Ends the operation: it goes and, while its task still runs, the task ends as done.
    /// </summary>
    void Finish(World world, int s)
    {
        var table = world.Characters;
        bool running = table.Cold(s)!.Running is { Row: Row };
        Drop(table, s);
        if (running) TaskStart.End(world, s, TaskEnd.Done);
    }

    #endregion

    #region Each tick

    /// <summary>
    /// Advances every operation: the walk until beside the table, then the work, one limb per <see cref="OperateSeconds"/>.
    /// </summary>
    public void SlowWorld(World world)
    {
        for (int k = _operations.Count - 1; k >= 0; k--)
        {
            if (k >= _operations.Count) continue;
            Step(world, _operations[k]);
        }
    }

    /// <summary>
    /// One tick of one operation.
    /// </summary>
    void Step(World world, Operation op)
    {
        var table = world.Characters;
        if (!table.TryResolveNext(op.Surgeon, out int s))
        {
            _operations.Remove(op);
            return;
        }
        if (!CanOperate(table.Cold(s)) || !table.TryResolveNext(op.Patient, out int p) || TableOf(world, table.Cold(p)) is null)
        {
            Finish(world, s);
            return;
        }

        if (op.Working) Work(world, op, s, p);
        else
            Approach(world, op, s, p);
    }

    /// <summary>
    /// The walk: beside the patient the work starts; a walk that ended short is tried again, then given up.
    /// </summary>
    void Approach(World world, Operation op, int s, int p)
    {
        var table = world.Characters;
        ref var n = ref table.Next[s];
        var patient = table.Next[p].Position;
        bool walking = n.Task == (byte)CharacterTask.GoTo;
        if (InReach(n.Position, patient) && (!walking || Vector2.Distance(Flat(n.Position), Flat(patient)) <= StandOff + 3))
        {
            StartWork(world, op, s);
            return;
        }

        bool moved = Vector2.Distance(op.Goal, Flat(patient)) > StandOff;
        if (walking && !moved) return;
        if (++op.Walks > MaxWalks)
        {
            world.Bark(op.Surgeon, "I can't get to the table.");
            Finish(world, s);
            return;
        }
        Walk(world, s, p, op);
    }

    /// <summary>
    /// The walk hands over to the work: the same order, now standing with the clip.
    /// </summary>
    void StartWork(World world, Operation op, int s)
    {
        var running = world.Characters.Cold(s)!.Running;
        var request = new TaskRequest(CharacterTask.Idle, Row, running?.Source ?? TaskSource.Order) { Target = op.Patient };
        _switching = true;
        try
        {
            TaskStart.Start(world, s, request);
        }
        finally
        {
            _switching = false;
        }

        op.Working = true;
        op.Time = 0;
        op.Stand = world.Characters.Next[s].Position;
    }

    /// <summary>
    /// The work: facing the patient, one amputation every <see cref="OperateSeconds"/>, the next chosen limb each time; done when none is left or the
    /// patient has died.
    /// </summary>
    void Work(World world, Operation op, int s, int p)
    {
        var table = world.Characters;
        ref var n = ref table.Next[s];
        if (n.Task != (byte)CharacterTask.Idle || table.Cold(s)!.Running is not { Row: Row } || !InReach(n.Position, table.Next[p].Position))
        {
            Finish(world, s);
            return;
        }
        n.Position = op.Stand;
        Face(ref n, table.Next[p].Position);

        var patient = table.Cold(p)!;
        if (NextLimb(patient.Medical!, ref op.Limbs) is null)
        {
            Finish(world, s);
            return;
        }
        op.Time += world.TickSeconds;
        if (op.Time < OperateSeconds) return;
        op.Time = 0;

        Amputate(world, s, p, NextLimb(patient.Medical!, ref op.Limbs)!);
        if (patient.Medical!.Dead || NextLimb(patient.Medical, ref op.Limbs) is null) Finish(world, s);
    }

    /// <summary>
    /// The next chosen limb still on (original or crushed), in slot order; the others leave <paramref name="limbs"/>. Null when none is left.
    /// </summary>
    static HealthPart? NextLimb(MedicalState medical, ref int limbs)
    {
        for (int k = 0; k < 4; k++)
        {
            if ((limbs & (1 << k)) == 0) continue;
            if (medical.LimbPart(k) is { Limb: LimbState.Original or LimbState.Crushed } part) return part;
            limbs &= ~(1 << k);
        }
        return null;
    }

    #endregion

    #region The amputation

    /// <summary>
    /// Cuts <paramref name="limb"/> off the patient: a stump with its limb dropped (the look and the item, as the game's own cut), the patient's
    /// toughness experience and cry, the blood (oil) the surgeon's skill and the botch roll set, with no wound left, and the surgeon's experience.
    /// </summary>
    void Amputate(World world, int s, int p, HealthPart limb)
    {
        var table = world.Characters;
        var surgeon = table.Cold(s)!;
        var patient = table.Cold(p)!;
        var medical = patient.Medical!;
        var stat = SkillFor(patient);
        float skill = Math.Clamp(surgeon.Stats![stat] * surgeon.Stats.Scale * surgeon.Medical!.StatMultiplier(stat), 0, 100) / 100;
        float share = CostAtZero + (CostAtFull - CostAtZero) * skill;
        bool botched = Roll(world, table.IdOf(p)) < BotchAtZero + (BotchAtFull - BotchAtZero) * skill;
        if (botched) share *= BotchMultiplier;

        int slot = limb.Template.LimbSlot;
        limb.Limb = LimbState.Stump;
        limb.Replacement = null;
        medical.Blood -= share * Capacity(patient);
        table.LimbsChanged.Enqueue((p, slot, true));
        _xp.ToughnessFromLimbLoss(patient.Stats!, patient.Race!);
        world.Defer(new Meitou.Simulation.Dialogue.DialogueEvent(table.IdOf(p), CharacterId.None, slot is 2 or 3 ? 70 : 71) { Tick = world.Tick + 1 });

        _xp.PerEvent(surgeon.Stats, surgeon.Race!, stat, SkillXpFactor);
        if (botched) world.Bark(table.IdOf(s), "Damn it. That went badly.");
    }

    /// <summary>
    /// The patient's blood capacity, as the game computes it (strength, the two body scales).
    /// </summary>
    static float Capacity(CharacterCold patient) =>
        MedicalState.BloodCapacity(patient.Race!, patient.Stats![StatsEnumerated.Strength], patient.Stats is not null, patient.Medical!.ScaleK,
            patient.Medical.ScaleZ);

    /// <summary>
    /// The botch roll, 0..1: from the world seed, the patient and the tick, so a replay rolls the same.
    /// </summary>
    static float Roll(World world, CharacterId patient) =>
        Rng.Float(Rng.Mix(world.Seed ^ Rng.Key(patient) * 0x9E3779B97F4A7C15UL ^ (ulong)world.Tick * 0xC2B2AE3D27D4EB4FUL ^ Rng.StableHash("operating-tables")));

    #endregion

    #region Geometry

    /// <summary>
    /// Sets off for a point beside the patient, on the side facing the surgeon, on the patient's floor.
    /// </summary>
    static void Walk(World world, int s, int p, Operation op)
    {
        var table = world.Characters;
        var from = table.Next[s].Position;
        var patient = table.Next[p].Position;
        var away = Flat(from) - Flat(patient);
        var dir = away.LengthSquared() > 1e-4f ? Vector2.Normalize(away) : Vector2.UnitX;
        var goal = new Vector3(patient.X + dir.X * StandOff, patient.Y, patient.Z + dir.Y * StandOff);
        MovementSystem.GoToFloor(world, s, goal, table.Cold(s)!.RunSpeed);
        op.Goal = Flat(patient);
    }

    /// <summary>
    /// Within <see cref="Reach"/> across the ground and on the same floor.
    /// </summary>
    static bool InReach(Vector3 at, Vector3 patient) =>
        Vector2.Distance(Flat(at), Flat(patient)) <= Reach && MathF.Abs(at.Y - patient.Y) <= MovementSystem.FloorSlack;

    /// <summary>
    /// The ground position (X/Z).
    /// </summary>
    static Vector2 Flat(Vector3 p) => new(p.X, p.Z);

    /// <summary>
    /// Turns the surgeon to face the patient.
    /// </summary>
    static void Face(ref CharacterHot n, Vector3 patient)
    {
        float dx = patient.X - n.Position.X, dz = patient.Z - n.Position.Z;
        if (dx * dx + dz * dz > 1e-4f) n.Yaw = MathF.Atan2(dx, dz);
    }

    #endregion
}
