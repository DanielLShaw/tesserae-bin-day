"""Fixed-rule date maths: a first collection date repeating every N weeks.

Reference calendar: Tue 6 Oct 2026 is "today" in most cases. UK clocks go
back on Sun 25 Oct 2026 and forward on Sun 28 Mar 2027.
"""

from datetime import date

import pytest

from bin_day_core.bin_logic import fixed_rule_events, occurrences

TODAY = date(2026, 10, 6)
WEEK_AHEAD = date(2026, 10, 13)


@pytest.mark.parametrize(
    ("first", "every_weeks", "expected"),
    [
        # Weekly: every Tuesday.
        (date(2026, 9, 1), 1, [date(2026, 10, 6), date(2026, 10, 13)]),
        # Fortnightly, two phases: 8 Sep -> 22 Sep -> 6 Oct; 15 Sep -> 29 Sep -> 13 Oct.
        (date(2026, 9, 8), 2, [date(2026, 10, 6)]),
        (date(2026, 9, 15), 2, [date(2026, 10, 13)]),
        # Three-weekly: 1 Sep -> 22 Sep -> 13 Oct.
        (date(2026, 9, 1), 3, [date(2026, 10, 13)]),
        # Four-weekly: 11 Aug -> 8 Sep -> 6 Oct.
        (date(2026, 8, 11), 4, [date(2026, 10, 6)]),
        # Four-weekly, off-phase this window: 18 Aug -> 15 Sep -> 13 Oct.
        (date(2026, 8, 18), 4, [date(2026, 10, 13)]),
        (date(2026, 8, 25), 4, []),
        # Eight-weekly, the longest allowed cycle: 11 Aug + 56 days = 6 Oct.
        (date(2026, 8, 11), 8, [date(2026, 10, 6)]),
    ],
)
def test_cycle_and_phase_come_from_the_first_date(first, every_weeks, expected):
    assert occurrences(first, every_weeks, TODAY, WEEK_AHEAD) == expected


def test_nothing_before_a_future_first_date():
    assert occurrences(date(2026, 10, 10), 1, TODAY, WEEK_AHEAD) == [date(2026, 10, 10)]


def test_first_date_after_the_window_gives_nothing():
    assert occurrences(date(2026, 10, 20), 1, TODAY, WEEK_AHEAD) == []


def test_window_bounds_are_inclusive():
    assert occurrences(date(2026, 10, 6), 1, date(2026, 10, 6), date(2026, 10, 13)) == [
        date(2026, 10, 6),
        date(2026, 10, 13),
    ]


@pytest.mark.parametrize(
    ("first", "every_weeks", "expected"),
    [
        (date(2026, 12, 29), 1, [date(2027, 1, 5)]),
        (date(2026, 12, 22), 2, [date(2027, 1, 5)]),
    ],
)
def test_cycle_continues_across_the_year_boundary(first, every_weeks, expected):
    assert occurrences(first, every_weeks, date(2026, 12, 30), date(2027, 1, 6)) == expected


@pytest.mark.parametrize(
    ("first", "start", "end", "expected"),
    [
        # Mondays either side of BST ending (Sun 25 Oct 2026).
        (
            date(2026, 10, 19),
            date(2026, 10, 24),
            date(2026, 11, 3),
            [date(2026, 10, 26), date(2026, 11, 2)],
        ),
        # Mondays either side of BST starting (Sun 28 Mar 2027).
        (
            date(2027, 3, 22),
            date(2027, 3, 27),
            date(2027, 4, 6),
            [date(2027, 3, 29), date(2027, 4, 5)],
        ),
    ],
)
def test_clock_changes_do_not_shift_collection_days(first, start, end, expected):
    assert occurrences(first, 1, start, end) == expected


def test_first_date_years_in_the_past_keeps_its_phase():
    # 4 Jan 2000 was a Tuesday; 1,396 weeks later is Tue 6 Oct 2026.
    assert occurrences(date(2000, 1, 4), 1, TODAY, TODAY) == [TODAY]


def test_empty_window_gives_nothing():
    assert occurrences(date(2026, 9, 1), 1, WEEK_AHEAD, TODAY) == []


@pytest.mark.parametrize("every_weeks", [0, 9, -1, 1.5, True, "2", None])
def test_every_weeks_must_be_a_whole_number_from_1_to_8(every_weeks):
    with pytest.raises(ValueError, match="every_weeks"):
        occurrences(date(2026, 9, 1), every_weeks, TODAY, WEEK_AHEAD)


class TestFixedRuleEvents:
    REFUSE = {
        "id": "refuse",
        "label": "Refuse",
        "icon": "trash",
        "body_colour": "black",
        "lid_colour": "black",
    }
    RECYCLING = {
        "id": "recycling",
        "label": "Recycling",
        "icon": "recycle",
        "body_colour": "blue",
        "lid_colour": "blue",
    }

    def test_each_stream_yields_its_dates_with_its_resolved_stream(self):
        streams = [
            {"label": "Refuse", "first_date": "2026-09-01", "every_weeks": 1},
            {"label": "Recycling", "first_date": "2026-09-08", "every_weeks": 2},
        ]
        assert fixed_rule_events(streams, TODAY, WEEK_AHEAD) == [
            (date(2026, 10, 6), self.REFUSE),
            (date(2026, 10, 13), self.REFUSE),
            (date(2026, 10, 6), self.RECYCLING),
        ]

    def test_streams_own_icon_and_colours_apply(self):
        streams = [
            {
                "label": "Green",
                "first_date": "2026-10-06",
                "every_weeks": 2,
                "icon": "leaf",
                "body_colour": "brown",
                "lid_colour": "black",
            }
        ]
        assert fixed_rule_events(streams, TODAY, WEEK_AHEAD) == [
            (
                date(2026, 10, 6),
                {
                    "id": "garden",
                    "label": "Green",
                    "icon": "leaf",
                    "body_colour": "brown",
                    "lid_colour": "black",
                },
            )
        ]

    def test_streams_own_fields_layer_over_a_matching_title_mapping(self):
        streams = [
            {
                "label": "Green",
                "first_date": "2026-10-06",
                "every_weeks": 1,
                "icon": "leaf",
                "body_colour": "",
            }
        ]
        mappings = [{"match": "Green", "body_colour": "brown", "icon": "tree"}]
        [(_, resolved)] = fixed_rule_events(streams, TODAY, TODAY, mappings)
        assert (resolved["icon"], resolved["body_colour"]) == ("leaf", "brown")

    @pytest.mark.parametrize("first_date", ["", "06/10/2026", "2026-13-01", None])
    def test_invalid_first_date_is_rejected_naming_the_stream(self, first_date):
        streams = [{"label": "Refuse", "first_date": first_date, "every_weeks": 1}]
        with pytest.raises(ValueError, match="Refuse"):
            fixed_rule_events(streams, TODAY, WEEK_AHEAD)

    def test_invalid_every_weeks_is_rejected_naming_the_stream(self):
        streams = [{"label": "Refuse", "first_date": "2026-09-01", "every_weeks": 0}]
        with pytest.raises(ValueError, match="Refuse"):
            fixed_rule_events(streams, TODAY, WEEK_AHEAD)

    def test_title_mapping_label_still_renames_a_fixed_rule_stream(self):
        streams = [{"label": "Green", "first_date": "2026-10-06", "every_weeks": 1, "icon": "leaf"}]
        mappings = [{"match": "Green", "label": "Garden"}]
        [(_, resolved)] = fixed_rule_events(streams, TODAY, TODAY, mappings)
        assert resolved["label"] == "Garden"
