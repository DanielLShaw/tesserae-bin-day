"""Bin Day widget: shows the source chosen in the Bin Day Core plugin."""

from flask import current_app

MISSING_CORE = "Install the Bin Day Core plugin to use this widget."


def _core():
    plugin = current_app.config["PLUGIN_REGISTRY"].get("bin_day_core")
    return plugin.server_module if plugin is not None else None


def fetch(options, settings, *, ctx):
    core = _core()
    if core is None:
        return {"error": MISSING_CORE}
    return core.collections(
        options.get("cutoff"), fresh=bool(ctx.get("fresh")), colours=options.get("colours")
    )
