"""Dev instrument for the 128px question — not a test, a readout.

The sprite programme's last open item is whether the sheet should be emitted
at a 128px cell instead of 64. `docs/density_128.md` is the verdict; this is
where its numbers come from, so a later campaign can re-take them rather than
trust them.

Three readouts:

  board    the texel arithmetic. What one source pixel of a cell is worth in
           screen pixels at every rung of the game's zoom ladder and every
           window scale it forces, at each candidate density.
  models   how coarse the voxel models actually are — voxels per model, the
           bounding box in voxels, and the pixels one voxel edge is drawn at.
  render   the 128 candidate itself: every unit rendered at k=2 and compared
           against a nearest 2x upscale of its shipped k=1 render, which is
           the difference between a denser drawing and more art.

Run: .venv/bin/python tests/measure_128.py [board|models|render ...]
"""

from __future__ import annotations

import sys

from PIL import Image

from spritegen import units
from spritegen.palette import faction_by_key
from spritegen.voxel import render_indexed

# The game's side of the arithmetic, read off grid_commanders and restated
# here so this file runs without a Godot checkout beside it:
# BattleView.TILE, the whole rungs of BattleZoom, and the window scales
# `display/window/stretch/scale_mode = "integer"` leaves reachable over the
# 640x360 canvas. The window is resizable and the game caps no resolution, so
# the set runs up to a 4K display: 360p, 720p, 1080p, 1440p, 2160p.
TILE = 16
ZOOM_RUNGS = [1, 2, 3, 4, 5]
WINDOW_SCALES = [1, 2, 3, 4, 6]
DEFAULT_ZOOM = 2
DEFAULT_WINDOW_SCALE = 2
DENSITIES = [64, 128]


def board() -> None:
    """What a source pixel is worth on the board, per density."""
    reach = sorted({z * w for z in ZOOM_RUNGS for w in WINDOW_SCALES})
    default = DEFAULT_ZOOM * DEFAULT_WINDOW_SCALE
    print(f"reachable s = zoom x window_scale: {reach}   (default s = {default})")
    for sprite_px in DENSITIES:
        per_logical = sprite_px // TILE
        print(
            f"\nSPRITE_PX={sprite_px}: 1 logical px = {per_logical} source px, "
            f"{sprite_px // per_logical} logical px per tile"
        )
        whole = [s for s in reach if (s / per_logical).is_integer()]
        lossless = [s for s in reach if s >= per_logical]
        for s in reach:
            texel = s / per_logical
            mark = "1:1" if texel == 1 else ("magnified" if texel > 1 else "decimated")
            flag = "  <- default" if s == default else ""
            print(f"   s={s:<3} texel:screen = {texel:<6.3f} {mark}{flag}")
        print(
            f"   every source pixel shown at s in {lossless} ({len(lossless)}/{len(reach)})"
        )
        print(f"   whole texel scale at s in {whole}")


def models() -> None:
    """How much model there is to draw, per unit."""
    print(
        f"{'unit':<12} {'voxels':>7} {'x':>3} {'y':>3} {'z':>3} {'64px cell':>11} {'128px cell':>11}"
    )
    for uid in units.ATLAS_ORDER:
        model = units.build_model(uid)
        xs = [v[0] for v in model.vox]
        ys = [v[1] for v in model.vox]
        zs = [v[2] for v in model.vox]
        span = (max(xs) - min(xs) + 1, max(ys) - min(ys) + 1, max(zs) - min(zs) + 1)
        one = render_indexed(model, faction_by_key("red"), k=1).image
        two = render_indexed(model, faction_by_key("red"), k=2).image
        print(
            f"{uid:<12} {len(model.vox):>7} {span[0]:>3} {span[1]:>3} {span[2]:>3} "
            f"{one.width:>4}x{one.height:<6} {two.width:>4}x{two.height:<6}"
        )


def _differs(a: Image.Image, b: Image.Image) -> tuple[int, int, int]:
    """Over every pixel either sprite paints: how many that is, how many the
    two disagree on, and how many of those are the SILHOUETTE disagreeing —
    a pixel one has and the other does not."""
    pa, pb = a.load(), b.load()
    union = differs = shape = 0
    for y in range(max(a.height, b.height)):
        for x in range(max(a.width, b.width)):
            ca = pa[x, y] if x < a.width and y < a.height else (0, 0, 0, 0)
            cb = pb[x, y] if x < b.width and y < b.height else (0, 0, 0, 0)
            if ca[3] != 255 and cb[3] != 255:
                continue
            union += 1
            if (ca[3] == 255) != (cb[3] == 255):
                shape += 1
                differs += 1
            elif ca != cb:
                differs += 1
    return union, differs, shape


def render() -> None:
    """The k=2 candidate against a nearest 2x upscale of the shipped render.

    A pixel that differs is a pixel the denser cube geometry drew differently.
    A pixel that differs only in SHAPE is the silhouette moving; everything
    else is a facet stair falling on a finer grid. Neither is a new form: the
    model underneath has the same voxels either way.
    """
    fac = faction_by_key("red")
    print(f"{'unit':<12} {'painted':>9} {'differs':>9} {'%':>7} {'silhouette':>11}")
    totals = [0, 0, 0]
    for uid in units.ATLAS_ORDER:
        model = units.build_model(uid)
        one = render_indexed(model, fac, k=1).image
        two = render_indexed(model, fac, k=2).image
        upscaled = one.resize((one.width * 2, one.height * 2), Image.NEAREST)
        union, differs, shape = _differs(upscaled, two)
        totals = [t + v for t, v in zip(totals, (union, differs, shape))]
        print(
            f"{uid:<12} {union:>9} {differs:>9} "
            f"{100 * differs / max(1, union):>6.1f}% {shape:>11}"
        )
    print(
        f"{'ALL':<12} {totals[0]:>9} {totals[1]:>9} "
        f"{100 * totals[1] / max(1, totals[0]):>6.1f}% {totals[2]:>11}"
    )


READOUTS = {"board": board, "models": models, "render": render}

if __name__ == "__main__":
    wanted = sys.argv[1:] or list(READOUTS)
    for name in wanted:
        if name not in READOUTS:
            sys.exit(f"unknown readout '{name}' (have: {', '.join(READOUTS)})")
        print(f"--- {name} " + "-" * (60 - len(name)))
        READOUTS[name]()
        print()
