"""Building the collection-days list: window, cutoff, merge, de-duplication."""

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from bin_day_core.bin_logic import collection_days, next_change_at, parse_cutoff

LONDON = ZoneInfo("Europe/London")
CUTOFF = time(10, 0)


def at(*args):
    return datetime(*args, tzinfo=LONDON)


def bin_(label, id_="other", colour="grey"):
    return {"id": id_, "label": label, "icon": None, "body_colour": colour, "lid_colour": colour}


REFUSE = bin_("Refuse", "refuse", "black")
RECYCLING = bin_("Recycling", "recycling", "blue")
GREEN = bin_("Green", "other", "green")

TUE_8AM = at(2026, 10, 6, 8, 0)


def test_days_carry_iso_date_count_and_streams():
    assert collection_days([(date(2026, 10, 7), REFUSE)], TUE_8AM, CUTOFF) == [
        {"date": "2026-10-07", "days_until": 1, "streams": [REFUSE]}
    ]


def test_window_is_today_to_seven_days_ahead_inclusive():
    events = [
        (date(2026, 10, 5), REFUSE),  # yesterday
        (date(2026, 10, 6), REFUSE),  # today, day 0
        (date(2026, 10, 13), RECYCLING),  # day 7
        (date(2026, 10, 14), GREEN),  # day 8
    ]
    days = collection_days(events, TUE_8AM, CUTOFF)
    assert [(d["date"], d["days_until"]) for d in days] == [("2026-10-06", 0), ("2026-10-13", 7)]


@pytest.mark.parametrize(
    ("now", "shows_today"),
    [
        (at(2026, 10, 6, 0, 0), True),
        (at(2026, 10, 6, 9, 59), True),
        (at(2026, 10, 6, 10, 0), False),
        (at(2026, 10, 6, 18, 0), False),
    ],
)
def test_todays_collection_is_done_from_the_cutoff(now, shows_today):
    events = [(date(2026, 10, 6), REFUSE), (date(2026, 10, 13), REFUSE)]
    dates = [d["date"] for d in collection_days(events, now, CUTOFF)]
    assert dates == (["2026-10-06", "2026-10-13"] if shows_today else ["2026-10-13"])


def test_streams_on_the_same_date_merge_into_one_day():
    events = [
        (date(2026, 10, 7), REFUSE),
        (date(2026, 10, 12), RECYCLING),
        (date(2026, 10, 7), GREEN),
    ]
    assert collection_days(events, TUE_8AM, CUTOFF) == [
        {"date": "2026-10-07", "days_until": 1, "streams": [REFUSE, GREEN]},
        {"date": "2026-10-12", "days_until": 6, "streams": [RECYCLING]},
    ]


def test_same_label_twice_on_one_day_shows_once():
    shouty = bin_("REFUSE", "refuse", "black")
    events = [(date(2026, 10, 7), REFUSE), (date(2026, 10, 7), shouty), (date(2026, 10, 7), REFUSE)]
    assert collection_days(events, TUE_8AM, CUTOFF)[0]["streams"] == [REFUSE]


def test_same_label_on_different_days_is_kept_on_each():
    events = [(date(2026, 10, 7), REFUSE), (date(2026, 10, 13), REFUSE)]
    assert [d["streams"] for d in collection_days(events, TUE_8AM, CUTOFF)] == [[REFUSE], [REFUSE]]


def test_streams_within_a_day_follow_material_order_whatever_the_input_order():
    food = bin_("Food", "food", "light_grey")
    garden = bin_("Garden", "garden", "green")
    events = [(date(2026, 10, 7), s) for s in (GREEN, food, RECYCLING, garden, REFUSE)]
    labels = [s["label"] for s in collection_days(events, TUE_8AM, CUTOFF)[0]["streams"]]
    assert labels == ["Refuse", "Recycling", "Garden", "Food", "Green"]


def test_days_are_in_date_order_whatever_the_input_order():
    events = [(date(2026, 10, 12), RECYCLING), (date(2026, 10, 7), REFUSE)]
    assert [d["date"] for d in collection_days(events, TUE_8AM, CUTOFF)] == [
        "2026-10-07",
        "2026-10-12",
    ]


def test_no_events_gives_no_days():
    assert collection_days([], TUE_8AM, CUTOFF) == []


def test_days_until_counts_calendar_days_not_elapsed_hours():
    # 23:30 the night before is half an hour away, but it is still "1 day".
    days = collection_days([(date(2026, 10, 26), REFUSE)], at(2026, 10, 25, 23, 30), CUTOFF)
    assert days[0]["days_until"] == 1


def test_days_until_crosses_the_year_boundary():
    days = collection_days([(date(2027, 1, 5), REFUSE)], at(2026, 12, 30, 12, 0), CUTOFF)
    assert days == [{"date": "2027-01-05", "days_until": 6, "streams": [REFUSE]}]


class TestParseCutoff:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("10:00", time(10, 0)),
            ("06:30", time(6, 30)),
            ("00:00", time(0, 0)),
            (" 23:30 ", time(23, 30)),
        ],
    )
    def test_valid_hh_mm_is_used(self, value, expected):
        assert parse_cutoff(value) == expected

    @pytest.mark.parametrize("value", ["24:00", "10:60", "1000", "07:30:00", "7:5", "", None])
    def test_anything_else_falls_back_to_ten_am(self, value):
        assert parse_cutoff(value) == time(10, 0)


class TestNextChangeAt:
    def test_todays_cutoff_while_a_collection_today_is_showing(self):
        days = collection_days([(date(2026, 10, 6), REFUSE)], TUE_8AM, CUTOFF)
        assert next_change_at(TUE_8AM, CUTOFF, days).isoformat() == "2026-10-06T10:00:00+01:00"

    def test_next_midnight_when_nothing_is_collected_today(self):
        days = collection_days([(date(2026, 10, 7), REFUSE)], TUE_8AM, CUTOFF)
        assert next_change_at(TUE_8AM, CUTOFF, days).isoformat() == "2026-10-07T00:00:00+01:00"

    def test_next_midnight_after_the_cutoff(self):
        now = at(2026, 10, 6, 11, 0)
        days = collection_days([(date(2026, 10, 6), REFUSE)], now, CUTOFF)
        assert next_change_at(now, CUTOFF, days).isoformat() == "2026-10-07T00:00:00+01:00"

    def test_next_midnight_when_there_are_no_days(self):
        assert next_change_at(TUE_8AM, CUTOFF, []).isoformat() == "2026-10-07T00:00:00+01:00"

    @pytest.mark.parametrize(
        ("now", "expected"),
        [
            # Clocks go back at 02:00 on Sun 25 Oct 2026.
            (at(2026, 10, 24, 22, 0), "2026-10-25T00:00:00+01:00"),
            (at(2026, 10, 25, 12, 0), "2026-10-26T00:00:00+00:00"),
            # Clocks go forward at 01:00 on Sun 28 Mar 2027.
            (at(2027, 3, 27, 22, 0), "2027-03-28T00:00:00+00:00"),
            (at(2027, 3, 28, 12, 0), "2027-03-29T00:00:00+01:00"),
        ],
    )
    def test_midnight_is_local_across_clock_changes(self, now, expected):
        assert next_change_at(now, CUTOFF, []).isoformat() == expected
