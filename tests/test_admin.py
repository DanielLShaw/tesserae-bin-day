"""The Bin Day Core admin page: show, edit and save mappings and schedules."""

import re

import pytest

INDEX = "/plugins/bin_day_core/"
SAVE = "/plugins/bin_day_core/save"

HOME = {
    "id": "home01",
    "name": "Home",
    "streams": [
        {
            "label": "Refuse",
            "first_date": "2026-09-01",
            "every_weeks": 2,
            "icon": "",
            "body_colour": "",
            "lid_colour": "",
        }
    ],
}


@pytest.fixture
def core(registry):
    return registry.get("bin_day_core").server_module


@pytest.fixture
def stored(app, core):
    def _stored(config=None):
        with app.app_context():
            if config is not None:
                core.save_config(config)
            return core.load_config()

    return _stored


def field_value(html, name):
    """The value="" of the input called ``name``."""
    match = re.search(rf'name="{re.escape(name)}"[^>]*value="([^"]*)"', html)
    assert match, f"no input {name}"
    return match[1]


def selected(html, name):
    """The selected option value of the select called ``name``."""
    block = re.search(rf'<select[^>]*name="{re.escape(name)}".*?</select>', html, re.S)
    assert block, f"no select {name}"
    option = re.search(r'<option value="([^"]*)" selected', block[0])
    return option[1] if option else ""


def test_page_shows_saved_mappings_and_schedules(client, stored):
    stored(
        {
            "mappings": [
                {"match": "Green", "label": "", "icon": "leaf", "body_colour": "", "lid_colour": ""}
            ],
            "schedules": [HOME],
        }
    )
    html = client.get(INDEX).get_data(as_text=True)
    assert field_value(html, "mappings-0-match") == "Green"
    assert selected(html, "mappings-0-icon") == "leaf"
    assert field_value(html, "schedules-0-name") == "Home"
    assert field_value(html, "schedules-0-streams-0-label") == "Refuse"
    assert field_value(html, "schedules-0-streams-0-first_date") == "2026-09-01"
    assert field_value(html, "schedules-0-streams-0-every_weeks") == "2"


def test_page_offers_blank_rows_for_adding(client, stored):
    stored({"mappings": [], "schedules": [HOME]})
    html = client.get(INDEX).get_data(as_text=True)
    assert field_value(html, "mappings-0-match") == ""
    assert field_value(html, "schedules-0-streams-1-label") == ""
    assert field_value(html, "schedules-1-name") == ""


def test_valid_save_stores_config_and_redirects_with_notice(client, stored):
    form = {
        "schedules-0-id": "",
        "schedules-0-name": "Home",
        "schedules-0-streams-0-label": "Recycling",
        "schedules-0-streams-0-first_date": "2026-10-07",
        "schedules-0-streams-0-every_weeks": "2",
        "mappings-0-match": "Green",
        "mappings-0-icon": "leaf",
    }
    resp = client.post(SAVE, data=form)
    assert resp.status_code == 302
    config = stored()
    assert config["mappings"][0]["match"] == "Green"
    [schedule] = config["schedules"]
    assert re.fullmatch(r"[0-9a-f]{8}", schedule["id"])
    assert schedule["streams"][0]["every_weeks"] == 2
    assert "Saved" in client.get(resp.headers["Location"]).get_data(as_text=True)


def test_existing_schedule_keeps_its_id_on_save(client, stored):
    stored({"mappings": [], "schedules": [HOME]})
    form = {
        "schedules-0-id": "home01",
        "schedules-0-name": "Home renamed",
        "schedules-0-streams-0-label": "Refuse",
        "schedules-0-streams-0-first_date": "2026-09-01",
        "schedules-0-streams-0-every_weeks": "2",
    }
    client.post(SAVE, data=form)
    assert [(s["id"], s["name"]) for s in stored()["schedules"]] == [("home01", "Home renamed")]


def test_invalid_save_shows_errors_keeps_input_and_changes_nothing(client, stored):
    stored({"mappings": [], "schedules": [HOME]})
    form = {
        "schedules-0-id": "home01",
        "schedules-0-name": "Home",
        "schedules-0-streams-0-label": "Refuse",
        "schedules-0-streams-0-first_date": "2026-09-01",
        "schedules-0-streams-0-every_weeks": "12",
    }
    resp = client.post(SAVE, data=form)
    html = resp.get_data(as_text=True)
    assert resp.status_code == 400
    assert "Home, stream 1: must repeat every 1 to 8 weeks" in html
    assert field_value(html, "schedules-0-streams-0-every_weeks") == "12"
    assert stored() == {"mappings": [], "schedules": [HOME]}


def test_custom_values_not_in_the_dropdowns_are_kept_selected(client, stored):
    mapping = {
        "match": "Bulky",
        "label": "",
        "icon": "tree",
        "body_colour": "#7a3e9d",
        "lid_colour": "",
    }
    stored({"mappings": [mapping], "schedules": []})
    html = client.get(INDEX).get_data(as_text=True)
    assert selected(html, "mappings-0-icon") == "tree"
    assert selected(html, "mappings-0-body_colour") == "#7a3e9d"
