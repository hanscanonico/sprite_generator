"""The field's phase variants — the sea's rule on the ground a board is mostly
made of.

One plains tile repeated is a lattice however its tufts are spread inside it,
because what lines up is the repeat. The generator emits the phases; placing
them is the game's, by coordinate hash. Phase 0 stays the atlas column exactly,
so a board that has not adopted the sheet is unchanged and adoption is additive.

Plains is also the reference ground most contrast pairs are read against, so a
phase may not move the field's value band: every phase is held to the same
ceilings and the same colour count as the tile it varies.

Run with `.venv/bin/python -m unittest discover tests`.
"""

from __future__ import annotations

import statistics
import unittest

from spritegen import atlas, autotile, terrain
from spritegen.terrain import CELL, TERRAIN_MEDIAN_CEILING, TERRAIN_VALUE_CEILING

from test_generated_output import (
    TerrainPalette,
    ValueCeiling,
    opaque_pixels,
    share_above,
)


class PlainsPhases(unittest.TestCase):
    def _phases(self):
        return [terrain.plains(phase) for phase in range(len(terrain.PLAINS_PHASES))]

    def test_phase_zero_is_the_atlas_plains_column(self):
        col = terrain.TERRAIN_ORDER.index("plains")
        column = atlas.build_terrain_atlas().crop(
            (col * CELL, 0, col * CELL + CELL, CELL)
        )
        self.assertEqual(
            column.convert("RGB").tobytes(), terrain.plains(0).convert("RGB").tobytes()
        )

    def test_every_phase_moves_the_field(self):
        frames = [tile.convert("RGB").tobytes() for tile in self._phases()]
        self.assertGreaterEqual(len(frames), 2)
        self.assertEqual(len(set(frames)), len(frames))

    def test_a_phase_is_the_same_tile_twice(self):
        for phase, tile in enumerate(self._phases()):
            with self.subTest(phase=phase):
                self.assertEqual(
                    tile.convert("RGB").tobytes(),
                    terrain.plains(phase).convert("RGB").tobytes(),
                )

    def test_no_phase_leaves_the_terrain_band_or_the_colour_ceiling(self):
        for phase, tile in enumerate(self._phases()):
            with self.subTest(phase=phase):
                px = opaque_pixels(tile)
                self.assertLessEqual(
                    share_above(px, TERRAIN_VALUE_CEILING),
                    ValueCeiling.TERRAIN_HIGHLIGHT_SHARE,
                )
                median = statistics.median(terrain.luminance(c) for c in px)
                self.assertLess(median, TERRAIN_MEDIAN_CEILING)
                self.assertLessEqual(len(set(px)), TerrainPalette.NATURE_CEILING)

    def test_every_phase_carries_the_same_props(self):
        """A phase moves the field's texture, never its density: the tufts wrap
        around the tile rather than off it, so no phase is a thinner field."""
        counts = [
            sum(1 for c in opaque_pixels(tile) if c == terrain.GRASS_DARK)
            for tile in self._phases()
        ]
        self.assertEqual(len(set(counts)), 1)

    def test_the_sheet_lays_the_phases_out_in_order(self):
        sheet = autotile.plains_sheet()
        phases = self._phases()
        self.assertEqual(sheet.size, (len(phases) * (CELL + 2) + 2, CELL + 4))
        for i, tile in enumerate(phases):
            with self.subTest(phase=i):
                x = i * (CELL + 2) + 2
                cut = sheet.crop((x, 2, x + CELL, 2 + CELL))
                self.assertEqual(cut.tobytes(), tile.convert("RGB").tobytes())


if __name__ == "__main__":
    unittest.main()
