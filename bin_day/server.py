"""Bin Day widget: delegates to the Bin Day Core plugin for its data."""

from flask import current_app

MISSING_CORE = "Install the Bin Day Core plugin to use this widget."


def _core():
    plugin = current_app.config["PLUGIN_REGISTRY"].get("bin_day_core")
    return plugin.server_module if plugin is not None else None


def choices(name):
    core = _core()
    return core.choices(name) if core is not None else []


def fetch(options, settings, *, ctx):
    core = _core()
    if core is None:
        return {"error": MISSING_CORE}
    return core.collections(
        options.get("source"), options.get("cutoff"), fresh=bool(ctx.get("fresh"))
    )
