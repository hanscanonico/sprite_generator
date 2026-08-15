"""The 14 terrain tiles, drawn native at the 64px atlas cell.

Ground colors mirror the game's tools/generate_tiles.gd so a regenerated
atlas drops into the same map without shifting the world's palette; the
detail on top (painted canopies, terraced mountains, foam, wear) is what
this generator adds. Ground fills are seamless — repeated tiles butt with no
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

# Connection bits, shared with autotile.py: which neighbours a tile's feature
# continues into.
N, E, S, W = 1, 2, 4, 8

# generate_tiles.gd palette (hex constants), the map's established hues.
# SAND and SNOW sit below the original hex values on purpose: terrain must
# never outshine a unit (see VALUE_CEILING), and those two were the only
# ground tones over the line.
GRASS = (120, 200, 80)  # 78c850
GRASS_DARK = (90, 166, 60)  # 5aa63c
ROAD = (201, 184, 132)  # c9b884
ROAD_DARK = (168, 152, 104)  # a89868
WATER = (63, 143, 220)  # 3f8fdc
WATER_DARK = (42, 111, 191)  # 2a6fbf
WATER_LIGHT = (124, 196, 240)  # 7cc4f0
SAND = (219, 206, 160)  # e0d3a4 pulled under the ceiling
SAND_DARK = (196, 181, 133)  # c4b585
ASPHALT = (111, 116, 124)  # 6f747c
SNOW = (202, 208, 216)  # cool foam/marking grey, capped (was eeeeee)

# Woods canopy tones (design review round 3): the tile is a filled canopy
# with its own value band — clearly darker than plains underfoot and than
# verdant hull green (58, 130, 64), so a green unit standing in woods stays
# separable from the tile it occupies.
CANOPY = (36, 96, 44)
CANOPY_DK = (24, 70, 33)
CANOPY_LT = (82, 152, 74)
TRUNK = (109, 76, 65)

# Terrain value ceiling (design review round 3): the eye must go to units,
# so no ground pixel may reach the unit sheet's top-face highlights (their
# p99 luminance is ~0.97). Every non-property tile is passed through
# _cap_value; the tones above are authored under the line so the cap is a
# guarantee, not the look.
VALUE_CEILING = 0.82


def _cap_value(img: Image.Image) -> Image.Image:
    """Scale any pixel brighter than VALUE_CEILING back down onto it."""
    ceil = VALUE_CEILING * 255.0
    px = img.load()
    for yy in range(img.height):
        for xx in range(img.width):
            r, g, b, a = px[xx, yy]
            lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
            if lum > ceil:
                k = ceil / lum
                px[xx, yy] = (round(r * k), round(g * k), round(b * k), a)
    return img


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
            t = lighten(c, n) if n > 0 else darken(c, -n)
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
        _rect(t, sx, sy, 2, 1, lighten(ROAD, 0.12))
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
        _rect(t, sx + (i % 2), sy - 1, 1, 1, lighten(GRASS, 0.18))
    # a couple of tiny wildflowers so big plains fields don't tile dead flat
    for fx, fy in ((30, 36), (50, 40)):
        _rect(t, fx, fy, 1, 1, SNOW)
        _rect(t, fx + 1, fy, 1, 1, (235, 179, 63))
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


def _crowns_within(open_edges: int) -> tuple[tuple[int, int, int], ...]:
    """The crown table with every disc pulled fully inside the cell on the
    edges the wood does not continue across, so a crown is never sliced flat
    by the tile border. A pulled crown stays tangent to that border, so the
    fringe scallops between crowns instead of gapping away from it. Crowns
    keep their authored overhang on a continued edge, which is what lets the
    interior of a wood butt seamlessly."""
    pulled = []
    for cx, cy, r in _CROWNS:
        if open_edges & W:
            cx = max(cx, r)
        if open_edges & E:
            cx = min(cx, CELL - 1 - r)
        if open_edges & N:
            cy = max(cy, r)
        if open_edges & S:
            cy = min(cy, CELL - 1 - r)
        pulled.append((cx, cy, r))
    return tuple(pulled)


def woods(open_edges: int = 0) -> Image.Image:
    """A filled canopy: crowns drawn back to front, each keeping its lit
    top-left rim, over grass that shows only in the clearings and at the
    fringe. The value drop against plains is the tile's read — cover, not
    decoration — and trunks at the fringe say the cover is trees.

    `open_edges` names the borders the wood ends at (see `_crowns_within`);
    0 — every edge continued — is the atlas tile."""
    t = _ground(GRASS, 3)
    px = t.load()
    covered = [[False] * CELL for _ in range(CELL)]
    for cx, cy, r in sorted(_crowns_within(open_edges), key=lambda c: c[1]):
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
                    c = lighten(CANOPY, n) if n > 0 else darken(CANOPY, -n)
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
    rock_hi = (178, 173, 164)
    rock_lt = (158, 154, 146)
    rock_dk = (117, 113, 108)
    rock_deep = (98, 95, 91)
    edge = (66, 63, 60)
    # cool light-grey snow, held under VALUE_CEILING: the caps were the
    # brightest thing on the board, louder than any unit highlight (round 3)
    snow_lt = (198, 206, 220)
    snow_dk = (164, 176, 196)
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
    t = _water_base(False, 8)
    # support shadows in the water under each pier
    for sx in (8, 28, 48):
        _rect(t, sx, 50, 10, 4, mix(WATER, (10, 30, 60), 0.35))
    # road deck carried over the water (same band as the old art)
    _rect(t, 0, 12, 64, 40, ROAD)
    _rect(t, 0, 12, 64, 2, mix(ROAD, (255, 255, 255), 0.25))  # lit rail
    _rect(t, 0, 50, 64, 2, ROAD_DARK)  # shaded rail
    _rect(t, 0, 14, 64, 1, ROAD_DARK)
    # railing posts
    for sx in range(2, 64, 8):
        _rect(t, sx, 12, 2, 4, ROAD_DARK)
        _rect(t, sx, 48, 2, 4, ROAD_DARK)
    # centre dashes matching the road tile
    _rect(t, 12, 30, 12, 4, ROAD_DARK)
    _rect(t, 40, 30, 12, 4, ROAD_DARK)
    # deck plank seams
    for sx in (21, 43):
        _rect(t, sx, 16, 1, 32, mix(ROAD, ROAD_DARK, 0.5))
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
    _rect(t, 0, 44, 64, 16, lighten(ASPHALT, 0.08))
    _rect(t, 0, 44, 64, 1, lighten(ASPHALT, 0.25))
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
    """One 64x64 RGBA tile. Non-property tiles ignore the faction and pass
    through the value cap; property grounds are authored under it and the
    buildings on top are the units' asset class, not scenery."""
    if tid in PROPERTY:
        if tid == "airport":
            return airport(fac)
        if tid == "port":
            return port(fac)
        return _grass_lot(fac, tid, _LOT_SALTS[tid])
    return _cap_value(_PLAIN_TILES[tid]())
