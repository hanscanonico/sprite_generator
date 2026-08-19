# Should the sheet be emitted at 128px? — measured 2026-08-19

The sprite programme's last open item, taken as a measurement rather than
decided as a taste (design review rounds 6–11). This is a dated reading: a
later campaign supersedes it wholesale rather than edits it.

**Verdict: no. 64 stays.** Not because 128 looks worse — because at 128 the
board shows *fewer* of the sheet's pixels than at 64 does, the art gains zero
logical pixels, and the emission that comes out of the generator today is
93.3% identical to a nearest 2x upscale of the 64px art. The switch is not a
knob; it is a re-authoring of every model, and even fully re-authored it pays
nothing below the rung above the default one, and nothing at all in the
cut-in.

Take the readings again with `.venv/bin/python tests/measure_128.py`.

## 1. The arithmetic, which settles it before any art is drawn

The game draws a unit at `SPRITE_SCALE = TILE / SPRITE_PX`, into a 640x360
canvas the window scales by a whole multiple (`display/window/stretch/
scale_mode = "integer"`), under a zoom ladder of whole rungs 1..5. So one
source pixel of a cell is worth

    texel:screen = s / (SPRITE_PX / TILE),    s = zoom x window_scale

and the reachable `s` are `1 2 3 4 5 6 8 9 10 12 15 16 18 20 24 30` — the
window scale running 1 to 6 because the window is resizable and nothing caps
the resolution, so 360p through a 4K display are all reachable. The default
play state — zoom 2 in a 720p window — is `s = 4`.

| | SPRITE_PX=64 | SPRITE_PX=128 |
|---|---|---|
| 1 logical px | 4 source px | 8 source px |
| **logical px per tile** | **16** | **16** |
| at the default `s=4` | **exactly 1:1** | 0.5 — every other pixel dropped |
| every source pixel shown | `s >= 4` (13 of 16 rungs) | `s >= 8` (10 of 16 rungs) |
| whole texel scale | `s = 4, 8, 12, 16, 20, 24` | `s = 8, 16, 24` |
| magnification at any reachable `s` | **twice the 128 sheet's, everywhere** | half the 64 sheet's |

Two lines of that table are the whole finding.

**The logical resolution is identical.** Round 10 pegged one logical pixel at
`SPRITE_PX / TILE` source pixels — that is what `CONTOUR_WEIGHT` counts in and
why the contour is 4 and not 1. Doubling `SPRITE_PX` doubles the source pixels
inside a logical pixel and adds no logical pixels: 16 per tile either way. The
contour band doubles with it, to 8 source pixels on the lit edges, so it eats
the same share of the sprite it always did. Every rule the art is authored
under is stated in logical pixels, and 128 buys none of them.

**The default view of a 128 sheet is a downsample of it.** At `s = 4` the 64px
cell lands one source texel on one screen pixel exactly — the shipped art is
already at 1:1 where the game is actually played. A 128px cell at the same
rung is decimated 2:1: it shows precisely the information a 64px cell shows,
having stored four times as much. It first shows all of itself at `s = 8`,
which needs zoom 4 in a 720p window or zoom 3 in a 1080p one, and it is at
half the 64px sheet's magnification at **every** rung — where 64 is at 1:1,
128 is dropping every other pixel. At `s = 8` and above both sheets cover the
same screen area; that is the entire window in which 128 could look sharper,
and it opens one rung past where the game is played.

## 2. The cut-in, where the resolution would have paid, is not parameterized

The one surface that already draws board art at 1:1 is the combat and capture
cut-in, and it is the one place more resolution would show. It cannot take it:
`CutsceneSide.FIGURE_PX` and `CaptureStage.FIGURE_PX` are both a hardcoded
`64` and both draw the region into a 64px box on the 640x360 canvas, where a
figure is already 18% of the canvas height. Drawn into that box a 128 cell is
a 2:1 downsample — zero gain; drawn at its own size it is 36% of the canvas
and every beat sheet in both directors is re-composed.

The game's legibility harness *does* parameterize — `LegibilityComposite`
samples at `step = cell.px / size` and takes `cell.px` from
`UnitSprite.SPRITE_PX` — so its board view would read a 128 sheet correctly
with no change. Its cut-in view would not: `CUTIN_PX` is bound to
`BattleView.TERRAIN_PX`, the terrain cell, not to the figure's own resolution.
`tests/unit/test_texel_stability.gd` pins `CaptureStage.FIGURE_PX ==
UnitSprite.SPRITE_PX`, so raising one without the other fails the game's suite
— correctly.

## 3. The models cannot honestly fill 128

`render_indexed` now takes a density `k`: the pixels one voxel edge is drawn
at, over the shipped 4x4 cube. `k = 2` is the 128px candidate, and it emits —
every unit fits its cell, the widest being the md_tank at 126 of 128.

But the models are coarse. They are 168 to 911 voxels, with bounding boxes of
4 to 22 voxels per axis — the sub and the battleship are **four voxels across**
their beam. At `k = 1` one voxel is drawn 4px; at `k = 2` it is drawn 8px. The
model is not denser, only the cubes are bigger:

    unit          voxels   x   y   z
    infantry         204   8   7  12
    md_tank          878  13  22   9
    battleship       401   4  27   9
    sub              203   4  22   9
    b_copter         168  11  19   9

So the candidate is measured against the thing it must beat — a plain nearest
2x upscale of the shipped render:

    18 units, red row:  82,916 painted pixels, 5,572 differ (6.7%),
                        of which 656 (0.8% of painted) are the silhouette.

**93.3% of the honest 128 emission is the 64 art, upscaled.** The 6.7% is
facet stairs falling on a finer grid — a cube's diagonal, drawn 8px instead of
4px, takes a truer staircase. No form in the sheet gains a feature, because no
model gains a voxel. Where the two rows *are* told apart, the denser drawing
reads worse rather than sharper: bigger cubes overlap each other less, so each
voxel's own top plate shows, and the md_tank's turret and hull come back
stepped and chevroned where the upscale is smooth. That is the finding said
twice — at this voxel count, drawing the cubes larger draws the cubes.

The palette agrees, and this is the answer to whether the colour caps scale:
**they do not, and they need not.** Peak colours per sprite is 23 at `k = 1`
and 23 at `k = 2`, against the cap of 24 — because the ramps are slot-indexed
rather than per-pixel shaded, so a denser drawing spends the same 23 colours
over four times the pixels. A gate that does not move is a gate whose subject
did not gain information.

Honestly filling 128 means re-authoring at roughly 2x voxel density on all
three axes — about 8x the voxels, so the md_tank goes from 878 to some 7,000 —
across 18 unit models, 14 terrains, 5 property buildings and 7 autotile
sheets, every one of them hand-authored voxel code — and only the unit
renderer takes `k` at all; the terrain, property and autotile passes draw at
64 with no density knob, so a whole-sheet candidate is more work again. That
is the programme's whole art corpus, redrawn, to be visible one rung above
where the game is played and never in the cut-in.

## 4. Recommendation

**Keep the 64px pipeline as the shipped default.** Nothing here is a defect to
fix; 64 is the density the board's own arithmetic asks for, and it is already
landing 1:1 where the game is played.

If it is ever revisited, the order is fixed by section 2 and section 3, and it
is not the order the question is usually asked in:

1. **The cut-in first.** It is the only surface where a source texel is
   already worth a screen pixel and where more would be seen immediately.
   Raising `FIGURE_PX` in both directors and `CUTIN_PX` in the legibility
   harness is a presentation change in the game, costs no art, and would
   measure whether the extra resolution is wanted at all.
2. **Re-author the models only after that says yes.** Emitting at `k = 2`
   before then ships an upscale at four times the memory, and the gates cannot
   catch it — as measured above, they all pass, because a gate that reads
   colour, band and silhouette cannot tell a denser drawing from a denser
   model.

`k` is committed as an instrument, not as a shipping route: it defaults to 1,
the 64px atlases are byte-identical across this change, and no snapshot moved.
