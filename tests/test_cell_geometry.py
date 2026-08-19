"""The unit cell's geometry: rectangular, and anchored to its bottom edge.

`compose_cell` takes a (width, height) cell so a silhouette can overflow its
tile upward. Every vertical landmark — the ground line, the hover line, the
air shadow's ground — is a height above the cell's BOTTOM, so a taller cell
adds sky above the sprite and moves nothing else. These tests hold that: the
board's cell is the bottom of a taller one, byte for byte.

Run with `.venv/bin/python -m unittest discover tests`.
"""

from __future__ import annotations

import unittest

from PIL import Image

from spritegen import atlas
from spritegen.palette import FACTIONS
from spritegen.units import ATLAS_ORDER, UNITS, WAKE, build_model
from spritegen.voxel import compose_cell, place_in_cell, render_indexed

TALLER = atlas.CELL_H + 32


def _sprite(uid: str):
    return render_indexed(build_model(uid, 0), FACTIONS[1]).image


def _cell(uid: str, cell: tuple[int, int], shadow: bool = True):
    kind = UNITS[uid][1]
    return compose_cell(_sprite(uid), kind, cell=cell, wake=uid in WAKE, shadow=shadow)


class BottomAnchor(unittest.TestCase):
    """A taller cell is the same cell with sky added on top."""

    def test_every_unit_composes_identically_in_a_taller_cell(self):
        for uid in ATLAS_ORDER:
            for shadow in (True, False):
                square = _cell(uid, (atlas.CELL_W, atlas.CELL_H), shadow)
                tall = _cell(uid, (atlas.CELL_W, TALLER), shadow)
                self.assertEqual(tall.size, (atlas.CELL_W, TALLER))
                base = tall.crop((0, TALLER - atlas.CELL_H, atlas.CELL_W, TALLER))
                self.assertEqual(
                    base.tobytes(),
                    square.tobytes(),
                    f"{uid} moved in a {TALLER}px cell (shadow={shadow})",
                )

    def test_the_added_height_is_empty_for_a_land_unit(self):
        tall = _cell("tank", (atlas.CELL_W, TALLER))
        sky = tall.crop((0, 0, atlas.CELL_W, TALLER - atlas.CELL_H))
        self.assertEqual(sky.getbbox(), None)


class CellSize(unittest.TestCase):
    """The sheet is laid out from CELL_W / CELL_H, never from a literal."""

    def test_a_unit_cell_is_the_atlas_cell(self):
        cell = atlas.unit_cell("infantry", FACTIONS[0])
        self.assertEqual(cell.size, (atlas.CELL_W, atlas.CELL_H))

    def test_the_units_atlas_is_the_cell_grid(self):
        for frame, shadow in ((0, True), (1, True), (0, False)):
            img = atlas.build_units_atlas(frame=frame, shadow=shadow)
            self.assertEqual(
                img.size,
                (len(ATLAS_ORDER) * atlas.CELL_W, len(FACTIONS) * atlas.CELL_H),
            )


class OverflowGate(unittest.TestCase):
    """place_in_cell still refuses to crop — that is the authoring gate."""

    def test_a_sprite_taller_than_its_cell_stops_the_build(self):
        sprite = _sprite("battleship")
        cell = Image.new("RGBA", (atlas.CELL_W, sprite.height), (0, 0, 0, 0))
        with self.assertRaises(ValueError):
            place_in_cell(cell, sprite, 0, 1)

    def test_a_land_unit_in_a_cell_shorter_than_it_stands_stops_the_build(self):
        with self.assertRaises(ValueError):
            _cell("md_tank", (atlas.CELL_W, 16))


if __name__ == "__main__":
    unittest.main()
