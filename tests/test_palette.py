"""Palette names -> hex, and the icon colour drawn on each bin fill."""

import re

import pytest

from bin_day_core.bin_logic import colour_hex, display_stream, icon_ink, mono_fill
from bin_day_core.bin_logic.resolve import COLOUR_WORDS, FALLBACK_COLOUR

from .conftest import HAVE_TESSERAE

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
        ("#00ff00", "#000000"),
    ],
)
def test_icon_ink_is_white_on_dark_fills_and_black_on_light(fill, ink):
    assert icon_ink(fill) == ink


@pytest.mark.parametrize(
    ("fill", "ink"),
    [
        ("#00ff00", "#ffffff"),
        ("#ff0000", "#ffffff"),
        ("#0000ff", "#ffffff"),
        ("#ffff00", "#000000"),
    ],
)
def test_e_ink_icons_go_by_how_each_ink_prints(fill, ink):
    # Nominal green #00ff00 is bright, but the ink prints dark forest green.
    assert icon_ink(fill, eink=True) == ink


# The six Spectra 6 ink values; fills of exactly these print as solid ink.
PANEL_INKS = {"#000000", "#ffffff", "#ffff00", "#ff0000", "#0000ff", "#00ff00"}


@pytest.mark.parametrize("name", PALETTE_NAMES)
def test_icon_on_every_screen_colour_meets_large_graphic_contrast(name):
    fill = colour_hex(name)
    assert wcag_contrast(fill, icon_ink(fill)) >= 3


@pytest.mark.parametrize("name", ["blue", "green", "red", "yellow"])
def test_screen_colours_are_softer_than_the_panel_inks(name):
    assert colour_hex(name) not in PANEL_INKS
    assert colour_hex(name) != colour_hex(name, eink=True)


@pytest.mark.skipif(not HAVE_TESSERAE, reason="needs a Tesserae checkout")
@pytest.mark.parametrize("ink", sorted(PANEL_INKS))
def test_icon_on_each_ink_meets_large_graphic_contrast_as_printed(ink):
    from app.quantizer import WAVESHARE_E6_CALIBRATED_PALETTE, WAVESHARE_E6_PALETTE

    printed = {
        f"#{r:02x}{g:02x}{b:02x}": f"#{pr:02x}{pg:02x}{pb:02x}"
        for (r, g, b), (pr, pg, pb) in zip(
            WAVESHARE_E6_PALETTE, WAVESHARE_E6_CALIBRATED_PALETTE, strict=True
        )
    }
    assert wcag_contrast(printed[ink], icon_ink(ink, eink=True)) >= 3


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
        "mono_fill": "solid",
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


def stream_of(id_, body):
    return {"id": id_, "label": "Bin", "icon": None, "body_colour": body, "lid_colour": body}


class TestMonoFill:
    @pytest.mark.parametrize(
        ("material", "body", "fill"),
        [
            ("refuse", "purple", "solid"),
            ("garden", "brown", "hatched"),
            ("recycling", "black", "white"),
        ],
    )
    def test_known_materials_keep_their_fill_whatever_the_colour(self, material, body, fill):
        assert mono_fill(stream_of(material, body)) == fill

    @pytest.mark.parametrize(
        ("body", "fill"),
        [
            ("black", "solid"),
            ("grey", "solid"),
            ("green", "hatched"),
            ("blue", "white"),
            ("white", "white"),
            ("light_grey", "white"),
            ("light_blue", "white"),
            ("yellow", "white"),
            ("brown", "dotted"),
            ("orange", "dotted"),
            ("purple", "crosshatch"),
            ("red", "crosshatch"),
            ("maroon", "crosshatch"),
            ("burgundy", "crosshatch"),
        ],
    )
    def test_other_bins_take_their_fill_from_their_colour(self, body, fill):
        assert mono_fill(stream_of("other", body)) == fill

    def test_every_palette_colour_has_a_fill(self):
        for name in PALETTE_NAMES:
            assert mono_fill(stream_of("other", name)) in {
                "solid",
                "hatched",
                "white",
                "dotted",
                "crosshatch",
            }

    def test_food_glass_and_paper_go_by_colour_too(self):
        assert mono_fill(stream_of("food", "light_grey")) == "white"
        assert mono_fill(stream_of("glass", "brown")) == "dotted"

    @pytest.mark.parametrize(
        ("body", "fill"),
        [("#202020", "solid"), ("#f0f0f0", "white"), ("#808080", "dotted")],
    )
    def test_custom_colours_go_by_brightness(self, body, fill):
        assert mono_fill(stream_of("other", body)) == fill

    def test_stockport_bins_all_look_different(self):
        fills = [mono_fill(stream_of("other", c)) for c in ("black", "green", "blue", "brown")]
        assert fills == ["solid", "hatched", "white", "dotted"]


@pytest.mark.skipif(not HAVE_TESSERAE, reason="needs a Tesserae checkout")
@pytest.mark.parametrize("name", ["black", "white", "blue", "green", "red", "yellow", "orange"])
def test_e_ink_colours_with_a_matching_panel_ink_use_it_exactly(name):
    from app.quantizer import SPECTRA_6_PALETTE

    inks = {f"#{r:02x}{g:02x}{b:02x}" for r, g, b in SPECTRA_6_PALETTE}
    assert colour_hex(name, eink=True) in inks


def test_display_stream_uses_the_e_ink_set_when_asked():
    stream = {"id": "recycling", "label": "Recycling", "icon": "recycle"}
    blue = {**stream, "body_colour": "blue", "lid_colour": "blue"}
    assert display_stream(blue, eink=True)["body_colour"] == "#0000ff"
    assert display_stream(blue)["body_colour"] not in PANEL_INKS
