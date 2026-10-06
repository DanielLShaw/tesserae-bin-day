"""The data a bin_day cell receives from fetch()::

    {"days": [{date, days_until, streams: [{id, label, icon, body_colour,
                                            lid_colour, icon_colour}]}],
     "next_change_at": ISO 8601}

``next_change_at`` tells polling panels when the frame goes stale.
"""

from datetime import timedelta

from .days import WINDOW_DAYS, collection_days, next_change_at
from .palette import display_stream
from .schedule import fixed_rule_events


def build_payload(events, now, cutoff, eink=False):
    """Payload for ``(date, stream)`` events as seen at ``now``, coloured from
    the screen set or (``eink``) the e-ink set."""
    days = collection_days(events, now, cutoff)
    for day in days:
        day["streams"] = [display_stream(stream, eink) for stream in day["streams"]]
    return {"days": days, "next_change_at": next_change_at(now, cutoff, days).isoformat()}


def fixed_rule_payload(schedule, now, cutoff, eink=False):
    """Payload for a manual schedule's bins (each carries its own icon and
    colours). Raises ValueError naming a bin whose rule is invalid."""
    today = now.date()
    events = fixed_rule_events(schedule, today, today + timedelta(days=WINDOW_DAYS))
    return build_payload(events, now, cutoff, eink)
