"""bin_day_core/server.py pieces that do not need a running Tesserae app."""

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SERVER = "_tesserae_plugins.bin_day_core.server"


def load_server(folder):
    """Import server.py by path the way Tesserae's plugin loader does."""
    spec = importlib.util.spec_from_file_location(SERVER, folder / "server.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[SERVER] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def clean_modules():
    yield
    for name in [n for n in sys.modules if n.startswith("_tesserae_plugins.bin_day_core")]:
        del sys.modules[name]


def test_reloading_the_plugin_picks_up_updated_logic(tmp_path, clean_modules):
    old, new = tmp_path / "old", tmp_path / "new"
    for folder in (old, new):
        shutil.copytree(REPO / "bin_day_core", folder, ignore=shutil.ignore_patterns("__pycache__"))
    resolve = new / "bin_logic" / "resolve.py"
    resolve.write_text(
        resolve.read_text().replace('FALLBACK_COLOUR = "grey"', 'FALLBACK_COLOUR = "purple"')
    )

    assert load_server(old).logic.resolve_stream("Bulky")["body_colour"] == "grey"
    assert load_server(new).logic.resolve_stream("Bulky")["body_colour"] == "purple"


def core_module(registry):
    return registry.get("bin_day_core").server_module


@pytest.mark.parametrize("content", ["[]", '"text"', "null"])
def test_config_that_is_not_an_object_reads_as_empty(app, registry, content):
    (registry.get("bin_day_core").data_dir / "config.json").write_text(content)
    with app.app_context():
        assert core_module(registry).load_config() == {
            "source": "schedule",
            "calendar": "",
            "schedule": [],
            "mappings": {},
        }


def test_saved_config_round_trips(app, registry):
    config = {
        "source": "calendar",
        "calendar": "calendar.bins",
        "schedule": [],
        "mappings": {
            "calendar.bins": [{"match": "Green", "icon": "leaf"}],
            "calendar.cottage": [],
        },
    }
    with app.app_context():
        core_module(registry).save_config(config)
        assert core_module(registry).load_config() == config


def test_now_is_in_the_tesserae_server_timezone(app, registry):
    from app.tz_resolve import app_timezone

    with app.app_context():
        now = core_module(registry)._now()
        assert now.tzinfo == app_timezone()


def test_now_falls_back_to_local_time_if_the_host_helper_is_missing(app, registry, monkeypatch):
    monkeypatch.setitem(sys.modules, "app.tz_resolve", None)
    with app.app_context():
        assert core_module(registry)._now().utcoffset() is not None


def test_an_unknown_source_or_odd_fields_read_as_defaults(app, registry):
    (registry.get("bin_day_core").data_dir / "config.json").write_text(
        '{"source": "pigeon", "calendar": 7, "schedule": "x", "mappings": null}'
    )
    with app.app_context():
        assert core_module(registry).load_config() == {
            "source": "schedule",
            "calendar": "",
            "schedule": [],
            "mappings": {},
        }


def test_a_calendars_mappings_that_are_not_a_list_are_dropped(app, registry):
    (registry.get("bin_day_core").data_dir / "config.json").write_text(
        '{"mappings": {"calendar.bins": [{"match": "Green"}], "calendar.odd": "x"}}'
    )
    with app.app_context():
        mappings = core_module(registry).load_config()["mappings"]
    assert mappings == {"calendar.bins": [{"match": "Green"}]}


def test_mappings_saved_before_they_were_per_calendar_go_to_the_saved_calendar(app, registry):
    (registry.get("bin_day_core").data_dir / "config.json").write_text(
        '{"source": "calendar", "calendar": "calendar.bins", "mappings": [{"match": "Green"}]}'
    )
    with app.app_context():
        mappings = core_module(registry).load_config()["mappings"]
    assert mappings == {"calendar.bins": [{"match": "Green"}]}


def test_mappings_saved_before_they_were_per_calendar_with_no_calendar_are_dropped(app, registry):
    (registry.get("bin_day_core").data_dir / "config.json").write_text(
        '{"mappings": [{"match": "Green"}]}'
    )
    with app.app_context():
        assert core_module(registry).load_config()["mappings"] == {}
