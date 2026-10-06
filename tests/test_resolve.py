"""Stream resolution: event title -> {id, label, icon, body, lid}.

Colours are palette names here; hex conversion is a separate step.
"""

import pytest

from bin_day_core.bin_logic import is_hidden, resolve_stream

REFUSE = ("refuse", "trash", "black")
RECYCLING = ("recycling", "recycle", "blue")
GARDEN = ("garden", "leaf", "green")
FOOD = ("food", "fork-knife", "light_grey")
GLASS = ("glass", "wine", "light_blue")
PAPER = ("paper", "newspaper", "white")


def stream(label, id_, icon, body, lid=None):
    return {
        "id": id_,
        "label": label,
        "icon": icon,
        "body_colour": body,
        "lid_colour": lid or body,
    }


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Refuse", REFUSE),
        ("General waste", REFUSE),
        ("Residual waste", REFUSE),
        ("Rubbish", REFUSE),
        ("Household waste", REFUSE),
        ("Non-recyclable waste", REFUSE),
        ("Landfill", REFUSE),
        ("Recycling", RECYCLING),
        ("Recyclable waste", RECYCLING),
        ("Mixed", RECYCLING),
        ("Dry mixed", RECYCLING),
        ("Garden", GARDEN),
        ("Green waste", GARDEN),
        ("Organic", GARDEN),
        ("Food", FOOD),
        ("Caddy", FOOD),
        ("Glass", GLASS),
        ("Bottles", GLASS),
        ("Jars", GLASS),
        ("Paper", PAPER),
        ("Card", PAPER),
        ("Cardboard", PAPER),
    ],
)
def test_material_keyword_sets_stream_icon_and_default_colour(title, expected):
    id_, icon, colour = expected
    assert resolve_stream(title) == stream(title, id_, icon, colour)


@pytest.mark.parametrize(
    ("title", "colour"),
    [
        ("Black bin", "black"),
        ("Dark grey bin", "dark_grey"),
        ("Dark gray bin", "dark_grey"),
        ("Grey bin", "grey"),
        ("Gray bin", "grey"),
        ("Light grey bin", "light_grey"),
        ("Light gray bin", "light_grey"),
        ("Blue bin", "blue"),
        ("Light blue bin", "light_blue"),
        ("Green bin", "green"),
        ("Brown bin", "brown"),
        ("Purple bin", "purple"),
        ("Pink bin", "pink"),
        ("Maroon bin", "maroon"),
        ("Burgundy bin", "burgundy"),
        ("Red bin", "red"),
        ("Yellow bin", "yellow"),
        ("Orange bin", "orange"),
        ("White bin", "white"),
    ],
)
def test_colour_word_sets_body_and_lid_but_no_icon(title, colour):
    assert resolve_stream(title) == stream(title, "other", None, colour)


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Purple refuse bin", stream("Purple refuse bin", "refuse", "trash", "purple")),
        ("Black recycling box", stream("Black recycling box", "recycling", "recycle", "black")),
    ],
)
def test_colour_word_overrides_material_default_colour_but_keeps_icon(title, expected):
    assert resolve_stream(title) == expected


def test_green_waste_phrase_is_not_read_as_a_colour_word():
    assert resolve_stream("Green waste (brown bin)") == stream(
        "Green waste (brown bin)", "garden", "leaf", "brown"
    )


def test_first_colour_word_in_the_title_wins():
    assert resolve_stream("Blue and black bins")["body_colour"] == "blue"


@pytest.mark.parametrize(
    ("title", "material"),
    [
        ("Food and garden waste", "food"),
        ("Garden and food waste", "garden"),
        ("Glass, paper and card", "glass"),
    ],
)
def test_first_material_in_the_title_wins(title, material):
    assert resolve_stream(title)["id"] == material


@pytest.mark.parametrize("title", ["Discarded items", "Glassworks clearance", "Foodbank drop-off"])
def test_keywords_only_match_whole_words(title):
    assert resolve_stream(title)["id"] == "other"


class TestCouncilExamples:
    """Real WCS titles from the spec and the WCS sources."""

    @pytest.mark.parametrize(
        ("title", "expected"),
        [
            ("Refuse", stream("Refuse", "refuse", "trash", "black")),
            ("Recycling", stream("Recycling", "recycling", "recycle", "blue")),
            ("Green", stream("Green", "other", None, "green")),
        ],
    )
    def test_liverpool_titles_without_mappings(self, title, expected):
        assert resolve_stream(title) == expected

    def test_liverpool_green_mapped_to_leaf_becomes_garden(self):
        mappings = [{"match": "Green", "icon": "leaf"}]
        assert resolve_stream("Green", mappings) == stream("Green", "garden", "leaf", "green")

    @pytest.mark.parametrize(
        ("title", "colour"),
        [
            ("Black bin", "black"),
            ("Blue bin", "blue"),
            ("Brown bin", "brown"),
            ("Green bin", "green"),
        ],
    )
    def test_stockport_colour_titles_get_body_colour_and_no_icon(self, title, colour):
        assert resolve_stream(title) == stream(title, "other", None, colour)


class TestUserMappings:
    def test_mapping_label_renames_but_icon_still_comes_from_the_title(self):
        mappings = [{"match": "Refuse", "label": "General waste"}]
        assert resolve_stream("Refuse", mappings) == stream(
            "General waste", "refuse", "trash", "black"
        )

    def test_mapping_body_colour_overrides_colour_word_and_lid_follows(self):
        mappings = [{"match": "Brown bin", "body_colour": "purple"}]
        assert resolve_stream("Brown bin", mappings)["body_colour"] == "purple"
        assert resolve_stream("Brown bin", mappings)["lid_colour"] == "purple"

    def test_mapping_lid_colour_alone_keeps_resolved_body(self):
        mappings = [{"match": "Recycling", "lid_colour": "black"}]
        assert resolve_stream("Recycling", mappings) == stream(
            "Recycling", "recycling", "recycle", "blue", lid="black"
        )

    def test_mapping_contains_match_is_case_insensitive_and_whole_word(self):
        mappings = [{"match": "garden", "body_colour": "brown"}]
        assert resolve_stream("GARDEN WASTE collection", mappings)["body_colour"] == "brown"
        assert resolve_stream("Gardenia trimmings", mappings)["body_colour"] == "grey"

    def test_exact_match_beats_an_earlier_contains_match(self):
        mappings = [
            {"match": "Green", "body_colour": "red"},
            {"match": "green waste", "body_colour": "brown"},
        ]
        assert resolve_stream("Green waste", mappings)["body_colour"] == "brown"

    def test_first_contains_match_in_list_order_wins(self):
        mappings = [
            {"match": "waste", "body_colour": "red"},
            {"match": "food", "body_colour": "yellow"},
        ]
        assert resolve_stream("Food waste collection", mappings)["body_colour"] == "red"

    def test_mapped_material_icon_brings_that_materials_default_colour(self):
        mappings = [{"match": "Bulky", "icon": "trash"}]
        assert resolve_stream("Bulky items", mappings) == stream(
            "Bulky items", "refuse", "trash", "black"
        )

    def test_unknown_icon_is_kept_and_stream_id_stays_from_title(self):
        mappings = [{"match": "Refuse", "icon": "ph-tree"}]
        resolved = resolve_stream("Refuse", mappings)
        assert (resolved["id"], resolved["icon"]) == ("refuse", "tree")

    @pytest.mark.parametrize(
        ("given", "stored"),
        [
            ("#7A3E9D", "#7a3e9d"),
            ("#abc", "#abc"),
            ("Light Blue", "light_blue"),
            ("gray", "grey"),
        ],
    )
    def test_mapping_colour_accepts_hex_or_palette_name(self, given, stored):
        mappings = [{"match": "Refuse", "body_colour": given}]
        assert resolve_stream("Refuse", mappings)["body_colour"] == stored

    @pytest.mark.parametrize("bad", ["banana", "#12", "#ggg", "", None])
    def test_invalid_or_empty_mapping_colour_is_ignored(self, bad):
        mappings = [{"match": "Refuse", "body_colour": bad}]
        assert resolve_stream("Refuse", mappings)["body_colour"] == "black"

    def test_empty_strings_in_mapping_leave_fields_unset(self):
        mappings = [{"match": "Refuse", "label": "", "icon": "  "}]
        assert resolve_stream("Refuse", mappings) == stream("Refuse", "refuse", "trash", "black")

    def test_mapping_with_blank_match_text_is_ignored(self):
        mappings = [{"match": " ", "label": "Everything"}]
        assert resolve_stream("Refuse", mappings)["label"] == "Refuse"


class TestLidColours:
    """Councils with one body colour tell bins apart by lid, and name them by
    it: "blue-lidded bin". A lid colour colours only the lid."""

    @pytest.mark.parametrize(
        ("title", "body", "lid"),
        [
            ("Blue lid bin", "dark_grey", "blue"),
            ("Red-lidded bin", "dark_grey", "red"),
            ("Pink Lid", "dark_grey", "pink"),
            ("Grey lids", "dark_grey", "grey"),
            ("Light blue lidded bin", "dark_grey", "light_blue"),
            ("Black bin with blue lid", "black", "blue"),
            ("Blue lid, black bin", "black", "blue"),
            ("Recycling bin (brown, grey lid)", "brown", "grey"),
        ],
    )
    def test_a_lid_colour_colours_only_the_lid(self, title, body, lid):
        resolved = resolve_stream(title)
        assert (resolved["body_colour"], resolved["lid_colour"]) == (body, lid)

    def test_a_lid_colour_keeps_the_materials_icon(self):
        title = "Garden waste - brown lid"
        assert resolve_stream(title) == stream(title, "garden", "leaf", "dark_grey", "brown")

    def test_lid_must_be_a_whole_word(self):
        resolved = resolve_stream("Blue lidless box")
        assert (resolved["body_colour"], resolved["lid_colour"]) == ("blue", "blue")

    def test_a_mapping_colour_still_wins(self):
        body = resolve_stream("Blue lid bin", [{"match": "Blue lid bin", "body_colour": "purple"}])
        lid = resolve_stream("Blue lid bin", [{"match": "Blue lid bin", "lid_colour": "red"}])
        assert (body["body_colour"], body["lid_colour"]) == ("purple", "blue")
        assert (lid["body_colour"], lid["lid_colour"]) == ("dark_grey", "red")


def test_title_whitespace_is_trimmed():
    assert resolve_stream("  Recycling \n")["label"] == "Recycling"


def test_unknown_title_falls_back_to_grey_with_no_icon_and_raw_label():
    assert resolve_stream("Bulky collection") == {
        "id": "other",
        "label": "Bulky collection",
        "icon": None,
        "body_colour": "grey",
        "lid_colour": "grey",
    }


class TestHiding:
    @pytest.mark.parametrize(
        ("title", "mappings", "hidden"),
        [
            ("Green", [{"match": "Green", "hide": True}], True),
            ("green", [{"match": "Green", "hide": True}], True),
            ("Green waste", [{"match": "Green", "hide": True}], True),
            ("Greenwich", [{"match": "Green", "hide": True}], False),
            ("Green", [{"match": "Green", "icon": "leaf"}], False),
            ("Green", [{"match": "Green", "hide": False}], False),
            ("Refuse", [{"match": "Green", "hide": True}], False),
            ("Green", [], False),
        ],
    )
    def test_a_title_is_hidden_when_its_mapping_says_so(self, title, mappings, hidden):
        assert is_hidden(title, mappings) is hidden

    def test_the_mapping_that_styles_a_title_also_decides_hiding(self):
        # The exact "Green bin" mapping wins over the "Green" contains match.
        mappings = [{"match": "Green", "hide": True}, {"match": "Green bin", "icon": "leaf"}]
        assert is_hidden("Green bin", mappings) is False
