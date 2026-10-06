"""Bin Day Core: shared config and data for the bin_day widget.

Holds the title mappings and fixed-rule schedules (edited on this plugin's
admin page) and builds the collection-days payload a bin_day cell shows,
from a fixed-rule schedule or a Home Assistant calendar (read through the
bundled Home Assistant Core plugin). The bin_day widget reaches this module
through the plugin registry.
"""

import importlib.util
import json
import re
import secrets
import sys
import urllib.error
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

_HERE = Path(__file__).resolve().parent


def _load_logic():
    """Load the bin_logic package by path: Tesserae imports this file with no
    parent package, so a normal relative import cannot reach it. Any copy
    from an earlier load is dropped first, so a plugin reload or update
    picks up the new code."""
    name = "_tesserae_plugins.bin_day_core.bin_logic"
    for loaded in [n for n in sys.modules if n == name or n.startswith(f"{name}.")]:
        del sys.modules[loaded]
    package = _HERE / "bin_logic"
    spec = importlib.util.spec_from_file_location(
        name, package / "__init__.py", submodule_search_locations=[str(package)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


logic = _load_logic()

EMPTY_CONFIG = {"mappings": [], "schedules": []}
CALENDAR_PREFIX = "calendar."
NEEDS_HA_CORE = (
    "Needs Home Assistant Core: install it, then set your Home Assistant URL "
    "and access token in Settings, Plugins, Home Assistant Core."
)


def _data_dir():
    return current_app.config["PLUGIN_REGISTRY"].get("bin_day_core").data_dir


def _config_path():
    return _data_dir() / "config.json"


def load_config():
    """The saved config; empty when there is none or it cannot be read."""
    try:
        config = json.loads(_config_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"mappings": [], "schedules": []}
    if not isinstance(config, dict):
        return {"mappings": [], "schedules": []}
    return {key: config.get(key) or [] for key in EMPTY_CONFIG}


def _write_json(path, value):
    """Write atomically so a crash mid-write never leaves a corrupt file."""
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(value, indent=2), encoding="utf-8")
    tmp.replace(path)


def save_config(config):
    _write_json(_config_path(), config)


def _now():
    """Now in the Tesserae server's timezone."""
    try:
        from app.tz_resolve import app_timezone

        return datetime.now(app_timezone())
    except Exception:  # noqa: BLE001 - internal host API; fall back to local time
        return datetime.now().astimezone()


def _ha_core():
    plugin = current_app.config["PLUGIN_REGISTRY"].get("ha_core")
    return plugin.server_module if plugin is not None else None


def _calendar_choices():
    """HA calendar entities, once Home Assistant Core is connected. An
    unreachable HA shows as Home Assistant Core's own guidance entry."""
    ha = _ha_core()
    if ha is None or not ha.is_configured():
        return []
    return [
        {**entry, "label": f"Calendar: {entry['label']}"}
        for entry in ha.entity_choices(domains=("calendar",))
    ]


def choices(name):
    """Dropdown entries for the bin_day cell editor: schedules, then calendars."""
    if name != "sources":
        return []
    return logic.source_choices(load_config()) + _calendar_choices()


def _cache_path(entity_id):
    folder = _data_dir() / "ha_cache"
    folder.mkdir(exist_ok=True)
    return folder / f"{re.sub(r'[^a-z0-9_.]', '_', entity_id)}.json"


def _read_cache(entity_id):
    """The last HA answer for ``entity_id`` as ``{fetched_at, events}``, or {}."""
    try:
        cached = json.loads(_cache_path(entity_id).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(cached, dict) or not isinstance(cached.get("events"), list):
        return {}
    return cached


def _fetch_events(ha, entity_id, now):
    start, end = logic.calendar_query_range(now)
    events = ha.request_json(f"/api/calendars/{quote(entity_id)}?start={start}&end={end}")
    if not isinstance(events, list):
        raise ValueError("Home Assistant sent something other than a list of events")
    return events


def _calendar_missing(ha, entity_id, err):
    """HA answers a 400 for an unknown calendar (and for a bad query), so a
    400 is only "missing" when the entity's state is a 404 too."""
    if not (isinstance(err, urllib.error.HTTPError) and err.code == 400):
        return False
    try:
        ha.get_state(entity_id)
    except Exception as state_err:  # noqa: BLE001 - any failure: not provably missing
        return isinstance(state_err, urllib.error.HTTPError) and state_err.code == 404
    return False


def _calendar_payload(entity_id, cutoff, fresh):
    """Payload from a Home Assistant calendar. Answers are cached for an hour;
    if HA fails, a cached answer up to a day old is used instead."""
    ha = _ha_core()
    if ha is None or not ha.is_configured():
        return {"error": NEEDS_HA_CORE}
    now = _now()
    cached = _read_cache(entity_id)
    state = logic.cache_state(cached.get("fetched_at"), now)
    if state == "fresh" and not fresh:
        events = cached["events"]
    else:
        try:
            events = _fetch_events(ha, entity_id, now)
        except Exception as err:  # noqa: BLE001 - ha_core raises urllib, OS and runtime errors
            if _calendar_missing(ha, entity_id, err):
                return {
                    "error": f"Calendar {entity_id} wasn't found in Home Assistant. If it "
                    "was renamed, pick it again in this cell's Source option."
                }
            if state == "expired":
                return {
                    "error": f"Couldn't load {entity_id} from Home Assistant: "
                    f"{ha.coerce_error(err)}"
                }
            events = cached["events"]
        else:
            _write_json(_cache_path(entity_id), {"fetched_at": now.isoformat(), "events": events})
    mappings = load_config()["mappings"]
    return logic.calendar_payload(events, mappings, now, logic.parse_cutoff(cutoff))


def collections(source, cutoff, fresh=False):
    """The bin_day payload for a cell's ``source`` and ``cutoff`` options, or
    ``{"error": ...}`` for the cell's error tile. ``fresh`` skips the Home
    Assistant cache. Never raises."""
    if not source:
        return {"error": "Choose a bin schedule or calendar in this cell's Source option."}
    if source.startswith(CALENDAR_PREFIX):
        return _calendar_payload(source, cutoff, fresh)
    config = load_config()
    schedule = logic.find_schedule(config, source)
    if schedule is None:
        return {
            "error": "This cell's bin schedule no longer exists. Pick another in its Source option."
        }
    try:
        return logic.fixed_rule_payload(
            schedule, config["mappings"], _now(), logic.parse_cutoff(cutoff)
        )
    except ValueError as err:
        return {"error": f"Bin schedule '{schedule['name']}' needs fixing in Bin Day Core: {err}"}


ICON_CHOICES = [("", "Automatic")] + [
    (icon, material.capitalize()) for material, (icon, _) in logic.resolve.MATERIAL_STYLES.items()
]
COLOUR_CHOICES = [("", "Automatic")] + [
    (name, name.replace("_", " ").capitalize()) for name in logic.palette.PALETTE
]


def _render_admin(config, errors=()):
    """The admin page for ``config``, with a blank row for each kind of add."""
    blank_stream = dict.fromkeys(logic.config.STREAM_FIELDS, "")
    schedules = [{**s, "streams": [*s["streams"], blank_stream]} for s in config["schedules"]]
    schedules.append({"id": "", "name": "", "streams": [blank_stream]})
    mappings = [*config["mappings"], dict.fromkeys(logic.config.MAPPING_FIELDS, "")]
    return render_template(
        "bin_day_core/index.html",
        schedules=schedules,
        mappings=mappings,
        errors=errors,
        icon_choices=ICON_CHOICES,
        colour_choices=COLOUR_CHOICES,
        max_every_weeks=logic.schedule.MAX_EVERY_WEEKS,
    )


def blueprint():
    bp = Blueprint("bin_day_core_admin", __name__, template_folder="templates")

    @bp.get("/")
    def index():
        return _render_admin(load_config())

    @bp.post("/save")
    def save():
        config, errors = logic.parse_admin_form(request.form, lambda: secrets.token_hex(4))
        if errors:
            return _render_admin(config, errors), 400
        save_config(config)
        flash("Saved.", "ok")
        return redirect(url_for("bin_day_core_admin.index"))

    return bp
