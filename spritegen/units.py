"""The 18 curated unit models, one per atlas column.

Every model is hand-placed voxels — no randomness — so each unit is a single
authored design that renders byte-identically on every run. Units face +y
(screen lower-left), the facing the game's atlas has always used. Column
order and ids mirror data/units/*.tres in grid_commanders.

Weapon silhouettes follow each unit's battle_style: small_arms carry rifles
or a pintle MG, rocket units carry tubes and pods, cannon units carry a
single big gun, autocannon units carry thin multi-barrels, and the unarmed
transports carry none.
"""

from __future__ import annotations

from .voxel import Model

# ---------------------------------------------------------------------------
# shared chassis parts
# ---------------------------------------------------------------------------


def _track(m: Model, x0: int, x1: int, y0: int, y1: int, z1: int = 1) -> None:
    """One tread block with link texture on its visible faces and road wheels."""
    m.box(x0, x1, y0, y1, 0, z1, "track")
    # alternating link texture along the outer (+x) face and the front (+y) face
    for y in range(y0, y1 + 1):
        m.set(x1, y, z1 if (y - y0) % 2 == 0 else 0, "track_lt")
    for x in range(x0, x1 + 1):
        m.set(x, y1, z1 if (x - x0) % 2 == 0 else 0, "track_lt")
    # road wheel hubs peeking out of the lower run
    for y in range(y0 + 1, y1, 3):
        m.set(x1, y, 0, "hub")


def _rotor_collar(
    m: Model, cx: int, cy: int, z: int, arms: tuple[tuple[int, int], ...]
) -> None:
    """Paint a rotor's hub cap and its four blade ROOTS in livery.

    A helicopter's disc is the one large mass on the sheet that carries no
    team colour, which is what put b_copter under the 55% faction-share gate
    (53.9%) and t_copter next to it at 60.2%. The roots are where a real
    airframe's paint runs out onto the blade, so the collar buys the share
    back without touching the silhouette or lightening the sweep at the tips.
    Both discs get it, so the two copters answer the gate the same way.
    """
    m.set(cx, cy, z, "hull_lt")
    for dx, dy in arms:
        m.set(cx + dx, cy + dy, z, "hull")
        m.set(cx + dx * 2, cy + dy * 2, z, "hull_dk")


def _tire(m: Model, x: int, y: int, big: bool = False) -> None:
    """One wheel: dark tire block with a hub dot on the outer face."""
    m.box(x, x + 1, y, y + 2, 0, 1, "tire")
    if big:
        m.box(x, x + 1, y, y + 2, 2, 2, "tire")
    m.set(x + 1, y + 1, 1, "hub")


# ---------------------------------------------------------------------------
# land
# ---------------------------------------------------------------------------


def infantry() -> Model:
    """Rifleman: helmet dome over an open face, legs apart mid-stride, rifle
    raised across the chest with the muzzle breaking the silhouette high to
    the right — the opposite corner from the mech's tube."""
    m = Model()
    # mid-stride legs: left boot planted a full step forward, right boot
    # trailing behind the hip line
    m.box(2, 3, 6, 7, 0, 0, "tire")
    m.box(5, 6, 2, 3, 0, 0, "tire")
    m.box(2, 3, 6, 7, 1, 2, "hull_dk")
    m.box(5, 6, 2, 3, 1, 2, "hull_dk")
    # hips bridging the stride
    m.box(2, 6, 3, 6, 3, 3, "hull_dk")
    # plain fatigue torso — the mech wears the plated chest, not the rifleman
    m.box(2, 6, 3, 6, 4, 6, "hull")
    # backpack
    m.box(3, 5, 2, 2, 4, 6, "body_dk")
    # left arm at the side; right arm raised across the chest to the grip
    m.box(1, 1, 3, 5, 4, 6, "hull")
    m.box(7, 7, 4, 6, 4, 5, "hull")
    # rifle at port arms, held a voxel clear of the torso so the barrel's
    # diagonal reads against sky rather than across the chest
    m.set(8, 6, 5, "wood")  # stock
    m.set(8, 5, 6, "gunmetal")  # receiver
    m.set(8, 4, 7, "gunmetal")
    m.set(8, 3, 8, "gunmetal")
    m.set(8, 2, 9, "gunmetal")
    m.set(8, 1, 10, "gunmetal_dk")  # muzzle
    # big open face under an overhanging dome helmet; the brim ring is a
    # voxel wider than the torso so the dome breaks the column silhouette
    m.box(3, 5, 4, 6, 7, 8, "skin")
    m.box(3, 5, 3, 3, 7, 8, "hull_dk")  # nape guard
    m.box(1, 7, 3, 6, 9, 9, "hull")  # brim
    for cx, cy in ((1, 3), (1, 6), (7, 3), (7, 6)):
        m.unset(cx, cy, 9)
    m.box(2, 6, 3, 6, 10, 10, "hull")  # dome
    for cx, cy in ((2, 3), (2, 6), (6, 3), (6, 6)):
        m.unset(cx, cy, 10)
    m.box(3, 5, 4, 5, 11, 11, "body")  # crown
    return m


def mech() -> Model:
    """Rocket trooper: planted wide stance, heavy pauldrons over a bulky
    torso, and a fat launch tube climbing forward over the left shoulder —
    taller, wider and squarer than the rifleman's stride (rocket)."""
    m = Model()
    # wide planted stance, two-voxel-thick armoured legs
    for x0 in (1, 6):
        m.box(x0, x0 + 1, 4, 6, 0, 0, "tire")
        m.box(x0, x0 + 1, 4, 6, 1, 2, "hull")
        m.box(x0, x0 + 1, 4, 6, 3, 3, "hull_dk")  # knee plates
    # belt line bridging the stance
    m.box(1, 7, 4, 6, 4, 4, "hull_dk")
    # bulky torso with a light chest plate
    m.box(1, 7, 3, 6, 5, 8, "hull")
    m.box(2, 6, 6, 6, 6, 8, "hull_lt")
    # ammo backpack with two spare-rocket tips
    m.box(2, 6, 2, 2, 5, 8, "hull_dk")
    m.set(3, 2, 9, "steel")
    m.set(5, 2, 9, "steel")
    # pauldrons — the pure team accents
    m.box(0, 0, 3, 6, 7, 9, "body")
    m.box(8, 8, 3, 6, 7, 9, "body")
    # big helmet with a glass visor band across the face
    m.box(3, 5, 4, 6, 9, 9, "skin")
    m.box(3, 5, 6, 6, 10, 10, "glass")
    m.box(3, 5, 3, 5, 10, 10, "hull")
    m.box(2, 6, 3, 6, 11, 12, "hull")
    for cx, cy in ((2, 3), (2, 6), (6, 3), (6, 6)):
        m.unset(cx, cy, 12)  # round the dome
    # fat launch tube seated on the left pauldron, climbing forward past the
    # helmet crown, venturi exhaust hanging off the back
    m.box(0, 1, 2, 2, 9, 10, "bore")  # exhaust
    for i in range(5):
        m.box(0, 1, 3 + i, 3 + i, 10 + i, 11 + i, "gunmetal")
    m.box(0, 1, 8, 8, 15, 16, "gunmetal_dk")  # muzzle ring
    m.set(0, 9, 16, "amber")  # loaded warhead tip
    m.set(1, 9, 16, "amber")
    m.box(1, 1, 5, 5, 9, 11, "hull")  # supporting arm
    return m


def recon() -> Model:
    """Scout car: four wheels, sloped hood, roof MG, whip antenna."""
    m = Model()
    for x in (0, 8):
        _tire(m, x, 2)
        _tire(m, x, 10)
    # hull bed in desaturated armour; a roof stripe carries the team color
    m.box(1, 8, 0, 13, 2, 3, "hull")
    # sloped hood toward the front
    m.box(1, 8, 14, 14, 2, 2, "hull")
    m.box(2, 7, 14, 15, 2, 2, "hull_lt")
    m.box(2, 7, 12, 13, 3, 3, "hull_lt")  # hood top
    # bumper and headlights
    m.box(1, 8, 15, 15, 2, 2, "hull_dk")
    m.set(2, 15, 2, "amber")
    m.set(7, 15, 2, "amber")
    # livery cabin with windshield and side glass, rounded roofline; a pure
    # team stripe survives on the roof front
    m.box(2, 7, 3, 9, 4, 4, "hull")
    m.box(2, 7, 3, 9, 5, 5, "hull")
    m.box(3, 5, 8, 8, 5, 5, "body")
    m.chamfer(2, 7, 3, 9, 5, 5)
    m.box(3, 6, 9, 9, 4, 5, "glass")
    m.box(7, 7, 4, 7, 4, 4, "glass_dk")
    m.box(2, 7, 3, 3, 4, 4, "hull_dk")  # rear cabin plate
    # pintle MG on a rear roof ring mount (small_arms)
    m.box(4, 5, 4, 5, 6, 6, "gunmetal_dk")
    m.box(4, 4, 5, 5, 7, 7, "gunmetal_dk")
    m.box(4, 4, 6, 9, 7, 7, "gunmetal")
    m.set(4, 10, 7, "bore")
    # spare tire on the tail
    m.box(3, 6, 0, 0, 3, 4, "tire")
    m.set(4, 0, 3, "hub")
    # antenna
    m.box(2, 2, 1, 1, 4, 7, "hull")
    return m


def tank() -> Model:
    """MBT: the low one — flattened turret, hull-hugging long gun (cannon)."""
    m = Model()
    _track(m, 0, 2, 0, 13)
    _track(m, 9, 11, 0, 13)
    # hull in desaturated armour; the turret crown carries the team color
    m.box(0, 11, 1, 12, 2, 3, "hull")
    m.box(1, 10, 13, 13, 2, 3, "hull")
    m.box(2, 9, 14, 14, 2, 2, "hull_lt")  # glacis lip
    m.box(2, 9, 13, 13, 3, 3, "hull_lt")  # glacis top
    # rear deck vents and exhausts
    m.box(2, 9, 1, 1, 3, 3, "hull_dk")
    m.box(2, 9, 3, 3, 3, 3, "hull_dk")
    m.box(0, 1, 0, 0, 2, 3, "hull_dk")
    # flattened turret: one low ring under a team crown — the lowest
    # profile of the land roster, so the barrel line reads alone
    m.box(3, 8, 4, 9, 4, 4, "hull")
    m.chamfer(3, 8, 4, 9, 4, 4)
    m.box(4, 7, 5, 8, 5, 5, "body")
    m.chamfer(4, 7, 5, 8, 5, 5)
    m.box(4, 5, 5, 6, 6, 6, "body_dk")  # commander cupola
    m.set(6, 8, 5, "body_lt")  # loader hatch glint
    m.box(4, 7, 4, 4, 5, 5, "hull_dk")  # stowage bustle
    # low mantlet and a gun grown two voxels — the unmistakable barrel line
    m.box(4, 7, 10, 10, 4, 4, "hull_dk")
    m.box(5, 6, 10, 19, 4, 4, "gunmetal")
    m.box(5, 6, 14, 14, 4, 4, "gunmetal_dk")  # bore evacuator
    m.box(4, 7, 19, 19, 4, 4, "gunmetal_dk")  # muzzle brake
    m.box(5, 6, 20, 20, 4, 4, "bore")
    return m


def md_tank() -> Model:
    """Heavy tank: wider, taller, skirted tracks, long heavy gun (cannon)."""
    m = Model()
    _track(m, 0, 2, 0, 15, 2)
    _track(m, 10, 12, 0, 15, 2)
    # hull with armoured side skirts over the tracks
    m.box(0, 12, 1, 14, 3, 4, "hull")
    m.box(10, 12, 2, 13, 3, 3, "hull_dk")
    m.box(0, 2, 2, 13, 3, 3, "hull_dk")
    # stepped heavy glacis
    m.box(1, 11, 15, 15, 3, 4, "hull")
    m.box(2, 10, 16, 16, 3, 3, "hull_lt")
    m.box(2, 10, 15, 15, 4, 4, "hull_lt")
    # rear engine deck and twin exhausts
    m.box(2, 10, 1, 2, 4, 4, "hull_dk")
    m.box(1, 2, 0, 0, 3, 4, "hull_dk")
    m.box(10, 11, 0, 0, 3, 4, "hull_dk")
    # big turret, two tiers: armour ring, rounded crown; the cupola and
    # hatch carry the team color
    m.box(3, 9, 4, 11, 5, 6, "hull")
    m.chamfer(3, 9, 4, 11, 5, 6)
    m.box(4, 8, 5, 10, 7, 7, "hull")
    m.chamfer(4, 8, 5, 10, 7, 7)
    m.box(4, 8, 4, 4, 7, 7, "hull_dk")  # bustle rack
    m.box(4, 5, 5, 6, 8, 8, "body_dk")  # cupola
    m.box(6, 7, 6, 7, 8, 8, "body")  # hatch
    # wide mantlet, longer gun with thermal-sleeve rings
    m.box(4, 8, 12, 12, 5, 7, "hull_dk")
    m.box(5, 7, 13, 19, 6, 6, "gunmetal")
    m.box(5, 7, 15, 15, 6, 6, "gunmetal_dk")
    m.box(5, 7, 17, 17, 6, 6, "gunmetal_dk")
    m.box(4, 8, 20, 20, 6, 6, "gunmetal_dk")  # muzzle brake
    m.box(5, 7, 21, 21, 6, 6, "bore")
    return m


def anti_air() -> Model:
    """Tracked flak: twin long barrels raked past 60 degrees over the battery
    box — the howitzer's climb, paired and thin — plus a search radar."""
    m = Model()
    _track(m, 0, 2, 0, 11)
    _track(m, 8, 10, 0, 11)
    # low hull in desaturated armour
    m.box(0, 10, 1, 11, 2, 3, "hull")
    m.box(1, 9, 12, 12, 2, 3, "hull_lt")
    m.box(2, 8, 1, 1, 3, 3, "hull_dk")
    # rotating battery box in livery armour; its base band and a roof panel
    # carry the team color
    m.box(2, 8, 3, 8, 4, 6, "hull")
    m.chamfer(2, 8, 3, 8, 6, 6)
    m.box(3, 7, 4, 5, 6, 6, "body")  # roof panel
    m.box(2, 8, 3, 8, 4, 4, "body_dk")
    m.box(3, 7, 3, 3, 5, 6, "hull_dk")  # ammo feed
    # elevating mount at the battery front: livery pedestal, gunmetal cradle
    m.box(4, 6, 6, 8, 6, 7, "hull")
    m.set(5, 7, 8, "amber")  # ranging light
    # twin long barrels climbing two z per tile like the howitzer, but
    # paired and one voxel thin — the raked lines ARE the identity
    for x in (3, 7):
        m.box(x, x, 8, 8, 6, 7, "gunmetal_dk")  # trunnion
        for i in range(5):
            m.box(x, x, 9 + i, 9 + i, 8 + 2 * i, 9 + 2 * i, "gunmetal")
        m.set(x, 14, 17, "gunmetal_dk")  # muzzle
        m.set(x, 14, 18, "bore")
    # search radar dish on a rear mast, big enough to read at map scale
    m.box(8, 8, 4, 4, 7, 8, "hull")
    m.box(7, 8, 3, 5, 9, 9, "hull_lt")
    m.box(7, 8, 4, 4, 10, 10, "hull_lt")
    m.set(8, 4, 9, "gunmetal_dk")
    return m


def artillery() -> Model:
    """SPG: open casemate, howitzer erected past 60 degrees, recoil spade."""
    m = Model()
    _track(m, 0, 2, 0, 12)
    _track(m, 8, 10, 0, 12)
    m.box(0, 10, 1, 12, 2, 3, "hull")
    m.box(1, 9, 13, 13, 2, 2, "hull_lt")
    # open casemate: an armoured wall ring around the gun pit, no roof;
    # the team color caps the walls
    m.box(1, 9, 2, 8, 4, 5, "hull")
    m.clear(2, 8, 3, 7, 4, 5)
    m.box(1, 1, 2, 8, 5, 5, "body_dk")  # wall caps
    m.box(9, 9, 2, 8, 5, 5, "body_dk")
    m.box(1, 9, 2, 2, 5, 5, "body")
    m.box(2, 8, 8, 8, 5, 5, "body")
    m.box(2, 8, 3, 7, 3, 3, "hull_dk")  # pit floor
    # howitzer erected steeply out of the pit: the rising spike no other
    # land unit carries — two z per y, well clear of the hull mass; the
    # lower barrel wears a livery recoil sleeve, the muzzle stays steel
    m.box(4, 6, 4, 6, 4, 5, "hull_dk")  # trunnion pedestal
    for i in range(5):
        paint = "hull_dk" if i < 2 else "gunmetal"
        m.box(4, 6, 6 + i, 6 + i, 6 + 2 * i, 7 + 2 * i, paint)
    m.box(3, 7, 11, 11, 15, 15, "gunmetal_dk")  # muzzle brake
    m.box(4, 6, 11, 11, 16, 16, "bore")
    # recoil spade dug in at the rear
    m.box(3, 7, 0, 0, 1, 3, "hull_dk")  # spade arms
    m.box(2, 8, -1, -1, 0, 2, "hull")  # blade
    return m


def rockets() -> Model:
    """Wheeled MLRS: long eight-wheel carrier, low cab, one wide flat rack
    pitched up over the tail — a tilted plane, never a turret."""
    m = Model()
    for y in (1, 5, 9, 13):
        _tire(m, 0, y)
        _tire(m, 8, y)
    # long chassis bed
    m.box(1, 8, 0, 16, 2, 3, "hull")
    # low cab tucked at the front, one voxel of glass and a team roof patch
    m.box(2, 7, 13, 16, 4, 4, "hull")
    m.box(3, 6, 14, 15, 5, 5, "body")
    m.box(3, 6, 16, 16, 4, 4, "glass")
    m.box(7, 7, 14, 15, 4, 4, "glass_dk")
    m.box(2, 7, 17, 17, 2, 3, "hull_dk")  # bumper
    m.set(3, 17, 3, "amber")
    m.set(6, 17, 3, "amber")
    # the launcher: one full-width rectangular slab pitched up toward the
    # rear, dark like a sealed tube pod; mouths open on the high end
    for k in range(6):
        y0 = 11 - 2 * k
        m.box(1, 8, y0, y0 + 1, 4 + k, 5 + k, "hull_dk")
        m.set(1, y0, 5 + k, "body_dk")  # livery rail down the pod edge
        m.set(8, y0, 5 + k, "body_dk")
    for x in (2, 4, 6):
        m.set(x, 1, 10, "bore")
        m.set(x, 2, 10, "bore")
    # solid launch-frame wall carrying the slab's high end
    m.box(2, 7, 1, 2, 4, 8, "hull_dk")
    return m


def apc() -> Model:
    """Tracked transport: the tall box — high flat-topped troop compartment
    over a sloped glacis, no turret at all — unarmed."""
    m = Model()
    _track(m, 0, 2, 0, 12)
    _track(m, 7, 9, 0, 12)
    # tall narrow slab hull: the highest solid mass on the land roster,
    # a track narrower than the gun tanks so the box reads upright
    m.box(0, 9, 1, 12, 2, 6, "hull")
    m.box(1, 8, 2, 12, 7, 7, "hull")  # inset roof, dead-flat top line
    # sloped glacis nose stepping down to the bumper; the team stripe
    # across it keeps a pure accent on an unshaded face
    m.box(1, 8, 13, 13, 2, 5, "hull")
    m.box(2, 7, 13, 13, 5, 5, "hull_lt")
    m.box(3, 6, 13, 13, 5, 5, "body")
    m.box(2, 7, 14, 14, 2, 3, "hull_lt")
    # driver visor slit and headlights
    m.box(3, 5, 14, 14, 3, 3, "glass_dk")
    m.set(2, 14, 3, "amber")
    m.set(7, 14, 3, "amber")
    # livery roof: a broad team panel and hatch pair, painted flush so the
    # top stays a slab
    m.box(2, 7, 4, 10, 7, 7, "body")
    m.box(3, 4, 8, 9, 7, 7, "body_dk")  # troop hatches
    m.box(5, 6, 8, 9, 7, 7, "body_dk")
    m.box(0, 0, 2, 11, 4, 4, "hull_dk")  # side stowage rail
    m.box(9, 9, 2, 11, 4, 4, "hull_dk")
    # rear troop door, full height
    m.box(3, 6, 0, 0, 2, 6, "hull_dk")
    m.set(5, 0, 4, "steel")  # door handle
    # tall comms whip — the APC keeps one; the gun tanks lost theirs
    m.box(8, 8, 3, 3, 8, 9, "hull_lt")
    m.set(8, 3, 10, "amber")
    return m


def missiles() -> Model:
    """Wheeled SAM battery: two big rounds erected near-vertical over the
    tail — thin steep spikes with daylight between — plus a radar dish."""
    m = Model()
    for y in (1, 8):
        _tire(m, 0, y)
        _tire(m, 8, y)
    # short four-wheel erector chassis
    m.box(1, 8, 0, 11, 2, 3, "hull")
    # livery cab forward, rounded roofline with a pure team patch
    m.box(2, 7, 8, 11, 4, 4, "hull")
    m.box(2, 7, 8, 11, 5, 5, "hull")
    m.box(3, 5, 10, 10, 5, 5, "body")
    m.chamfer(2, 7, 8, 11, 5, 5)
    m.box(3, 6, 11, 11, 4, 5, "glass")
    m.box(7, 7, 9, 10, 4, 4, "glass_dk")
    m.box(2, 7, 12, 12, 2, 3, "hull_dk")
    m.set(3, 12, 3, "amber")
    m.set(6, 12, 3, "amber")
    # erector pedestal over the tail axle
    m.box(2, 7, 1, 4, 4, 5, "hull_dk")
    m.box(2, 7, 1, 1, 6, 7, "hull_dk")  # raised launch-rail shoe
    # two fat rounds climbing two z per y — steep solid spikes, a clear
    # sky gap between them where the rockets truck is one joined slab;
    # livery booster sleeves and a pure team band under white warheads
    for x0 in (2, 6):
        for i in range(5):
            paint = ("hull", "hull", "body", "white", "white")[i]
            m.box(x0, x0 + 1, 3 + i, 4 + i, 5 + 2 * i, 7 + 2 * i, paint)
        m.set(x0, 9, 16, "amber")  # seeker tips
        m.set(x0 + 1, 9, 16, "amber")
    # fire-control dish on a rear mast, plate tilted up at the sky
    m.box(4, 5, 0, 1, 4, 6, "hull")
    m.box(3, 6, 0, 0, 7, 8, "hull_lt")
    m.box(3, 6, 1, 1, 9, 9, "hull_lt")
    m.set(4, 0, 9, "gunmetal_dk")
    m.set(5, 0, 9, "gunmetal_dk")
    return m


# ---------------------------------------------------------------------------
# air
# ---------------------------------------------------------------------------


def fighter() -> Model:
    """Swept-wing air-superiority jet (autocannon)."""
    m = Model()
    # fuselage in desaturated airframe grey, nose toward +y
    m.box(4, 5, 0, 17, 3, 4, "hull")
    m.box(4, 5, 16, 18, 3, 3, "hull")
    m.set(4, 19, 3, "hull_dk")  # radome tip
    m.set(5, 19, 3, "hull_dk")
    # canopy
    m.box(4, 5, 11, 13, 5, 5, "glass")
    m.set(4, 10, 5, "glass_dk")
    m.set(5, 10, 5, "glass_dk")
    # air intakes
    m.box(3, 3, 8, 11, 3, 4, "hull_dk")
    m.box(6, 6, 8, 11, 3, 4, "hull_dk")
    # swept wings in hull livery (the mass the player reads from above)
    for i in range(1, 7):
        wy = 9 - i
        m.box(4 - i, 4 - i, wy, wy + 4, 3, 3, "hull")
        m.box(5 + i, 5 + i, wy, wy + 4, 3, 3, "hull")
    # wingtip missiles
    m.box(-2, -2, 3, 6, 3, 3, "white")
    m.box(11, 11, 3, 6, 3, 3, "white")
    m.set(-2, 7, 3, "amber")
    m.set(11, 7, 3, "amber")
    # tailplane in livery; the twin canted fins keep the pure team accent
    m.box(2, 7, 0, 2, 3, 3, "hull")
    m.box(3, 3, 0, 1, 4, 6, "body_dk")
    m.box(6, 6, 0, 1, 4, 6, "body_dk")
    # engine nozzles
    m.box(4, 5, 0, 0, 3, 4, "gunmetal_dk")
    m.set(4, -1, 3, "bore")
    m.set(5, -1, 3, "bore")
    return m


def bomber() -> Model:
    """Heavy strategic bomber: four podded engines, deep fuselage (bomb)."""
    m = Model()
    # deep fuselage in airframe grey; rounded nose
    m.box(4, 7, 0, 19, 3, 5, "hull")
    m.box(4, 7, 18, 19, 3, 4, "hull")
    m.chamfer(4, 7, 0, 19, 5, 5)
    m.box(5, 6, 20, 20, 3, 4, "hull_lt")  # nose cap
    # flight-deck glazing
    m.box(4, 7, 16, 17, 5, 5, "glass")
    # livery straight wings with slight rearward rake; dark trailing edge so
    # the big top surface doesn't read flat, pure team color on the wingtips
    for i in range(1, 9):
        wy = 10 - (i + 1) // 2
        wing = "body" if i == 8 else "hull"
        edge = "body_dk" if i == 8 else "hull_dk"
        m.box(4 - i, 4 - i, wy, wy + 5, 4, 4, wing)
        m.box(7 + i, 7 + i, wy, wy + 5, 4, 4, wing)
        m.set(4 - i, wy, 4, edge)
        m.set(7 + i, wy, 4, edge)
    # four engine pods slung under the wings, mirrored about the fuselage
    # centre; the outer pair sits one step back, following the wing rake
    for x, fwd in ((-3, 0), (-1, 1), (12, 1), (14, 0)):
        m.box(x, x, 9 + fwd, 12 + fwd, 3, 3, "gunmetal")
        m.set(x, 13 + fwd, 3, "bore")
    # bomb-bay doors line on the belly sides
    m.box(7, 7, 6, 12, 3, 3, "hull_dk")
    # tailplane in livery; the tall fin keeps the pure team accent
    m.box(1, 10, 0, 2, 4, 4, "hull")
    m.box(5, 6, 0, 1, 5, 8, "body_dk")
    m.box(5, 6, 2, 2, 5, 6, "body_dk")
    # tail turret hint
    m.box(5, 6, 0, 0, 3, 3, "gunmetal_dk")
    return m


def b_copter(frame: int = 0) -> Model:
    """Attack helicopter: chin gun, stub-wing rocket pods, tail rotor.

    `frame` 1 is the ambient-animation pose: the same aircraft with its
    rotor blades swept 45 degrees, so alternating the two frames spins the
    disc. Nothing else may differ between frames.
    """
    m = Model()
    # fuselage in hull livery, rounded nose
    m.box(3, 5, 6, 14, 3, 5, "hull")
    m.box(3, 5, 14, 15, 3, 4, "hull")
    m.unset(3, 15, 3)
    m.unset(5, 15, 3)
    m.chamfer(3, 5, 6, 14, 5, 5)
    # tandem canopy
    m.box(3, 5, 13, 14, 5, 5, "glass")
    m.box(3, 5, 11, 12, 6, 6, "glass_dk")
    m.box(3, 5, 10, 10, 6, 6, "body")
    # chin autocannon
    m.box(4, 4, 15, 17, 2, 2, "gunmetal")
    m.set(4, 18, 2, "bore")
    # stub wings with rocket pods
    m.box(1, 2, 9, 11, 4, 4, "hull_dk")
    m.box(6, 7, 9, 11, 4, 4, "hull_dk")
    m.box(1, 1, 9, 12, 3, 3, "hull_dk")
    m.box(7, 7, 9, 12, 3, 3, "hull_dk")
    m.set(1, 13, 3, "bore")
    m.set(7, 13, 3, "bore")
    # tail boom, fin and tail rotor
    m.box(4, 4, 0, 6, 4, 4, "hull")
    m.box(4, 4, 0, 1, 5, 6, "body_dk")
    m.box(5, 5, 0, 0, 5, 7, "rotor")
    m.set(5, 0, 6, "hub")
    # skids
    m.box(2, 2, 8, 14, 1, 1, "hull_dk")
    m.box(6, 6, 8, 14, 1, 1, "hull_dk")
    # main rotor: hub mast + four blades over the fuselage (frame 1 sweeps
    # the blades 45 degrees; the tail rotor is vertical and stays)
    m.box(4, 4, 10, 10, 7, 8, "hull_dk")
    if frame == 0:
        m.box(4, 4, 5, 15, 9, 9, "rotor")
        m.box(-1, 9, 10, 10, 9, 9, "rotor")
        _rotor_collar(m, 4, 10, 9, ((0, 1), (0, -1), (1, 0), (-1, 0)))
    else:
        for d in range(-4, 5):
            m.set(4 + d, 10 + d, 9, "rotor")
            m.set(4 + d, 10 - d, 9, "rotor")
        _rotor_collar(m, 4, 10, 9, ((1, 1), (-1, -1), (1, -1), (-1, 1)))
    return m


def t_copter(frame: int = 0) -> Model:
    """Tandem-rotor transport helicopter — unarmed.

    `frame` 1 sweeps both rotor discs 45 degrees, as on b_copter.
    """
    m = Model()
    # boxy hold in hull livery, rounded top edges so it stops reading as a
    # brick; the roof spine keeps a pure team stripe
    m.box(3, 6, 2, 15, 3, 6, "hull")
    m.chamfer(3, 6, 2, 15, 6, 6)
    m.box(4, 5, 2, 15, 6, 6, "body")
    m.box(3, 6, 15, 16, 3, 5, "hull")
    # cockpit glazing
    m.box(3, 6, 15, 16, 5, 5, "glass")
    m.box(3, 6, 17, 17, 3, 4, "glass_dk")
    # side cargo door and stripe
    m.box(6, 6, 6, 9, 4, 5, "hull_dk")
    m.box(6, 6, 2, 15, 3, 3, "hull_dk")
    # rear loading ramp
    m.box(3, 6, 1, 1, 3, 5, "hull_dk")
    # fixed gear sponsons in dark livery
    m.box(2, 2, 4, 5, 1, 2, "hull_dk")
    m.box(7, 7, 4, 5, 1, 2, "hull_dk")
    m.box(2, 2, 12, 13, 1, 2, "hull_dk")
    m.box(7, 7, 12, 13, 1, 2, "hull_dk")
    # tandem rotor masts and overlapping blades
    m.box(4, 5, 4, 4, 7, 8, "hull_dk")
    m.box(4, 5, 13, 13, 7, 8, "hull_dk")
    if frame == 0:
        m.box(4, 4, 0, 8, 9, 9, "rotor")
        m.box(-1, 9, 4, 4, 9, 9, "rotor")
        m.box(5, 5, 9, 17, 9, 9, "rotor")
        m.box(0, 10, 13, 13, 9, 9, "rotor")
        axes = ((0, 1), (0, -1), (1, 0), (-1, 0))
        _rotor_collar(m, 4, 4, 9, axes)
        _rotor_collar(m, 5, 13, 9, axes)
    else:
        # One diagonal blade pair per disc, opposed between the discs: two
        # full X sweeps overlap on the tandem hull and read as a different
        # aircraft at 32px, while a two-blade mid-turn keeps the silhouette.
        for d in range(-4, 5):
            m.set(4 + d, 4 + d, 9, "rotor")
            m.set(5 + d, 13 - d, 9, "rotor")
        _rotor_collar(m, 4, 4, 9, ((1, 1), (-1, -1)))
        _rotor_collar(m, 5, 13, 9, ((1, -1), (-1, 1)))
    return m


# ---------------------------------------------------------------------------
# sea
# ---------------------------------------------------------------------------


def battleship() -> Model:
    """Dreadnought: the fleet's LONG one — a hull with a clear margin over
    every other keel, turrets fore and aft, midships bridge mast (cannon)."""
    m = Model()
    # long low naval-grey hull, tapered bow (+y) and stern; dark waterline.
    # Narrow beam on purpose: length is the identity, so the slab stays
    # 4 wide and spends the whole cell diagonal (sprite width 64, exactly).
    m.box(2, 5, 2, 23, 0, 1, "hull")
    m.box(3, 4, 24, 25, 0, 1, "hull")
    m.box(3, 4, 26, 26, 0, 1, "hull")
    m.box(3, 4, 0, 1, 0, 1, "hull")
    m.box(2, 5, 2, 23, 0, 0, "hull_dk")
    m.box(3, 4, 24, 26, 0, 0, "hull_dk")
    m.box(3, 4, 0, 1, 0, 0, "hull_dk")
    # deck in hull livery; the bow keeps the pure team flash
    m.box(2, 5, 2, 23, 2, 2, "hull")
    m.box(3, 4, 24, 25, 2, 2, "body")
    m.box(3, 4, 0, 1, 2, 2, "hull")
    # fore main turret: barbette + twin guns reaching up the long foredeck
    m.box(2, 5, 16, 18, 3, 3, "hull")
    m.box(3, 4, 16, 18, 4, 4, "hull_dk")
    for x in (3, 4):
        m.box(x, x, 19, 22, 4, 4, "gunmetal")
        m.set(x, 23, 4, "bore")
    # aft turret facing the stern
    m.box(2, 5, 3, 5, 3, 3, "hull")
    m.box(3, 4, 3, 5, 4, 4, "body_dk")
    for x in (3, 4):
        m.box(x, x, 1, 2, 4, 4, "gunmetal")
        m.set(x, 0, 4, "bore")
    # midships bridge with glazing toward the bow and a lattice mast — kept
    # below the cruiser's tower on purpose; the cruiser owns "tallest"
    m.box(2, 5, 10, 14, 3, 4, "hull")
    m.chamfer(2, 5, 10, 14, 4, 4)
    m.box(3, 4, 14, 14, 4, 4, "glass_dk")
    m.box(3, 4, 11, 13, 5, 5, "hull")
    m.box(3, 4, 13, 13, 5, 5, "glass_dk")
    m.box(3, 3, 12, 12, 6, 7, "steel")
    m.set(3, 12, 8, "gunmetal_dk")
    # lone funnel between bridge and aft turret — one more evenly spaced bump
    m.box(3, 4, 7, 8, 3, 4, "hull_dk")
    m.box(3, 4, 7, 8, 5, 5, "bore")
    return m


def cruiser() -> Model:
    """Escort cruiser: the fleet's TOWER — one tall blocky superstructure
    amidships on a beamy mid-length hull, flat helipad aft (autocannon)."""
    m = Model()
    # mid-length hull, a strake beamier than the battleship's; dark waterline
    m.box(1, 6, 2, 15, 0, 1, "hull")
    m.box(2, 5, 16, 17, 0, 1, "hull")
    m.box(3, 4, 18, 18, 0, 1, "hull")
    m.box(2, 5, 0, 1, 0, 1, "hull")
    m.box(1, 6, 2, 15, 0, 0, "hull_dk")
    m.box(2, 5, 16, 17, 0, 0, "hull_dk")
    m.box(3, 4, 18, 18, 0, 0, "hull_dk")
    m.box(2, 5, 0, 1, 0, 0, "hull_dk")
    # deck in hull livery; the bow cells keep the pure team flash
    m.box(1, 6, 2, 15, 2, 2, "hull")
    m.box(2, 5, 16, 17, 2, 2, "hull")
    m.box(3, 4, 16, 17, 2, 2, "body")
    m.box(2, 5, 0, 1, 2, 2, "hull")
    # forward deck autocannon: twin thin barrels raked up over the bow
    m.box(3, 4, 12, 13, 3, 3, "hull_dk")
    for x in (3, 4):
        m.box(x, x, 14, 15, 3, 3, "gunmetal")
        m.set(x, 16, 4, "gunmetal_dk")
    # the tower: one tall blocky superstructure amidships, clearly the
    # tallest mass in the fleet; its band keeps the pure team accent
    m.box(2, 5, 6, 10, 3, 6, "hull")
    m.box(2, 5, 6, 10, 5, 5, "body")
    m.chamfer(2, 5, 6, 10, 6, 6)
    m.box(3, 4, 10, 10, 6, 6, "glass_dk")
    m.box(3, 4, 7, 9, 7, 8, "hull")
    m.box(3, 4, 9, 9, 7, 7, "glass_dk")
    m.box(3, 3, 8, 8, 9, 10, "steel")
    m.set(3, 8, 11, "gunmetal_dk")
    # flat helipad aft, painted on the deck: dark pad, white H
    m.box(2, 5, 1, 4, 2, 2, "hull_dk")
    m.set(3, 2, 2, "white")
    m.set(4, 2, 2, "white")
    return m


def sub() -> Model:
    """Attack submarine: the LOW one — decks awash, a beamy saddle amidships
    riding the waterline under one prominent sail with dive planes and
    periscopes."""
    m = Model()
    # decks awash: one dark waterline row end to end, one livery deck row of
    # freeboard that stops short of the tapered bow and stern. The saddle
    # tanks widen both rows amidships: the round-4 mass finding measured the
    # sub the smallest sprite on the sheet at 22.9% legibility, and a hull
    # two voxels wide leaves a deck the player cannot see is a deck.
    m.box(3, 4, 0, 21, 0, 0, "hull_dk")
    m.box(2, 5, 3, 19, 0, 0, "hull_dk")
    m.box(3, 4, 1, 19, 1, 1, "hull")
    m.box(2, 5, 4, 18, 1, 1, "hull")
    # deck hatches fore and aft of the sail
    m.set(3, 16, 1, "body_lt")
    m.set(4, 4, 1, "body_lt")
    # the sail: one prominent conning tower, the silhouette's single fin —
    # raised a voxel over the round-3 model so the fin, not the deck, is what
    # separates the boat from open sea; its top band keeps the pure team color
    m.box(3, 4, 9, 13, 2, 5, "hull_dk")
    m.box(3, 4, 9, 13, 6, 6, "body")
    # dive planes off the sail flanks
    m.box(2, 2, 11, 12, 3, 3, "hull_dk")
    m.box(5, 5, 11, 12, 3, 3, "hull_dk")
    # periscope and attack scope over the sail
    m.box(3, 3, 11, 11, 7, 8, "steel")
    m.set(4, 13, 7, "steel")
    return m


def lander() -> Model:
    """Landing craft: the SHORT FAT one — stubbiest, beamiest hull, raised
    bow ramp, high cargo house aft. Unarmed."""
    m = Model()
    # short wide hull; dark waterline
    m.box(0, 8, 1, 9, 0, 1, "hull")
    m.box(1, 7, 10, 10, 0, 1, "hull")
    m.box(1, 7, 0, 0, 0, 1, "hull")
    m.box(0, 8, 1, 9, 0, 0, "hull_dk")
    m.box(1, 7, 10, 10, 0, 0, "hull_dk")
    m.box(1, 7, 0, 0, 0, 0, "hull_dk")
    # gunwales around the forward cargo well
    m.box(0, 8, 1, 9, 2, 2, "hull")
    m.clear(1, 7, 2, 8, 2, 2)
    # tie-down lanes on the well floor
    m.box(2, 6, 5, 8, 1, 1, "hull_lt")
    m.box(4, 4, 5, 8, 1, 1, "hull_dk")
    # high cargo house aft — the tall half of the stubby-block silhouette
    m.box(1, 7, 1, 4, 2, 5, "hull")
    m.chamfer(1, 7, 1, 4, 5, 5)
    m.box(2, 6, 4, 4, 4, 4, "glass_dk")
    m.box(2, 6, 2, 3, 6, 6, "body")  # team-colored house roof
    m.box(6, 6, 1, 1, 6, 7, "steel")  # exhaust stack
    # blunt bow ramp raised for sea travel; lip and ribs keep the team accent
    m.box(1, 7, 10, 10, 2, 4, "hull")
    m.box(2, 6, 10, 10, 2, 3, "body_lt")  # ramp ribs
    m.box(1, 7, 10, 10, 5, 5, "body_dk")  # ramp lip
    # bollards on the gunwale corners
    m.set(0, 1, 3, "gunmetal_dk")
    m.set(8, 1, 3, "gunmetal_dk")
    m.set(0, 9, 3, "gunmetal_dk")
    m.set(8, 9, 3, "gunmetal_dk")
    return m


# ---------------------------------------------------------------------------
# registry: id -> (builder, cell kind), in atlas_col order 0..17
# ---------------------------------------------------------------------------

UNITS: dict[str, tuple] = {
    "infantry": (infantry, "land"),
    "mech": (mech, "land"),
    "recon": (recon, "land"),
    "tank": (tank, "land"),
    "md_tank": (md_tank, "land"),
    "anti_air": (anti_air, "land"),
    "artillery": (artillery, "land"),
    "rockets": (rockets, "land"),
    "apc": (apc, "land"),
    "fighter": (fighter, "air"),
    "bomber": (bomber, "air"),
    "b_copter": (b_copter, "air"),
    "t_copter": (t_copter, "air"),
    "missiles": (missiles, "land"),
    "battleship": (battleship, "sea"),
    "cruiser": (cruiser, "sea"),
    "sub": (sub, "sea"),
    "lander": (lander, "sea"),
}

# The two units whose model itself changes between ambient frames. Everything
# else animates (or not) purely in composition — see atlas.unit_cell.
_FRAMED = ("b_copter", "t_copter")

# Hulls that run awash and so carry a wake (voxel._wake). A ship with
# freeboard reads against open sea on its own; the sub is the one model whose
# deck is at the waterline, which is what left it last in the round-4
# legibility measure.
WAKE: frozenset[str] = frozenset({"sub"})


def build_model(uid: str, frame: int = 0) -> Model:
    """The one seam a frame number reaches a builder through."""
    builder = UNITS[uid][0]
    return builder(1) if frame == 1 and uid in _FRAMED else builder()


# atlas_col -> unit id (contiguous 0..17), the order the sheet is assembled in
ATLAS_ORDER: tuple[str, ...] = (
    "infantry",
    "mech",
    "recon",
    "tank",
    "md_tank",
    "anti_air",
    "artillery",
    "rockets",
    "apc",
    "fighter",
    "bomber",
    "b_copter",
    "t_copter",
    "missiles",
    "battleship",
    "cruiser",
    "sub",
    "lander",
)
