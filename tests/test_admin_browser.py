"""The Bin Day Core admin page's scripts, driven in a real browser."""

from datetime import datetime, timedelta

import pytest

ADMIN = "/plugins/bin_day_core/"
LIVERPOOL = "calendar.liverpool_city_council"


def wcs_event(summary, day):
    end = (datetime.fromisoformat(day) + timedelta(days=1)).date().isoformat()
    return {"summary": summary, "start": {"date": day}, "end": {"date": end}}


@pytest.fixture
def core(app, registry):
    module = registry.get("bin_day_core").server_module

    def save(**config):
        with app.app_context():
            module.save_config(
                {"source": "schedule", "calendar": "", "schedule": [], "mappings": {}, **config}
            )

    def load():
        with app.app_context():
            return module.load_config()

    module.save, module.load = save, load
    return module


def open_admin(tab):
    tab.goto(tab.base_url + ADMIN)
    tab.wait_for_load_state("networkidle")


def bin_rows(tab):
    return tab.locator('[data-rows="schedule"] [data-row]')


def test_choosing_a_source_shows_its_section(tab, core):
    core.save(source="schedule")
    open_admin(tab)
    calendar, schedule = (
        tab.locator(f'section[data-show-for="{k}"]') for k in ("calendar", "schedule")
    )
    assert schedule.is_visible() and not calendar.is_visible()
    tab.check('input[name="source"][value="calendar"]')
    assert calendar.is_visible() and not schedule.is_visible()


def test_add_reveals_a_new_bin_row_with_placeholders(tab, core):
    core.save(schedule=[{"label": "Refuse", "first_date": "2026-09-01", "every_weeks": 1}])
    open_admin(tab)
    tab.click('[data-add-row="schedule"]')
    assert bin_rows(tab).count() == 2
    new_name = bin_rows(tab).nth(1).locator('input[aria-label="Bin name"]')
    assert new_name.get_attribute("name") == "schedule-1-label"
    assert new_name.get_attribute("placeholder") == "Refuse"
    assert new_name.evaluate("el => el === document.activeElement")


def test_the_x_button_removes_a_row(tab, core):
    core.save(
        schedule=[
            {"label": "Refuse", "first_date": "2026-09-01", "every_weeks": 1},
            {"label": "Green", "first_date": "2026-09-01", "every_weeks": 2},
        ]
    )
    open_admin(tab)
    bin_rows(tab).nth(0).locator("[data-remove-row]").click()
    assert bin_rows(tab).count() == 1
    assert bin_rows(tab).nth(0).locator('input[aria-label="Bin name"]').input_value() == "Green"


def test_the_eye_button_hides_and_shows_a_row(tab, core):
    core.save(schedule=[{"label": "Green", "first_date": "2026-09-01", "every_weeks": 2}])
    open_admin(tab)
    row = bin_rows(tab).nth(0)
    row.locator("[data-toggle-hide]").click()
    assert row.locator("[data-hide-input]").input_value() == "on"
    assert "is-disabled" in row.get_attribute("class")
    assert row.locator("[data-toggle-hide] i").get_attribute("class") == "ph ph-eye-slash"
    row.locator("[data-toggle-hide]").click()
    assert row.locator("[data-hide-input]").input_value() == ""


def test_custom_icon_reveals_a_name_field_with_a_live_preview(tab, core):
    core.save(schedule=[{"label": "Bulky", "first_date": "2026-09-01", "every_weeks": 1}])
    open_admin(tab)
    row = bin_rows(tab).nth(0)
    field = row.locator("[data-icon-input]")
    assert not field.is_visible()
    row.locator('select[aria-label="Icon"]').select_option("custom")
    assert field.is_visible()
    field.fill("ph-armchair")
    assert (
        row.locator(".bd-icon-preview").get_attribute("class")
        == "ph-bold ph-armchair bd-icon-preview"
    )


def test_custom_colour_reveals_a_picker_kept_in_step_with_its_hex(tab, core):
    core.save(schedule=[{"label": "Bulky", "first_date": "2026-09-01", "every_weeks": 1}])
    open_admin(tab)
    row = bin_rows(tab).nth(0)
    row.locator('select[aria-label="Bin colour"]').select_option("custom")
    hex_field = row.locator('input[aria-label="Bin colour hex code"]')
    assert hex_field.is_visible()
    picker = row.locator('input[aria-label="Bin colour picker"]')
    hex_field.fill("#7a3e9d")
    assert picker.input_value() == "#7a3e9d"
    picker.fill("#1f4fd1")
    assert hex_field.input_value() == "#1f4fd1"


def test_a_new_row_is_saved(tab, core):
    open_admin(tab)
    tab.click('[data-add-row="schedule"]')
    row = bin_rows(tab).nth(0)
    row.locator('input[aria-label="Bin name"]').fill("Recycling")
    row.locator('input[aria-label="First collection"]').fill("2026-10-07")
    row.locator('input[aria-label="Every (weeks)"]').fill("2")
    tab.click('button[type="submit"]')
    tab.wait_for_load_state("networkidle")
    [saved] = core.load()["schedule"]
    assert (saved["label"], saved["first_date"], saved["every_weeks"]) == (
        "Recycling",
        "2026-10-07",
        2,
    )


COTTAGE = "calendar.cottage"
EMPTY = "calendar.nothing_due"


@pytest.fixture
def two_calendars(ha_connected):
    ha_connected.add_calendar(
        LIVERPOOL,
        "Liverpool City Council",
        [wcs_event("Refuse", "2026-10-07"), wcs_event("Green", "2026-10-07")],
    )
    ha_connected.add_calendar(COTTAGE, "Cottage", [wcs_event("Garden waste", "2026-10-09")])
    ha_connected.add_calendar(EMPTY, "Nothing due", [])
    return ha_connected


def shown_list(tab):
    """The rows of the calendar now chosen."""
    return tab.locator("[data-calendar-rows]:not([hidden])")


def shown_titles(tab, count):
    titles = shown_list(tab).locator("[data-title-text]")
    titles.nth(count - 1).wait_for()
    return [t.inner_text() for t in titles.all()]


def choose(tab, calendar):
    tab.select_option("[data-calendar-select]", calendar)


def test_choosing_a_calendar_lists_its_bins(tab, core, two_calendars):
    core.save(source="calendar")
    open_admin(tab)
    assert not tab.locator("[data-calendar-bins]").is_visible()
    choose(tab, LIVERPOOL)
    assert shown_titles(tab, 2) == ["Refuse", "Green"]
    names = [i.get_attribute("name") for i in shown_list(tab).locator("[name$=-match]").all()]
    assert names == ["mappings-0-match", "mappings-1-match"]
    assert tab.locator("[data-calendar-bins]").is_visible()


def test_switching_calendar_shows_only_that_calendars_bins(tab, core, two_calendars):
    core.save(source="calendar", calendar=LIVERPOOL)
    open_admin(tab)
    assert shown_titles(tab, 2) == ["Refuse", "Green"]
    choose(tab, COTTAGE)
    assert shown_titles(tab, 1) == ["Garden waste"]
    assert shown_list(tab).count() == 1
    choose(tab, LIVERPOOL)
    assert shown_titles(tab, 2) == ["Refuse", "Green"]
    choose(tab, "")
    assert not tab.locator("[data-calendar-bins]").is_visible()


def test_the_line_above_the_bins_follows_the_chosen_calendar(tab, core, two_calendars):
    core.save(source="calendar", calendar=LIVERPOOL)
    open_admin(tab)
    status = tab.locator("[data-titles-status]")
    choose(tab, EMPTY)
    tab.wait_for_function(
        "document.querySelector('[data-titles-status]').textContent.startsWith('No bin')"
    )
    assert status.inner_text() == "No bin collections in the next 8 weeks."
    choose(tab, LIVERPOOL)
    assert status.text_content() == ""
    choose(tab, EMPTY)
    assert status.inner_text() == "No bin collections in the next 8 weeks."


def test_a_calendars_saved_settings_come_with_its_bins(tab, core, two_calendars):
    refuse = {"match": "refuse", "label": "", "icon": "", "body_colour": "purple"}
    core.save(
        source="calendar",
        mappings={LIVERPOOL: [{**refuse, "lid_colour": "", "hide": False}]},
    )
    open_admin(tab)
    choose(tab, LIVERPOOL)
    assert shown_titles(tab, 2) == ["Refuse", "Green"]
    body = shown_list(tab).locator('select[aria-label="Bin colour"]').first
    assert body.input_value() == "purple"


def test_edits_survive_switching_and_every_calendar_shown_is_saved(tab, core, two_calendars):
    core.save(source="calendar", calendar=LIVERPOOL)
    open_admin(tab)
    shown_titles(tab, 2)
    shown_list(tab).locator('select[aria-label="Bin colour"]').first.select_option("purple")
    choose(tab, COTTAGE)
    shown_titles(tab, 1)
    shown_list(tab).locator("[data-toggle-hide]").click()
    choose(tab, LIVERPOOL)
    assert shown_list(tab).locator('select[aria-label="Bin colour"]').first.input_value() == (
        "purple"
    )
    tab.click('button[type="submit"]')
    tab.wait_for_load_state("networkidle")
    saved = core.load()
    assert saved["calendar"] == LIVERPOOL
    liverpool = {m["match"]: m for m in saved["mappings"][LIVERPOOL]}
    assert liverpool["Refuse"]["body_colour"] == "purple"
    assert [(m["match"], m["hide"]) for m in saved["mappings"][COTTAGE]] == [("Garden waste", True)]


def test_add_a_name_adds_to_the_chosen_calendar(tab, core, two_calendars):
    core.save(source="calendar", calendar=LIVERPOOL)
    open_admin(tab)
    shown_titles(tab, 2)
    choose(tab, COTTAGE)
    shown_titles(tab, 1)
    tab.click('[data-add-row="mappings"]')
    added = shown_list(tab).locator("[data-row]").last
    assert added.locator("[data-calendar-input]").input_value() == COTTAGE
    assert added.locator("[name$=-match]").get_attribute("name") == "mappings-3-match"
    assert added.locator("[name$=-match]").evaluate("el => el === document.activeElement")
