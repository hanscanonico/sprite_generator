"""Direction-aware tile variants: road/river autotiles, bridges, coastlines.

The main terrain atlas keeps its fixed 14-column contract (whole-tile road,
E-W river and bridge) so it stays a drop-in for the game. This module is the
opt-in upgrade path: 16-variant connection sets for roads and rivers, both
bridge orientations, and coast tiles for sea that borders land — so roads can
turn, rivers can flow north-south, and shorelines stop being a hard blue
edge. The demo map composes from these, and sprite_generator exports the
variant sheets under out/autotiles/. Deterministic like everything else here.

Connection masks are N|E|S|W bits naming which neighbours continue the
feature (for coast: which edges touch land). Mask 0 falls back to E|W.
"""

from __future__ import annotations

from PIL import Image

from .palette import h01, lighten, mix
from .terrain import (
    CELL,
    GRASS_DARK,
    ROAD,
    ROAD_DARK,
    SAND,
    SAND_DARK,
    SNOW,
    TIMBER,
    TIMBER_DARK,
    WATER,
    WATER_DARK,
    WATER_LIGHT,
    _ground,
    _lit,
    _rect,
    plains,
    sea,
)

N, E, S, W = 1, 2, 4, 8

_RLO, _RHI = 22, 42  # road band bounds (20px wide)
_WLO, _WHI = 20, 44  # river channel bounds (24px wide)


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


def river_tile(mask: int, salt: int = 0) -> Image.Image:
    """A river channel to each connected edge, banked and streaked to match
    its flow direction. `salt` shifts the streak placement so a run of
    same-mask tiles doesn't chain its glints into a dashed line."""
    if mask == 0:
        mask = E | W
    t = plains()
    _fill_arms(t, mask, _WLO, _WHI, WATER)
    _edge_pass(t, lambda c: c == WATER, WATER_DARK, GRASS_DARK)
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
