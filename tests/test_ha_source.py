"""The Home Assistant calendar source, end to end against a fake HA."""

import json
from datetime import datetime, timedelta
from urllib.parse import quote
from zoneinfo import ZoneInfo

import pytest

TUE_8AM = datetime(2026, 10, 6, 8, 0, tzinfo=ZoneInfo("Europe/London"))
LIVERPOOL = "calendar.liverpool_city_council"
GREEN_MAPPING = {"match": "Green", "label": "", "icon": "leaf", "body_colour": "", "lid_colour": ""}


def wcs_event(summary, day):
    """An all-day event as Waste Collection Schedule's calendar returns it."""
    end = (datetime.fromisoformat(day) + timedelta(days=1)).date().isoformat()
    return {
        "summary": summary,
        "start": {"date": day},
        "end": {"date": end},
        "description": None,
        "location": None,
        "uid": "9f1c-random-per-call",
        "recurrence_id": None,
        "rrule": None,
        "status": None,
    }


LIVERPOOL_EVENTS = [
    wcs_event("Refuse", "2026-10-07"),
    wcs_event("Green", "2026-10-07"),
    wcs_event("Recycling", "2026-10-12"),
]


@pytest.fixture
def clock(registry, monkeypatch):
    """Pins bin_day_core's clock; ``clock.now`` can be moved on."""
    core = registry.get("bin_day_core").server_module

    class Clock:
        now = TUE_8AM

    monkeypatch.setattr(core, "_now", lambda: Clock.now)
    return Clock


@pytest.fixture
def liverpool(app, registry, ha_connected, clock):
    ha_connected.add_calendar(LIVERPOOL, "Liverpool City Council", LIVERPOOL_EVENTS)
    with app.app_context():
        registry.get("bin_day_core").server_module.save_config(
            {"mappings": [GREEN_MAPPING], "schedules": []}
        )
    return ha_connected


def cell_data(client, source, fresh=False):
    opts = quote(json.dumps({"source": source, "cutoff": "10:00"}))
    url = f"/_test/render?plugin=bin_day&size=sm&opts={opts}" + ("&fresh=1" if fresh else "")
    body = client.get(url).get_data(as_text=True)
    start = body.index("data-data='") + len("data-data='")
    return json.loads(body[start : body.index("'", start)])


def shown(data):
    return [(d["date"], [s["label"] for s in d["streams"]]) for d in data["days"]]


LIVERPOOL_SHOWN = [("2026-10-07", ["Refuse", "Green"]), ("2026-10-12", ["Recycling"])]


def sources(app, registry):
    with app.app_context():
        return registry.get("bin_day").server_module.choices("sources")


class TestSources:
    def test_calendars_follow_schedules_when_ha_is_connected(self, app, registry, liverpool):
        with app.app_context():
            registry.get("bin_day_core").server_module.save_config(
                {"mappings": [], "schedules": [{"id": "home01", "name": "Home", "streams": []}]}
            )
        assert sources(app, registry) == [
            {"value": "schedule:home01", "label": "Schedule: Home"},
            {
                "value": LIVERPOOL,
                "label": f"Calendar: Liverpool City Council ({LIVERPOOL})",
            },
        ]

    def test_no_calendars_offered_until_ha_core_is_connected(self, app, registry):
        assert sources(app, registry) == []

    def test_unreachable_ha_says_so_in_the_dropdown(self, app, registry, ha_connected):
        ha_connected.stop()
        [entry] = sources(app, registry)
        assert entry["value"] == ""
        assert "unreachable" in entry["label"]


class TestFetch:
    def test_cell_shows_the_calendars_collections(self, client, liverpool):
        data = cell_data(client, LIVERPOOL)
        assert shown(data) == LIVERPOOL_SHOWN
        assert data["days"][0]["streams"][1]["icon"] == "leaf"
        assert data["next_change_at"] == "2026-10-07T00:00:00+01:00"

    def test_events_are_asked_for_from_local_midnight_for_nine_days(self, client, liverpool):
        cell_data(client, LIVERPOOL)
        [(entity_id, query, headers)] = liverpool.requests
        assert entity_id == LIVERPOOL
        assert query == {"start": ["2026-10-05T23:00:00Z"], "end": ["2026-10-14T23:00:00Z"]}
        assert headers["Authorization"] == "Bearer test-token"

    def test_missing_calendar_is_named_in_the_error(self, client, liverpool):
        error = cell_data(client, "calendar.renamed_bins")["error"]
        assert "calendar.renamed_bins" in error
        assert "wasn't found" in error

    def test_ha_core_not_connected(self, client, clock):
        assert cell_data(client, LIVERPOOL)["error"].startswith("Needs Home Assistant Core")

    def test_ha_core_plugin_missing(self, client, registry, clock, monkeypatch):
        monkeypatch.delitem(registry.plugins, "ha_core")
        assert cell_data(client, LIVERPOOL)["error"].startswith("Needs Home Assistant Core")

    def test_ha_rejecting_a_known_calendar_is_a_load_error_not_a_rename(self, client, liverpool):
        liverpool.fail_with = 400
        error = cell_data(client, LIVERPOOL)["error"]
        assert error.startswith(f"Couldn't load {LIVERPOOL} from Home Assistant")

    def test_a_response_that_is_not_an_event_list_is_a_load_error(self, client, liverpool):
        liverpool.calendars[LIVERPOOL] = {"message": "surprise"}
        assert "Couldn't load" in cell_data(client, LIVERPOOL)["error"]


class TestCache:
    def test_within_an_hour_the_cached_answer_is_used(self, client, liverpool, clock):
        cell_data(client, LIVERPOOL)
        clock.now = TUE_8AM + timedelta(minutes=59)
        assert shown(cell_data(client, LIVERPOOL)) == LIVERPOOL_SHOWN
        assert len(liverpool.requests) == 1

    def test_after_an_hour_ha_is_asked_again(self, client, liverpool, clock):
        cell_data(client, LIVERPOOL)
        clock.now = TUE_8AM + timedelta(hours=1)
        cell_data(client, LIVERPOOL)
        assert len(liverpool.requests) == 2

    def test_a_fresh_render_skips_the_cache(self, client, liverpool):
        cell_data(client, LIVERPOOL)
        cell_data(client, LIVERPOOL, fresh=True)
        assert len(liverpool.requests) == 2

    @pytest.mark.parametrize("failure", ["http_error", "unreachable"])
    def test_ha_failing_serves_a_cached_answer_under_a_day_old(
        self, client, liverpool, clock, failure
    ):
        cell_data(client, LIVERPOOL)
        if failure == "http_error":
            liverpool.fail_with = 500
        else:
            liverpool.stop()
        clock.now = TUE_8AM + timedelta(hours=20)  # 04:00 Wednesday
        data = cell_data(client, LIVERPOOL)
        # Recomputed for the new day: Refuse and Green are today now.
        assert shown(data) == LIVERPOOL_SHOWN
        assert data["days"][0]["days_until"] == 0

    def test_ha_failing_with_a_day_old_cache_is_an_error(self, client, liverpool, clock):
        cell_data(client, LIVERPOOL)
        liverpool.fail_with = 500
        clock.now = TUE_8AM + timedelta(hours=24)
        error = cell_data(client, LIVERPOOL)["error"]
        assert error.startswith(f"Couldn't load {LIVERPOOL} from Home Assistant")
        assert "500" in error

    def test_ha_unreachable_with_no_cache_is_an_error(self, client, liverpool):
        liverpool.stop()
        assert "unreachable" in cell_data(client, LIVERPOOL)["error"]

    def test_each_calendar_has_its_own_cache(self, client, liverpool):
        liverpool.add_calendar("calendar.cottage", "Cottage", [wcs_event("Refuse", "2026-10-09")])
        cell_data(client, LIVERPOOL)
        assert shown(cell_data(client, "calendar.cottage")) == [("2026-10-09", ["Refuse"])]

    @pytest.mark.parametrize(
        "content",
        [
            "{not json",
            '["a list"]',
            '{"fetched_at": "2026-10-06T07:59:00+01:00", "events": "not a list"}',
        ],
    )
    def test_a_damaged_cache_file_is_ignored(self, client, registry, liverpool, content):
        folder = registry.get("bin_day_core").data_dir / "ha_cache"
        folder.mkdir(exist_ok=True)
        (folder / f"{LIVERPOOL}.json").write_text(content)
        assert shown(cell_data(client, LIVERPOOL)) == LIVERPOOL_SHOWN
        assert len(liverpool.requests) == 1
