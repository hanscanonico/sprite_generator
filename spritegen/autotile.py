"""Direction-aware tile variants: road/river autotiles, bridges, coastlines.

The main terrain atlas keeps its fixed 14-column contract (whole-tile road,
E-W river and bridge) so it stays a drop-in for the game. This module is the
opt-in upgrade path: 16-variant connection sets for roads and rivers, both
bridge orientations, and coast tiles for sea that borders land — so roads can
turn, rivers can flow north-south, and shorelines stop being a hard blue
edge. The demo map composes from these, and sprite_generator exports the
variant sheets under out/autotiles/. Deterministic like everything else here.

Connection masks are N|E|S|W bits naming which neighbours continue the
feature (for coast: which edges touch land). A road's mask 0 falls back to
E|W; a river's is a pond, since a watercourse joined to nothing is a pool.
"""

from __future__ import annotations

from PIL import Image

from .palette import h01, lighten, mix
from .terrain import (
    CELL,
    E,
    GRASS_DARK,
    N,
    PLAINS_PHASES,
    ROAD,
    ROAD_DARK,
    S,
    SAND,
    SAND_DARK,
    SEA_PHASES,
    SNOW,
    TIMBER,
    TIMBER_DARK,
    W,
    WATER,
    WATER_DARK,
    WATER_LIGHT,
    _ground,
    _lit,
    _rect,
    plains,
    sea,
    woods,
)

_RLO, _RHI = 22, 42  # road band bounds (20px wide)
_WLO, _WHI = 20, 44  # river channel bounds (24px wide)
_BLO, _BHI = 16, 48  # the bank the channel is cut into: 4px of shore a side

# Bank tones, mixed from the ground and water constants the atlas already
# authors under the terrain ceiling rather than written as fresh hexes — the
# woods-seam rule: a bank that carried its own green would step against the
# plains it borders the moment either moved. Silt where the grass gives out,
# its shaded outer edge, and wet mud at the waterline.
BANK = mix(SAND, GRASS_DARK, 0.2)
BANK_DARK = mix(BANK, GRASS_DARK, 0.55)
BANK_WET = mix(SAND_DARK, WATER_DARK, 0.25)

# A run that stops has a rounded nose rather than a sawn-off bar: the water
# ends on a semicircle centred in the joint square, the bank ringing it at the
# same width it keeps along the channel.
_HEAD_R = (_WHI - _WLO) / 2
_BANK_R = _HEAD_R + (_WLO - _BLO)
_POND_R = 14.0  # a standalone cell reads as a pool, so its water is wider

# The pond's own bank (design review round 6). One width and one tone around a
# circle of water is a button: the round-5 pond read as a badge with a cream
# outline. Everything about this ring varies except its minimum — water may
# never meet grass, which is the lip rule the channel tiles are held to — so it
# is widest and darkest on the lower-right, the shadow side away from the light
# every tile is lit from, and thins to that lip in the notches the reeds stand
# in. Its tone is ~20L under the channel's own BANK, mixed from the same ground
# constants: a bank that carried its own hex would step against the shore the
# moment either moved.
POND_BANK = mix(BANK, GRASS_DARK, 0.65)
POND_BANK_DK = mix(POND_BANK, BANK_WET, 0.55)
_POND_LIP = 1
_POND_BANK_MIN, _POND_BANK_MAX = 2.0, 7.0
_POND_SHADE_DIR = (0.5**0.5, 0.5**0.5)  # down-right, away from the light
# Screen directions the reeds stand in, and how wide a clump notches the ring.
_REEDS = ((-0.94, -0.34), (0.20, -0.98), (-0.55, 0.84))
_REED_NOTCH = 0.93


def _closed_half(x: int, y: int, open_bit: int) -> bool:
    """Whether a pixel is past the joint centre on the side a one-connection
    run terminates — the half the nose is cut into."""
    return {
        N: y * 2 >= CELL,
        S: y * 2 < CELL,
        E: x * 2 < CELL,
        W: x * 2 >= CELL,
    }[open_bit]


def _radius(x: int, y: int) -> float:
    half = CELL / 2
    return ((x + 0.5 - half) ** 2 + (y + 0.5 - half) ** 2) ** 0.5


def _fill_arms(img: Image.Image, mask: int, lo: int, hi: int, c) -> None:
    """The joint square plus a rect running to each connected edge."""
    _rect(img, lo, lo, hi - lo, hi - lo, c)
    if mask & N:
        _rect(img, lo, 0, hi - lo, lo, c)
    if mask & S:
        _rect(img, lo, hi, hi - lo, CELL - hi, c)
    if mask & E:
        _rect(img, hi, lo, CELL - hi, hi - lo, c)
    if mask & W:
        _rect(img, 0, lo, lo, hi - lo, c)


def _edge_pass(img: Image.Image, inside, edge_c, outside_c=None) -> None:
    """Outline a filled region: inside pixels touching outside get edge_c,
    outside pixels touching inside optionally get outside_c (banks)."""
    px = img.load()
    marks = []
    for y in range(CELL):
        for x in range(CELL):
            a = inside(px[x, y][:3])
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if not (0 <= nx < CELL and 0 <= ny < CELL):
                    continue
                if a != inside(px[nx, ny][:3]):
                    if a:
                        marks.append((x, y, edge_c))
                    elif outside_c is not None:
                        marks.append((x, y, outside_c))
                    break
    for x, y, c in marks:
        px[x, y] = (*c, 255)


def road_tile(mask: int) -> Image.Image:
    """A road running to each connected edge over a plains base."""
    if mask == 0:
        mask = E | W
    t = plains()
    _fill_arms(t, mask, _RLO, _RHI, ROAD)
    _edge_pass(t, lambda c: c == ROAD, ROAD_DARK)
    # centre dashes along each arm, clear of the joint
    dash = ROAD_DARK
    cy = (_RLO + _RHI) // 2 - 2
    if mask & W:
        _rect(t, 6, cy, 9, 3, dash)
    if mask & E:
        _rect(t, 49, cy, 9, 3, dash)
    if mask & N:
        _rect(t, cy, 6, 3, 9, dash)
    if mask & S:
        _rect(t, cy, 49, 3, 9, dash)
    # a few embedded stones for wear
    for sx, sy in ((26, 26), (36, 37), (30, 34)):
        _rect(t, sx, sy, 3, 2, ROAD_DARK)
        _rect(t, sx, sy, 2, 1, lighten(ROAD, 0.12))
    return t


def _shape_river(t: Image.Image, base: Image.Image, mask: int) -> None:
    """Cut the channel and its banks into the plains plate `t`, `base` being
    the untouched plate a rounded end gives ground back to."""
    if mask == 0:
        _pond(t, base)
        return
    _fill_arms(t, mask, _BLO, _BHI, BANK)
    _fill_arms(t, mask, _WLO, _WHI, WATER)
    if mask in (N, E, S, W):
        _round_head(t, base, mask)


def _bank_width(ux: float, uy: float) -> float:
    """How far the pond's bank reaches out along the unit direction (ux, uy):
    widest down the shadow diagonal, cut back to the lip in a reed notch."""
    for rx, ry in _REEDS:
        if ux * rx + uy * ry > _REED_NOTCH:
            return _POND_LIP
    shade = ux * _POND_SHADE_DIR[0] + uy * _POND_SHADE_DIR[1]
    return _POND_BANK_MIN + (_POND_BANK_MAX - _POND_BANK_MIN) * (0.5 + 0.5 * shade)


def _reeds(t: Image.Image) -> None:
    """Blades standing in the notches, over the plate rather than over the
    bank: the interruption is what stops the ring reading as a stamped
    outline, and the lip guard is what keeps it a bank all the way round."""
    px = t.load()
    half = CELL / 2
    for rx, ry in _REEDS:
        bx = round(half + rx * (_POND_R + _POND_LIP + 2))
        by = round(half + ry * (_POND_R + _POND_LIP + 2))
        for dx, height in ((-2, 2), (0, 4), (2, 3)):
            for y in range(by - height + 1, by + 1):
                x = bx + dx
                if not (0 <= x < CELL and 0 <= y < CELL):
                    continue
                if _radius(x, y) > _POND_R + _POND_LIP:
                    px[x, y] = (*GRASS_DARK, 255)


def _pond(t: Image.Image, base: Image.Image) -> None:
    """A banked pool: water inside `_POND_R`, a bank of varying weight around
    it, the plate itself beyond — a lone cell is a pond, not a bar."""
    px, bp = t.load(), base.load()
    half = CELL / 2
    for y in range(CELL):
        for x in range(CELL):
            dx, dy = x + 0.5 - half, y + 0.5 - half
            d = (dx * dx + dy * dy) ** 0.5
            if d <= _POND_R:
                px[x, y] = (*WATER, 255)
                continue
            ux, uy = dx / d, dy / d
            if d > _POND_R + _bank_width(ux, uy):
                px[x, y] = bp[x, y]
                continue
            shade = ux * _POND_SHADE_DIR[0] + uy * _POND_SHADE_DIR[1]
            px[x, y] = (*(POND_BANK_DK if shade > 0.25 else POND_BANK), 255)
    _reeds(t)


def _round_head(t: Image.Image, base: Image.Image, open_bit: int) -> None:
    """Taper the closed end of a one-connection run to a rounded nose."""
    px, bp = t.load(), base.load()
    for y in range(CELL):
        for x in range(CELL):
            if not _closed_half(x, y, open_bit):
                continue
            d = _radius(x, y)
            if d <= _HEAD_R:
                continue
            px[x, y] = (*BANK, 255) if d <= _BANK_R else bp[x, y]


def river_tile(mask: int, salt: int = 0) -> Image.Image:
    """A river channel to each connected edge, banked and streaked to match
    its flow direction. `salt` shifts the streak placement so a run of
    same-mask tiles doesn't chain its glints into a dashed line."""
    base = plains()
    t = base.copy()
    _shape_river(t, base, mask)
    shore = {BANK, POND_BANK, POND_BANK_DK, WATER}
    _edge_pass(t, lambda c: c in shore, BANK_DARK, GRASS_DARK)
    _edge_pass(t, lambda c: c == WATER, WATER_DARK, BANK_WET)
    if mask == 0:
        _rect(t, 25, 30, 7, 2, WATER_LIGHT)
        _rect(t, 34, 36, 5, 1, mix(WATER, WATER_LIGHT, 0.5))
        return t
    # flow streaks oriented along each arm, drifted per tile
    half = mix(WATER, WATER_LIGHT, 0.5)
    d1 = int(h01(salt, 1, 45) * 10) - 5
    d2 = int(h01(salt, 2, 45) * 8) - 4
    if mask & W:
        _rect(t, 5 + (d1 % 4), 27 + d2 // 2, 9, 2, WATER_LIGHT)
        _rect(t, 8, 36 + d1 // 3, 7, 1, half)
    if mask & E:
        _rect(t, 47 + (d2 % 4), 27 - d1 // 3, 9, 2, WATER_LIGHT)
        _rect(t, 46, 36 + d2 // 2, 7, 1, half)
    if mask & N:
        _rect(t, 27 + d1, 5 + (d2 % 4), 2, 9, WATER_LIGHT)
        _rect(t, 36 + d2, 8, 1, 7, half)
    if mask & S:
        _rect(t, 27 + d2, 47 + (d1 % 4), 2, 9, WATER_LIGHT)
        _rect(t, 36 + d1, 46, 1, 7, half)
    # one glint in the joint
    _rect(t, 29 + d1 // 2, 31 + d2 // 2, 4, 1, WATER_LIGHT)
    return t


def _bridge_h() -> Image.Image:
    """Horizontal timber deck carried over a north-south river."""
    t = river_tile(N | S)
    # support shadows in the water above and below the deck
    for sy in (14, 46):
        _rect(t, 24, sy, 7, 4, mix(WATER, (10, 30, 60), 0.35))
        _rect(t, 34, sy, 7, 4, mix(WATER, (10, 30, 60), 0.35))
    # timber deck, slightly wider than the gravel road band it joins
    _rect(t, 0, 20, 64, 24, TIMBER)
    _rect(t, 0, 20, 64, 2, _lit(TIMBER, 0.25))  # lit rail
    _rect(t, 0, 42, 64, 2, TIMBER_DARK)  # shaded rail
    _rect(t, 0, 22, 64, 1, TIMBER_DARK)
    for sx in range(2, 64, 8):
        _rect(t, sx, 20, 2, 4, TIMBER_DARK)  # railing posts
        _rect(t, sx, 40, 2, 4, TIMBER_DARK)
    for sy in range(24, 42, 6):
        _rect(t, 0, sy, 64, 1, mix(TIMBER, TIMBER_DARK, 0.55))  # plank courses
    for sx in (21, 43):
        _rect(t, sx, 24, 1, 16, mix(TIMBER, TIMBER_DARK, 0.5))  # plank seams
    return t


def bridge_tile(horizontal: bool = True) -> Image.Image:
    t = _bridge_h()
    return t if horizontal else t.transpose(Image.ROTATE_90)


def coast_tile(edges: int, corners: int = 0) -> Image.Image:
    """Sea with a sand-and-surf shoreline along each landward edge.

    `edges` marks which sides touch land; `corners` (same N|E|S|W bits,
    N=north-east going clockwise: N->NE, E->SE, S->SW, W->NW) adds a small
    corner patch where land touches only diagonally.
    """
    t = sea()
    foam_mix = mix(WATER, SNOW, 0.55)

    def surf(along_x: bool, sand_at_low: bool) -> None:
        # 4px dry sand, 1px wet lip, then irregular foam in the water
        if along_x:
            y_sand = 0 if sand_at_low else CELL - 4
            _rect(t, 0, y_sand, CELL, 4, SAND)
            y_lip = 4 if sand_at_low else CELL - 5
            _rect(t, 0, y_lip, CELL, 1, SAND_DARK)
            for k, sx in enumerate(range(0, CELL, 8)):
                wob = int(h01(sx, y_lip, 43) * 2)
                y_foam = (5 + wob) if sand_at_low else (CELL - 7 - wob)
                _rect(t, sx, y_foam, 5 + (k % 2) * 2, 1, SNOW)
                _rect(t, sx + 2, y_foam + (1 if sand_at_low else -1), 3, 1, foam_mix)
        else:
            x_sand = 0 if sand_at_low else CELL - 4
            _rect(t, x_sand, 0, 4, CELL, SAND)
            x_lip = 4 if sand_at_low else CELL - 5
            _rect(t, x_lip, 0, 1, CELL, SAND_DARK)
            for k, sy in enumerate(range(0, CELL, 8)):
                wob = int(h01(x_lip, sy, 44) * 2)
                x_foam = (5 + wob) if sand_at_low else (CELL - 7 - wob)
                _rect(t, x_foam, sy, 1, 5 + (k % 2) * 2, SNOW)
                _rect(t, x_foam + (1 if sand_at_low else -1), sy + 2, 1, 3, foam_mix)

    if edges & N:
        surf(True, True)
    if edges & S:
        surf(True, False)
    if edges & W:
        surf(False, True)
    if edges & E:
        surf(False, False)

    # diagonal-only land: a small sand nub in that corner, skipped when an
    # adjacent edge strip already reaches it
    nubs = {N: (CELL - 6, 0), E: (CELL - 6, CELL - 6), S: (0, CELL - 6), W: (0, 0)}
    adjacent = {N: N | E, E: E | S, S: S | W, W: W | N}
    for bit, (cx, cy) in nubs.items():
        if corners & bit and not edges & adjacent[bit]:
            _rect(t, cx, cy, 6, 6, SAND)
            _rect(t, cx, cy + (5 if cy == 0 else 0), 6, 1, SAND_DARK)
            _rect(t, cx + (5 if cx == 0 else 0), cy, 1, 6, SAND_DARK)
            fx = cx + (6 if cx == 0 else -2)
            fy = cy + (6 if cy == 0 else -2)
            _rect(t, fx, fy, 2, 1, SNOW)
    return t


def shoal_tile(edges: int) -> Image.Image:
    """A beach tile: dry sand with surf along each seaward edge."""
    if edges == 0:
        edges = S
    t = _ground(SAND, 7)
    foam_mix = mix(WATER, SNOW, 0.55)

    def surf(along_x: bool, water_at_low: bool) -> None:
        # 8px of water, a wet-sand lip, then scalloped breaking foam
        if along_x:
            y_w = 0 if water_at_low else CELL - 8
            _rect(t, 0, y_w, CELL, 8, WATER)
            y_lip = 8 if water_at_low else CELL - 9
            _rect(t, 0, y_lip, CELL, 1, SAND_DARK)
            for k, sx in enumerate(range(0, CELL, 8)):
                wob = int(h01(sx, y_lip, 46) * 2)
                y_f = (5 - wob) if water_at_low else (CELL - 7 + wob)
                _rect(t, sx, y_f, 5 + (k % 2) * 2, 2, SNOW)
                _rect(t, sx + 2, y_f + (-1 if water_at_low else 2), 3, 1, foam_mix)
        else:
            x_w = 0 if water_at_low else CELL - 8
            _rect(t, x_w, 0, 8, CELL, WATER)
            x_lip = 8 if water_at_low else CELL - 9
            _rect(t, x_lip, 0, 1, CELL, SAND_DARK)
            for k, sy in enumerate(range(0, CELL, 8)):
                wob = int(h01(x_lip, sy, 47) * 2)
                x_f = (5 - wob) if water_at_low else (CELL - 7 + wob)
                _rect(t, x_f, sy, 2, 5 + (k % 2) * 2, SNOW)
                _rect(t, x_f + (-1 if water_at_low else 2), sy + 2, 1, 3, foam_mix)

    if edges & N:
        surf(True, True)
    if edges & S:
        surf(True, False)
    if edges & W:
        surf(False, True)
    if edges & E:
        surf(False, False)
    # dry-sand speckles kept clear of the surf bands
    for sx, sy in ((26, 26), (36, 20), (24, 38), (40, 32)):
        _rect(t, sx, sy, 3, 2, SAND_DARK)
    return t


def woods_tile(mask: int) -> Image.Image:
    """A wood whose canopy runs off each connected edge and scallops to a
    tree line on the rest. Mask 15 — wood on all four sides — is the atlas
    tile exactly, so only a wood's fringe leaves the base sheet."""
    return woods(~mask & 15)


def sheet(tiles: list[Image.Image], cols: int) -> Image.Image:
    """Lay tiles out row-major on the shared 2px-gutter contact sheet."""
    rows = (len(tiles) + cols - 1) // cols
    img = Image.new("RGB", (cols * (CELL + 2) + 2, rows * (CELL + 2) + 2), (52, 52, 60))
    for i, tile in enumerate(tiles):
        x = (i % cols) * (CELL + 2) + 2
        y = (i // cols) * (CELL + 2) + 2
        img.paste(tile.convert("RGB"), (x, y))
    return img


def variant_sheet(builder, cols: int = 4) -> Image.Image:
    """All 16 masks of one builder on a labelled-by-position grid sheet."""
    return sheet([builder(mask) for mask in range(16)], cols)


def bridge_sheet() -> Image.Image:
    """Both deck orientations: E-W over a north-south river, then N-S."""
    return sheet([bridge_tile(True), bridge_tile(False)], 2)


def plains_sheet() -> Image.Image:
    """The field's phase variants, left to right, phase 0 first.

    Same sheet contract as the sea's and for the same reason: what a field of
    one tile repeats at is the tile, so the fix is more than one tile and a rule
    for choosing between them. Phase 0 is the atlas plains column byte for byte.
    """
    return sheet([plains(phase) for phase in range(len(PLAINS_PHASES))], len(PLAINS_PHASES))


def sea_sheet() -> Image.Image:
    """The sea's phase variants, left to right, phase 0 first.

    Phase 0 is the atlas sea column byte for byte, so a board that knows
    nothing about this sheet is unchanged and one that adopts it picks a
    column per cell (the game hashes the coordinate) to break the repeat.
    """
    return sheet([sea(phase) for phase in range(len(SEA_PHASES))], len(SEA_PHASES))
