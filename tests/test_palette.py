"""Palette names -> hex, and the icon colour drawn on each bin fill."""

import re

import pytest

from bin_day_core.bin_logic import colour_hex, display_stream, icon_ink
from bin_day_core.bin_logic.resolve import COLOUR_WORDS, FALLBACK_COLOUR

HEX6 = re.compile(r"#[0-9a-f]{6}")
PALETTE_NAMES = sorted({name for _, name in COLOUR_WORDS} | {FALLBACK_COLOUR})


def wcag_contrast(a, b):
    """WCAG 2 contrast ratio, computed here independently of the code under test."""

    def luminance(hex_colour):
        channels = [int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


@pytest.mark.parametrize("name", PALETTE_NAMES)
def test_every_palette_name_has_a_hex_colour(name):
    assert HEX6.fullmatch(colour_hex(name))


def test_palette_names_map_to_distinct_colours():
    hexes = [colour_hex(name) for name in PALETTE_NAMES]
    assert len(set(hexes)) == len(hexes)


@pytest.mark.parametrize(("given", "expected"), [("#7a3e9d", "#7a3e9d"), ("#abc", "#aabbcc")])
def test_custom_hex_passes_through_as_six_digits(given, expected):
    assert colour_hex(given) == expected


def test_unknown_colour_falls_back_to_the_grey_fill():
    assert colour_hex("banana") == colour_hex(FALLBACK_COLOUR)


@pytest.mark.parametrize(
    ("fill", "ink"),
    [
        ("#000000", "#ffffff"),
        ("#ffffff", "#000000"),
        ("#1f4fd1", "#ffffff"),
        ("#f5c400", "#000000"),
    ],
)
def test_icon_ink_is_white_on_dark_fills_and_black_on_light(fill, ink):
    assert icon_ink(fill) == ink


@pytest.mark.parametrize("name", PALETTE_NAMES)
def test_icon_on_every_palette_fill_meets_large_graphic_contrast(name):
    fill = colour_hex(name)
    assert wcag_contrast(fill, icon_ink(fill)) >= 3


def test_display_stream_converts_colours_and_adds_icon_colour():
    stream = {
        "id": "refuse",
        "label": "Refuse",
        "icon": "trash",
        "body_colour": "#000000",
        "lid_colour": "#fff",
    }
    assert display_stream(stream) == {
        "id": "refuse",
        "label": "Refuse",
        "icon": "trash",
        "body_colour": "#000000",
        "lid_colour": "#ffffff",
        "icon_colour": "#ffffff",
    }


def test_display_stream_resolves_palette_names():
    shown = display_stream(
        {
            "id": "other",
            "label": "Brown bin",
            "icon": None,
            "body_colour": "brown",
            "lid_colour": "brown",
        }
    )
    assert HEX6.fullmatch(shown["body_colour"])
    assert shown["body_colour"] == shown["lid_colour"] != colour_hex(FALLBACK_COLOUR)
