"""The Bin Day Core admin page: source, bins, title mappings, saving."""

import re
from datetime import datetime, timedelta
from html import unescape
from zoneinfo import ZoneInfo

import pytest

INDEX = "/plugins/bin_day_core/"
SAVE = "/plugins/bin_day_core/save"
TITLES = "/plugins/bin_day_core/titles"
TUE_8AM = datetime(2026, 10, 6, 8, 0, tzinfo=ZoneInfo("Europe/London"))
LIVERPOOL = "calendar.liverpool_city_council"


def wcs_event(summary, day):
    end = (datetime.fromisoformat(day) + timedelta(days=1)).date().isoformat()
    return {"summary": summary, "start": {"date": day}, "end": {"date": end}}


def bin_(label, **extra):
    return {
        "label": label,
        "first_date": "2026-09-01",
        "every_weeks": 2,
        "icon": "",
        "body_colour": "",
        "lid_colour": "",
        "hide": False,
        **extra,
    }


def mapping(match, **extra):
    return {
        "match": match,
        "label": "",
        "icon": "",
        "body_colour": "",
        "lid_colour": "",
        "hide": False,
        **extra,
    }


@pytest.fixture
def core(registry, monkeypatch):
    module = registry.get("bin_day_core").server_module
    monkeypatch.setattr(module, "_now", lambda: TUE_8AM)
    return module


@pytest.fixture
def stored(app, core):
    def _stored(**config):
        with app.app_context():
            if config:
                core.save_config(
                    {"source": "schedule", "calendar": "", "schedule": [], "mappings": [], **config}
                )
            return core.load_config()

    return _stored


@pytest.fixture
def liverpool(ha_connected):
    ha_connected.add_calendar(
        LIVERPOOL,
        "Liverpool City Council",
        [
            wcs_event("Refuse", "2026-10-07"),
            wcs_event("Green", "2026-10-07"),
            wcs_event("Recycling", "2026-10-12"),
            wcs_event("Refuse", "2026-10-21"),
        ],
    )
    return ha_connected


def page(client):
    resp = client.get(INDEX)
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


def tag(html, name):
    """The opening tag of the element with ``name="<name>"``."""
    match = re.search(rf'<[^>]*name="{re.escape(name)}"[^>]*>', html)
    assert match, f"no element named {name}"
    return match[0]


def value(html, name):
    return re.search(r'value="([^"]*)"', tag(html, name))[1]


def selected(html, name):
    block = re.search(rf'<select[^>]*name="{re.escape(name)}".*?</select>', html, re.S)
    assert block, f"no select {name}"
    option = re.search(r'<option value="([^"]*)" selected', block[0])
    return option[1] if option else ""


def radio_checked(html, name, val):
    match = re.search(rf'<input[^>]*name="{name}"[^>]*value="{val}"[^>]*>', html)
    assert match, f"no radio {name}={val}"
    return "checked" in match[0]


def mapping_rows(html):
    """Each mapping row on the page, leaving out the Add templates."""
    rows = re.findall(r'<li class="bd-row bd-mapping.*?</li>', html, re.S)
    return [row for row in rows if "__N__" not in row]


def section_hidden(html, kind):
    match = re.search(rf'<section[^>]*data-show-for="{kind}"[^>]*>', html)
    assert match, f"no {kind} section"
    return "hidden" in match[0]


class TestSource:
    def test_manual_schedule_source_shows_only_its_section(self, client, stored):
        stored(source="schedule")
        html = page(client)
        assert radio_checked(html, "source", "schedule")
        assert not radio_checked(html, "source", "calendar")
        assert not section_hidden(html, "schedule")
        assert section_hidden(html, "calendar")

    def test_calendar_source_shows_only_its_section(self, client, stored):
        stored(source="calendar", calendar=LIVERPOOL)
        html = page(client)
        assert radio_checked(html, "source", "calendar")
        assert section_hidden(html, "schedule")
        assert not section_hidden(html, "calendar")

    def test_calendar_picker_lists_ha_calendars_with_the_saved_one_chosen(
        self, client, stored, liverpool
    ):
        liverpool.add_calendar("calendar.cottage", "Cottage", [])
        stored(source="calendar", calendar=LIVERPOOL)
        html = page(client)
        assert selected(html, "calendar") == LIVERPOOL
        assert 'value="calendar.cottage"' in html
        assert "sensor.outside_temperature" not in html

    def test_a_saved_calendar_ha_no_longer_lists_stays_chosen(self, client, stored, liverpool):
        stored(source="calendar", calendar="calendar.old_bins")
        assert selected(page(client), "calendar") == "calendar.old_bins"

    def test_the_manual_schedule_never_asks_ha_for_bins(self, client, stored, liverpool):
        stored(source="schedule", calendar=LIVERPOOL)
        page(client)
        assert liverpool.requests == []

    def test_without_ha_core_connected_the_page_says_how_to_connect(self, client, stored):
        stored(source="calendar")
        assert "Connect Home Assistant Core" in page(client)


class TestSchedule:
    def test_saved_bins_are_shown_as_rows(self, client, stored):
        stored(schedule=[bin_("Refuse", icon="trash")])
        html = page(client)
        assert value(html, "schedule-0-label") == "Refuse"
        assert value(html, "schedule-0-first_date") == "2026-09-01"
        assert value(html, "schedule-0-every_weeks") == "2"
        assert selected(html, "schedule-0-icon") == "trash"

    def test_a_hidden_bin_keeps_its_eye_state(self, client, stored):
        stored(schedule=[bin_("Green", hide=True), bin_("Refuse")])
        html = page(client)
        assert value(html, "schedule-0-hide") == "on"
        assert value(html, "schedule-1-hide") == ""
        assert html.count('<li class="bd-row bd-bin is-disabled"') == 1

    def test_custom_icon_and_colour_are_shown_as_custom(self, client, stored):
        stored(schedule=[bin_("Bulky", icon="armchair", body_colour="#7a3e9d")])
        html = page(client)
        assert selected(html, "schedule-0-icon") == "custom"
        assert value(html, "schedule-0-icon_custom") == "armchair"
        assert selected(html, "schedule-0-body_colour") == "custom"
        assert value(html, "schedule-0-body_colour_custom") == "#7a3e9d"

    def test_add_uses_a_row_template(self, client, stored):
        html = page(client)
        assert re.search(r'<template[^>]*data-row-template="schedule"', html)
        assert 'name="schedule-__N__-label"' in html


class TestCalendarBins:
    def test_each_title_in_the_calendar_gets_a_row_once(self, client, stored, liverpool):
        stored(source="calendar", calendar=LIVERPOOL)
        html = page(client)
        titles = re.findall(r'name="mappings-\d+-match" value="([^"]*)"', html)
        assert titles == ["Refuse", "Green", "Recycling"]

    def test_the_calendars_own_names_are_fixed_and_cannot_be_removed(
        self, client, stored, liverpool
    ):
        stored(source="calendar", calendar=LIVERPOOL)
        rows = mapping_rows(page(client))
        assert len(rows) == 3
        for n, row in enumerate(rows):
            assert f'<input type="hidden" name="mappings-{n}-match"' in row
            assert "data-remove-row" not in row

    def test_saved_mappings_fill_in_their_titles_row(self, client, stored, liverpool):
        stored(source="calendar", calendar=LIVERPOOL, mappings=[mapping("Green", icon="leaf")])
        html = page(client)
        row = re.findall(r'name="mappings-(\d+)-match" value="Green"', html)[0]
        assert selected(html, f"mappings-{row}-icon") == "leaf"

    def test_a_saved_mapping_for_another_title_stays_as_an_editable_row(
        self, client, stored, liverpool
    ):
        stored(source="calendar", calendar=LIVERPOOL, mappings=[mapping("Bulky")])
        html = page(client)
        assert re.search(r'<input type="text"[^>]*name="mappings-\d+-match" value="Bulky"', html)

    def test_unreachable_ha_says_so_and_keeps_saved_mappings(self, client, stored, liverpool):
        stored(source="calendar", calendar=LIVERPOOL, mappings=[mapping("Green", icon="leaf")])
        liverpool.stop()
        html = page(client)
        assert "can't be reached" in html
        assert 'value="Green"' in html

    def test_a_calendar_that_fails_to_load_is_reported(self, client, stored, liverpool):
        stored(source="calendar", calendar=LIVERPOOL)
        liverpool.fail_with = 500
        assert f"Couldn't read {LIVERPOOL}" in unescape(page(client))

    def test_titles_endpoint_lists_a_calendars_titles(self, client, core, liverpool):
        assert client.get(f"{TITLES}?calendar={LIVERPOOL}").get_json() == {
            "titles": ["Refuse", "Green", "Recycling"]
        }

    def test_titles_are_looked_for_8_weeks_ahead(self, client, core, liverpool):
        client.get(f"{TITLES}?calendar={LIVERPOOL}")
        [(_, query, _)] = liverpool.requests
        assert query == {"start": ["2026-10-05T23:00:00Z"], "end": ["2026-12-01T00:00:00Z"]}

    def test_titles_endpoint_reports_a_failure(self, client, core):
        data = client.get(f"{TITLES}?calendar={LIVERPOOL}").get_json()
        assert data["titles"] == []
        assert "Home Assistant Core" in data["error"]


class TestSaving:
    def test_a_valid_save_stores_the_config_and_says_saved(self, client, stored):
        form = {
            "source": "schedule",
            "schedule-0-label": "Refuse",
            "schedule-0-first_date": "2026-10-07",
            "schedule-0-every_weeks": "2",
            "schedule-0-icon": "custom",
            "schedule-0-icon_custom": "armchair",
            "schedule-0-hide": "on",
        }
        resp = client.post(SAVE, data=form)
        assert resp.status_code == 302
        [saved] = stored()["schedule"]
        assert (saved["label"], saved["every_weeks"], saved["icon"], saved["hide"]) == (
            "Refuse",
            2,
            "armchair",
            True,
        )
        assert "Saved" in client.get(resp.headers["Location"]).get_data(as_text=True)

    def test_an_invalid_save_shows_errors_keeps_input_and_changes_nothing(self, client, stored):
        stored(schedule=[bin_("Refuse")])
        form = {
            "source": "schedule",
            "schedule-0-label": "Refuse",
            "schedule-0-first_date": "2026-09-01",
            "schedule-0-every_weeks": "12",
        }
        resp = client.post(SAVE, data=form)
        html = resp.get_data(as_text=True)
        assert resp.status_code == 400
        assert "Bin 1: must repeat every 1 to 8 weeks" in html
        assert value(html, "schedule-0-every_weeks") == "12"
        assert stored()["schedule"] == [bin_("Refuse")]
