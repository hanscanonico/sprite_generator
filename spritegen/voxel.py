"""A tiny dimetric voxel engine — the whole sheet's look lives here.

Projection matches the PixVoxel art the game shipped with: screen
x = (vx - vy) * 2, y = (vx + vy) - vz * 2, each voxel drawn as a 4x4 cube
sprite overlapping its neighbours by 2px, which is what produces the classic
2px-run stair edges. +x runs toward screen lower-right, +y toward screen
lower-left (units face +y), +z is up.

Two renderers share that geometry. `render_indexed` draws units: one flat
ramp slot per visible plane, ambient occlusion and the ground contact
charged as whole slot steps, a per-faction contour, and a material id
emitted beside every pixel. `render` is the older shading path — three
computed face tones, fractional occlusion, dither on broad tops and a
per-part outline — and terrain and buildings still draw with it. All of it
is deterministic: no RNG anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image

from .palette import (
    DITHERED,
    GLOSSY,
    IRON_SLOT_CEILING,
    MID_ACCENT,
    MID_CONTOUR,
    MID_EMPTY,
    MID_FACTION,
    MID_GUNMETAL,
    RGB,
    S_CONTOUR,
    S_RIM,
    S_TOP,
    SLOTS,
    Faction,
    Ramp,
    darken,
    h01,
    lighten,
    luminance,
    material_slot,
    mix,
    ramp_for,
    resolve,
    shade,
)


class Model:
    """Sparse voxel set: (x, y, z) -> material name."""

    def __init__(self) -> None:
        self.vox: dict[tuple[int, int, int], str] = {}

    def set(self, x: int, y: int, z: int, m: str) -> None:
        self.vox[(x, y, z)] = m

    def unset(self, x: int, y: int, z: int) -> None:
        self.vox.pop((x, y, z), None)

    def box(self, x0: int, x1: int, y0: int, y1: int, z0: int, z1: int, m: str) -> None:
        """Filled box, inclusive bounds (order-insensitive)."""
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    self.vox[(x, y, z)] = m

    def clear(self, x0: int, x1: int, y0: int, y1: int, z0: int, z1: int) -> None:
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    self.vox.pop((x, y, z), None)

    def chamfer(self, x0: int, x1: int, y0: int, y1: int, z0: int, z1: int) -> None:
        """Knock the four corner columns off a box between z0..z1.

        Turns a slab into an octagonal mass — the cheap trick that keeps
        turrets, cabs and roofs from reading as pure cubes.
        """
        for z in range(min(z0, z1), max(z0, z1) + 1):
            for cx, cy in ((x0, y0), (x0, y1), (x1, y0), (x1, y1)):
                self.vox.pop((cx, cy, z), None)


def _face_pixels(sx: int, sy: int, k: int = 1) -> dict[str, list[tuple[int, int]]]:
    """The 4k x 4k cube sprite at screen anchor (sx, sy): top / left / right.

    `k` is the DENSITY: how many pixels one voxel edge is drawn at, over the
    shipped 4x4 cube. It is the only geometric knob in the engine, and it is
    what a 128px cell would be emitted through (k=2). It scales the drawing,
    not the model — see `tests/measure_128.py` and `docs/density_128.md` for
    what that distinction costs.

    The top face is the dimetric rhombus: 2k rows, row j spanning
    2k-1-j .. 2k+j, so it widens 2, 4, ... 4k. The two side faces are the
    2k x 2k blocks under it. At k=1 that is the shipped 4x4 cube exactly.
    """
    top: list[tuple[int, int]] = []
    for j in range(2 * k):
        top.extend((sx + i, sy + j) for i in range(2 * k - 1 - j, 2 * k + j + 1))
    left: list[tuple[int, int]] = []
    right: list[tuple[int, int]] = []
    for j in range(2 * k, 4 * k):
        left.extend((sx + i, sy + j) for i in range(2 * k))
        right.extend((sx + i, sy + j) for i in range(2 * k, 4 * k))
    return {"top": top, "left": left, "right": right}


Anchors = dict[tuple[int, int, int], tuple[int, int]]

# Up, left, down, right — the four edges a contour is measured across. Up and
# left are the lit ones; down and right face the ground the unit stands on.
UP, LEFT, DOWN, RIGHT = (0, -1), (-1, 0), (0, 1), (1, 0)

# How thick the S0 band across each edge is, at the 64px cell the models are
# drawn at. The board draws that cell onto a 16px grid with nearest filtering,
# so it keeps ONE SOURCE PIXEL IN FOUR: a contour thinner than four is sampled
# or skipped by where it happens to fall, which is why a structurally
# guaranteed S0 boundary (round 9) still left the apc's roof line dissolving
# into plains. Four is ONE LOGICAL PIXEL — whatever the phase, the board lands
# on it.
#
# Round 10 measured four on every edge against four on the lit edges and two on
# the ground-facing ones, through the game's own legibility sweep; the lighter
# pair is what ships (see README, "The contour is one logical pixel").
CONTOUR_WEIGHT: dict[tuple[int, int], int] = {UP: 4, LEFT: 4, DOWN: 2, RIGHT: 2}

# How much of that band may sit OUTSIDE the silhouette. It is the round-9 halo
# unchanged, and it is a cell budget rather than a taste: the md_tank is 63 of
# the 64 px its cell allows, so a band that grew outward would either crop a
# model or shrink one. The rest of the weight is claimed inward, off the plane
# behind the edge — the silhouette stays the shape the model drew.
_HALO: dict[tuple[int, int], int] = {UP: 1, LEFT: 1, DOWN: 2, RIGHT: 2}


def _bounds(model: Model, k: int = 1) -> tuple[Anchors, int, int, int, int]:
    """Screen anchors per voxel plus the crop the sprite needs (2px margin for
    the doubled terrain-facing contour), at density `k`."""
    anchors: Anchors = {}
    for x, y, z in model.vox:
        anchors[(x, y, z)] = ((x - y) * 2 * k, ((x + y) - z * 2) * k)
    minx = min(a[0] for a in anchors.values()) - k
    miny = min(a[1] for a in anchors.values()) - k
    w = max(a[0] for a in anchors.values()) + (4 + 2) * k - minx
    h = max(a[1] for a in anchors.values()) + (4 + 2) * k - miny
    return anchors, minx, miny, w, h


@dataclass
class IndexedSprite:
    """A rendered sprite plus the material id behind every pixel.

    The id is what makes a tint a lookup rather than a colour match: material
    1 is the faction's, and nothing else on the sprite moves when a row does.
    """

    image: Image.Image
    materials: bytearray

    def mid(self, x: int, y: int) -> int:
        return self.materials[y * self.image.width + x]


def render_indexed(
    model: Model, faction: Faction, outline: bool = True, k: int = 1
) -> IndexedSprite:
    """Render a unit out of the indexed ramps: one flat slot per visible plane.

    The old path shades every pixel by arithmetic, so one physical face lands
    on dozens of near-identical colours and no post-hoc quantiser can recover
    the plane structure that was never there. Here a face normal picks a SLOT
    — top, rim, body, shadow, under — and the ramp picks the colour, so a
    sprite costs tens of palette entries and a faction is a ramp swap.
    """
    if not model.vox:
        return IndexedSprite(Image.new("RGBA", (1, 1), (0, 0, 0, 0)), bytearray([255]))

    anchors, minx, miny, w, h = _bounds(model, k)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    mids = bytearray([MID_EMPTY]) * (w * h)
    ramps: list[Ramp | None] = [None] * (w * h)

    vox = model.vox
    zmin = min(v[2] for v in vox)
    # A lit plane stops at the top slot and the rim alone steps above it, so
    # a light livery material cannot carpet a deck in near-white — the
    # blotching the spec's own post-hoc quantiser produced. Iron stops one
    # lower still: see IRON_SLOT_CEILING.
    faction_cap = IRON_SLOT_CEILING if faction.key == "iron" else S_TOP
    for x, y, z in sorted(vox, key=lambda v: (v[0] + v[1], v[2])):
        mat = vox[(x, y, z)]
        spec = material_slot(mat)
        ramp = ramp_for(mat, faction)
        cap = faction_cap if spec.mid == MID_FACTION else SLOTS - 1
        # A fixed accent is a small part — a lamp, a canopy, a nose cone —
        # and five bands on twenty pixels is palette spent on nothing, so an
        # accent gets shadow / body / top and no rim or under.
        floor = spec.slot - 1 if spec.mid == MID_ACCENT else 0
        cap = min(cap, spec.slot + 1) if spec.mid == MID_ACCENT else cap
        sx, sy = anchors[(x, y, z)]
        sx -= minx
        sy -= miny

        # Ambient occlusion and the ground contact are whole slot steps: a
        # fractional darkening is exactly the per-pixel drift this rewrite
        # exists to delete.
        top_steps = 0
        if (x - 1, y, z + 1) in vox or (x, y - 1, z + 1) in vox:
            top_steps += 1
        if (x + 1, y, z + 1) in vox or (x, y + 1, z + 1) in vox:
            top_steps += 1
        # The rim is a lit plane's LEADING EDGE — the last voxel before the
        # top surface falls away toward the camera, on either camera-facing
        # side. The front corner alone (both sides open) is one voxel per
        # mass, which is why half the land group carried under 3% of its
        # pixels in the bright band the terrain ceiling reserves for units
        # (round-5 verdict): a low flat-topped hull has exactly one corner
        # and a tall one has none to spare. An edge is still an edge — an
        # interior top voxel is never rim, so this cannot bloom into
        # brightening the whole plane, and `_despeckle` folds away the lone
        # pixels a notch leaves.
        top_lit = top_steps == 0 and (x, y, z + 1) not in vox
        rim = top_lit and ((x + 1, y, z) not in vox or (x, y + 1, z) not in vox)
        under = 1 if z == zmin else 0
        left_steps = under + (1 if (x, y + 1, z + 1) in vox else 0)
        right_steps = under + (1 if (x + 1, y, z + 1) in vox else 0)

        offsets = {
            "top": 1 + (1 if rim else 0) - top_steps,
            "left": -left_steps,
            "right": -1 - right_steps,
        }
        for face, pixels in _face_pixels(sx, sy, k).items():
            # The rim is the one place a ceiling gives way, and it gives way
            # to the top of the ramp: it is an edge one voxel deep, and it is
            # where Iron's light-steel flash lives. Lifting Iron only to its
            # capped top plane's next step left the darkest faction with no
            # pixel at all in the band above L200 that the terrain ceiling
            # reserves for units.
            lifts_rim = rim and face == "top" and spec.mid == MID_FACTION
            ceiling = S_RIM if lifts_rim else cap
            slot = min(ceiling, max(floor, spec.slot + offsets[face]))
            slot = max(0, min(SLOTS - 1, slot))
            c = ramp[slot]
            for ix, iy in pixels:
                px[ix, iy] = (c[0], c[1], c[2], 255)
                idx = iy * w + ix
                mids[idx] = spec.mid
                ramps[idx] = ramp

    if outline:
        _contour(img, mids, ramps, k)
    _despeckle(img, mids)
    return IndexedSprite(img, mids)


_NEIGHBOURS4 = ((0, -1), (-1, 0), (1, 0), (0, 1))
_NEIGHBOURS8 = _NEIGHBOURS4 + ((-1, -1), (1, -1), (-1, 1), (1, 1))


def _exposed(px, w: int, h: int) -> list[bool]:
    """Every opaque pixel that touches transparency, diagonals included.

    The outer boundary is what the unit is read against, so it is defined the
    way an eye reads it — a step's inner corner is on the silhouette even
    though no side of it faces out.
    """
    out = [False] * (w * h)
    for y in range(h):
        for x in range(w):
            if px[x, y][3] != 255:
                continue
            for dx, dy in _NEIGHBOURS8:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < w and 0 <= ny < h) or px[nx, ny][3] != 255:
                    out[y * w + x] = True
                    break
    return out


def _despeckle(img: Image.Image, mids: bytearray) -> None:
    """Fold every lone pixel into the plane it is most like.

    A pixel sharing its colour with none of its four orthogonal neighbours
    is dirt at cut-in scale and shimmer at zoom-out (sprite fix spec, section
    2, rule 3). Stair corners and the contour's own diagonals leave a
    handful per sprite, so they are snapped to the neighbouring colour
    closest in value — the plane they were nearly part of already.

    In place and in scan order, not from a snapshot: a snapshot updates two
    lone neighbours at once and can strand each on the colour the other just
    left, so it needs a second pass to settle. Snapping against the live
    image settles in one, because a pixel that was snapped to a neighbour
    has given that neighbour a match and neither can move again.

    On the outer boundary it may only snap S0 to S0. The contour is the last
    word on every pixel that meets the ground (`_claim_outer_boundary`), so a
    lone pixel out there settles between neighbouring contours or stays as it
    is; folding it into the plane behind it is what left a rim standing naked
    against a light tile.
    """
    px = img.load()
    w, h = img.size
    exposed = _exposed(px, w, h)
    for y in range(h):
        for x in range(w):
            here = px[x, y]
            if here[3] != 255:
                continue
            neigh = []
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= nx < w and 0 <= ny < h:
                    c = px[nx, ny]
                    if c[3] == 255:
                        neigh.append((c, ny * w + nx))
            if not neigh or any(c[:3] == here[:3] for c, _ in neigh):
                continue
            if exposed[y * w + x]:
                neigh = [n for n in neigh if mids[n[1]] == MID_CONTOUR]
                if not neigh:
                    continue
            level = luminance(here[:3])
            best, src = min(neigh, key=lambda n: abs(luminance(n[0][:3]) - level))
            px[x, y] = best
            mids[y * w + x] = mids[src]


def _contour(
    img: Image.Image, mids: bytearray, ramps: list[Ramp | None], k: int = 1
) -> None:
    """Per-faction S0 contour, CONTOUR_WEIGHT * k pixels thick across each edge.

    The weight is stated in LOGICAL pixels (round 10), so it scales with the
    density: at k=2 the band is 8 source pixels on the lit edges, which is the
    same one logical pixel it is at k=1 — and the same reason 128 buys no
    outline the board can see that 64 does not.

    Every contour pixel takes the S0 of the ramp it borders — never a shared
    black, which reads as a sticker edge. The band runs `_HALO` pixels outward
    into the transparency and the rest of the weight inward off the plane
    behind the edge, so a board that keeps one source pixel in four lands on it
    whatever the phase (see CONTOUR_WEIGHT).

    The band alone only answers for the pixels a plane faces out of; the corner
    of every stair step still met the ground with whatever plane drew it, which
    on a long top-facing edge is a dotted line of top and rim breaking the
    outline every other pixel. `_claim_outer_boundary` closes that, and is what
    makes the contour the last pass to speak.
    """
    px = img.load()
    w, h = img.size
    opaque = [px[x, y][3] == 255 for y in range(h) for x in range(w)]

    def solid(x: int, y: int) -> bool:
        return 0 <= x < w and 0 <= y < h and opaque[y * w + x]

    # First claim wins, so a pixel two edges reach takes its S0 from the plane
    # above it and then from the one to its left — one stated order, rather
    # than whichever of them happened to be painted last.
    edges: dict[tuple[int, int], Ramp] = {}
    # Rims the band reaches, with the direction it came from: a rim is the lit
    # edge of the plane behind it, so it retreats ahead of the contour rather
    # than being painted over (`_settle_rims`).
    reached: list[tuple[int, int, tuple[int, int], Ramp]] = []

    def claim(x: int, y: int, ramp: Ramp, step: tuple[int, int] | None = None) -> None:
        if (x, y) in edges:
            return
        edges[(x, y)] = ramp
        if step is not None and mids[y * w + x] == MID_FACTION:
            if px[x, y][:3] == ramp[S_RIM]:
                reached.append((x, y, step, ramp))

    for yy in range(h):
        for xx in range(w):
            if not opaque[yy * w + xx]:
                continue
            ramp = ramps[yy * w + xx]
            if ramp is None:
                continue
            for step, logical in CONTOUR_WEIGHT.items():
                if solid(xx + step[0], yy + step[1]):
                    continue
                weight = logical * k
                halo = _HALO[step] * k
                for out in range(1, halo + 1):  # outward, into the transparency
                    ex, ey = xx + step[0] * out, yy + step[1] * out
                    if not (0 <= ex < w and 0 <= ey < h) or solid(ex, ey):
                        break
                    claim(ex, ey, ramp)
                for inw in range(weight - halo):  # inward, off the plane behind
                    ex, ey = xx - step[0] * inw, yy - step[1] * inw
                    if not (0 <= ex < w and 0 <= ey < h) or not solid(ex, ey):
                        break
                    # The band eats plane, never highlight — the same rule
                    # `_interior_contour` draws by, that the hull gives up the
                    # pixel and the feature does not. An accent is a lamp, a
                    # canopy or a face and keeps every pixel it was drawn with;
                    # a fitting keeps the two lit slots it is read by, because
                    # on a 31px infantry or an awash sub those are most of the
                    # bright band the terrain ceiling reserves for units. What
                    # is still on the silhouette after that is
                    # `_claim_outer_boundary`'s, absolutely, as it always was.
                    if _is_highlight(px, mids, ramps, w, ex, ey):
                        break
                    claim(ex, ey, ramp, step)

    retreats = _settle_rims(px, mids, w, h, edges, reached, k)
    interior = _interior_contour(px, mids, ramps, w, h, opaque)
    for xx, yy, ramp in [(x, y, r) for (x, y), r in edges.items()] + interior:
        c = ramp[S_CONTOUR]
        px[xx, yy] = (c[0], c[1], c[2], 255)
        idx = yy * w + xx
        mids[idx] = MID_CONTOUR
        ramps[idx] = ramp
    for (nx, ny), ramp in retreats.items():
        c = ramp[S_RIM]
        px[nx, ny] = (c[0], c[1], c[2], 255)
    _claim_outer_boundary(px, mids, ramps, w, h)


def _is_highlight(
    px, mids: bytearray, ramps: list[Ramp | None], w: int, x: int, y: int
) -> bool:
    """Is this pixel a fitting's lit face — a thing the band may not eat?

    An accent always is: it is a lamp, a canopy or a face, drawn on tens of
    pixels, and it identifies the unit. A gunmetal fitting is one only in its
    two lit slots — a barrel's top, a deck's steel — because its dark slots are
    tracks and hulls that the outline may run straight through. The faction
    plane is not asked: its lit edge is a rim, and a rim retreats rather than
    stands (`_settle_rims`).
    """
    i = y * w + x
    if mids[i] == MID_ACCENT:
        return True
    if mids[i] != MID_GUNMETAL:
        return False
    ramp = ramps[i]
    return ramp is not None and px[x, y][:3] in (ramp[S_TOP], ramp[S_RIM])


def _settle_rims(
    px,
    mids: bytearray,
    w: int,
    h: int,
    edges: dict[tuple[int, int], Ramp],
    reached: list[tuple[int, int, tuple[int, int], Ramp]],
    k: int = 1,
) -> dict[tuple[int, int], Ramp]:
    """Move every rim the band reached one plane inboard, or leave it standing.

    A rim is the lit edge of the plane behind it, and it is the brightest thing
    on the sprite — the band `UnitBandCoverage` reserves for units. A band four
    pixels deep swallows whole leading edges, so a rim RETREATS ahead of it,
    onto the first top-plane pixel the band did not take.

    A rim with nowhere to retreat to keeps its pixel, and the band gives way
    there rather than the art: on a 31px infantry the lit plane is the rim and
    nothing else, so eating it is the terrain ceiling losing its counterpart to
    win an outline the halo outside it is already drawing. Returns the pixels to
    relight; the ones it spared are dropped from `edges` in place.
    """
    retreats: dict[tuple[int, int], tuple[Ramp, tuple[int, int]]] = {}
    for x, y, step, ramp in reached:
        target = None
        for step_back in range(1, CONTOUR_WEIGHT[step] * k + 1):
            nx, ny = x - step[0] * step_back, y - step[1] * step_back
            if not (0 <= nx < w and 0 <= ny < h):
                break
            # The band, and the rest of the leading edge it is eating: a rim
            # runs the depth of the voxel face it lit, and each of its pixels
            # asks this question for itself.
            if mids[ny * w + nx] != MID_FACTION or px[nx, ny][:3] == ramp[S_RIM]:
                continue
            if px[nx, ny][:3] != ramp[S_TOP] or (nx, ny) in edges:
                break
            # One pixel of plane cannot answer for two pixels of rim, or a
            # leading edge quietly loses half its length to a shared target.
            if (nx, ny) in retreats:
                continue
            target = (nx, ny)
            break
        if target is None:
            edges.pop((x, y), None)
            _free_lit_tip(px, mids, w, h, x, y, step, ramp, edges, retreats)
        else:
            retreats[target] = (ramp, step)
    return _pair_lone_rims(px, mids, w, h, edges, retreats)


def _free_lit_tip(
    px,
    mids: bytearray,
    w: int,
    h: int,
    x: int,
    y: int,
    step: tuple[int, int],
    ramp: Ramp,
    edges: dict[tuple[int, int], Ramp],
    retreats: dict[tuple[int, int], tuple[Ramp, tuple[int, int]]],
) -> None:
    """Give a spared rim the pixel behind it when the band took everything else.

    A lit tip one pixel wide — an infantry's shoulder, a mast — is a rim with
    nothing behind it to retreat onto, so the band gives way and leaves it
    standing. Standing alone in contour it is dirt, and `_despeckle` folds it
    away, which spends the sprite's brightest pixel on an outline the halo
    outside it is already drawing. So the tip keeps the pixel behind it too.
    """
    nx, ny = x - step[0], y - step[1]
    if not (0 <= nx < w and 0 <= ny < h) or mids[ny * w + nx] != MID_FACTION:
        return
    if px[nx, ny][:3] not in (ramp[S_TOP], ramp[S_RIM]):
        return
    edges.pop((nx, ny), None)
    retreats[(nx, ny)] = (ramp, step)


def _pair_lone_rims(
    px,
    mids: bytearray,
    w: int,
    h: int,
    edges: dict[tuple[int, int], Ramp],
    retreats: dict[tuple[int, int], tuple[Ramp, tuple[int, int]]],
) -> dict[tuple[int, int], Ramp]:
    """A rim that retreated alone takes the next pixel of plane with it.

    One lit pixel among four unlike neighbours is dirt by `_despeckle`'s own
    rule, and `_despeckle` duly folds it back into the plane — so a retreat
    that lands alone is a retreat that never happened. It lands as a pair
    instead, which is also how a rim was drawn in the first place: the leading
    face of a voxel, two rows deep.
    """
    lit = {cell: ramp for cell, (ramp, _) in retreats.items()}

    def lit_beside(x: int, y: int, ramp: Ramp) -> bool:
        for dx, dy in _NEIGHBOURS4:
            nx, ny = x + dx, y + dy
            if (nx, ny) in retreats:
                return True
            if not (0 <= nx < w and 0 <= ny < h) or (nx, ny) in edges:
                continue
            if px[nx, ny][:3] == ramp[S_RIM]:
                return True
        return False

    for (x, y), (ramp, step) in retreats.items():
        if lit_beside(x, y, ramp):
            continue
        nx, ny = x - step[0], y - step[1]
        if not (0 <= nx < w and 0 <= ny < h) or (nx, ny) in edges:
            continue
        if mids[ny * w + nx] == MID_FACTION and px[nx, ny][:3] == ramp[S_TOP]:
            lit[(nx, ny)] = ramp
    return lit


def _claim_outer_boundary(
    px, mids: bytearray, ramps: list[Ramp | None], w: int, h: int
) -> None:
    """The outer boundary is S0's, absolutely: no plane touches the ground.

    Claiming the pixel rather than growing the halo into the gap keeps the
    silhouette the shape the model drew — the alpha does not move, only the
    colour under it — so what changes is that the outline reads as one line
    instead of a dotted one.

    A rim caught out there is MOVED, not deleted: it steps one pixel inboard
    onto the top plane it leads, because a rim is the lit edge of that plane
    and the plane is still lit one pixel in. Every other claimed plane simply
    gives up the pixel; the outline is what the pixel is for.
    """
    exposed = _exposed(px, w, h)
    for yy in range(h):
        for xx in range(w):
            i = yy * w + xx
            if not exposed[i] or mids[i] == MID_CONTOUR:
                continue
            ramp = ramps[i]
            if ramp is None:
                continue
            if mids[i] == MID_FACTION and px[xx, yy][:3] == ramp[S_RIM]:
                _step_rim_inboard(px, mids, exposed, w, h, xx, yy, ramp)
            c = ramp[S_CONTOUR]
            px[xx, yy] = (c[0], c[1], c[2], 255)
            mids[i] = MID_CONTOUR


def _step_rim_inboard(
    px, mids: bytearray, exposed: list[bool], w: int, h: int, x: int, y: int, ramp: Ramp
) -> None:
    """Light the first inboard top-plane pixel this rim can retreat onto."""
    for dx, dy in _NEIGHBOURS4:
        nx, ny = x + dx, y + dy
        if not (0 <= nx < w and 0 <= ny < h):
            continue
        j = ny * w + nx
        if exposed[j] or mids[j] != MID_FACTION or px[nx, ny][:3] != ramp[S_TOP]:
            continue
        c = ramp[S_RIM]
        px[nx, ny] = (c[0], c[1], c[2], 255)
        return


_INTERIOR_STEP = 36.0  # under ~2 ramp slots of value


def _interior_contour(
    px, mids: bytearray, ramps: list[Ramp | None], w: int, h: int, opaque: list[bool]
) -> list[tuple[int, int, Ramp]]:
    """S0 between two materials whose value step is too small to read.

    The hull gives up the pixel, never the feature: a gunmetal barrel on a
    light Iron hull gets its contour out of the hull's own ramp, so the thing
    that identifies the unit keeps every pixel it was drawn with.
    """
    out: list[tuple[int, int, Ramp]] = []
    for yy in range(h):
        for xx in range(w):
            i = yy * w + xx
            if not opaque[i] or mids[i] != MID_FACTION:
                continue
            here = luminance(px[xx, yy][:3])
            for nx, ny in ((xx + 1, yy), (xx, yy + 1), (xx - 1, yy), (xx, yy - 1)):
                if not (0 <= nx < w and 0 <= ny < h and opaque[ny * w + nx]):
                    continue
                if mids[ny * w + nx] != MID_GUNMETAL:
                    continue
                if abs(here - luminance(px[nx, ny][:3])) < _INTERIOR_STEP:
                    out.append((xx, yy, ramps[i]))
                    break
    return out


def render(model: Model, faction: Faction, outline: bool = True) -> Image.Image:
    """Render to a tightly-cropped RGBA image (1px border reserved for outline)."""
    if not model.vox:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))

    anchors, minx, miny, w, h = _bounds(model)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    vox = model.vox
    zmin = min(v[2] for v in vox)
    zmax = max(v[2] for v in vox)
    zspan = max(1, zmax - zmin)
    order = sorted(vox, key=lambda v: (v[0] + v[1], v[2]))
    for x, y, z in order:
        mat = vox[(x, y, z)]
        base = resolve(mat, faction)
        gloss = mat in GLOSSY
        sx, sy = anchors[(x, y, z)]
        sx -= minx
        sy -= miny
        faces = _face_pixels(sx, sy)

        # -- ambient occlusion ------------------------------------------------
        # Top face: shadowed by walls behind it and overhangs beside it.
        ao_top = 1.0
        if (x - 1, y, z + 1) in vox or (x, y - 1, z + 1) in vox:
            ao_top *= 0.80
        if (x + 1, y, z + 1) in vox or (x, y + 1, z + 1) in vox:
            ao_top *= 0.86
        if (x - 1, y - 1, z + 1) in vox:
            ao_top *= 0.93
        # Rim light on unshadowed front-corner tops — the crisp bright edge
        # facing the camera.
        rim = (
            ao_top == 1.0
            and (x + 1, y, z) not in vox
            and (x, y + 1, z) not in vox
            and (x, y, z + 1) not in vox
        )
        # Side faces: darkened under an overhang one up and one out.
        ao_right = 0.78 if (x + 1, y, z + 1) in vox else 1.0
        ao_left = 0.82 if (x, y + 1, z + 1) in vox else 1.0
        # Contact occlusion where the model meets the ground, and a soft
        # vertical gradient so tall masses darken toward their base — the
        # extra value step that keeps big flat sides from reading flat.
        depth = (zmax - z) / zspan
        grad_left = depth * 0.10 + (0.08 if z == zmin else 0.0)
        grad_right = depth * 0.12 + (0.08 if z == zmin else 0.0)

        for face, pixels in faces.items():
            tone = shade(base, face, gloss)
            if face == "top":
                tone = mix(tone, (12, 16, 28), 1 - ao_top) if ao_top < 1.0 else tone
                if rim:
                    tone = lighten(tone, 0.13)
            elif face == "left":
                shade_amt = (1 - ao_left) + grad_left
                if shade_amt > 0:
                    tone = mix(tone, (12, 16, 28), min(0.5, shade_amt))
            elif face == "right":
                shade_amt = (1 - ao_right) + grad_right
                if shade_amt > 0:
                    tone = mix(tone, (12, 16, 28), min(0.55, shade_amt))
            dither = mat in DITHERED and face == "top"
            for ix, iy in pixels:
                c = tone
                if dither:
                    n = (h01(ix, iy, 7) - 0.5) * 0.07
                    c = lighten(tone, n) if n > 0 else darken(tone, -n)
                px[ix, iy] = (c[0], c[1], c[2], 255)

    if outline:
        _outline(img)
    return img


def _outline(img: Image.Image) -> None:
    """1px per-part outline: each edge pixel is a dark tint of its neighbour."""
    px = img.load()
    w, h = img.size
    edges: list[tuple[int, int, RGB]] = []
    for yy in range(h):
        for xx in range(w):
            if px[xx, yy][3] != 0:
                continue
            neigh = []
            for nx, ny in ((xx - 1, yy), (xx + 1, yy), (xx, yy - 1), (xx, yy + 1)):
                if 0 <= nx < w and 0 <= ny < h:
                    c = px[nx, ny]
                    if c[3] == 255:
                        neigh.append(c)
            if neigh:
                r = sum(c[0] for c in neigh) // len(neigh)
                g = sum(c[1] for c in neigh) // len(neigh)
                b = sum(c[2] for c in neigh) // len(neigh)
                edges.append((xx, yy, darken((r, g, b), 0.68)))
    for xx, yy, c in edges:
        px[xx, yy] = (c[0], c[1], c[2], 255)


def compose_cell(
    sprite: Image.Image,
    kind: str = "land",
    cell: int = 64,
    bottom: int | None = None,
    dx: int = 0,
    wake: bool = False,
) -> Image.Image:
    """Center a rendered sprite on a transparent atlas cell with its shadow.

    Shadow policy (sprite review round 3): land units get a tight hard
    dithered CONTACT shadow — without one they float over the tile — and
    the airborne cue is the shadow's offset and the sky between unit and
    shadow, not its presence: 'air' hovers over a larger dithered ellipse
    displaced down-right. Dither, never blurred alpha — a gaussian smudge
    is a grey stain at cut-in scale and breaks under nearest sampling.
    'sea' sits in the water on a displacement shadow with waterline foam;
    `wake` adds the running foam a hull that is mostly under water needs to
    separate from open sea at all (see `_wake`).
    'prop' composes with no shadow (terrain tiles draw their own grounding).

    Shadow density now encodes altitude (sprite fix spec, section 4): a land
    unit's contact shadow is a quarter-tone hugging the hull, an airborne
    one a half-tone offset down-right with ground showing between. Nothing
    here is semi-transparent — every shadow and every fleck of foam is an
    opaque dither, because partial alpha is a blurred halo at cut-in scale.
    """
    out = Image.new("RGBA", (cell, cell), (0, 0, 0, 0))
    w, h = sprite.size
    if kind == "air":
        bottom = bottom if bottom is not None else 44
    else:
        bottom = bottom if bottom is not None else 55
    x0 = (cell - w) // 2 + dx
    y0 = bottom - h

    if kind == "sea":
        # Ships sit IN the water: a flat displacement shading right under the
        # hull instead of a floating blob, then foam hugging the waterline.
        rx = max(6, int(w * 0.42))
        _dither_ellipse(out, cell // 2 + dx, bottom - 1, rx, max(2, rx // 5))
    elif kind == "air":
        rx = max(6, int(w * 0.30))
        _dither_ellipse(out, cell // 2 + dx + 4, 58, rx, max(2, rx // 3))
    elif kind == "land":
        rx = max(4, int(w * 0.34))
        _dither_ellipse(
            out, cell // 2 + dx, bottom - 1, rx, max(2, rx // 4), quarter=True
        )
    place_in_cell(out, sprite, x0, y0)
    if kind == "sea":
        if wake:
            _wake(out, sprite, x0, y0)
        _waterline_foam(out)
    return out


def place_in_cell(cell_img: Image.Image, sprite: Image.Image, x0: int, y0: int) -> None:
    """Composite a sprite into a fixed-size cell, refusing to crop it.

    Pillow clips a paste at the destination edge without complaining, which
    turns a sprite that outgrew its cell into a silently trimmed barrel or
    roof. Overflow is an authoring error, so it stops the build instead.
    """
    cw, ch = cell_img.size
    sw, sh = sprite.size
    if x0 < 0 or y0 < 0 or x0 + sw > cw or y0 + sh > ch:
        raise ValueError(
            f"sprite {sw}x{sh} placed at ({x0}, {y0}) does not fit the "
            f"{cw}x{ch} cell — shorten the model or move it inward"
        )
    cell_img.alpha_composite(sprite, (x0, y0))


FOAM_ROWS = 4
FOAM: RGB = (226, 240, 250)
# How far the wake runs on past the stern, in cell columns.
WAKE_TRAIL = 6


def _wake(img: Image.Image, sprite: Image.Image, x0: int, y0: int) -> None:
    """Running foam along an awash hull's whole length, trailing off the stern.

    A ship reads against open sea by its freeboard; a submarine has none, so
    the round-4 legibility measure put the sub last on the sheet. The foam is
    what the water does about the hull it is breaking over, so it follows the
    hull's own underside — the bottom-most sprite pixel of every column —
    rather than a fixed row, and then keeps going up-right past the stern
    along the dimetric hull axis (2 columns per row).

    Opaque dither, never partial alpha, and only into empty pixels: the
    displacement shadow is laid on the same parity, so the wake shows exactly
    where that shadow does not reach instead of stippling on top of it.
    """
    px = img.load()
    sp = sprite.load()
    w, h = img.size
    sw, sh = sprite.size

    def fleck(x: int, y: int) -> None:
        if 0 <= x < w and 0 <= y < h and (x + y) % 2 == 0 and px[x, y][3] == 0:
            px[x, y] = (*FOAM, 255)

    keel = []
    for sx in range(sw):
        column = [sy for sy in range(sh) if sp[sx, sy][3] == 255]
        if column:
            keel.append((x0 + sx, y0 + max(column)))
    if not keel:
        return
    for i, (x, y) in enumerate(keel):
        fleck(x, y + 1)
        if i % 2 == 0:
            fleck(x, y + 2)
    stern_x, stern_y = keel[-1]
    for k in range(1, WAKE_TRAIL + 1):
        y = stern_y - (k + 1) // 2
        fleck(stern_x + k, y)
        fleck(stern_x + k, y + 1)


def _waterline_foam(img: Image.Image) -> None:
    """Foam flecks just outside the hull along its real waterline rows.

    The waterline is wherever the hull actually bottoms out, so the rows come
    from the composed pixels rather than from the ground line the sprite was
    placed against: `render` reserves a trailing empty row, and the dimetric
    hull tapers to a narrow tip, so a fixed offset misses the wide part of
    the wake. Flecks trail outward along the hull's last few rows, widest at
    the bottom.
    """
    px = img.load()
    w, h = img.size
    foam = FOAM
    spans = []
    for yy in range(h):
        xs = [xx for xx in range(w) if px[xx, yy][3] == 255]
        if xs:
            spans.append((yy, min(xs), max(xs)))
    if not spans:
        return
    # The outer fleck used to fade on alpha; it now thins out as a dither
    # instead, because a semi-transparent pixel is a halo at cut-in scale.
    for i, (yy, lo, hi) in enumerate(reversed(spans[-FOAM_ROWS:])):
        n = 2 if i < 2 else 1
        for k in range(1, n + 1):
            if k > 1 and yy % 2:
                continue
            if lo - k >= 0:
                px[lo - k, yy] = (*foam, 255)
            if hi + k < w:
                px[hi + k, yy] = (*foam, 255)


def _dither_ellipse(
    img: Image.Image, cx: int, cy: int, rx: int, ry: int, quarter: bool = False
) -> None:
    """A hard checkerboard shadow: opaque dark pixels, no partial alpha.

    Reads as half-tone from the board and stays crisp at cut-in scale, where
    a blurred alpha ellipse becomes a grey stain; the empty pixels let the
    terrain underneath show through, so the shadow tints without smearing.
    `quarter` is the lighter grid a land unit's contact shadow uses.
    """
    px = img.load()
    w, h = img.size
    for yy in range(cy - ry, cy + ry + 1):
        for xx in range(cx - rx, cx + rx + 1):
            if not (0 <= xx < w and 0 <= yy < h):
                continue
            if (xx + yy) % 2 or (quarter and xx % 2):
                continue
            if ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 > 1.0:
                continue
            if px[xx, yy][3] == 0:
                px[xx, yy] = (16, 18, 24, 255)
