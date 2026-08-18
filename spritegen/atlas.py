"""Atlas assembly and per-cell export, matching grid_commanders' contracts.

units_atlas.png   — 18 columns x 5 rows of 64px RGBA cells (1152x320),
                    columns in data/units atlas_col order, rows in
                    SideIdentity order (neutral, meridian, aurora, iron,
                    verdant).
terrain_atlas.png — 14 columns x 5 rows of 64px RGBA cells (896x320),
                    columns in tools/generate_tiles.gd order; non-property
                    columns repeat one opaque tile down all rows, property
                    columns are faction-tinted per row and transparent
                    around the building, for the board to paint under.
unit cells        — <unit id>_<team>.png, 64x64 RGBA, the inputs
                    tools/paste_unit_sprites.gd consumes.
building cells    — <building>_<team>.png, 64x64 RGBA transparent-backed
                    sprites for assets/sprites/iso_buildings.
"""

from __future__ import annotations

from PIL import Image

from . import autotile, buildings, terrain
from .palette import FACTIONS, Faction
from .units import ATLAS_ORDER, UNITS, WAKE, build_model
from .voxel import compose_cell, place_in_cell, render, render_indexed

CELL = 64
# Ambient animation frame B: air and sea units ride one voxel-scale pixel
# higher (their shadows stay put, so the bob reads as hover/swell), and the
# copters' rotor discs sweep 45 degrees inside build_model. Land units are
# byte-identical between frames — they are parked on the ground.
_BOB_BOTTOM = {"air": 43, "sea": 54}


def unit_cell(uid: str, fac: Faction, frame: int = 0) -> Image.Image:
    """One atlas cell. Units render through the indexed ramps; terrain and
    buildings keep the shading renderer until their own pass moves them."""
    kind = UNITS[uid][1]
    bottom = _BOB_BOTTOM.get(kind) if frame == 1 else None
    sprite = render_indexed(build_model(uid, frame), fac).image
    return compose_cell(sprite, kind, bottom=bottom, wake=uid in WAKE)


def build_units_atlas(frame: int = 0) -> Image.Image:
    atlas = Image.new(
        "RGBA", (len(ATLAS_ORDER) * CELL, len(FACTIONS) * CELL), (0, 0, 0, 0)
    )
    for row, fac in enumerate(FACTIONS):
        for col, uid in enumerate(ATLAS_ORDER):
            atlas.alpha_composite(unit_cell(uid, fac, frame), (col * CELL, row * CELL))
    return atlas


def build_terrain_atlas() -> Image.Image:
    atlas = Image.new("RGBA", (len(terrain.TERRAIN_ORDER) * CELL, len(FACTIONS) * CELL))
    for col, tid in enumerate(terrain.TERRAIN_ORDER):
        if tid in terrain.PROPERTY:
            for row, fac in enumerate(FACTIONS):
                atlas.paste(terrain.tile(tid, fac), (col * CELL, row * CELL))
        else:
            one = terrain.tile(tid, FACTIONS[0])
            for row in range(len(FACTIONS)):
                atlas.paste(one, (col * CELL, row * CELL))
    return atlas


def building_cell(bid: str, fac: Faction) -> Image.Image:
    """A property building alone on a transparent cell, placed exactly as the
    terrain tiles place it, for the game's iso_buildings compositor."""
    # model_for, not BUILDINGS[bid]: the neutral row swaps hue-carrying
    # materials for greys, and the exported cells must match the tiles.
    sprite = render(buildings.model_for(bid, fac), fac)
    out = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    cx, bottom = terrain.PROPERTY_ANCHOR[bid]
    place_in_cell(out, sprite, cx - sprite.width // 2, bottom - sprite.height)
    return out


# ---------------------------------------------------------------------------
# previews
# ---------------------------------------------------------------------------


def checker(w: int, h: int) -> Image.Image:
    img = Image.new("RGBA", (w, h), (52, 52, 60, 255))
    px = img.load()
    for y in range(h):
        for x in range(w):
            if ((x // 8) + (y // 8)) % 2:
                px[x, y] = (60, 60, 69, 255)
    return img


def preview(atlas: Image.Image, zoom: int = 2) -> Image.Image:
    base = checker(atlas.width, atlas.height)
    base.alpha_composite(atlas.convert("RGBA"))
    return base.resize((atlas.width * zoom, atlas.height * zoom), Image.NEAREST)


# A small authored scene proving the sheet works as a map: terrain ids per
# cell, then units placed on top with mixed factions. Roads, the river, the
# bridge, every coastline and every wood's tree line resolve through the
# autotile variants, so the preview shows the connected look the game gets if
# it adopts them.
_DEMO_MAP = [
    "sea    sea    sea    sea    sea    sea    sea    sea    sea    sea",
    "sea    reef   shoal  plains woods  plains river  city   port   sea",
    "sea    shoal  plains road   road   road   bridge road   hq     sea",
    "sea    plains woods  road   mount  road   river  road   city   sea",
    "sea    base   road   road   plains woods  river  road   base   sea",
    "sea    plains airport plains plains plains river  plains plains sea",
    "sea    sea    sea    sea    sea    sea    sea    sea    sea    sea",
]
_DEMO_ALIAS = {"mount": "mountain"}
# Tiles that read as open water (no coastline against them).
_WATERY = frozenset({"sea", "reef", "river", "bridge", "port"})
# (unit, faction row, col, row)
_DEMO_UNITS = [
    ("infantry", 1, 3, 2),
    ("tank", 1, 4, 2),
    ("recon", 1, 2, 3),
    ("mech", 2, 7, 2),
    ("md_tank", 2, 4, 4),
    ("artillery", 2, 7, 5),
    ("rockets", 1, 1, 4),
    ("apc", 2, 5, 1),
    ("anti_air", 1, 3, 5),
    ("missiles", 2, 8, 5),
    ("fighter", 1, 5, 3),
    ("bomber", 2, 2, 5),
    ("b_copter", 1, 6, 1),
    ("t_copter", 2, 4, 5),
    ("battleship", 1, 1, 6),
    ("cruiser", 2, 8, 6),
    ("sub", 1, 3, 0),
    ("lander", 2, 6, 6),
]


def build_demo() -> Image.Image:
    rows = [[_DEMO_ALIAS.get(t, t) for t in r.split()] for r in _DEMO_MAP]
    h, w = len(rows), len(rows[0])
    img = Image.new("RGBA", (w * CELL, h * CELL))
    fac_for_prop = {
        (7, 1): 2,
        (8, 1): 2,
        (8, 2): 2,
        (8, 3): 2,
        (8, 4): 2,
        (1, 4): 1,
        (2, 5): 1,
    }

    def at(x: int, y: int) -> str:
        if 0 <= x < w and 0 <= y < h:
            return rows[y][x]
        return "sea"  # off-map reads as open sea

    def mask(x: int, y: int, joins: frozenset[str]) -> int:
        m = 0
        for bit, (dx, dy) in (
            (autotile.N, (0, -1)),
            (autotile.E, (1, 0)),
            (autotile.S, (0, 1)),
            (autotile.W, (-1, 0)),
        ):
            if at(x + dx, y + dy) in joins:
                m |= bit
        return m

    road_joins = frozenset({"road", "bridge"})
    river_joins = frozenset({"river", "bridge", "sea"})
    for y, row in enumerate(rows):
        for x, tid in enumerate(row):
            if tid == "road":
                tile = autotile.road_tile(mask(x, y, road_joins))
            elif tid == "river":
                tile = autotile.river_tile(mask(x, y, river_joins), salt=x * 7 + y)
            elif tid == "shoal":
                tile = autotile.shoal_tile(mask(x, y, _WATERY))
            elif tid == "woods":
                tile = autotile.woods_tile(mask(x, y, frozenset({"woods"})))
            elif tid == "bridge":
                horiz = bool(mask(x, y, road_joins) & (autotile.E | autotile.W))
                tile = autotile.bridge_tile(horiz)
            elif tid == "sea":
                # shoals carry their own surf, so the sea draws no coast
                # against them — only against hard land
                def hard_land(t: str) -> bool:
                    return t not in _WATERY and t != "shoal"

                edges = 0
                corners = 0
                for bit, (dx, dy) in (
                    (autotile.N, (0, -1)),
                    (autotile.E, (1, 0)),
                    (autotile.S, (0, 1)),
                    (autotile.W, (-1, 0)),
                ):
                    if hard_land(at(x + dx, y + dy)):
                        edges |= bit
                for bit, (dx, dy) in (
                    (autotile.N, (1, -1)),
                    (autotile.E, (1, 1)),
                    (autotile.S, (-1, 1)),
                    (autotile.W, (-1, -1)),
                ):
                    if hard_land(at(x + dx, y + dy)):
                        corners |= bit
                tile = (
                    autotile.coast_tile(edges, corners)
                    if edges or corners
                    else terrain.tile("sea", FACTIONS[0])
                )
            else:
                fac_row = fac_for_prop.get((x, y), 1 if x < 5 else 2)
                fac = FACTIONS[fac_row if tid in terrain.PROPERTY else 0]
                tile = terrain.tile(tid, fac)
            if tid in terrain.PROPERTY:
                # A property ships as a transparent overlay, so the ground
                # under it is the board's to paint — the default ground,
                # which is what these cells used to bake.
                img.paste(terrain.tile("plains", FACTIONS[0]), (x * CELL, y * CELL))
                img.alpha_composite(tile, (x * CELL, y * CELL))
            else:
                img.paste(tile.convert("RGBA"), (x * CELL, y * CELL))
    for uid, fac_row, x, y in _DEMO_UNITS:
        img.alpha_composite(unit_cell(uid, FACTIONS[fac_row]), (x * CELL, y * CELL))
    return img
