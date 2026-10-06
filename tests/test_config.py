"""The Bin Day Core admin form -> stored config."""

import pytest

from bin_day_core.bin_logic import parse_admin_form


def bin_row(n, label="", first_date="", every_weeks="", **extra):
    fields = {
        f"schedule-{n}-label": label,
        f"schedule-{n}-first_date": first_date,
        f"schedule-{n}-every_weeks": every_weeks,
        f"schedule-{n}-icon": "",
        f"schedule-{n}-body_colour": "",
        f"schedule-{n}-lid_colour": "",
        f"schedule-{n}-hide": "",
    }
    fields.update({f"schedule-{n}-{k}": v for k, v in extra.items()})
    return fields


def mapping_row(n, match, **extra):
    fields = {
        f"mappings-{n}-match": match,
        f"mappings-{n}-label": "",
        f"mappings-{n}-icon": "",
        f"mappings-{n}-body_colour": "",
        f"mappings-{n}-lid_colour": "",
        f"mappings-{n}-hide": "",
    }
    fields.update({f"mappings-{n}-{k}": v for k, v in extra.items()})
    return fields


def test_empty_form_is_an_empty_manual_schedule():
    assert parse_admin_form({}) == (
        {"source": "schedule", "calendar": "", "schedule": [], "mappings": []},
        [],
    )


class TestSource:
    def test_calendar_source_keeps_the_chosen_calendar(self):
        form = {"source": "calendar", "calendar": "calendar.liverpool_city_council"}
        config, errors = parse_admin_form(form)
        assert errors == []
        assert (config["source"], config["calendar"]) == (
            "calendar",
            "calendar.liverpool_city_council",
        )

    def test_calendar_source_needs_a_calendar(self):
        _, errors = parse_admin_form({"source": "calendar", "calendar": ""})
        assert errors == ["Choose your Home Assistant bin calendar."]

    def test_an_unknown_source_falls_back_to_the_manual_schedule(self):
        assert parse_admin_form({"source": "carrier pigeon"})[0]["source"] == "schedule"


class TestSchedule:
    def test_bin_rows_are_stored_typed_and_trimmed(self):
        form = {"source": "schedule", **bin_row(0, " Refuse ", "2026-09-01", "2", icon="trash")}
        config, errors = parse_admin_form(form)
        assert errors == []
        assert config["schedule"] == [
            {
                "label": "Refuse",
                "first_date": "2026-09-01",
                "every_weeks": 2,
                "icon": "trash",
                "body_colour": "",
                "lid_colour": "",
                "hide": False,
            }
        ]

    def test_rows_keep_numeric_order_with_gaps(self):
        form = {
            **bin_row(10, "Glass", "2026-09-03", "4"),
            **bin_row(2, "Recycling", "2026-09-02", "2"),
            **bin_row(0, "Refuse", "2026-09-01", "1"),
        }
        labels = [b["label"] for b in parse_admin_form(form)[0]["schedule"]]
        assert labels == ["Refuse", "Recycling", "Glass"]

    def test_an_added_row_left_blank_is_dropped(self):
        form = {**bin_row(0, "Refuse", "2026-09-01", "1"), **bin_row(1)}
        assert len(parse_admin_form(form)[0]["schedule"]) == 1

    def test_the_eye_button_hides_a_bin(self):
        form = bin_row(0, "Green", "2026-09-01", "2", hide="on")
        assert parse_admin_form(form)[0]["schedule"][0]["hide"] is True

    @pytest.mark.parametrize(
        ("label", "first_date", "every_weeks", "problem"),
        [
            ("", "2026-09-01", "1", "needs a name"),
            ("Refuse", "", "1", "needs a first collection date"),
            ("Refuse", "01/09/2026", "1", "needs a first collection date"),
            ("Refuse", "2026-09-01", "", "every 1 to 8 weeks"),
            ("Refuse", "2026-09-01", "0", "every 1 to 8 weeks"),
            ("Refuse", "2026-09-01", "9", "every 1 to 8 weeks"),
            ("Refuse", "2026-09-01", "1.5", "every 1 to 8 weeks"),
            ("Refuse", "2026-09-01", "²", "every 1 to 8 weeks"),
        ],
    )
    def test_an_invalid_bin_is_reported_by_position(self, label, first_date, every_weeks, problem):
        form = {
            "source": "schedule",
            **bin_row(0, "Recycling", "2026-09-08", "2"),
            **bin_row(1, label, first_date, every_weeks),
        }
        _, errors = parse_admin_form(form)
        assert len(errors) == 1
        assert errors[0].startswith("Bin 2:")
        assert problem in errors[0]

    @pytest.mark.parametrize("weeks", [1, 8])
    def test_every_1_to_8_weeks_is_accepted(self, weeks):
        form = {"source": "schedule", **bin_row(0, "Bulky", "2026-09-01", str(weeks))}
        config, errors = parse_admin_form(form)
        assert errors == []
        assert config["schedule"][0]["every_weeks"] == weeks

    def test_an_invalid_bin_keeps_what_was_typed_for_redisplay(self):
        form = {"source": "schedule", **bin_row(0, "Refuse", "2026-09-01", "nine")}
        config, _ = parse_admin_form(form)
        assert config["schedule"][0]["every_weeks"] == "nine"

    def test_schedule_rows_are_not_checked_while_the_calendar_is_the_source(self):
        form = {
            "source": "calendar",
            "calendar": "calendar.bins",
            **bin_row(0, "Refuse", "", "nine"),
        }
        config, errors = parse_admin_form(form)
        assert errors == []
        assert config["schedule"][0]["label"] == "Refuse"


class TestMappings:
    def test_mapping_rows_are_stored_with_trimmed_fields(self):
        form = mapping_row(0, " Green ", icon="leaf", lid_colour="black")
        assert parse_admin_form(form)[0]["mappings"] == [
            {
                "match": "Green",
                "label": "",
                "icon": "leaf",
                "body_colour": "",
                "lid_colour": "black",
                "hide": False,
            }
        ]

    def test_rows_without_match_text_are_dropped(self):
        assert parse_admin_form(mapping_row(0, "  ", label="Ignored"))[0]["mappings"] == []

    def test_the_eye_button_hides_a_collection(self):
        form = mapping_row(0, "Green", hide="on")
        assert parse_admin_form(form)[0]["mappings"][0]["hide"] is True


class TestCustomValues:
    @pytest.mark.parametrize("kind", ["schedule", "mappings"])
    def test_custom_icon_takes_the_typed_name(self, kind):
        row = (
            bin_row(0, "Bulky", "2026-09-01", "1", icon="custom", icon_custom=" armchair ")
            if kind == "schedule"
            else mapping_row(0, "Bulky", icon="custom", icon_custom=" armchair ")
        )
        assert parse_admin_form(row)[0][kind][0]["icon"] == "armchair"

    def test_custom_colours_take_the_typed_hex(self):
        form = mapping_row(
            0,
            "Bulky",
            body_colour="custom",
            body_colour_custom="#7A3E9D",
            lid_colour="custom",
            lid_colour_custom="#000000",
        )
        mapping = parse_admin_form(form)[0]["mappings"][0]
        assert (mapping["body_colour"], mapping["lid_colour"]) == ("#7A3E9D", "#000000")

    def test_custom_left_blank_means_automatic(self):
        form = mapping_row(0, "Bulky", icon="custom", icon_custom="")
        assert parse_admin_form(form)[0]["mappings"][0]["icon"] == ""
