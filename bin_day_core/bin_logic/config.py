"""The Bin Day Core admin config: form parsing and cell source choices.

Stored shape::

    {"mappings": [{match, label, icon, body_colour, lid_colour, hide}],
     "schedules": [{id, name, streams: [{label, first_date, every_weeks,
                                         icon, body_colour, lid_colour}]}]}

The admin form posts flat fields named ``mappings-<n>-<field>`` and
``schedules-<n>-streams-<m>-<field>``; a ``-delete`` field drops a row.
"""

import re
from datetime import date

from .resolve import clean_text
from .schedule import MAX_EVERY_WEEKS

MAPPING_FIELDS = ("match", "label", "icon", "body_colour", "lid_colour")
STREAM_FIELDS = ("label", "first_date", "every_weeks", "icon", "body_colour", "lid_colour")
SOURCE_PREFIX = "schedule:"


def _indices(form, prefix):
    """Row numbers present in the form under ``<prefix>-<n>-``, in order."""
    pattern = re.compile(rf"{re.escape(prefix)}-(\d+)-")
    return sorted({int(m[1]) for key in form if (m := pattern.match(key))})


def _row(form, prefix, fields):
    return {field: clean_text(form.get(f"{prefix}-{field}")) for field in fields}


def _deleted(form, prefix):
    return bool(form.get(f"{prefix}-delete"))


def _parse_stream(stream, where, errors):
    """Validate one stream in place; append a message per problem."""
    if not stream["label"]:
        errors.append(f"{where}: needs a label.")
    try:
        stream["first_date"] = date.fromisoformat(stream["first_date"]).isoformat()
    except ValueError:
        errors.append(f"{where}: needs a first collection date (YYYY-MM-DD).")
    weeks = stream["every_weeks"]
    if weeks.isdecimal() and 1 <= int(weeks) <= MAX_EVERY_WEEKS:
        stream["every_weeks"] = int(weeks)
    else:
        errors.append(f"{where}: must repeat every 1 to {MAX_EVERY_WEEKS} weeks (a whole number).")
    return stream


def _parse_schedule(form, prefix, position, new_id, errors):
    name = clean_text(form.get(f"{prefix}-name"))
    rows = []
    for n in _indices(form, f"{prefix}-streams"):
        row_prefix = f"{prefix}-streams-{n}"
        row = _row(form, row_prefix, STREAM_FIELDS)
        if not _deleted(form, row_prefix) and any(
            row[f] for f in ("label", "first_date", "every_weeks")
        ):
            rows.append((n, row))
    if not name and not rows:
        return None
    if not name:
        errors.append(f"Schedule {position} needs a name.")
    streams = [
        _parse_stream(row, f"{name or f'Schedule {position}'}, stream {number}", errors)
        for number, (_, row) in enumerate(rows, start=1)
    ]
    schedule_id = clean_text(form.get(f"{prefix}-id")) or new_id()
    return {"id": schedule_id, "name": name, "streams": streams}


def parse_admin_form(form, new_id):
    """``(config, errors)`` from the posted admin form. ``new_id()`` names a
    new schedule. With errors, the config keeps what was typed so the page
    can show it again; save it only when ``errors`` is empty."""
    errors = []
    mappings = []
    for n in _indices(form, "mappings"):
        prefix = f"mappings-{n}"
        row = _row(form, prefix, MAPPING_FIELDS)
        if row["match"] and not _deleted(form, prefix):
            mappings.append({**row, "hide": bool(form.get(f"{prefix}-hide"))})
    schedules = []
    for position, n in enumerate(_indices(form, "schedules"), start=1):
        prefix = f"schedules-{n}"
        if _deleted(form, prefix):
            continue
        schedule = _parse_schedule(form, prefix, position, new_id, errors)
        if schedule:
            schedules.append(schedule)
    return {"mappings": mappings, "schedules": schedules}, errors


def source_choices(config):
    """The cell's Source dropdown entries for the saved schedules."""
    return [
        {"value": f"{SOURCE_PREFIX}{s['id']}", "label": f"Schedule: {s['name']}"}
        for s in config["schedules"]
    ]
