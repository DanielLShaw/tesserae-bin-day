"""Pure Bin Day logic: title resolution, fixed-rule dates, collection days.

No Tesserae, Flask or Home Assistant imports, so it is unit testable on its
own. Tesserae loads a plugin's server.py as a lone file with no parent
package, so server.py loads this package by path; the relative imports
between its modules then work as normal.
"""

from .calendar import (
    cache_state,
    calendar_payload,
    calendar_query_range,
    distinct_titles,
    events_by_date,
)
from .config import parse_admin_form
from .days import collection_days, next_change_at, parse_cutoff
from .palette import colour_hex, display_stream, icon_ink, mono_fill
from .payload import build_payload, fixed_rule_payload
from .resolve import is_hidden, resolve_stream
from .schedule import fixed_rule_events, occurrences

__all__ = [
    "build_payload",
    "cache_state",
    "calendar_payload",
    "calendar_query_range",
    "collection_days",
    "colour_hex",
    "display_stream",
    "distinct_titles",
    "events_by_date",
    "fixed_rule_events",
    "fixed_rule_payload",
    "is_hidden",
    "mono_fill",
    "icon_ink",
    "next_change_at",
    "occurrences",
    "parse_admin_form",
    "parse_cutoff",
    "resolve_stream",
]
