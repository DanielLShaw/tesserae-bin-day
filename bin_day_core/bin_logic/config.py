"""The Bin Day Core admin form -> stored config.

Stored shape::

    {"source": "schedule" | "calendar",
     "calendar": "calendar.<entity>",
     "schedule": [{label, first_date, every_weeks, icon, body_colour,
                   lid_colour, hide}],
     "mappings": {"calendar.<entity>": [{match, label, icon, body_colour,
                                         lid_colour, hide}]}}

Every cell shows this one source: the manual schedule's bins, or the Home
Assistant calendar's events styled by that calendar's title mappings. Each
calendar keeps its own mappings, so switching calendar loses nothing.

The form posts ``source``, ``calendar``, and rows as ``schedule-<n>-<field>``
and ``mappings-<n>-<field>``; a mapping row's ``calendar`` field says whose it
is, and ``mappings_for`` names each calendar whose rows the page showed (so a
calendar with every row removed is stored empty). A row's icon or colour may
be "custom", its value then coming from ``<field>_custom``. ``-hide`` is set
by the row's eye button. A removed row is simply not posted.
"""

import re
from datetime import date

from .resolve import clean_text
from .schedule import MAX_EVERY_WEEKS

SOURCES = ("schedule", "calendar")
CUSTOM = "custom"
STYLE_FIELDS = ("icon", "body_colour", "lid_colour")
BIN_FIELDS = ("label", "first_date", "every_weeks")
MAPPING_FIELDS = ("match", "label")


def _all(form, key):
    """Every value posted for ``key``: a MultiDict's list, or a plain dict's
    list or single value."""
    if hasattr(form, "getlist"):
        return form.getlist(key)
    value = form.get(key)
    return value if isinstance(value, list) else [value]


def _indices(form, prefix):
    """Row numbers present in the form under ``<prefix>-<n>-``, in order."""
    pattern = re.compile(rf"{re.escape(prefix)}-(\d+)-")
    return sorted({int(m[1]) for key in form if (m := pattern.match(key))})


def _style(form, prefix, field):
    value = clean_text(form.get(f"{prefix}-{field}"))
    if value == CUSTOM:
        return clean_text(form.get(f"{prefix}-{field}_custom"))
    return value


def _row(form, prefix, fields):
    row = {field: clean_text(form.get(f"{prefix}-{field}")) for field in fields}
    row.update({field: _style(form, prefix, field) for field in STYLE_FIELDS})
    row["hide"] = bool(form.get(f"{prefix}-hide"))
    return row


def _check_bin(row, where, errors):
    """Validate one bin in place; append a message per problem."""
    if not row["label"]:
        errors.append(f"{where}: needs a name.")
    try:
        row["first_date"] = date.fromisoformat(row["first_date"]).isoformat()
    except ValueError:
        errors.append(f"{where}: needs a first collection date (YYYY-MM-DD).")
    weeks = row["every_weeks"]
    if weeks.isdecimal() and 1 <= int(weeks) <= MAX_EVERY_WEEKS:
        row["every_weeks"] = int(weeks)
    else:
        errors.append(f"{where}: must repeat every 1 to {MAX_EVERY_WEEKS} weeks (a whole number).")


def parse_admin_form(form):
    """``(config, errors)`` from the posted admin form. With errors, the config
    keeps what was typed so the page can show it again; save it only when
    ``errors`` is empty. Schedule rows are only checked while the manual
    schedule is the source, so a hidden section never blocks a save."""
    errors = []
    source = form.get("source") if form.get("source") in SOURCES else "schedule"
    calendar = clean_text(form.get("calendar"))
    if source == "calendar" and not calendar:
        errors.append("Choose your Home Assistant bin calendar.")

    schedule = []
    for n in _indices(form, "schedule"):
        row = _row(form, f"schedule-{n}", BIN_FIELDS)
        if any(row[field] for field in BIN_FIELDS):
            schedule.append(row)
    if source == "schedule":
        for position, row in enumerate(schedule, start=1):
            _check_bin(row, f"Bin {position}", errors)

    mappings = {clean_text(cal): [] for cal in _all(form, "mappings_for")}
    for n in _indices(form, "mappings"):
        row = _row(form, f"mappings-{n}", MAPPING_FIELDS)
        rows = mappings.setdefault(clean_text(form.get(f"mappings-{n}-calendar")), [])
        if row["match"]:
            rows.append(row)
    mappings.pop("", None)

    config = {"source": source, "calendar": calendar, "schedule": schedule, "mappings": mappings}
    return config, errors
