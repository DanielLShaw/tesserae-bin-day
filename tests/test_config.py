"""Admin form -> stored config, and the sources a cell can pick from."""

import pytest

from bin_day_core.bin_logic import parse_admin_form, source_choices


def ids(*values):
    """A new-schedule id generator returning ``values`` in order."""
    it = iter(values)
    return lambda: next(it)


def stream_fields(prefix, label="", first_date="", every_weeks="", **extra):
    fields = {
        f"{prefix}-label": label,
        f"{prefix}-first_date": first_date,
        f"{prefix}-every_weeks": every_weeks,
        f"{prefix}-icon": "",
        f"{prefix}-body_colour": "",
        f"{prefix}-lid_colour": "",
    }
    fields.update({f"{prefix}-{k}": v for k, v in extra.items()})
    return fields


def test_empty_form_gives_empty_config():
    assert parse_admin_form({}, ids()) == ({"mappings": [], "schedules": []}, [])


class TestMappings:
    def test_mapping_row_is_stored_with_trimmed_fields(self):
        form = {
            "mappings-0-match": " Green ",
            "mappings-0-label": "",
            "mappings-0-icon": "leaf",
            "mappings-0-body_colour": "",
            "mappings-0-lid_colour": "black",
        }
        config, errors = parse_admin_form(form, ids())
        assert errors == []
        assert config["mappings"] == [
            {
                "match": "Green",
                "label": "",
                "icon": "leaf",
                "body_colour": "",
                "lid_colour": "black",
            }
        ]

    def test_rows_without_match_text_are_skipped(self):
        form = {"mappings-0-match": "", "mappings-0-label": "Ignored"}
        assert parse_admin_form(form, ids())[0]["mappings"] == []

    def test_deleted_rows_are_dropped(self):
        form = {
            "mappings-0-match": "Green",
            "mappings-0-delete": "on",
            "mappings-1-match": "Refuse",
        }
        assert [m["match"] for m in parse_admin_form(form, ids())[0]["mappings"]] == ["Refuse"]

    def test_rows_keep_numeric_order_with_gaps(self):
        form = {"mappings-10-match": "C", "mappings-2-match": "B", "mappings-0-match": "A"}
        assert [m["match"] for m in parse_admin_form(form, ids())[0]["mappings"]] == ["A", "B", "C"]


class TestSchedules:
    def test_existing_schedule_keeps_its_id_and_streams_are_typed(self):
        form = {
            "schedules-0-id": "home01",
            "schedules-0-name": "Home",
            **stream_fields("schedules-0-streams-0", "Refuse", "2026-09-01", "2", icon="trash"),
        }
        config, errors = parse_admin_form(form, ids())
        assert errors == []
        assert config["schedules"] == [
            {
                "id": "home01",
                "name": "Home",
                "streams": [
                    {
                        "label": "Refuse",
                        "first_date": "2026-09-01",
                        "every_weeks": 2,
                        "icon": "trash",
                        "body_colour": "",
                        "lid_colour": "",
                    }
                ],
            }
        ]

    def test_new_schedule_gets_a_generated_id(self):
        form = {
            "schedules-0-id": "",
            "schedules-0-name": "Cottage",
            **stream_fields("schedules-0-streams-0", "Recycling", "2026-10-07", "1"),
        }
        config, _ = parse_admin_form(form, ids("new123"))
        assert config["schedules"][0]["id"] == "new123"

    def test_untouched_new_schedule_block_is_ignored(self):
        form = {
            "schedules-0-id": "",
            "schedules-0-name": "",
            **stream_fields("schedules-0-streams-0"),
        }
        assert parse_admin_form(form, ids())[0]["schedules"] == []

    def test_blank_and_deleted_stream_rows_are_skipped(self):
        form = {
            "schedules-0-id": "home01",
            "schedules-0-name": "Home",
            **stream_fields("schedules-0-streams-0", "Refuse", "2026-09-01", "1", delete="on"),
            **stream_fields("schedules-0-streams-1", "Recycling", "2026-09-08", "2"),
            **stream_fields("schedules-0-streams-2"),
        }
        streams = parse_admin_form(form, ids())[0]["schedules"][0]["streams"]
        assert [s["label"] for s in streams] == ["Recycling"]

    def test_deleted_schedule_is_dropped(self):
        form = {
            "schedules-0-id": "home01",
            "schedules-0-name": "Home",
            "schedules-0-delete": "on",
            **stream_fields("schedules-0-streams-0", "Refuse", "not a date", "0"),
        }
        assert parse_admin_form(form, ids()) == ({"mappings": [], "schedules": []}, [])

    @pytest.mark.parametrize(
        ("label", "first_date", "every_weeks", "problem"),
        [
            ("", "2026-09-01", "1", "needs a label"),
            ("Refuse", "", "1", "needs a first collection date"),
            ("Refuse", "01/09/2026", "1", "needs a first collection date"),
            ("Refuse", "2026-09-01", "", "every 1 to 8 weeks"),
            ("Refuse", "2026-09-01", "0", "every 1 to 8 weeks"),
            ("Refuse", "2026-09-01", "9", "every 1 to 8 weeks"),
            ("Refuse", "2026-09-01", "1.5", "every 1 to 8 weeks"),
            ("Refuse", "2026-09-01", "\u00b2", "every 1 to 8 weeks"),
        ],
    )
    def test_invalid_stream_is_reported_with_schedule_and_row(
        self, label, first_date, every_weeks, problem
    ):
        form = {
            "schedules-0-id": "home01",
            "schedules-0-name": "Home",
            **stream_fields("schedules-0-streams-0", "Recycling", "2026-09-08", "2"),
            **stream_fields("schedules-0-streams-1", label, first_date, every_weeks),
        }
        _, errors = parse_admin_form(form, ids())
        assert len(errors) == 1
        assert errors[0].startswith("Home, stream 2:")
        assert problem in errors[0]

    def test_invalid_stream_keeps_what_was_typed_for_redisplay(self):
        form = {
            "schedules-0-id": "home01",
            "schedules-0-name": "Home",
            **stream_fields("schedules-0-streams-0", "Refuse", "2026-09-01", "nine"),
        }
        config, _ = parse_admin_form(form, ids())
        assert config["schedules"][0]["streams"][0]["every_weeks"] == "nine"

    def test_schedule_with_streams_needs_a_name(self):
        form = {
            "schedules-0-id": "",
            "schedules-0-name": " ",
            **stream_fields("schedules-0-streams-0", "Refuse", "2026-09-01", "1"),
        }
        _, errors = parse_admin_form(form, ids("x"))
        assert errors == ["Schedule 1 needs a name."]


def test_source_choices_list_each_schedule_by_name():
    config = {
        "mappings": [],
        "schedules": [
            {"id": "home01", "name": "Home", "streams": []},
            {"id": "c2", "name": "Cottage", "streams": []},
        ],
    }
    assert source_choices(config) == [
        {"value": "schedule:home01", "label": "Schedule: Home"},
        {"value": "schedule:c2", "label": "Schedule: Cottage"},
    ]
