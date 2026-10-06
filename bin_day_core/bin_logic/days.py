"""Collection days: the 7-day window, the day cutoff and the refresh hint."""

import re
from datetime import datetime, time, timedelta

from .resolve import STREAM_ORDER, clean_text

# Days shown: today to today + WINDOW_DAYS inclusive, so a weekly bin is
# still shown ("7 days") after the cutoff on its collection day.
WINDOW_DAYS = 7

DEFAULT_CUTOFF = time(10, 0)
_CUTOFF = re.compile(r"([01]\d|2[0-3]):([0-5]\d)")

_STREAM_RANK = {stream_id: rank for rank, stream_id in enumerate(STREAM_ORDER)}


def _stream_rank(stream):
    """Streams within a day: materials in STREAM_ORDER, then the rest."""
    return _STREAM_RANK.get(stream["id"], len(_STREAM_RANK))


def collection_days(events, now, cutoff):
    """Group ``(date, stream)`` events into collection days.

    Keeps today to today + WINDOW_DAYS inclusive, dropping today once ``now``
    reaches ``cutoff``. Events on one date merge into one day, and a label
    that appears twice on a day is shown once. Day counts are calendar days.
    """
    today = now.date()
    first_day = today if now.time() < cutoff else today + timedelta(days=1)
    last_day = today + timedelta(days=WINDOW_DAYS)
    by_date = {}
    for day, stream in events:
        if first_day <= day <= last_day:
            by_date.setdefault(day, {}).setdefault(stream["label"].casefold(), stream)
    return [
        {
            "date": day.isoformat(),
            "days_until": (day - today).days,
            "streams": sorted(streams.values(), key=_stream_rank),
        }
        for day, streams in sorted(by_date.items())
    ]


def parse_cutoff(value):
    """The "HH:MM" day-cutoff option as a time; 10:00 if missing or malformed."""
    match = _CUTOFF.fullmatch(clean_text(value))
    return time(int(match[1]), int(match[2])) if match else DEFAULT_CUTOFF


def next_change_at(now, cutoff, days):
    """When the output built at ``now`` goes stale: today's cutoff while a
    collection today is showing, otherwise the next local midnight."""
    today = now.date()
    if days and days[0]["days_until"] == 0:
        return datetime.combine(today, cutoff, now.tzinfo)
    return datetime.combine(today + timedelta(days=1), time(0), now.tzinfo)
