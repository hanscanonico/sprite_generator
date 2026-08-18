"""Colors: faction ramps, fixed materials, shading math, deterministic noise.

Faction colors mirror grid_commanders' CommanderVisuals.FactionTheme so the
sprites this tool bakes and the UI chrome the game draws can never disagree
about which color a faction is. Row order mirrors SideIdentity._ROW_FOR_KEY:
0 neutral, 1 meridian(red), 2 aurora(blue), 3 iron, 4 verdant.
"""

from __future__ import annotations

from dataclasses import dataclass

RGB = tuple[int, int, int]


@dataclass(frozen=True)
class Faction:
    key: str  # atlas row key (side_identity.gd)
    team: str  # per-unit PNG suffix (paste_unit_sprites.gd TEAM_ROWS)
    body: RGB  # FactionTheme.color
    body_dk: RGB  # FactionTheme.color_dark
    body_lt: RGB  # FactionTheme.color_light


# Atlas row order. Every row is the exact FactionTheme from the game's
# commander_visuals.gd (color / color_dark / color_light, x255), neutral
# included — the sprites and the UI chrome can never disagree about a
# faction's color.
FACTIONS: tuple[Faction, ...] = (
    Faction("neutral", "neutral", (96, 106, 113), (60, 68, 74), (130, 140, 146)),
    Faction("meridian", "red", (219, 74, 59), (169, 54, 49), (239, 114, 95)),
    Faction("aurora", "blue", (56, 101, 216), (43, 78, 168), (109, 140, 232)),
    Faction("iron", "iron", (74, 82, 88), (47, 54, 59), (107, 116, 123)),
    Faction("verdant", "verdant", (44, 134, 54), (29, 97, 39), (79, 168, 90)),
)

# Fixed (faction-independent) materials. Names are what models paint with.
MATERIALS: dict[str, RGB] = {
    "gunmetal": (104, 112, 124),
    "gunmetal_dk": (76, 82, 93),
    "steel": (176, 183, 193),
    "track": (61, 64, 72),
    "track_lt": (92, 96, 106),
    "tire": (50, 52, 60),
    "hub": (120, 124, 132),
    "glass": (110, 205, 228),
    "glass_dk": (58, 148, 186),
    "skin": (226, 178, 134),
    "hair": (92, 68, 50),
    "wood": (128, 92, 66),
    "rotor": (52, 54, 60),
    "bore": (28, 30, 34),
    "amber": (235, 179, 63),
    "white": (240, 242, 245),
    "deck": (139, 145, 155),
    "deck_dk": (112, 118, 128),
    "concrete": (176, 174, 166),
    "concrete_dk": (140, 138, 130),
    "asphalt": (111, 116, 124),
    "leaf": (52, 128, 58),
    "leaf_dk": (33, 96, 42),
    "leaf_lt": (94, 165, 76),
    "trunk": (109, 76, 65),
    "rock": (145, 142, 138),
    "rock_dk": (108, 106, 104),
    "snow": (238, 240, 244),
    "flame": (238, 120, 46),
    "stone": (158, 154, 146),
    "stone_dk": (122, 118, 111),
}

# Materials whose big top surfaces get a whisper of per-pixel dither texture.
DITHERED = {
    "body",
    "body_dk",
    "body_lt",
    "hull",
    "hull_dk",
    "hull_lt",
    "deck",
    "leaf",
    "concrete",
    "asphalt",
    "stone",
}
# Materials rendered glossy: hot specular top, brighter left face.
GLOSSY = {"glass", "glass_dk"}

# Cyan glass is Aurora's alone (sprite review round 3): an untinted cyan
# canopy on every row was the largest accent on some sprites and competed
# with the faction read — a verdant copter was a green-and-blue unit. Every
# other faction's canopies and bridge glass go warm grey-white.
_CANOPY: RGB = (215, 211, 200)
_CANOPY_DK: RGB = (174, 170, 158)


def resolve(material: str, faction: Faction) -> RGB:
    """A model's material name -> concrete RGB for one faction row.

    Terrain and buildings paint with this directly. Units go through the
    indexed ramps at the bottom of this file, so a unit material resolves
    only when it is a fixed accent whose ramp is derived from its colour.
    """
    if material == "body":
        return faction.body
    if material == "body_dk":
        return faction.body_dk
    if material == "body_lt":
        return faction.body_lt
    if material == "glass":
        return MATERIALS["glass"] if faction.key == "aurora" else _CANOPY
    if material == "glass_dk":
        return MATERIALS["glass_dk"] if faction.key == "aurora" else _CANOPY_DK
    return MATERIALS[material]


def clamp8(v: float) -> int:
    return max(0, min(255, round(v)))


def luminance(c: RGB) -> float:
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def mix(a: RGB, b: RGB, t: float) -> RGB:
    return (
        clamp8(a[0] + (b[0] - a[0]) * t),
        clamp8(a[1] + (b[1] - a[1]) * t),
        clamp8(a[2] + (b[2] - a[2]) * t),
    )


def lighten(c: RGB, t: float) -> RGB:
    return mix(c, (255, 255, 255), t)


def darken(c: RGB, t: float) -> RGB:
    return mix(c, (0, 0, 0), t)


# Shadows drift toward a cold blue rather than plain black — the one hue trick
# the whole sheet leans on for its slightly stylised light. The mix is kept
# mild: at 0.24 it drained the faction hue out of every right face and the
# armies went grey at board zoom (sprite review, 2026-08-13).
_SHADOW_TINT: RGB = (34, 48, 84)
_SHADOW_MIX = 0.16


def shade(c: RGB, face: str, gloss: bool = False) -> RGB:
    """The three dimetric face tones. Light comes from the top-left.

    The left (+y) face is the pure material color, as in the pack art —
    it is the face the player mostly reads, so it must stay vivid. The top
    face is always the lightest plane, and its lift is multiplicative with
    only a whisper of white: a plain white mix drained the saturation out of
    every sunlit face, and flat-decked vehicles are mostly sunlit face, so
    whole armies rendered grey-topped (sprite review, 2026-08-13). Scaling
    brightens while preserving chroma; the white mix is just the sheen.
    """
    if face == "top":
        k, w = (1.45, 0.20) if gloss else (1.30, 0.10)
        return mix(tuple(clamp8(v * k) for v in c), (255, 255, 255), w)
    if face == "left":
        return lighten(c, 0.18) if gloss else c
    # right face: darkest, cold-shifted
    return mix(darken(c, 0.40), _SHADOW_TINT, _SHADOW_MIX)


def h01(x: int, y: int, salt: int = 0) -> float:
    """Deterministic hash noise in [0,1) — stable across runs and platforms."""
    v = (x * 374761393 + y * 668265263 + salt * 2246822519) & 0xFFFFFFFF
    v = ((v ^ (v >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((v ^ (v >> 16)) & 0xFFFF) / 65536.0


def faction_by_key(key: str) -> Faction:
    for f in FACTIONS:
        if f.key == key or f.team == key:
            return f
    raise KeyError(key)


# ---------------------------------------------------------------------------
# indexed ramps — the unit palette
# ---------------------------------------------------------------------------
#
# Units are painted out of fixed six-step ramps instead of out of shading
# arithmetic (sprite fix spec round 4, sections 2-3). A slot is a lighting
# BAND, not a brightness: S0 contour, S1 under, S2 shadow, S3 body, S4 top,
# S5 rim. `shade` above computes a colour per pixel and so spends a thousand
# palette entries per atlas row on one physical surface; a slot index spends
# one, which is what makes the tint a swap rather than a blend.
#
# S3 is the design-system token itself, so a faction reads at its brand
# luminance rather than at half of it.

SLOTS = 6
S_CONTOUR, S_UNDER, S_SHADOW, S_BODY, S_TOP, S_RIM = range(SLOTS)

Ramp = tuple[RGB, ...]

# Per-pixel material ids emitted beside the colour. Tinting is a lookup on
# FACTION alone; every other id is faction-independent by construction. The
# spec's fifth id, shadow, has no entry here because a shadow is composed
# under the sprite at cell level and never lands in a sprite's map.
MID_CONTOUR = 0
MID_FACTION = 1
MID_GUNMETAL = 2
MID_ACCENT = 3
MID_EMPTY = 255


def _hexramp(*hexes: str) -> Ramp:
    return tuple((int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)) for h in hexes)


# The authored faction ramps: S3 is the game's own FactionTheme colour.
RAMPS: dict[str, Ramp] = {
    "meridian": _hexramp("2b0f0e", "6b2320", "a4362c", "d84a3c", "f2705a", "ffc0ab"),
    "aurora": _hexramp("0e1330", "1f3070", "2d47a4", "3c64d8", "6188f2", "bacdff"),
    "verdant": _hexramp("0d2113", "174d24", "22682c", "2c8636", "51b45c", "b6ecbc"),
    # Iron keeps its inverted identity — near-black panels jumping to light
    # steel, a value structure no chromatic faction has — but its ceiling is
    # pulled in (see IRON_TOP_SLOT) so it sits with them instead of above.
    # Its own token is at the value floor, so it is the shadow plane.
    # S4 sat at L176 while every chromatic S4 sits at L134-147, and the
    # round-5 rim pass then lifted a rimmed shadow plane INTO that slot on
    # every model — which is how Iron came back as the brightest row (17.3%
    # of its pixels above L160 against 14.0-14.9%, round-6 review). It comes
    # down to L151, under the band, and Iron's flash stays the S5 rim.
    "iron": _hexramp("05070a", "1b2026", "2b3238", "79838d", "8f99a2", "dfe6ec"),
    # Warm khaki: neutral separates from Iron's cool steel by hue rather than
    # by value, so it stops competing with the exhausted state. The round-5
    # verdict measured that hue paid for at the top of the ramp — 27% of
    # neutral pixels above L160, 4,280 of them the S4 top plane alone, which
    # made the row nobody owns the brightest row on the board. S4 comes down
    # to L156 and the hue is carried further into the sand instead, which is
    # what keeps the row a wide margin off Iron with less light in it.
    "neutral": _hexramp("1c1207", "4a3a22", "7a6440", "a4874f", "b89a5e", "ecdcab"),
}

# Shared by every faction. Five authored steps plus one interpolated mid,
# because the spec draws the gunmetal strip without a rim slot. Its body slot
# sits at L132 so an identifying feature — a barrel, a mount, a rotor mast —
# reads on a dark hull instead of only on Iron's light one.
GUNMETAL_RAMP: Ramp = _hexramp(
    "14161a", "3a4048", "5a626d", "7a848f", "a7b1bb", "d2dae1"
)

# Iron's ceiling. Shipped Iron put 27-51% of its pixels above L160 and used
# pure white, so it stopped being dark and started out-reading all three
# chromatic factions. Its top plane therefore stops at the body slot and only
# the rim steps above it: the near-black-to-light-steel jump survives — it is
# what Iron IS — while the bright band above L160 stays the chromatic
# factions' to own.
IRON_SLOT_CEILING = S_BODY


@dataclass(frozen=True)
class MaterialSlot:
    """Where a model's material name sits in the indexed palette."""

    ramp: str  # "faction", "gunmetal", or "" = derived from resolve()
    slot: int
    mid: int


_FACTION_SLOT = "faction"
_GUNMETAL_SLOT = "gunmetal"


def _fac(slot: int) -> MaterialSlot:
    return MaterialSlot(_FACTION_SLOT, slot, MID_FACTION)


def _gun(slot: int) -> MaterialSlot:
    return MaterialSlot(_GUNMETAL_SLOT, slot, MID_GUNMETAL)


def _accent(slot: int) -> MaterialSlot:
    return MaterialSlot("", slot, MID_ACCENT)


# The livery convention, restated as slots: the chassis mass wears the body
# slot, the identity accents the two above it. `hull` is no longer a blend
# toward chassis grey — the ramp already carries the value structure the
# blend was faking, and the blend is what halved the brand luminance.
UNIT_MATERIALS: dict[str, MaterialSlot] = {
    "hull": _fac(S_BODY),
    "hull_dk": _fac(S_SHADOW),
    "hull_lt": _fac(S_TOP),
    "body": _fac(S_TOP),
    "body_dk": _fac(S_BODY),
    "body_lt": _fac(S_RIM),
    "gunmetal": _gun(S_BODY),
    "gunmetal_dk": _gun(S_SHADOW),
    "steel": _gun(S_TOP),
    "hub": _gun(S_BODY),
    "deck": _gun(S_BODY),
    "deck_dk": _gun(S_SHADOW),
    "track": _gun(S_UNDER),
    "track_lt": _gun(S_SHADOW),
    "tire": _gun(S_UNDER),
    "rotor": _gun(S_UNDER),
    "bore": _gun(S_CONTOUR),
}


def material_slot(material: str) -> MaterialSlot:
    """Slot for a model's material name; anything unlisted is a fixed accent."""
    return UNIT_MATERIALS.get(material, _accent(S_BODY))


def _derived_ramp(base: RGB) -> Ramp:
    """A six-step ramp around a fixed accent colour, shaped like the authored
    faction ones: S0 at ~12% luminance, S3 the colour itself, S5 a pale rim."""
    return (
        darken(base, 0.82),
        darken(base, 0.55),
        darken(base, 0.28),
        base,
        mix(tuple(clamp8(v * 1.22) for v in base), (255, 255, 255), 0.10),
        lighten(base, 0.62),
    )


_DERIVED: dict[RGB, Ramp] = {}


def ramp_for(material: str, faction: Faction) -> Ramp:
    """The ramp a material is painted out of, for one faction row."""
    spec = material_slot(material)
    if spec.ramp == _FACTION_SLOT:
        return RAMPS[faction.key]
    if spec.ramp == _GUNMETAL_SLOT:
        return GUNMETAL_RAMP
    base = resolve(material, faction)
    ramp = _DERIVED.get(base)
    if ramp is None:
        ramp = _derived_ramp(base)
        _DERIVED[base] = ramp
    return ramp
