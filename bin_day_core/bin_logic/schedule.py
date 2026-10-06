"""Fixed-rule schedules: a first collection date repeating every N weeks."""

from datetime import date, timedelta

from .resolve import clean_text, is_hidden, resolve_stream

MAX_EVERY_WEEKS = 8


def occurrences(first, every_weeks, start, end):
    """Collection dates ``first + k * every_weeks`` weeks (k >= 0) that fall
    within ``start``..``end`` inclusive. Pure calendar-date arithmetic, so
    clock changes cannot shift a collection day."""
    if type(every_weeks) is not int or not 1 <= every_weeks <= MAX_EVERY_WEEKS:
        raise ValueError(f"every_weeks must be a whole number from 1 to {MAX_EVERY_WEEKS}")
    period = timedelta(weeks=every_weeks)
    # Whole cycles to skip to reach start (ceiling division, never negative).
    current = first + max(0, -((first - start) // period)) * period
    dates = []
    while current <= end:
        dates.append(current)
        current += period
    return dates


def fixed_rule_events(streams, start, end, mappings=()):
    """``(date, stream)`` events for a fixed-rule schedule's streams within
    ``start``..``end``. A stream's own icon and colours layer over any title
    mapping, and streams the user has hidden (their own eye button, or a
    mapping's) are left out. Raises ValueError
    naming the stream if its rule is invalid."""
    events = []
    for config in streams:
        label = clean_text(config.get("label"))
        if config.get("hide") or is_hidden(label, mappings):
            continue
        try:
            first = date.fromisoformat(config.get("first_date"))
            dates = occurrences(first, config.get("every_weeks"), start, end)
        except (TypeError, ValueError) as err:
            raise ValueError(f"bin {label!r}: {err}") from err
        stream = resolve_stream(label, mappings, overrides=config)
        events.extend((day, stream) for day in dates)
    return events
