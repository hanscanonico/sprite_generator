"""The 14 terrain tiles, drawn native at the 64px atlas cell.

Ground hues are the game's tools/generate_tiles.gd palette, revalued under
the ceiling below so scenery never out-keys an army; the detail on top
(painted canopies, terraced mountains, foam, wear) is what this generator
adds. Ground fills are seamless — repeated tiles butt with no
border treatment (design review 2026-08-13: the old darkened-edge
convention read as a seam grid over any open field). Non-property tiles
are identical on every faction row; property tiles compose a
faction-tinted voxel building onto their ground.
"""

from __future__ import annotations

from PIL import Image

from . import buildings
from .palette import RGB, FACTIONS, Faction, darken, h01, lighten, mix
from .voxel import place_in_cell, render

CELL = 64

# The terrain value ceiling (fix spec round 4, item 7). The rule was not
# merely unimplemented, it was inverted: plains sat at median L174, road L183
# and shoal L202 while unit pixels top out at L145-165 at the 95th percentile,
# so the ground out-keyed 95% of every army on the board. The top of the ramp
# is reserved for units — L175-255 is theirs — and terrain is authored under
# that line rather than dimmed afterwards, because a post-multiply over a
# finished tile flattens the contrast that separates one ground from another.
TERRAIN_VALUE_CEILING = 175.0  # no more than 5% of a tile's pixels above it
TERRAIN_MEDIAN_CEILING = 165.0  # and no tile's median may reach it
# Property buildings out-keyed units by ~90L (highlights at L248 against a
# unit 95th percentile of 155). Units carry their own highlight band above
# L200; a building may only glint into it — lit windows, glazing — so its
# share there stays a third of the share the unit sheet is held to.
BUILDING_KEY_CEILING = 200.0

# generate_tiles.gd's hues, revalued under the ceiling above. The hues are the
# map's own; what moved is their value, plus the three tans that had collapsed
# into one: road, bridge deck and shoal sand now sit ~18L apart with a hue
# split — gravel grey, timber brown, beach sand — so movement cost reads from
# across the room.
GRASS = (108, 181, 73)  # L158
GRASS_DARK = (81, 150, 54)  # L131
ROAD = (146, 142, 133)  # gravel, L142 — road is ground
ROAD_DARK = (115, 111, 103)  # L112
TIMBER = (150, 120, 87)  # bridge deck, L124 — bridge is structure
TIMBER_DARK = (113, 90, 65)  # L93
WATER = (63, 143, 220)  # 3f8fdc
WATER_DARK = (42, 111, 191)  # 2a6fbf
WATER_LIGHT = (113, 179, 219)  # L168
SAND = (178, 166, 127)  # L166
SAND_DARK = (150, 139, 106)  # L139
ASPHALT = (111, 116, 124)  # 6f747c
SNOW = (168, 174, 182)  # cool foam/marking grey, L173

# Woods canopy tones (design review round 3): the tile is a filled canopy
# with its own value band — clearly darker than plains underfoot and than
# verdant hull green (58, 130, 64), so a green unit standing in woods stays
# separable from the tile it occupies.
CANOPY = (36, 96, 44)
CANOPY_DK = (24, 70, 33)
CANOPY_LT = (82, 152, 74)
TRUNK = (109, 76, 65)


def luminance(c: RGB) -> float:
    """Rec. 709 luma, the scale every ceiling in this module is stated on."""
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _lit(c: RGB, t: float) -> RGB:
    """A highlight, held under the ceiling. Lightening is the one way an
    authored tone leaves its band, so the ceiling is applied here — on the
    tone, at the moment it is chosen — and scaling keeps its hue."""
    hi = lighten(c, t)
    lum = luminance(hi)
    if lum <= TERRAIN_VALUE_CEILING:
        return hi
    k = TERRAIN_VALUE_CEILING / lum
    return (round(hi[0] * k), round(hi[1] * k), round(hi[2] * k))


def _ground(c: RGB, salt: int, grain: float = 0.03) -> Image.Image:
    """Base tile: edge-to-edge fill with 4px-block grain (kept at 4px so it
    survives the game's 4:1 nearest downsample). No border treatment — the
    border must be statistically indistinguishable from the interior so
    repeated ground tiles butt seamlessly."""
    img = Image.new("RGBA", (CELL, CELL), (*c, 255))
    px = img.load()
    for by in range(0, CELL, 4):
        for bx in range(0, CELL, 4):
            n = (h01(bx, by, salt) - 0.5) * grain * 2
            t = _lit(c, n) if n > 0 else darken(c, -n)
            for yy in range(by, by + 4):
                for xx in range(bx, bx + 4):
                    px[xx, yy] = (*t, 255)
    return img


def _rect(img: Image.Image, x0: int, y0: int, w: int, h: int, c: RGB) -> None:
    px = img.load()
    for yy in range(max(0, y0), min(CELL, y0 + h)):
        for xx in range(max(0, x0), min(CELL, x0 + w)):
            px[xx, yy] = (*c, 255)


def _paste_prop(tile: Image.Image, prop: Image.Image, cx: int, bottom: int) -> None:
    place_in_cell(tile, prop, cx - prop.width // 2, bottom - prop.height)


# ---------------------------------------------------------------------------
# plain grounds
# ---------------------------------------------------------------------------


def road() -> Image.Image:
    t = _ground(ROAD, 1)
    # tire-wear bands
    _rect(t, 4, 18, 56, 3, mix(ROAD, ROAD_DARK, 0.2))
    _rect(t, 4, 43, 56, 3, mix(ROAD, ROAD_DARK, 0.2))
    # the classic centre dashes, thinned to read as lane markings
    _rect(t, 12, 30, 12, 4, ROAD_DARK)
    _rect(t, 40, 30, 12, 4, ROAD_DARK)
    # a few embedded stones
    for sx, sy in ((22, 12), (50, 50), (8, 54), (34, 8)):
        _rect(t, sx, sy, 3, 2, ROAD_DARK)
        _rect(t, sx, sy, 2, 1, _lit(ROAD, 0.12))
    return t


def plains() -> Image.Image:
    t = _ground(GRASS, 2)
    # grass tufts: a dark check with a light blade, like the old speckles
    # but drawn as 3px clusters
    spots = (
        (10, 12),
        (34, 8),
        (52, 22),
        (18, 30),
        (42, 38),
        (8, 44),
        (28, 52),
        (54, 48),
        (24, 20),
        (46, 12),
        (14, 56),
        (38, 24),
    )
    for i, (sx, sy) in enumerate(spots):
        _rect(t, sx, sy, 3, 2, GRASS_DARK)
        _rect(t, sx + (i % 2), sy - 1, 1, 1, _lit(GRASS, 0.18))
    # a couple of tiny wildflowers so big plains fields don't tile dead flat
    for fx, fy in ((30, 36), (50, 40)):
        _rect(t, fx, fy, 1, 1, SNOW)
        _rect(t, fx + 1, fy, 1, 1, (214, 163, 57))
    return t


# (crown x, crown y, radius) — clustered cover leaving two grass clearings,
# so the tile reads as one occupied canopy rather than scattered props.
_CROWNS = (
    (8, 6, 9),
    (26, 4, 10),
    (45, 8, 10),
    (60, 3, 8),
    (4, 20, 9),
    (19, 18, 10),
    (36, 24, 10),
    (58, 18, 9),
    (10, 34, 10),
    (27, 38, 9),
    (61, 33, 8),
    (5, 50, 9),
    (22, 54, 10),
    (42, 52, 10),
    (59, 50, 9),
    (34, 63, 8),
    (52, 62, 8),
)


def woods() -> Image.Image:
    """A filled canopy: crowns drawn back to front, each keeping its lit
    top-left rim, over grass that shows only in the clearings and at the
    fringe. The value drop against plains is the tile's read — cover, not
    decoration — and trunks at the fringe say the cover is trees."""
    t = _ground(GRASS, 3)
    px = t.load()
    covered = [[False] * CELL for _ in range(CELL)]
    for cx, cy, r in sorted(_CROWNS, key=lambda c: c[1]):
        rim = (r - 2) * (r - 2)
        for yy in range(max(0, cy - r), min(CELL, cy + r + 1)):
            for xx in range(max(0, cx - r), min(CELL, cx + r + 1)):
                dx, dy = xx - cx, yy - cy
                d = dx * dx + dy * dy
                if d > r * r:
                    continue
                if d > rim:  # crown edge: lit toward the light, shaded away
                    c = CANOPY_LT if dx + dy * 1.5 < 0 else CANOPY_DK
                elif h01(xx, yy, 34) < 0.14:
                    c = CANOPY_DK  # leaf clumps
                else:
                    n = (h01(xx, yy, 33) - 0.5) * 0.12
                    c = _lit(CANOPY, n) if n > 0 else darken(CANOPY, -n)
                px[xx, yy] = (*c, 255)
                covered[yy][xx] = True
    # contact shadow along the canopy's lower fringe
    for x in range(CELL):
        for y in range(CELL - 1):
            if covered[y][x] and not covered[y + 1][x]:
                px[x, y + 1] = (*GRASS_DARK, 255)
    # trunks where the fringe meets the clearings
    for tx, ty in ((46, 31), (12, 59)):
        _rect(t, tx, ty, 2, 3, TRUNK)
        _rect(t, tx, ty, 1, 3, darken(TRUNK, 0.25))
    # a tuft in each clearing
    for sx, sy in ((50, 38), (5, 61)):
        _rect(t, sx, sy, 3, 2, GRASS_DARK)
    return t


def mountain() -> Image.Image:
    """A painted three-peak massif: light/dark faces split at each ridge,
    jagged dithered snow caps, altitude banding down to a talus skirt."""
    t = _ground(GRASS, 4)
    px = t.load()
    base_y = 56
    # (apex_x, apex_y, slope) — summit, right shoulder, low left foothill
    peaks = ((26, 10, 1.2), (46, 27, 1.3), (11, 36, 1.5))
    rock_hi = (166, 161, 153)
    rock_lt = (148, 144, 137)
    rock_dk = (117, 113, 108)
    rock_deep = (98, 95, 91)
    edge = (66, 63, 60)
    # cool light-grey snow, authored under TERRAIN_VALUE_CEILING: the caps
    # were the brightest thing on the board, louder than any unit highlight
    snow_lt = (164, 171, 182)
    snow_dk = (138, 148, 166)
    for x in range(4, 60):
        tops = [int(ay + s * abs(x - ax)) for ax, ay, s in peaks]
        y_top = min(tops)
        if y_top >= base_y - 2:
            continue
        owner = tops.index(y_top)
        ax, ay, _s = peaks[owner]
        lit = x <= ax
        # jagged snow line per column; only the two tall peaks hold snow
        zig = (x * 7) % 3 + ((x // 3) % 2) * 3
        snow_until = ay + 6 + zig if owner < 2 else y_top
        mid = (y_top + base_y) // 2
        for y in range(y_top, base_y):
            if y == y_top:
                c = edge
            elif y < snow_until:
                c = snow_lt if lit else snow_dk
            elif y == snow_until and (x + y) % 2 == 0:
                c = snow_dk if lit else mix(snow_dk, rock_dk, 0.5)  # melt dither
            elif y >= base_y - 5:
                c = rock_dk if lit else rock_deep  # talus skirt
            elif y < mid:
                c = rock_hi if lit else rock_dk  # sunlit high faces
            else:
                c = rock_lt if lit else rock_dk
            px[x, y] = (*c, 255)
    # ridge lines below the apexes and a few cracks
    for x, y0, ln in (
        (26, 17, 32),
        (18, 34, 10),
        (34, 30, 8),
        (46, 34, 16),
        (11, 41, 9),
    ):
        for y in range(y0, min(base_y - 1, y0 + ln)):
            if px[x, y][3] == 255 and px[x, y][:3] in (rock_hi, rock_lt, rock_dk):
                px[x, y] = (*mix(rock_dk, edge, 0.5), 255)
    # contact shadow and scree at the foot
    for x in range(6, 58):
        if px[x, base_y - 1][:3] in (rock_lt, rock_dk, rock_deep):
            px[x, base_y] = (*GRASS_DARK, 255)
    for sx, sy in ((8, 52), (52, 54), (14, 58), (46, 59)):
        _rect(t, sx, sy, 3, 2, GRASS_DARK)
    return t


def _water_base(deep: bool, salt: int) -> Image.Image:
    return _ground(WATER_DARK if deep else WATER, salt, grain=0.027)


def _glints(t: Image.Image, base: RGB, light: RGB, salt: int) -> None:
    """Three hash-placed flow glints: short, staggered, low-contrast.

    The old four dashes sat on the same rows in every repeated tile, and a
    stretch of water read as a lattice from across the room (round 3). The
    hash spreads them with no shared row; nothing here aligns to a grid.
    """
    for i in range(3):
        sx = 3 + int(h01(i, 0, salt) * 42)
        sy = 4 + int(h01(i, 1, salt) * 55)
        w = 7 + int(h01(i, 2, salt) * 7)
        _rect(t, sx, sy, w, 1, mix(base, light, 0.55))
        _rect(t, sx + 2 + i, sy + 1, max(3, w - 4), 1, mix(base, light, 0.3))


def river() -> Image.Image:
    t = _water_base(False, 5)
    _glints(t, WATER, WATER_LIGHT, 78)
    # rounded pebble breaking the current
    _rect(t, 28, 54, 6, 3, mix(WATER, WATER_DARK, 0.7))
    _rect(t, 29, 53, 4, 1, mix(WATER, WATER_LIGHT, 0.55))
    return t


def sea() -> Image.Image:
    t = _water_base(True, 6)
    _glints(t, WATER_DARK, WATER, 73)
    return t


def shoal() -> Image.Image:
    t = _ground(SAND, 7)
    # water across the bottom with a scalloped surf line — irregular foam
    # clusters, not the uniform dashes that read as road markings
    _rect(t, 0, 40, 64, 24, WATER)
    _rect(t, 0, 40, 64, 2, SAND_DARK)  # wet sand lip
    for k, sx in enumerate(range(0, 64, 8)):
        wob = int(h01(sx, 0, 41) * 3)
        _rect(t, sx, 41 + wob, 5 + (k % 2) * 2, 2, SNOW)
        _rect(t, sx + 2, 43 + wob, 3, 1, mix(WATER, SNOW, 0.55))
    _rect(t, 8, 52, 14, 2, WATER_LIGHT)
    _rect(t, 40, 56, 12, 2, WATER_LIGHT)
    # dry-sand speckles and a shell
    for sx, sy in ((12, 12), (36, 20), (24, 32), (48, 8), (54, 30)):
        _rect(t, sx, sy, 3, 2, SAND_DARK)
    _rect(t, 44, 24, 2, 2, SNOW)
    return t


def bridge() -> Image.Image:
    """A timber deck standing over the water. The deck is deliberately not
    the road tile's gravel: the two shared one dominant colour, so a bridge
    read as a road that happened to be wet."""
    t = _water_base(False, 8)
    # support shadows in the water under each pier
    for sx in (8, 28, 48):
        _rect(t, sx, 50, 10, 4, mix(WATER, (10, 30, 60), 0.35))
    _rect(t, 0, 12, 64, 40, TIMBER)
    _rect(t, 0, 12, 64, 2, _lit(TIMBER, 0.25))  # lit rail
    _rect(t, 0, 50, 64, 2, TIMBER_DARK)  # shaded rail
    _rect(t, 0, 14, 64, 1, TIMBER_DARK)
    # railing posts
    for sx in range(2, 64, 8):
        _rect(t, sx, 12, 2, 4, TIMBER_DARK)
        _rect(t, sx, 48, 2, 4, TIMBER_DARK)
    # plank courses across the deck, the structure's own grain
    for sy in range(18, 50, 6):
        _rect(t, 0, sy, 64, 1, mix(TIMBER, TIMBER_DARK, 0.55))
    # deck plank seams
    for sx in (21, 43):
        _rect(t, sx, 16, 1, 32, mix(TIMBER, TIMBER_DARK, 0.5))
    return t


def reef() -> Image.Image:
    t = _water_base(True, 9)
    spots = ((14, 22, 3), (40, 16, 2), (22, 44, 2), (48, 46, 3))
    for sx, sy, size in spots:
        # rock materials are faction-independent; any row renders the same
        rock = render(buildings.rock_outcrop(size), FACTIONS[0])
        # foam ring where the rock breaks the surface
        _rect(
            t,
            sx - rock.width // 2 - 2,
            sy - 2,
            rock.width + 4,
            2,
            mix(WATER_DARK, SNOW, 0.55),
        )
        _paste_prop(t, rock, sx, sy)
    _rect(t, 8, 56, 10, 2, WATER)
    _rect(t, 52, 8, 8, 2, WATER)
    return t


# ---------------------------------------------------------------------------
# property tiles
# ---------------------------------------------------------------------------


def _grass_lot(fac: Faction, building: str, salt: int) -> Image.Image:
    t = _ground(GRASS, salt)
    prop = render(buildings.model_for(building, fac), fac)
    _paste_prop(t, prop, 32, 61)
    return t


def airport(fac: Faction) -> Image.Image:
    t = _ground(ASPHALT, 10, grain=0.024)
    # runway strip across the lower apron
    _rect(t, 0, 44, 64, 16, _lit(ASPHALT, 0.08))
    _rect(t, 0, 44, 64, 1, _lit(ASPHALT, 0.25))
    _rect(t, 0, 59, 64, 1, darken(ASPHALT, 0.2))
    for sx in range(4, 64, 12):
        _rect(t, sx, 51, 6, 2, SNOW)  # centreline dashes
    _rect(t, 2, 46, 2, 12, SNOW)  # threshold bars
    _rect(t, 6, 46, 2, 12, SNOW)
    prop = render(buildings.model_for("airport", fac), fac)
    _paste_prop(t, prop, 31, 46)
    return t


def port(fac: Faction) -> Image.Image:
    t = _water_base(True, 11)
    _rect(t, 4, 50, 12, 2, WATER)  # harbour ripples
    _rect(t, 44, 56, 14, 2, WATER)
    prop = render(buildings.model_for("port", fac), fac)
    _paste_prop(t, prop, 32, 52)
    return t


# ---------------------------------------------------------------------------
# registry, in atlas column order 0..13
# ---------------------------------------------------------------------------

TERRAIN_ORDER: tuple[str, ...] = (
    "road",
    "plains",
    "woods",
    "mountain",
    "river",
    "city",
    "base",
    "hq",
    "sea",
    "airport",
    "port",
    "shoal",
    "bridge",
    "reef",
)
# Tiles whose art changes with the faction row (team-tinted properties).
PROPERTY: frozenset[str] = frozenset({"city", "base", "hq", "airport", "port"})

_PLAIN_TILES = {
    "road": road,
    "plains": plains,
    "woods": woods,
    "mountain": mountain,
    "river": river,
    "sea": sea,
    "shoal": shoal,
    "bridge": bridge,
    "reef": reef,
}
_LOT_SALTS = {"city": 12, "base": 13, "hq": 14}


def tile(tid: str, fac: Faction) -> Image.Image:
    """One 64x64 RGBA tile. Non-property tiles ignore the faction; every
    ground here is authored under TERRAIN_VALUE_CEILING and the buildings a
    property tile carries under BUILDING_KEY_CEILING, so nothing on the board
    needs dimming after the fact."""
    if tid in PROPERTY:
        if tid == "airport":
            return airport(fac)
        if tid == "port":
            return port(fac)
        return _grass_lot(fac, tid, _LOT_SALTS[tid])
    return _PLAIN_TILES[tid]()
