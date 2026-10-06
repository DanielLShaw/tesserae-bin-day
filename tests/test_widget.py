"""bin_day + bin_day_core in a real Tesserae app: sources, fetch and errors."""

import json
from datetime import datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

import pytest

TUE_8AM = datetime(2026, 10, 6, 8, 0, tzinfo=ZoneInfo("Europe/London"))


def stream(label, first_date="2026-09-01", every_weeks=1):
    return {
        "label": label,
        "first_date": first_date,
        "every_weeks": every_weeks,
        "icon": "",
        "body_colour": "",
        "lid_colour": "",
    }


HOME = {"id": "home01", "name": "Home", "streams": [stream("Refuse")]}


@pytest.fixture
def core(registry, monkeypatch):
    module = registry.get("bin_day_core").server_module
    monkeypatch.setattr(module, "_now", lambda: TUE_8AM)
    return module


@pytest.fixture
def save(app, core):
    def _save(*schedules, mappings=()):
        with app.app_context():
            core.save_config({"mappings": list(mappings), "schedules": list(schedules)})

    return _save


def cell_data(client, size="sm", **opts):
    """The JSON fetch() handed the cell, read back out of the rendered markup."""
    resp = client.get(f"/_test/render?plugin=bin_day&size={size}&opts={quote(json.dumps(opts))}")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    start = body.index("data-data='") + len("data-data='")
    return json.loads(body[start : body.index("'", start)])


def widget_choices(app, registry, name):
    with app.app_context():
        return registry.get("bin_day").server_module.choices(name)


class TestSources:
    def test_source_dropdown_lists_saved_schedules(self, app, registry, save):
        save(HOME, {"id": "c2", "name": "Cottage", "streams": []})
        assert widget_choices(app, registry, "sources") == [
            {"value": "schedule:home01", "label": "Schedule: Home"},
            {"value": "schedule:c2", "label": "Schedule: Cottage"},
        ]

    def test_unknown_choices_key_gives_nothing(self, app, registry, save):
        save(HOME)
        assert widget_choices(app, registry, "colours") == []

    def test_no_sources_without_the_core_plugin(self, app, registry, monkeypatch):
        monkeypatch.delitem(registry.plugins, "bin_day_core")
        assert widget_choices(app, registry, "sources") == []

    def test_corrupt_config_file_gives_no_sources_rather_than_crashing(self, app, registry):
        (registry.get("bin_day_core").data_dir / "config.json").write_text("{not json")
        assert widget_choices(app, registry, "sources") == []


class TestFetch:
    def test_cell_shows_the_schedules_collections(self, client, save):
        save(HOME)
        data = cell_data(client, source="schedule:home01", cutoff="10:00")
        assert [(d["date"], d["days_until"]) for d in data["days"]] == [
            ("2026-10-06", 0),
            ("2026-10-13", 7),
        ]
        assert data["days"][0]["streams"][0]["icon"] == "trash"
        assert data["next_change_at"] == "2026-10-06T10:00:00+01:00"

    def test_cutoff_option_marks_todays_collection_done(self, client, save):
        save(HOME)
        data = cell_data(client, source="schedule:home01", cutoff="07:00")
        assert [d["date"] for d in data["days"]] == ["2026-10-13"]

    def test_title_mappings_from_core_apply(self, client, save):
        save(HOME, mappings=[{"match": "Refuse", "label": "General waste"}])
        data = cell_data(client, source="schedule:home01")
        assert data["days"][0]["streams"][0]["label"] == "General waste"

    def test_no_source_chosen_asks_for_one(self, client, save, core):
        save(HOME)
        assert cell_data(client)["error"].startswith("Choose a bin schedule")

    def test_deleted_schedule_is_reported(self, client, save):
        save(HOME)
        assert "no longer exists" in cell_data(client, source="schedule:gone")["error"]

    def test_invalid_saved_schedule_names_the_stream(self, client, save):
        save({"id": "home01", "name": "Home", "streams": [stream("Refuse", every_weeks=0)]})
        error = cell_data(client, source="schedule:home01")["error"]
        assert error.startswith("Bin schedule 'Home' needs fixing in Bin Day Core")
        assert "Refuse" in error

    def test_missing_core_plugin_is_reported(self, client, registry, monkeypatch):
        monkeypatch.delitem(registry.plugins, "bin_day_core")
        assert "Bin Day Core" in cell_data(client, source="schedule:home01")["error"]
