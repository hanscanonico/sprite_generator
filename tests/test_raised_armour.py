"""The armour family, raised into the taller cell.

The cell is 64x96 and bottom-anchored, so the top 32 rows are sky over the
tile a unit stands on. The armour family is the first to spend that headroom:
a tank should out-mass the grass tile under it, and a gun that elevates
should break the tile's line.

What the growth may NOT be is fine detail. The board draws the cell onto a
16px grid with nearest filtering — one source pixel in four at rung 1 — so a
whisker of a mast is drawn or not drawn depending on where the sampling grid
falls. These tests hold the mass reading rather than the pixels: the family
is what reaches out of its tile, nothing else does, and what it added is
still there after the board has thrown three pixels in four away.

Run with `.venv/bin/python -m unittest discover tests`.
"""

from __future__ import annotations

import unittest

from spritegen import atlas
from spritegen.palette import FACTIONS
from spritegen.units import ATLAS_ORDER

# The risers: tracked armour and the two guns that elevate.
RAISED = ("tank", "md_tank", "artillery", "rockets")
# What armour has to out-mass: the light vehicles on the same tile.
LIGHT = ("recon", "apc")
# The board's coarsest sampling of the cell — see docs, rung 1 is 4:1.
RUNG_1 = 4


def _silhouette(uid: str) -> list[tuple[int, int]]:
    """Every drawn pixel of a cell, shadow left off: the shadow is the tile's
    and would report the ground line as art."""
    cell = atlas.unit_cell(uid, FACTIONS[1], shadow=False).convert("RGBA")
    px = cell.load()
    return [
        (x, y)
        for y in range(atlas.CELL_H)
        for x in range(atlas.CELL_W)
        if px[x, y][3] > 0
    ]


def _top(uid: str) -> int:
    return min(y for _, y in _silhouette(uid))


class Headroom(unittest.TestCase):
    """Who reaches above the tile, and who stays inside it."""

    # The tile the unit stands on is the cell's bottom CELL_W square.
    TILE_TOP = atlas.CELL_H - atlas.CELL_W

    def test_the_headroom_is_spent_rather_than_declared(self):
        above = {uid: self.TILE_TOP - _top(uid) for uid in RAISED}
        self.assertTrue(
            any(v > 0 for v in above.values()),
            f"no raised unit reaches out of its tile: {above}",
        )

    def test_nothing_outside_the_family_reaches_out_of_its_tile(self):
        for uid in ATLAS_ORDER:
            if uid in RAISED:
                continue
            with self.subTest(unit=uid):
                self.assertGreaterEqual(_top(uid), self.TILE_TOP)

    def test_every_unit_still_stands_on_the_ground_line(self):
        for uid in ATLAS_ORDER:
            with self.subTest(unit=uid):
                bottom = max(y for _, y in _silhouette(uid))
                self.assertGreaterEqual(bottom, self.TILE_TOP)
                self.assertLess(bottom, atlas.CELL_H)


class Mass(unittest.TestCase):
    """The growth is mass, and it survives the board's own decimation."""

    # How much of the silhouette counts as what the family gained.
    CROWN_ROWS = 8

    def test_armour_out_masses_the_light_vehicles(self):
        tallest_light = max(_top(uid) for uid in LIGHT)
        for uid in RAISED:
            with self.subTest(unit=uid):
                self.assertLess(_top(uid), tallest_light)

    def test_the_crown_draws_at_every_rung_1_sampling_phase(self):
        for uid in RAISED:
            pixels = _silhouette(uid)
            top = min(y for _, y in pixels)
            crown = [p for p in pixels if p[1] < top + self.CROWN_ROWS]
            for phase_y in range(RUNG_1):
                for phase_x in range(RUNG_1):
                    drawn = [
                        1
                        for x, y in crown
                        if x % RUNG_1 == phase_x and y % RUNG_1 == phase_y
                    ]
                    with self.subTest(unit=uid, phase=(phase_x, phase_y)):
                        self.assertTrue(drawn, "the crown is a whisker, not mass")


if __name__ == "__main__":
    unittest.main()
