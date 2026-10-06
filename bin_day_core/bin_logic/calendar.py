"""Home Assistant calendar events to collection days.

HA's REST API (GET /api/calendars/<entity_id>?start=&end=) returns events
with ``start: {"date": "YYYY-MM-DD"}`` when they are all-day, as Waste
Collection Schedule's are, or ``{"dateTime": ISO 8601}`` when timed.
"""

from datetime import UTC, date, datetime, time, timedelta

from .days import WINDOW_DAYS
from .payload import build_payload
from .resolve import clean_text, is_hidden, resolve_stream

# Days to ask HA for: one more than the window shows, so a cached answer up
# to a day old still covers today to today + WINDOW_DAYS.
QUERY_DAYS = WINDOW_DAYS + 2
CACHE_FRESH = timedelta(hours=1)
CACHE_USABLE = timedelta(hours=24)


def _utc(moment):
    # A "Z" suffix, not "+00:00": an unencoded "+" in a query string reads as a space.
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def calendar_query_range(now):
    """``(start, end)`` for the events query: local midnight today to local
    midnight QUERY_DAYS later, as UTC timestamps."""
    today = now.date()
    start = datetime.combine(today, time(0), now.tzinfo)
    end = datetime.combine(today + timedelta(days=QUERY_DAYS), time(0), now.tzinfo)
    return _utc(start), _utc(end)


def _start_date(start, tz):
    if "date" in start:
        return date.fromisoformat(start["date"])
    return datetime.fromisoformat(start["dateTime"]).astimezone(tz).date()


def events_by_date(events, tz):
    """``(date, title)`` per event: all-day events on their date, timed
    events on their local date in ``tz``. Events with no title or no
    readable start are skipped."""
    found = []
    for event in events:
        try:
            title = clean_text(event.get("summary"))
            day = _start_date(event["start"], tz)
        except (AttributeError, KeyError, TypeError, ValueError):
            continue
        if title:
            found.append((day, title))
    return found


def calendar_payload(events, mappings, now, cutoff):
    """The cell payload for HA calendar ``events`` as seen at ``now``. Titles
    the user has hidden are dropped."""
    return build_payload(
        [
            (day, resolve_stream(title, mappings))
            for day, title in events_by_date(events, now.tzinfo)
            if not is_hidden(title, mappings)
        ],
        now,
        cutoff,
    )


def cache_state(fetched_at, now):
    """How a cached HA answer fetched at ``fetched_at`` (ISO 8601) can be used:
    "fresh" (serve it, skip HA), "usable" (fetch, but fall back to it if HA
    fails) or "expired"."""
    try:
        age = now - datetime.fromisoformat(fetched_at)
    except (TypeError, ValueError):
        return "expired"
    if age < timedelta(0) or age >= CACHE_USABLE:
        return "expired"
    return "fresh" if age < CACHE_FRESH else "usable"
