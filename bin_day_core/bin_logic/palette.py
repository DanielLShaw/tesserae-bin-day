"""Display colours: palette names to hex, and the icon colour on each fill.

Bin colours are data-identity colours (the colour of the real bin), so they
are fixed hexes rather than theme tokens. There are two sets:

- screen: natural colours for browsers and ordinary colour displays.
- e-ink: colours a colour e-ink panel has an ink for (black, white, blue,
  green, red, yellow, and orange on 7-colour panels) use that ink's exact
  value, so they print as solid ink; Tesserae dithers anything else into a
  mix of inks, which speckles. They look saturated in a browser; on the
  reTerminal E1002 they print as its navy, forest, dusty red and mustard.
"""

import re

from .resolve import FALLBACK_COLOUR

SCREEN_PALETTE = {
    "black": "#111111",
    "dark_grey": "#4d4d4d",
    "grey": "#8c8c8c",
    "light_grey": "#cfcfcf",
    "blue": "#1f4fd1",
    "light_blue": "#8ec5ff",
    "green": "#13803a",
    "brown": "#7a4a21",
    "purple": "#6b2c91",
    "pink": "#e5609e",
    "maroon": "#800000",
    "burgundy": "#7a1f3d",
    "red": "#d42020",
    "yellow": "#f5c400",
    "orange": "#f07a00",
    "white": "#ffffff",
}

EINK_PALETTE = {
    **SCREEN_PALETTE,
    "black": "#000000",
    "blue": "#0000ff",
    "green": "#00ff00",
    "red": "#ff0000",
    "yellow": "#ffff00",
    "orange": "#ff8c00",
}

WHITE = "#ffffff"
BLACK = "#000000"

# How each Spectra 6 ink actually prints (measured values, from Tesserae's
# calibrated E6 palette, itself from paperlesspaper/epdoptimize). In the
# e-ink set an icon must contrast with the printed ink, not the nominal
# value: nominal green #00ff00 is bright, but the ink is a dark forest green.
PRINTED_INKS = {
    "#000000": "#1f2226",
    "#ffffff": "#b9c7c9",
    "#ffff00": "#c1bb1e",
    "#ff0000": "#62201e",
    "#0000ff": "#233f8e",
    "#00ff00": "#35563a",
}

# Black-and-white fills, so bins stay tell-apart on mono panels and themes:
# known materials keep the mockup's meaning, other bins follow their colour.
MATERIAL_FILLS = {"refuse": "solid", "garden": "hatched", "recycling": "white"}
COLOUR_FILLS = {
    "black": "solid",
    "dark_grey": "solid",
    "grey": "solid",
    "green": "hatched",
    "blue": "white",
    "white": "white",
    "light_grey": "white",
    "light_blue": "white",
    "yellow": "white",
    "brown": "dotted",
    "orange": "dotted",
    "purple": "crosshatch",
    "pink": "crosshatch",
    "red": "crosshatch",
    "maroon": "crosshatch",
    "burgundy": "crosshatch",
}

_HEX = re.compile(r"#([0-9a-f]{3}|[0-9a-f]{6})", re.IGNORECASE)


def colour_hex(value, eink=False):
    """A palette name (from the screen or e-ink set) or hex, as six-digit
    lower-case hex; unknown -> grey."""
    match = _HEX.fullmatch(value or "")
    if match:
        digits = match[1].lower()
        return "#" + (digits if len(digits) == 6 else "".join(c * 2 for c in digits))
    palette = EINK_PALETTE if eink else SCREEN_PALETTE
    return palette.get(value, palette[FALLBACK_COLOUR])


def _luminance(hex_colour):
    """WCAG relative luminance of a six-digit hex colour."""
    channels = [int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def icon_ink(fill, eink=False):
    """White or black, whichever contrasts more with ``fill``; for e-ink,
    with ``fill`` as the panel prints it."""
    lum = _luminance(PRINTED_INKS.get(fill, fill) if eink else fill)
    return WHITE if (1.05 / (lum + 0.05)) >= ((lum + 0.05) / 0.05) else BLACK


def mono_fill(stream):
    """The bin's black-and-white fill: its material's, else its lid colour's
    (the lid is the body colour unless the bin is told apart by its lid); a
    custom hex colour goes by brightness."""
    if stream["id"] in MATERIAL_FILLS:
        return MATERIAL_FILLS[stream["id"]]
    colour = stream["lid_colour"]
    if colour in COLOUR_FILLS:
        return COLOUR_FILLS[colour]
    lum = _luminance(colour_hex(colour))
    if lum < 0.15:
        return "solid"
    return "white" if lum > 0.5 else "dotted"


def display_stream(stream, eink=False):
    """``stream`` with hex body and lid colours from the screen or e-ink set,
    the icon colour on its body and on its chip (which shows the lid colour,
    the one lid-coded bins are named by), and its black-and-white ``mono_fill``."""
    body = colour_hex(stream["body_colour"], eink)
    lid = colour_hex(stream["lid_colour"], eink)
    return {
        **stream,
        "body_colour": body,
        "lid_colour": lid,
        "icon_colour": icon_ink(body, eink),
        "chip_icon_colour": icon_ink(lid, eink),
        "mono_fill": mono_fill(stream),
    }
