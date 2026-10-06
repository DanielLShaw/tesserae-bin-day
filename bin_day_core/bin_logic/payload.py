"""The data a bin_day cell receives from fetch()::

    {"days": [{date, days_until, streams: [{id, label, icon, body_colour,
                                            lid_colour, icon_colour}]}],
     "next_change_at": ISO 8601}

``next_change_at`` tells polling panels when the frame goes stale.
"""

from datetime import timedelta

from .config import SOURCE_PREFIX
from .days import WINDOW_DAYS, collection_days, next_change_at
from .palette import display_stream
from .schedule import fixed_rule_events


def build_payload(events, now, cutoff):
    """Payload for ``(date, stream)`` events as seen at ``now``."""
    days = collection_days(events, now, cutoff)
    for day in days:
        day["streams"] = [display_stream(stream) for stream in day["streams"]]
    return {"days": days, "next_change_at": next_change_at(now, cutoff, days).isoformat()}


def fixed_rule_payload(schedule, mappings, now, cutoff):
    """Payload for a fixed-rule schedule. Raises ValueError for a bad rule."""
    today = now.date()
    events = fixed_rule_events(
        schedule["streams"], today, today + timedelta(days=WINDOW_DAYS), mappings
    )
    return build_payload(events, now, cutoff)


def find_schedule(config, source):
    """The saved schedule a cell's ``schedule:<id>`` source names, or None."""
    if not isinstance(source, str) or not source.startswith(SOURCE_PREFIX):
        return None
    schedule_id = source.removeprefix(SOURCE_PREFIX)
    return next((s for s in config["schedules"] if s["id"] == schedule_id), None)
