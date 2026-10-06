"""Pure Bin Day logic: title resolution, fixed-rule dates, collection days.

No Tesserae, Flask or Home Assistant imports, so it is unit testable on its
own. Tesserae loads a plugin's server.py as a lone file with no parent
package, so server.py loads this package by path; the relative imports
between its modules then work as normal.
"""

from .config import parse_admin_form, source_choices
from .days import collection_days, next_change_at, parse_cutoff
from .palette import colour_hex, display_stream, icon_ink
from .payload import build_payload, find_schedule, fixed_rule_payload
from .resolve import resolve_stream
from .schedule import fixed_rule_events, occurrences

__all__ = [
    "build_payload",
    "collection_days",
    "colour_hex",
    "display_stream",
    "find_schedule",
    "fixed_rule_events",
    "fixed_rule_payload",
    "icon_ink",
    "next_change_at",
    "occurrences",
    "parse_admin_form",
    "parse_cutoff",
    "resolve_stream",
    "source_choices",
]
