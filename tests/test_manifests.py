"""plugin.json contracts, checked against the pinned Tesserae host."""

import json

import pytest

from bin_day_core.bin_logic import parse_cutoff

from .conftest import HAVE_TESSERAE, REPO, TESSERAE_SRC

pytestmark = pytest.mark.skipif(not HAVE_TESSERAE, reason="needs a Tesserae checkout")


def manifest(folder):
    return json.loads((REPO / folder / "plugin.json").read_text())


def cell_option(name):
    return next(o for o in manifest("bin_day")["cell_options"] if o["name"] == name)


@pytest.mark.parametrize("folder", ["bin_day", "bin_day_core"])
def test_manifest_validates_against_the_host_schema(folder):
    import jsonschema

    schema = json.loads((TESSERAE_SRC / "schema" / "plugin.schema.json").read_text())
    jsonschema.validate(manifest(folder), schema)


def test_both_plugins_share_one_version():
    assert manifest("bin_day")["version"] == manifest("bin_day_core")["version"]


def test_cell_editor_offers_saved_schedules_as_sources(app, registry):
    from app.page_routes import _materialize_cell_options

    with app.app_context():
        registry.get("bin_day_core").server_module.save_config(
            {"mappings": [], "schedules": [{"id": "home01", "name": "Home", "streams": []}]}
        )
        options = _materialize_cell_options([registry.get("bin_day")])["bin_day"]
    source = next(o for o in options if o["name"] == "source")
    assert source["choices"] == [{"value": "schedule:home01", "label": "Schedule: Home"}]


def test_every_cutoff_choice_is_honoured_and_default_is_ten():
    option = cell_option("cutoff")
    values = [c["value"] for c in option["choices"]]
    assert option["default"] == "10:00"
    assert "10:00" in values
    assert [parse_cutoff(v).strftime("%H:%M") for v in values] == values


def test_widget_offers_the_daily_refresh(registry):
    from app.scheduled_refresh import _supported

    assert _supported("bin_day", "daily", registry)
