"""Display colours: palette names to hex, and the icon colour on each fill.

Bin colours are data-identity colours (the colour of the real bin), so they
are fixed hexes rather than theme tokens. Provisional values: milestone 5
tunes them against the Spectra 6 inks on the reTerminal E1002.
"""

import re

from .resolve import FALLBACK_COLOUR

PALETTE = {
    "black": "#111111",
    "grey": "#8c8c8c",
    "light_grey": "#cfcfcf",
    "blue": "#1f4fd1",
    "light_blue": "#8ec5ff",
    "green": "#13803a",
    "brown": "#7a4a21",
    "purple": "#6b2c91",
    "maroon": "#800000",
    "burgundy": "#7a1f3d",
    "red": "#d42020",
    "yellow": "#f5c400",
    "orange": "#f07a00",
    "white": "#ffffff",
}

WHITE = "#ffffff"
BLACK = "#000000"

_HEX = re.compile(r"#([0-9a-f]{3}|[0-9a-f]{6})", re.IGNORECASE)


def colour_hex(value):
    """A palette name or hex as six-digit lower-case hex; unknown -> grey."""
    match = _HEX.fullmatch(value or "")
    if match:
        digits = match[1].lower()
        return "#" + (digits if len(digits) == 6 else "".join(c * 2 for c in digits))
    return PALETTE.get(value, PALETTE[FALLBACK_COLOUR])


def _luminance(hex_colour):
    """WCAG relative luminance of a six-digit hex colour."""
    channels = [int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def icon_ink(fill):
    """White or black, whichever contrasts more with ``fill``."""
    lum = _luminance(fill)
    return WHITE if (1.05 / (lum + 0.05)) >= ((lum + 0.05) / 0.05) else BLACK


def display_stream(stream):
    """``stream`` with hex body and lid colours and an ``icon_colour``."""
    body = colour_hex(stream["body_colour"])
    return {
        **stream,
        "body_colour": body,
        "lid_colour": colour_hex(stream["lid_colour"]),
        "icon_colour": icon_ink(body),
    }
