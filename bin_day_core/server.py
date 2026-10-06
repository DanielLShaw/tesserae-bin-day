"""Bin Day Core: shared config and data for the bin_day widget.

Holds the title mappings and fixed-rule schedules (edited on this plugin's
admin page) and builds the collection-days payload a bin_day cell shows.
The bin_day widget reaches this module through the plugin registry.
"""

import importlib.util
import json
import secrets
import sys
from datetime import datetime
from pathlib import Path

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


def _config_path():
    return current_app.config["PLUGIN_REGISTRY"].get("bin_day_core").data_dir / "config.json"


def load_config():
    """The saved config; empty when there is none or it cannot be read."""
    try:
        config = json.loads(_config_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"mappings": [], "schedules": []}
    if not isinstance(config, dict):
        return {"mappings": [], "schedules": []}
    return {key: config.get(key) or [] for key in EMPTY_CONFIG}


def save_config(config):
    """Write the config atomically so a crash mid-write never corrupts it."""
    path = _config_path()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(config, indent=2), encoding="utf-8")
    tmp.replace(path)


def _now():
    """Now in the Tesserae server's timezone."""
    try:
        from app.tz_resolve import app_timezone

        return datetime.now(app_timezone())
    except Exception:  # noqa: BLE001 - internal host API; fall back to local time
        return datetime.now().astimezone()


def choices(name):
    """Dropdown entries for the bin_day cell editor."""
    if name != "sources":
        return []
    return logic.source_choices(load_config())


def collections(source, cutoff):
    """The bin_day payload for a cell's ``source`` and ``cutoff`` options, or
    ``{"error": ...}`` for the cell's error tile. Never raises."""
    if not source:
        return {"error": "Choose a bin schedule in this cell's Source option."}
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
