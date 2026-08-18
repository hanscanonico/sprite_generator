#!/usr/bin/env python3
"""Deterministic sprite pipeline for grid_commanders.

Generates the game's two atlases — 18 units x 5 faction rows and 14 terrain
tiles x 5 rows — as curated isometric-voxel pixel art. There are no seeds and
no randomness: every sprite is an authored model, and every run reproduces
the same bytes.

Outputs (under --out, default ./out):
  units_atlas.png        1152x320 RGBA — drop-in for assets/tiles/units_atlas.png
  units_atlas_b.png      ambient animation frame B (rotors swept, air/sea bobbed)
  terrain_atlas.png       896x320 RGBA — drop-in for assets/tiles/terrain_atlas.png
                          (the five property columns are transparent overlays)
  units/<id>_<team>.png   64x64 RGBA cells for tools/paste_unit_sprites.gd
  iso_buildings/<id>_<team>.png  64x64 RGBA property buildings
  preview_units.png / preview_terrain.png / preview_map.png  review sheets
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from spritegen import atlas, terrain
from spritegen.palette import FACTIONS, faction_by_key
from spritegen.units import ATLAS_ORDER


def _write(img, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    print(f"  wrote {path}")


def _preview_only(ids: list[str], team: str, zoom: int, out: Path) -> None:
    """Fast iteration: render a hand-picked subset at high zoom."""
    from PIL import Image

    fac = faction_by_key(team)
    cells = []
    for sid in ids:
        if sid in ATLAS_ORDER:
            cells.append(atlas.unit_cell(sid, fac))
        elif sid in terrain.TERRAIN_ORDER:
            cells.append(terrain.tile(sid, fac))
        else:
            sys.exit(
                f"unknown id '{sid}' (units: {', '.join(ATLAS_ORDER)}; "
                f"terrain: {', '.join(terrain.TERRAIN_ORDER)})"
            )
    sheet = Image.new("RGBA", (len(cells) * 66 + 2, 68), (52, 52, 60, 255))
    for i, c in enumerate(cells):
        sheet.alpha_composite(c.convert("RGBA"), (i * 66 + 2, 2))
    sheet = sheet.resize((sheet.width * zoom, sheet.height * zoom), 0)
    _write(sheet, out / "preview_only.png")


def _install(src: Path, dest: Path) -> None:
    import shutil

    pairs = [
        (src / "units_atlas.png", dest / "assets/tiles/units_atlas.png"),
        (src / "units_atlas_b.png", dest / "assets/tiles/units_atlas_b.png"),
        (src / "terrain_atlas.png", dest / "assets/tiles/terrain_atlas.png"),
    ]
    for cell in sorted((src / "units").glob("*.png")):
        pairs.append((cell, dest / "assets/sprites/units" / cell.name))
    for cell in sorted((src / "iso_buildings").glob("*.png")):
        pairs.append((cell, dest / "assets/sprites/iso_buildings" / cell.name))
    for sheet in sorted((src / "autotiles").glob("*.png")):
        pairs.append((sheet, dest / "assets/tiles/autotiles" / sheet.name))
    for s, d in pairs:
        if not s.exists():
            sys.exit(f"missing {s} — run a full generation first")
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(s, d)
    print(f"installed atlases + {len(pairs) - 3} cells into {dest}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument(
        "-o", "--out", type=Path, default=Path("out"), help="output directory"
    )
    ap.add_argument(
        "--only",
        metavar="IDS",
        help="comma list of unit/terrain ids: render only a zoomed "
        "preview_only.png of those (fast iteration)",
    )
    ap.add_argument(
        "--team",
        default="red",
        help="faction row for --only previews (neutral/red/blue/iron/verdant)",
    )
    ap.add_argument(
        "--zoom", type=int, default=6, help="zoom factor for --only previews"
    )
    ap.add_argument(
        "--no-cells", action="store_true", help="skip the per-cell PNG exports"
    )
    ap.add_argument(
        "--install",
        nargs="?",
        const=Path("../grid_commanders"),
        type=Path,
        metavar="GAME_DIR",
        help="copy atlases and cells into a grid_commanders "
        "checkout (default ../grid_commanders)",
    )
    args = ap.parse_args()

    if args.only:
        _preview_only(args.only.split(","), args.team, args.zoom, args.out)
        return

    print("building units atlas (18 units x 5 factions)")
    units_atlas = atlas.build_units_atlas()
    _write(units_atlas, args.out / "units_atlas.png")

    print("building ambient frame B (rotors swept, air/sea bobbed)")
    _write(atlas.build_units_atlas(frame=1), args.out / "units_atlas_b.png")

    print("building terrain atlas (14 terrains x 5 rows)")
    terrain_atlas = atlas.build_terrain_atlas()
    _write(terrain_atlas, args.out / "terrain_atlas.png")

    if not args.no_cells:
        print("exporting unit cells")
        for uid in ATLAS_ORDER:
            for fac in FACTIONS:
                _write(
                    atlas.unit_cell(uid, fac),
                    args.out / "units" / f"{uid}_{fac.team}.png",
                )
        print("exporting property-building cells")
        for bid in sorted(terrain.PROPERTY):
            for fac in FACTIONS:
                _write(
                    atlas.building_cell(bid, fac),
                    args.out / "iso_buildings" / f"{bid}_{fac.team}.png",
                )

    print("building autotile sheets (roads, rivers, coast, shoals, woods, bridges)")
    from spritegen import autotile

    _write(
        autotile.variant_sheet(autotile.road_tile), args.out / "autotiles" / "roads.png"
    )
    _write(
        autotile.variant_sheet(autotile.river_tile),
        args.out / "autotiles" / "rivers.png",
    )
    _write(
        autotile.variant_sheet(autotile.coast_tile),
        args.out / "autotiles" / "coast.png",
    )
    _write(
        autotile.variant_sheet(autotile.shoal_tile),
        args.out / "autotiles" / "shoals.png",
    )
    _write(
        autotile.variant_sheet(autotile.woods_tile),
        args.out / "autotiles" / "woods.png",
    )
    _write(autotile.bridge_sheet(), args.out / "autotiles" / "bridges.png")

    print("rendering previews")
    _write(atlas.preview(units_atlas, 2), args.out / "preview_units.png")
    _write(
        atlas.preview(terrain_atlas.convert("RGBA"), 2),
        args.out / "preview_terrain.png",
    )
    _write(atlas.build_demo(), args.out / "preview_map.png")

    if args.install is not None:
        _install(args.out, args.install)


if __name__ == "__main__":
    main()
