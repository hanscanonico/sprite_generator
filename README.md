# Sprite Generator

Deterministic sprite pipeline for [`../grid_commanders`](../grid_commanders):
it generates the game's complete **units atlas** (18 units x 5 faction rows)
and **terrain atlas** (14 terrains x 5 rows) as curated isometric-voxel pixel
art, in the same dimetric style as the PixVoxel pack the game shipped with —
but with more detail: finer voxels, baked ambient occlusion, front-edge rim
light, per-part outlines, and consistent scale, light and palette across the
whole roster.

There are **no seeds and no randomness**. Every sprite is a hand-authored
voxel model (`spritegen/units.py`, `spritegen/buildings.py`) or tile painter
(`spritegen/terrain.py`); texture "noise" comes from a fixed hash, so every
run reproduces the same bytes. Regenerating after an edit changes exactly the
sprites you edited.

## The roster

| Group | Columns (atlas order) |
| --- | --- |
| Land | infantry, mech, recon, tank, md_tank, anti_air, artillery, rockets, apc (0-8), missiles (13) |
| Air | fighter, bomber, b_copter, t_copter (9-12) |
| Sea | battleship, cruiser, sub, lander (14-17) |
| Terrain | road, plains, woods, mountain, river, city, base, hq, sea, airport, port, shoal, bridge, reef (0-13) |

Rows follow `SideIdentity._ROW_FOR_KEY`: 0 neutral, 1 meridian (red),
2 aurora (blue), 3 iron, 4 verdant — every row's ramp is the exact
`CommanderVisuals.FactionTheme` (color / dark / light) from the game's code,
neutral's slate theme included. Weapon silhouettes follow each unit's
`battle_style` (small arms, rocket, cannon, autocannon, bomb, torpedo,
unarmed). Property terrains (city, base, hq, airport, port) are tinted per
row; every other terrain repeats one tile down its column.

The five property columns are **transparent overlays**: the building, its
base plate and a dithered drop shadow, with the ground around them left
empty. Baking the plains green into those cells put a green square around
every city standing on road or beach; the board paints the ground under a
property and the building reads as an object on it. Consumers compose
default ground first, then the property cell — `preview_map.png` does
exactly that.

Units are painted out of **indexed ramps**: six slots per faction — S0
contour, S1 under, S2 shadow, S3 body, S4 top, S5 rim — plus one shared
gunmetal ramp and a small derived ramp per fixed accent. A face normal picks
the slot and the ramp picks the colour, so a sprite spends about twenty
palette entries instead of a few hundred, and a faction is a ramp swap rather
than a blend. **S3 is the design-system token itself**: the old livery
multiplied the faction hue against a chassis grey, which preserved hue and
halved brightness, so every army read a value darker than its own brand.
Every pixel also carries a **material id** — 0 contour, 1 faction, 2
gunmetal, 3 fixed accent — and only material 1 moves between rows.
**Iron is inverted**: its theme colour is at the value floor, so it is Iron's
shadow plane and the identity comes from the near-black-to-light-steel jump
no other faction has. Its ceiling is pulled in — lit planes stop at the body
slot and only the rim steps above — because the previous pass overshot and
made the dark faction the brightest thing on the board. Neutral goes warm
khaki so it separates from Iron by hue rather than by value, and its top
plane sits below the bright band so the row nobody owns is never the loudest
one. The **rim is a lit plane's leading edge**, not just the model's front
corner, and it is the one place a ceiling gives way, Iron's included — that
edge light is how every unit claims the L200+ band the terrain ceiling
reserves for it. Two build gates hold the pair up, with no unit exempt from
either: at least 3% of a unit's pixels above L200 on every row, and at least
55% of a unit changing colour when the row does. A third gate holds the rows
in **order** rather than at a number: no row's share of the band above L160
may sit more than a percentage point over the widest chromatic row's. Freezing
that as an absolute figure is what let Iron come back as the loudest row once
the rim pass lifted everybody (17.3% against 14.0-14.9%, round 6) — the pixels
moved, the pinned number did not. Buildings are
neutral concrete and stone under faction-colored roofs, caps and banners, and
still render through the older shading path (`render`), which terrain shares.
Shadow density encodes altitude: land units get a quarter-tone contact
shadow, air units a half-tone one offset down-right with ground showing
between, ships a displacement shadow with waterline foam. The sub carries a
**wake** on top of that — running foam down its own underside and trailing off
the stern — because a hull with no freeboard has nothing else to separate it
from open sea. Its hull and awash deck also sit a band under every other keel
(the under and shadow slots), so the sneak boat is the darkest ship in the
line and separates as a contrast pair — dark hull against mid water, under a
lit sail and a light wake edge — rather than by out-valuing the sea, which is
a contest a boat awash cannot win. Nothing a unit
emits is semi-transparent — every shadow and fleck is an opaque dither,
because partial alpha is a blurred halo at cut-in scale.

## Setup

```sh
python3 -m venv .venv
.venv/bin/pip install pillow
```

## Usage

```sh
# everything: atlases + per-cell sprites + review sheets, into ./out
.venv/bin/python sprite_generator.py

# iterate on specific sprites at high zoom while editing models
.venv/bin/python sprite_generator.py --only tank,city --team verdant --zoom 8

# copy atlases and cells into the game checkout
.venv/bin/python sprite_generator.py --install            # ../grid_commanders
.venv/bin/python sprite_generator.py --install ~/somewhere/grid_commanders
```

| Flag | Meaning |
| --- | --- |
| `-o / --out` | output directory (default `out/`) |
| `--only` | comma list of unit/terrain ids — renders just `preview_only.png` |
| `--team` | faction row for `--only` (neutral/red/blue/iron/verdant) |
| `--zoom` | zoom factor for `--only` previews (default 6) |
| `--no-cells` | skip the 115 per-cell PNGs, write only atlases + previews |
| `--install` | copy outputs into a grid_commanders checkout |

## Outputs

| File | Contract |
| --- | --- |
| `units_atlas.png` | 1152x320 RGBA — drop-in `assets/tiles/units_atlas.png` |
| `terrain_atlas.png` | 896x320 RGBA — drop-in `assets/tiles/terrain_atlas.png`; property columns carry alpha |
| `units/<id>_<team>.png` | 90 cells, the inputs `tools/paste_unit_sprites.gd` reads |
| `iso_buildings/<id>_<team>.png` | 25 property-building cells for `assets/sprites/iso_buildings` |
| `preview_units.png`, `preview_terrain.png` | 2x atlas contact sheets on checkerboard |
| `preview_map.png` | an authored little battle map proving the sheet in context |
| `autotiles/{roads,rivers,coast,shoals,woods}.png` | 16-variant connection sheets (see below) |
| `autotiles/bridges.png` | the two bridge deck orientations, E-W then N-S |
| `autotiles/sea.png` | the three sea phase variants, phase 0 first (see below) |

The `autotiles/` sheets are the opt-in upgrade path beyond the fixed
14-column terrain contract: roads and rivers as N/E/S/W connection sets (so
they can turn and junction), both bridge orientations, coastline tiles for
sea bordering land, shoals surfed on whichever edges face water, and woods
whose canopy runs off the edges the wood continues across and scallops to a
tree line on the rest (so a stand of trees stops ending in a razor cut
against the grass). Each connection sheet lays out masks 0-15 row-major (bit
order N=1, E=2, S=4, W=8); `bridges.png` carries its two decks side by side.
Mask 15 on the woods sheet is the atlas tile exactly, so only a wood's fringe
leaves the base sheet. A river is cut into a bank rather than laid on the
grass — silt, its shaded outer edge and a wet lip at the waterline, all mixed
from the same ground constants the plains and shoal tones come from — a run
that stops ends on a rounded nose, and a river's mask 0 is a banked pond,
since a watercourse joined to nothing is a pool rather than an E-W bar — a
pool whose bank is widest and darkest down the shadow diagonal and thins to a
one-pixel lip in the notches its reeds stand in, because a ring of one weight
and one tone is a badge rather than a shore. The
demo map composes from these, which is why its roads connect and its island
has a shoreline; the atlases themselves are
unchanged drop-ins.

`autotiles/sea.png` is the one sheet that is not a connection set: it is the
same open water in three **phases**, laid out left to right with a 2px gutter
like every other sheet. A field of sea reads visibly row-aligned however the
glints are spread inside one tile, because what lines up is the repeat — so
the fix is more than one tile and a rule for choosing between them. **The
generator emits the phases; the game places them**, by hashing the cell
coordinate into `0..2`. **Phase 0 is the terrain atlas's sea column byte for
byte**, so a board that knows nothing about this sheet is unchanged and a
board that adopts it keeps every cell it does not re-key; nothing has to move
on the day the game registers the sheet.

Note the game's `make tiles` rebuilds its atlases from its own PixVoxel
pipeline and would overwrite installed atlases; the per-cell exports exist so
that pipeline's paste step can be pointed at this art instead.

## How it works

1. **`spritegen/voxel.py`** — a tiny dimetric voxel engine. Screen
   `x=(vx-vy)*2, y=(vx+vy)-vz*2`, each voxel a 4x4 cube sprite overlapping
   its neighbours by 2px (the classic 2px stair edge), painter's-algorithm
   ordering, and `Model.chamfer` cutting corner columns so turrets, cabs and
   roofs read as octagonal masses instead of cubes. Two renderers sit on
   that geometry:
   - `render_indexed` (units) shades **per face normal into ramp slots** —
     top, rim, body, shadow, under — with ambient occlusion, the ground
     contact and the depth gradient charged as whole slot steps rather than
     as fractions of a colour. Then a per-faction S0 contour, doubled on the
     lower-right edges the unit has to separate from the ground on, S0
     between two materials whose values are too close to read apart, and a
     despeckle pass folding lone pixels into the plane they were nearly part
     of. It also returns a per-pixel material id.
   - `render` (terrain and buildings) is the older path: three shaded face
     tones per material, fractional occlusion, hash dither on broad tops and
     a 1px per-part outline.
2. **`spritegen/palette.py`** — the indexed ramps and the material-to-slot
   table units are painted from, the faction colours mirroring the game's
   `CommanderVisuals`, fixed materials (gunmetal, track, glass, skin, ...),
   the older shading math, and the deterministic hash noise.
3. **`spritegen/units.py`** — 18 authored models, all facing +y
   (screen lower-left) like the game's art. Land units get a contact
   shadow, ships sit in a flat displacement shadow with foam hugging the
   waterline, air units hover high over a small detached one.
4. **`spritegen/buildings.py` / `spritegen/terrain.py`** — voxel property
   buildings and nature props composed onto 64px tile grounds. The grounds
   keep `tools/generate_tiles.gd`'s hues but not its values: every tone is
   authored under `terrain.TERRAIN_VALUE_CEILING` so the top of the ramp
   stays the units'. A building's masonry is picked by its **lit** plane
   rather than by its own value — a voxel top face is the material scaled
   1.3x and rim-lit on top of that — so the greys are dark enough that no
   wall reaches the units' band; a lit window and a pane of glazing are the
   only things that glint into it (`BUILDING_KEY_CEILING`). Under the cap is
   not the same thing as readable, though, so the ladder sits a further rung
   down: the **mass** of every wall, lot and roof is dark — the lit half of a
   property measures L79-111 — and the rung it used to be is **trim, drawn
   only as a line**: a parapet, a coping, a ridge, a seam. Roofs follow the
   same rule inside the faction's own ramp, the theme's dark as the plane and
   the theme colour as the ridge, because a `body` roof lit to L152 sat
   exactly on a verdant unit's own top slot. The woods canopy carries a lit
   top plane so a dark or green unit standing on it has a value step to
   separate against: it is authored one step under the dimmest plains pixel
   and painted over most of each crown rather than its cap alone, which is
   what makes it something a green hull is actually seen against while the
   woods/plains seam rule stays true.
5. **`spritegen/autotile.py`** — the direction-aware road/river/bridge/
   coast/shoal/woods variants and the sea's phase variants, exported under
   `autotiles/`.
6. **`spritegen/atlas.py`** — assembles atlases, exports cells, renders the
   preview sheets and the demo map (which resolves roads, the river, the
   bridge, every coastline and every wood's tree line through the autotile
   variants).

Python 3.10+, no dependencies beyond Pillow. The old seed-driven generator
(creatures/ships/items/robots/tanks) lives in git history before this
rewrite.

## Checks

`.github/workflows/ci.yml` runs on every push to `main` and every pull
request: `ruff check` and `ruff format --check` (ruff pinned in the workflow,
style settings in `ruff.toml`), the contract tests
(`python -m unittest discover tests`), two generator runs diffed against each
other for byte determinism, and a pixel comparison of the committed
`.lavish/assets` snapshots — atlases, previews, autotile sheets and
`iso_buildings` cells — against fresh generator output. Change what the
generator draws and those snapshots have to be regenerated in the same
commit, or CI fails.
