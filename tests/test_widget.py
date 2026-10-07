"""bin_day in a real Tesserae app: every cell shows Bin Day Core's source."""

import json
from datetime import datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

import pytest

TUE_8AM = datetime(2026, 10, 6, 8, 0, tzinfo=ZoneInfo("Europe/London"))


def bin_(label, first_date="2026-09-01", every_weeks=1, **extra):
    return {
        "label": label,
        "first_date": first_date,
        "every_weeks": every_weeks,
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
def save(app, core):
    def _save(**config):
        with app.app_context():
            core.save_config(
                {"source": "schedule", "calendar": "", "schedule": [], "mappings": {}, **config}
            )

    return _save


def cell_data(client, size="sm", **opts):
    """The JSON fetch() handed the cell, read back out of the rendered markup."""
    resp = client.get(f"/_test/render?plugin=bin_day&size={size}&opts={quote(json.dumps(opts))}")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    start = body.index("data-data='") + len("data-data='")
    return json.loads(body[start : body.index("'", start)])


class TestManualSchedule:
    def test_cell_shows_the_schedules_collections(self, client, save):
        save(schedule=[bin_("Refuse")])
        data = cell_data(client, cutoff="10:00")
        assert [(d["date"], d["days_until"]) for d in data["days"]] == [
            ("2026-10-06", 0),
            ("2026-10-13", 7),
        ]
        assert data["days"][0]["streams"][0]["icon"] == "trash"
        assert data["next_change_at"] == "2026-10-06T10:00:00+01:00"

    def test_cutoff_option_marks_todays_collection_done(self, client, save):
        save(schedule=[bin_("Refuse")])
        assert [d["date"] for d in cell_data(client, cutoff="07:00")["days"]] == ["2026-10-13"]

    def test_a_bins_own_icon_and_colours_apply(self, client, save):
        save(schedule=[bin_("Green", icon="leaf", body_colour="brown")])
        [stream] = cell_data(client)["days"][0]["streams"]
        assert (stream["id"], stream["icon"], stream["mono_fill"]) == ("garden", "leaf", "hatched")

    def test_a_hidden_bin_is_left_out(self, client, save):
        save(schedule=[bin_("Refuse"), bin_("Green", hide=True)])
        labels = [s["label"] for d in cell_data(client)["days"] for s in d["streams"]]
        assert set(labels) == {"Refuse"}

    def test_colour_for_e_ink_option_sends_exact_ink_colours(self, client, save):
        save(schedule=[bin_("Refuse")])
        eink = cell_data(client, colours="eink")["days"][0]["streams"][0]
        screen = cell_data(client, colours="colour")["days"][0]["streams"][0]
        assert eink["body_colour"] == "#000000"
        assert screen["body_colour"] != "#000000"

    def test_no_bins_yet_asks_for_them(self, client, save):
        save()
        assert cell_data(client)["error"] == (
            "Add your bins in Bin Day Core (Widgets menu, Admin pages)."
        )

    def test_an_invalid_saved_bin_is_named(self, client, save):
        save(schedule=[bin_("Refuse", every_weeks=0)])
        error = cell_data(client)["error"]
        assert error.startswith("Fix your bins in Bin Day Core")
        assert "Refuse" in error


class TestOtherErrors:
    def test_calendar_source_with_no_calendar_chosen(self, client, save):
        save(source="calendar")
        assert cell_data(client)["error"] == (
            "Choose your bin calendar in Bin Day Core (Widgets menu, Admin pages)."
        )

    def test_missing_core_plugin_is_reported(self, client, registry, monkeypatch):
        monkeypatch.delitem(registry.plugins, "bin_day_core")
        assert "Bin Day Core" in cell_data(client)["error"]

    def test_corrupt_config_file_reads_as_no_bins(self, client, registry, core):
        (registry.get("bin_day_core").data_dir / "config.json").write_text("{not json")
        assert cell_data(client)["error"].startswith("Add your bins in Bin Day Core")
