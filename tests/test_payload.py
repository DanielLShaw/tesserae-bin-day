"""What fetch() hands the client: display-ready days plus the refresh hint."""

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from bin_day_core.bin_logic import build_payload, find_schedule, fixed_rule_payload

LONDON = ZoneInfo("Europe/London")
TUE_8AM = datetime(2026, 10, 6, 8, 0, tzinfo=LONDON)
CUTOFF = time(10, 0)

HOME = {
    "id": "home01",
    "name": "Home",
    "streams": [{"label": "Refuse", "first_date": "2026-09-01", "every_weeks": 1}],
}
CONFIG = {"mappings": [], "schedules": [HOME]}


def test_build_payload_gives_display_streams_and_next_change():
    events = [
        (
            date(2026, 10, 7),
            {
                "id": "refuse",
                "label": "Refuse",
                "icon": "trash",
                "body_colour": "#000",
                "lid_colour": "#000",
            },
        )
    ]
    assert build_payload(events, TUE_8AM, CUTOFF) == {
        "days": [
            {
                "date": "2026-10-07",
                "days_until": 1,
                "streams": [
                    {
                        "id": "refuse",
                        "label": "Refuse",
                        "icon": "trash",
                        "body_colour": "#000000",
                        "lid_colour": "#000000",
                        "icon_colour": "#ffffff",
                    }
                ],
            }
        ],
        "next_change_at": "2026-10-07T00:00:00+01:00",
    }


def test_no_events_gives_no_days_and_midnight_refresh():
    assert build_payload([], TUE_8AM, CUTOFF) == {
        "days": [],
        "next_change_at": "2026-10-07T00:00:00+01:00",
    }


def test_fixed_rule_payload_covers_today_to_seven_days_ahead():
    payload = fixed_rule_payload(HOME, [], TUE_8AM, CUTOFF)
    assert [(d["date"], d["days_until"]) for d in payload["days"]] == [
        ("2026-10-06", 0),
        ("2026-10-13", 7),
    ]
    assert payload["next_change_at"] == "2026-10-06T10:00:00+01:00"


def test_fixed_rule_payload_applies_title_mappings():
    mappings = [{"match": "Refuse", "label": "General waste"}]
    payload = fixed_rule_payload(HOME, mappings, TUE_8AM, CUTOFF)
    assert payload["days"][0]["streams"][0]["label"] == "General waste"


@pytest.mark.parametrize(
    ("source", "found"),
    [
        ("schedule:home01", HOME),
        ("schedule:gone", None),
        ("home01", None),
        ("calendar.bins", None),
        ("", None),
        (None, None),
    ],
)
def test_find_schedule_by_cell_source(source, found):
    assert find_schedule(CONFIG, source) == found
