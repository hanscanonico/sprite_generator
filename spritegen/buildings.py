"""Voxel props for terrain tiles: reef rocks — and the five property
buildings (city, base, hq, airport, port), tinted per faction row.

Buildings carry their own isometric base plate, the convention the game's
compositor has always assumed (the lot IS the plate; no square of pavement
behind a diamond footprint). Each building owns one mass identity the
others don't (design review round 3: five near-identical grey lumps):
city two towers, base a long sawtooth shed, hq a wide low fort, airport a
hangar arch with a control tower, port a crane over a warehouse.
"""

from __future__ import annotations

from .palette import Faction, h01
from .voxel import Model

# The masonry these models are built from (fix spec rounds 4, 6 and 7, item 7).
# A voxel top face is the material scaled 1.3x and a front-corner top is rim-lit
# on top of that, so a material's lit plane lands ~45L above its own value.
# Round 6 picked the greys by that LIT plane rather than by their own value,
# which brought every wall under terrain.TERRAIN_VALUE_CEILING. Round 7 is the
# other half of the same finding: a wall under the cap is not the same thing as
# a wall a unit separates from, and the old ladder's lit planes (L150-164) sat
# exactly on every faction's S4 top slot (L135-156), so a unit standing on a
# property had its own lit planes to read against a wall of the same value.
# The whole ladder therefore steps down one rung — the mass lands at L100-121
# lit, roughly 40L clear of the band units key in — and the rung it vacated
# becomes TRIM, which may only ever be drawn as a LINE: a parapet, a coping, a
# seam. Highlights as trim, never as fields, is what keeps the buildings from
# flattening into dark blocks now that their mass is dark.
TRIM = "rock_dk"  # lit top L150 — lines only, never a plane
METAL = "track_lt"  # lit top L137 — machinery: cranes, masts, chimney caps
WALL = "gunmetal_dk"  # lit top L121 — the mass every wall and lot is built of
WALL_DK = "track"  # lit top L100 — its shaded rung: rear walls, sheds, kerbs
DETAIL = "bore"  # doors, seams, cables and openings, read as near-black
MASONRY = WALL
MASONRY_DK = WALL_DK

# A roof is the same rule in the faction's own ramp: the theme's dark is the
# roof plane and the theme colour itself is the ridge, the cap and the banner.
# The pale roofs the review named were `body` fields — verdant's lit to L152
# against a verdant unit's S4 at L153 — and a ridge line carries the same hue
# at the same value without being the thing a silhouette has to cross.
ROOF = "body_dk"
ROOF_TRIM = "body"

# ---------------------------------------------------------------------------
# nature props
# ---------------------------------------------------------------------------


def rock_outcrop(size: int = 2) -> Model:
    """A low shelf of reef rock breaking the surface."""
    m = Model()
    m.box(0, size, 0, size, 0, 0, "rock_dk")
    m.box(0, size - 1, 0, size - 1, 1, 1, "rock_dk")
    m.set(0, 0, 1, "gunmetal_dk")
    m.set(size - 1, size - 1, 1, "gunmetal_dk")
    return m


# ---------------------------------------------------------------------------
# property buildings
# ---------------------------------------------------------------------------


def _pad(
    m: Model,
    x0: int,
    x1: int,
    y0: int,
    y1: int,
    mat: str = WALL,
    rim: str = WALL_DK,
) -> None:
    """The building's own base plate, with a darker rim."""
    m.box(x0, x1, y0, y1, 0, 0, mat)
    for x in range(x0, x1 + 1):
        m.set(x, y0, 0, rim)
        m.set(x, y1, 0, rim)
    for y in range(y0, y1 + 1):
        m.set(x0, y, 0, rim)
        m.set(x1, y, 0, rim)


def _windows(
    m: Model,
    face: str,
    along0: int,
    along1: int,
    wall: int,
    z0: int,
    z1: int,
    salt: int,
) -> None:
    """A window grid on a wall: every other column/row, a few lit amber.

    `along0..along1` runs along the wall and `wall` is the wall's fixed
    coordinate on the other axis — for face 'y' that means x along and y
    fixed, for face 'x' the reverse.
    """
    for along in range(along0, along1 + 1, 2):
        for z in range(z0, z1 + 1, 2):
            mat = "amber" if h01(along, z, salt) < 0.28 else "glass_dk"
            if face == "y":
                m.set(along, wall, z, mat)
            else:
                m.set(wall, along, z, mat)


def city() -> Model:
    """Two grey towers of different heights on a compact plaza — the
    tall-narrow silhouette of the set."""
    m = Model()
    _pad(m, 1, 12, 1, 12)
    # tall slab tower, right: concrete walls, faction roof + penthouse
    m.box(7, 11, 2, 6, 1, 7, WALL)
    m.box(7, 11, 2, 6, 8, 8, ROOF)
    m.box(8, 10, 3, 5, 9, 9, ROOF_TRIM)  # penthouse, the tower's lit cap
    m.chamfer(8, 10, 3, 5, 9, 9)
    _windows(m, "y", 8, 10, 6, 2, 7, 23)
    _windows(m, "x", 3, 5, 11, 2, 7, 24)
    # shorter tower, left: faction roof over grey walls, coped along the front
    m.box(2, 6, 7, 11, 1, 4, WALL)
    m.box(2, 6, 7, 11, 5, 5, ROOF)
    m.box(2, 6, 11, 11, 5, 5, ROOF_TRIM)  # parapet coping
    m.chamfer(2, 6, 7, 11, 5, 5)
    _windows(m, "y", 3, 5, 11, 2, 4, 21)
    _windows(m, "x", 8, 10, 6, 2, 4, 22)
    # plaza planter at the front corner
    m.set(11, 11, 1, "leaf")
    m.set(12, 11, 1, "leaf_dk")
    return m


def base() -> Model:
    """A factory: a long grey shed under a faction sawtooth roof, chimney,
    crates. The lot is a shallow full-width strip, so the silhouette reads
    long and low — never the square diamond the hq owns."""
    m = Model()
    _pad(m, 0, 13, 5, 13)
    # main shed in industrial concrete, running the full width
    m.box(1, 12, 5, 12, 1, 3, WALL_DK)
    # sawtooth roof: three north-lit ridges in the owner's color
    for k in range(3):
        y0 = 12 - k * 3
        m.box(1, 12, y0 - 1, y0, 4, 4, ROOF)
        m.box(1, 12, y0, y0, 5, 5, ROOF_TRIM)  # lit ridge
        m.box(1, 12, y0 - 1, y0 - 1, 5, 5, DETAIL)  # skylight band
    # big vehicle door on the front face with hazard stripe
    m.box(3, 8, 12, 12, 1, 3, DETAIL)
    m.box(3, 8, 12, 12, 3, 3, "amber")
    m.box(5, 6, 12, 12, 1, 1, DETAIL)  # door gap
    # chimney at the rear corner
    m.box(12, 13, 5, 6, 1, 6, WALL_DK)
    m.box(12, 13, 5, 6, 6, 6, METAL)
    m.set(12, 5, 7, DETAIL)
    m.set(13, 6, 7, DETAIL)
    # crates on the front apron
    m.box(0, 1, 12, 13, 1, 2, "wood")
    return m


def hq() -> Model:
    """A stone fortress; faction color on the tower caps, keep roof, banner."""
    m = Model()
    _pad(m, 0, 13, 0, 13)
    # curtain walls in castle stone
    m.box(1, 12, 1, 12, 1, 4, MASONRY)
    m.clear(3, 10, 3, 10, 1, 4)  # hollow courtyard (hidden anyway)
    # crenellations along the front and right parapets — spaced merlons, the
    # dotted trim line that keeps the curtain wall from reading as a slab
    for i in range(1, 13, 2):
        m.set(i, 12, 5, TRIM)
        m.set(12, i, 5, TRIM)
        m.set(i, 1, 5, TRIM)
        m.set(1, i, 5, TRIM)
    # corner towers, capped in the owner's color at parapet height — the
    # rear corner sets the sprite's top line, so the height budget goes to
    # the central keep instead
    for tx, ty in ((1, 1), (1, 11), (11, 1), (11, 11)):
        m.box(tx, tx + 1, ty, ty + 1, 1, 4, MASONRY)
        m.box(tx, tx + 1, ty, ty + 1, 5, 5, ROOF_TRIM)
    # gatehouse: arched gate with a wooden door on the front wall
    m.box(5, 8, 12, 12, 1, 4, MASONRY_DK)
    m.box(6, 7, 12, 12, 1, 3, "wood")
    m.set(6, 12, 4, DETAIL)
    m.set(7, 12, 4, DETAIL)
    # central stone keep under a faction roof, banner mast above
    m.box(4, 9, 4, 9, 1, 6, MASONRY)
    m.box(4, 9, 4, 9, 7, 7, ROOF)
    m.box(5, 8, 5, 8, 8, 8, ROOF_TRIM)
    m.chamfer(5, 8, 5, 8, 8, 8)
    _windows(m, "y", 5, 8, 9, 3, 6, 31)
    m.box(6, 6, 6, 6, 9, 10, METAL)
    m.box(7, 8, 6, 6, 9, 10, ROOF_TRIM)  # banner
    return m


def airport() -> Model:
    """A hangar with an arched roof and a glass-cab control tower."""
    m = Model()
    # apron plate
    _pad(m, 0, 13, 3, 13)
    # hangar: concrete walls under a faction barrel roof, doors facing the
    # runway (front)
    m.box(1, 8, 6, 13, 1, 4, WALL)
    m.box(1, 8, 7, 12, 5, 5, ROOF)  # arch tier 1
    m.box(2, 7, 8, 11, 6, 6, ROOF)  # arch crown
    m.box(2, 7, 9, 10, 6, 6, ROOF_TRIM)  # lit ridge along the barrel
    m.chamfer(2, 7, 8, 11, 6, 6)
    m.box(2, 7, 13, 13, 1, 3, DETAIL)  # hangar door
    m.box(4, 5, 13, 13, 1, 3, METAL)  # door seam
    m.box(1, 8, 6, 6, 1, 4, WALL_DK)  # rear wall
    # control tower with glass cab and radar
    m.box(10, 12, 4, 6, 1, 4, WALL)
    m.box(9, 13, 3, 7, 5, 5, WALL_DK)  # balcony ring
    m.box(10, 12, 4, 6, 6, 6, "glass_dk")
    m.box(10, 12, 4, 6, 7, 7, ROOF_TRIM)  # cap
    m.set(11, 5, 8, DETAIL)  # radar knob
    # windsock on the apron corner
    m.box(13, 13, 11, 11, 1, 4, METAL)
    m.set(13, 12, 4, "amber")
    return m


def port() -> Model:
    """A quay over the water: warehouse, gantry crane, stacked containers."""
    m = Model()
    # quay deck standing on pilings
    m.box(0, 13, 4, 13, 1, 1, WALL)
    for x in range(0, 14, 3):
        m.set(x, 4, 0, WALL_DK)  # pilings at the water edge
    for x in range(14):
        m.set(x, 4, 1, WALL_DK)  # quay edge trim
    # warehouse: concrete walls under a shallow faction gabled roof
    m.box(1, 6, 7, 13, 2, 5, WALL)
    m.box(1, 6, 8, 12, 6, 6, ROOF)
    m.box(1, 6, 10, 10, 7, 7, ROOF_TRIM)  # ridge
    m.box(3, 4, 13, 13, 2, 4, DETAIL)  # cargo door
    # gantry crane over the dockside
    m.box(9, 10, 11, 12, 2, 7, METAL)
    m.box(9, 10, 4, 12, 8, 8, METAL)  # jib reaching the water
    m.set(9, 5, 7, DETAIL)  # cable
    m.set(9, 5, 6, DETAIL)
    m.box(9, 10, 11, 12, 8, 9, DETAIL)  # cab + counterweight
    # container stack on the quay
    m.box(11, 13, 6, 8, 2, 2, ROOF)
    m.box(11, 13, 6, 7, 3, 3, ROOF_TRIM)
    m.set(11, 6, 3, "amber")  # one lit marker, not a lit roof
    # bollards
    m.set(1, 5, 2, DETAIL)
    m.set(6, 5, 2, DETAIL)
    m.set(12, 5, 2, DETAIL)
    return m


BUILDINGS = {
    "city": city,
    "base": base,
    "hq": hq,
    "airport": airport,
    "port": port,
}

# The neutral row strips hue: an unowned property must not read as lit or
# owned, so every hue-carrying material resolves to a grey (design review
# 2026-08-13). The greys are the ladder above rather than the pale
# `rock`/`stone_dk` pair, for the reason the ladder itself moved: `rock` lit a
# top plane at L200 and `stone_dk` at L176, which put the row nobody owns the
# furthest into the units' band. Every entry is a rung, so an unowned property
# is keyed exactly like an owned one — the roof plane lands a rung above the
# wall and its ridge on TRIM, which is the same three-step read with the hue
# taken out. Owned rows keep their accents untouched, so the lit-window glint
# is an owned property's alone. `bore` stays — the palette has no dark true
# grey and its few pixels read black. The machinery greys need no entry now
# that the ladder itself is built of them.
_NEUTRAL_GREYS = {
    "amber": TRIM,  # lit windows, hazard stripe, windsock, container marker
    "glass_dk": METAL,  # window and cab glazing
    "wood": WALL_DK,  # doors, crates
    "leaf": METAL,  # plaza planter
    "leaf_dk": WALL,
    ROOF: METAL,  # roof planes: the slate theme's cast still reads owned
    ROOF_TRIM: TRIM,  # and their ridges, caps and banner
    "body_lt": TRIM,
}


def model_for(bid: str, fac: Faction) -> Model:
    """The property building's model for one faction row."""
    m = BUILDINGS[bid]()
    if fac.key == "neutral":
        for pos, mat in m.vox.items():
            m.vox[pos] = _NEUTRAL_GREYS.get(mat, mat)
    return m
