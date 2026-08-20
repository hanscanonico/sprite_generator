"""The mountain's phase variants — the sea's rule on the board's most
silhouette-dominant tile.

A range drawn from one mountain tile is a wall of identical peaks, which is what
the phases break. What a phase may move is where the summits stand and how the
snow line zigzags; what it may not move is the horizon — the ground line and the
contact shadow are the same row in every phase, or a ridge of them would read as
peaks at different altitudes rather than as a range. Phase 0 stays the atlas
column exactly, so a board that has not adopted the sheet is unchanged.

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

_BASE_Y = 56


class MountainPhases(unittest.TestCase):
    def _phases(self):
        return [
            terrain.mountain(phase) for phase in range(len(terrain.MOUNTAIN_PHASES))
        ]

    def test_phase_zero_is_the_atlas_mountain_column(self):
        col = terrain.TERRAIN_ORDER.index("mountain")
        column = atlas.build_terrain_atlas().crop(
            (col * CELL, 0, col * CELL + CELL, CELL)
        )
        self.assertEqual(
            column.convert("RGB").tobytes(),
            terrain.mountain(0).convert("RGB").tobytes(),
        )

    def test_every_phase_moves_the_massif(self):
        frames = [tile.convert("RGB").tobytes() for tile in self._phases()]
        self.assertGreaterEqual(len(frames), 2)
        self.assertEqual(len(set(frames)), len(frames))

    def test_a_phase_is_the_same_tile_twice(self):
        for phase, tile in enumerate(self._phases()):
            with self.subTest(phase=phase):
                self.assertEqual(
                    tile.convert("RGB").tobytes(),
                    terrain.mountain(phase).convert("RGB").tobytes(),
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

    def test_every_phase_stands_on_the_same_horizon(self):
        """The rock stops at the same row in every phase and nothing of the
        massif is drawn below it, so a range sits on one ground line."""
        for phase, tile in enumerate(self._phases()):
            with self.subTest(phase=phase):
                rows = _rock_rows(tile)
                self.assertTrue(rows, "phase draws no rock at all")
                self.assertEqual(max(rows), _BASE_Y - 1)

    def test_every_phase_casts_the_same_contact_shadow_row(self):
        for phase, tile in enumerate(self._phases()):
            with self.subTest(phase=phase):
                shadow = [
                    x
                    for x in range(CELL)
                    if tile.convert("RGB").getpixel((x, _BASE_Y)) == terrain.GRASS_DARK
                ]
                self.assertGreater(len(shadow), CELL // 2)

    def test_every_phase_keeps_a_summit_worth_a_silhouette(self):
        """A phase that flattened the massif would cost the range its read, so
        each one is held to the shipped tile's own headroom."""
        tops = [min(_rock_rows(tile)) for tile in self._phases()]
        self.assertTrue(all(top <= tops[0] + 4 for top in tops), tops)

    def test_the_sheet_lays_the_phases_out_in_order(self):
        sheet = autotile.mountain_sheet()
        phases = self._phases()
        self.assertEqual(sheet.size, (len(phases) * (CELL + 2) + 2, CELL + 4))
        for i, tile in enumerate(phases):
            with self.subTest(phase=i):
                x = i * (CELL + 2) + 2
                cut = sheet.crop((x, 2, x + CELL, 2 + CELL))
                self.assertEqual(cut.tobytes(), tile.convert("RGB").tobytes())


def _rock_rows(tile) -> list[int]:
    """The rows the massif's own greys are drawn on. Rock is the one family on
    the tile with no hue: the ground around it is grass and the caps are the
    cool blue-grey snow."""
    rgb = tile.convert("RGB")
    rows = []
    for y in range(CELL):
        for x in range(CELL):
            r, g, b = rgb.getpixel((x, y))
            if abs(r - g) <= 6 and abs(g - b) <= 6 and r > b and 60 <= r <= 180:
                rows.append(y)
                break
    return rows


if __name__ == "__main__":
    unittest.main()
