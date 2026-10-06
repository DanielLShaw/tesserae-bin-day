"""Home Assistant calendar events -> collection days (pure parts)."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from bin_day_core.bin_logic import (
    cache_state,
    calendar_payload,
    calendar_query_range,
    events_by_date,
)

LONDON = ZoneInfo("Europe/London")
CUTOFF = time(10, 0)


def at(*args):
    return datetime(*args, tzinfo=LONDON)


def all_day(summary, day):
    """An all-day event as HA's REST API returns it (WCS style)."""
    end = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
    return {"summary": summary, "start": {"date": day}, "end": {"date": end}}


class TestQueryRange:
    def test_local_midnight_today_to_nine_days_ahead_in_utc(self):
        # BST (UTC+1): local midnight is 23:00 UTC the day before.
        assert calendar_query_range(at(2026, 10, 6, 8, 0)) == (
            "2026-10-05T23:00:00Z",
            "2026-10-14T23:00:00Z",
        )

    def test_range_spanning_the_clocks_going_back(self):
        # Starts in BST, ends in GMT: the end is 00:00 UTC.
        assert calendar_query_range(at(2026, 10, 20, 8, 0)) == (
            "2026-10-19T23:00:00Z",
            "2026-10-29T00:00:00Z",
        )


class TestEventsByDate:
    def test_all_day_events_use_their_date(self):
        events = [all_day("Refuse", "2026-10-07"), all_day("Green", "2026-10-07")]
        assert events_by_date(events, LONDON) == [
            (date(2026, 10, 7), "Refuse"),
            (date(2026, 10, 7), "Green"),
        ]

    @pytest.mark.parametrize(
        ("start", "local_day"),
        [
            ("2026-10-07T07:00:00+01:00", date(2026, 10, 7)),
            # 23:30 UTC on the 6th is 00:30 BST on the 7th.
            ("2026-10-06T23:30:00+00:00", date(2026, 10, 7)),
            ("2026-10-06T23:30:00Z", date(2026, 10, 7)),
        ],
    )
    def test_timed_events_use_their_local_date(self, start, local_day):
        event = {"summary": "Refuse", "start": {"dateTime": start}, "end": {"dateTime": start}}
        assert events_by_date([event], LONDON) == [(local_day, "Refuse")]

    def test_titles_are_trimmed(self):
        assert events_by_date([all_day("  Recycling ", "2026-10-07")], LONDON) == [
            (date(2026, 10, 7), "Recycling")
        ]

    @pytest.mark.parametrize(
        "event",
        [
            {"start": {"date": "2026-10-07"}},
            {"summary": "  ", "start": {"date": "2026-10-07"}},
            {"summary": "Refuse"},
            {"summary": "Refuse", "start": {}},
            {"summary": "Refuse", "start": {"date": "07/10/2026"}},
            {"summary": "Refuse", "start": {"dateTime": "soon"}},
            "not an event",
        ],
    )
    def test_events_without_a_title_or_readable_start_are_skipped(self, event):
        assert events_by_date([event, all_day("Refuse", "2026-10-08")], LONDON) == [
            (date(2026, 10, 8), "Refuse")
        ]


class TestCalendarPayload:
    def test_events_become_display_ready_collection_days(self):
        events = [
            all_day("Refuse", "2026-10-07"),
            all_day("Green", "2026-10-07"),
            all_day("Recycling", "2026-10-12"),
        ]
        mappings = [{"match": "Green", "icon": "leaf"}]
        payload = calendar_payload(events, mappings, at(2026, 10, 6, 8, 0), CUTOFF)
        assert [(d["date"], [s["icon"] for s in d["streams"]]) for d in payload["days"]] == [
            ("2026-10-07", ["trash", "leaf"]),
            ("2026-10-12", ["recycle"]),
        ]
        assert payload["next_change_at"] == "2026-10-07T00:00:00+01:00"

    def test_events_beyond_the_window_are_dropped(self):
        # The query asks for 9 days so a day-old cache still covers 0..7.
        events = [all_day("Refuse", "2026-10-13"), all_day("Refuse", "2026-10-14")]
        payload = calendar_payload(events, [], at(2026, 10, 6, 8, 0), CUTOFF)
        assert [d["date"] for d in payload["days"]] == ["2026-10-13"]

    def test_same_title_twice_on_a_day_shows_once(self):
        events = [all_day("Refuse", "2026-10-07"), all_day("Refuse", "2026-10-07")]
        payload = calendar_payload(events, [], at(2026, 10, 6, 8, 0), CUTOFF)
        assert len(payload["days"][0]["streams"]) == 1


class TestCacheState:
    FETCHED = at(2026, 10, 6, 8, 0)

    @pytest.mark.parametrize(
        ("age", "state"),
        [
            (timedelta(0), "fresh"),
            (timedelta(minutes=59), "fresh"),
            (timedelta(hours=1), "usable"),
            (timedelta(hours=23, minutes=59), "usable"),
            (timedelta(hours=24), "expired"),
        ],
    )
    def test_fresh_for_an_hour_usable_for_a_day(self, age, state):
        assert cache_state(self.FETCHED.isoformat(), self.FETCHED + age) == state

    @pytest.mark.parametrize("fetched_at", [None, "", "yesterday", "2026-10-06T09:00:00+01:00"])
    def test_missing_unreadable_or_future_timestamps_are_expired(self, fetched_at):
        assert cache_state(fetched_at, self.FETCHED) == "expired"
