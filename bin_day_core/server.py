"""Bin Day Core: shared config and data for the bin_day widget.

Holds the one source every bin_day cell shows, chosen on this plugin's admin
page: a manual schedule of bins, or a Home Assistant calendar (read through
the bundled Home Assistant Core plugin) styled by title mappings. Builds the
collection-days payload a cell shows; the bin_day widget reaches this module
through the plugin registry.
"""

import importlib.util
import json
import re
import sys
import urllib.error
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

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

DEFAULT_CONFIG = {"source": "schedule", "calendar": "", "schedule": [], "mappings": []}
DISCOVERY_DAYS = 56  # how far ahead the admin page looks for a calendar's bin titles
NEEDS_HA_CORE = (
    "Needs Home Assistant Core: install it, then set your Home Assistant URL "
    "and access token in Settings, Plugins, Home Assistant Core."
)
NEEDS_BINS = "Add your bins in Bin Day Core (Plugins, Bin Day Core)."
NEEDS_CALENDAR = "Choose your bin calendar in Bin Day Core (Plugins, Bin Day Core)."


def _data_dir():
    return current_app.config["PLUGIN_REGISTRY"].get("bin_day_core").data_dir


def _config_path():
    return _data_dir() / "config.json"


def load_config():
    """The saved config, with defaults for anything missing or unreadable."""
    try:
        raw = json.loads(_config_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    calendar = raw.get("calendar")
    return {
        "source": raw.get("source") if raw.get("source") in logic.config.SOURCES else "schedule",
        "calendar": calendar if isinstance(calendar, str) else "",
        "schedule": raw.get("schedule") if isinstance(raw.get("schedule"), list) else [],
        "mappings": raw.get("mappings") if isinstance(raw.get("mappings"), list) else [],
    }


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
    """Home Assistant Core's module once it is installed and connected, else None."""
    plugin = current_app.config["PLUGIN_REGISTRY"].get("ha_core")
    ha = plugin.server_module if plugin is not None else None
    return ha if ha is not None and ha.is_configured() else None


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


def _fetch_events(ha, entity_id, now, days=logic.calendar.QUERY_DAYS):
    start, end = logic.calendar_query_range(now, days)
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


def _calendar_payload(entity_id, mappings, cutoff, fresh, eink):
    """Payload from a Home Assistant calendar. Answers are cached for an hour;
    if HA fails, a cached answer up to a day old is used instead."""
    ha = _ha_core()
    if ha is None:
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
                    "was renamed, pick it again in Bin Day Core."
                }
            if state == "expired":
                return {
                    "error": f"Couldn't load {entity_id} from Home Assistant: "
                    f"{ha.coerce_error(err)}"
                }
            events = cached["events"]
        else:
            _write_json(_cache_path(entity_id), {"fetched_at": now.isoformat(), "events": events})
    return logic.calendar_payload(events, mappings, now, logic.parse_cutoff(cutoff), eink)


def collections(cutoff, fresh=False, colours=None):
    """The bin_day payload for Bin Day Core's source and a cell's ``cutoff``
    and ``colours`` options, or ``{"error": ...}`` for the cell's error tile.
    ``fresh`` skips the Home Assistant cache. Never raises."""
    eink = colours == "eink"
    config = load_config()
    if config["source"] == "calendar":
        if not config["calendar"]:
            return {"error": NEEDS_CALENDAR}
        return _calendar_payload(config["calendar"], config["mappings"], cutoff, fresh, eink)
    if not config["schedule"]:
        return {"error": NEEDS_BINS}
    try:
        return logic.fixed_rule_payload(
            config["schedule"], _now(), logic.parse_cutoff(cutoff), eink
        )
    except ValueError as err:
        return {"error": f"Fix your bins in Bin Day Core: {err}"}


# ---- admin page --------------------------------------------------------------

ICON_CHOICES = [("", "Automatic")] + [
    (icon, material.capitalize()) for material, (icon, _) in logic.resolve.MATERIAL_STYLES.items()
]
COLOUR_CHOICES = [("", "Automatic")] + [
    (name, name.replace("_", " ").capitalize()) for name in logic.palette.SCREEN_PALETTE
]
_STYLE_CHOICES = {
    "icon": {value for value, _ in ICON_CHOICES},
    "body_colour": {value for value, _ in COLOUR_CHOICES},
    "lid_colour": {value for value, _ in COLOUR_CHOICES},
}


def _row_view(row, **extra):
    """A saved row for the page: each style as a dropdown choice, or "custom"
    with the typed value alongside."""
    view = {**row, **extra}
    for field, known in _STYLE_CHOICES.items():
        value = row.get(field) or ""
        custom = value not in known
        view[f"{field}_choice"] = logic.config.CUSTOM if custom else value
        view[f"{field}_custom"] = value if custom else ""
    return view


def _calendar_options():
    """``(options, problem)``: HA's calendar entities as ``(value, label)``, or
    a sentence saying why there are none."""
    ha = _ha_core()
    if ha is None:
        return [], "unconfigured"
    entries = ha.entity_choices(domains=("calendar",))
    options = [(e["value"], e["label"]) for e in entries if e["value"]]
    return options, (None if options or not entries else "unreachable")


def discover_titles(entity_id):
    """``(titles, error)``: each bin title in the calendar's next weeks."""
    ha = _ha_core()
    if ha is None:
        return [], NEEDS_HA_CORE
    try:
        events = _fetch_events(ha, entity_id, _now(), DISCOVERY_DAYS)
    except Exception as err:  # noqa: BLE001 - surfaced on the page, never raised
        return [], f"Couldn't read {entity_id} from Home Assistant: {ha.coerce_error(err)}"
    return logic.distinct_titles(events), None


def _mapping_views(config, titles):
    """A row per title in the calendar, carrying its saved mapping, then the
    saved mappings for other names as editable rows."""
    saved = {m["match"].casefold(): m for m in config["mappings"]}
    blank = dict.fromkeys(("label", *_STYLE_CHOICES), "")
    rows = []
    for title in titles:
        row = saved.pop(title.casefold(), None) or {**blank, "hide": False}
        rows.append(_row_view({**row, "match": title}, discovered=True))
    rows += [_row_view(m, discovered=False) for m in saved.values()]
    return rows


def _render_admin(config, errors=()):
    options, ha_problem = _calendar_options()
    titles, discovery_error = [], None
    if config["source"] == "calendar" and config["calendar"] and not ha_problem:
        titles, discovery_error = discover_titles(config["calendar"])
    return render_template(
        "bin_day_core/index.html",
        config=config,
        errors=errors,
        calendar_options=options,
        ha_problem=ha_problem,
        discovery_error=discovery_error,
        schedule_rows=[_row_view(row) for row in config["schedule"]],
        mapping_rows=_mapping_views(config, titles),
        blank_row=_row_view(dict.fromkeys(("label", *_STYLE_CHOICES), ""), hide=False),
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
        config, errors = logic.parse_admin_form(request.form)
        if errors:
            return _render_admin(config, errors), 400
        save_config(config)
        flash("Saved.", "ok")
        return redirect(url_for("bin_day_core_admin.index"))

    @bp.get("/titles")
    def titles():
        found, error = discover_titles(request.args.get("calendar", ""))
        return jsonify({"titles": found, **({"error": error} if error else {})})

    return bp
