"""Each screenshot scenario renders the situation it is named for."""

import json
from urllib.parse import quote

import pytest

from preview.scenarios import SCENARIOS

from .conftest import REPO

DOCS = REPO / "docs"


def cell_data(client, opts):
    resp = client.get(f"/_test/render?plugin=bin_day&size=sm&opts={quote(json.dumps(opts))}")
    body = resp.get_data(as_text=True)
    start = body.index("data-data='") + len("data-data='")
    return json.loads(body[start : body.index("'", start)])


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s.name for s in SCENARIOS])
def test_scenario_renders_what_it_is_named_for(app, client, registry, monkeypatch, scenario):
    core = registry.get("bin_day_core").server_module
    monkeypatch.setattr(core, "_now", lambda: scenario.now)
    with app.app_context():
        core.save_config(scenario.config)

    data = cell_data(client, scenario.options)

    if isinstance(scenario.expect, str):
        assert data.get("error", "").startswith(scenario.expect)
    else:
        shown = [(d["days_until"], [s["icon"] for s in d["streams"]]) for d in data["days"]]
        assert shown == scenario.expect


DOCS_IMAGES = [f"images/{s.name}-{size}.png" for s in SCENARIOS for size in s.docs]


@pytest.mark.parametrize("image", DOCS_IMAGES)
def test_each_docs_image_is_rendered_and_shown(image):
    assert (DOCS / image).is_file(), "run: uv run preview/shoot.py --docs"
    pages = (REPO / "README.md").read_text() + (DOCS / "bin-colours.md").read_text()
    assert image in pages


def test_the_readme_shows_every_size():
    assert {"xs", "sm", "md", "lg"} <= {
        size
        for s in SCENARIOS
        for size in s.docs
        if f"docs/images/{s.name}-{size}.png" in (REPO / "README.md").read_text()
    }


def test_scenario_names_are_unique_folder_names():
    names = [s.name for s in SCENARIOS]
    assert len(set(names)) == len(names)
    assert all(n.replace("-", "").isalnum() and n == n.lower() for n in names)
