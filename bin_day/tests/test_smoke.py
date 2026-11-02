"""Smoke test, in Tesserae's pattern (its docs/widgets.md, "Smoke test
pattern"): Bin Day renders at each size it supports, and as each of its
canvas fragments.

``client`` comes from the root conftest.py: Tesserae's own in a Tesserae
checkout (``pytest plugins/bin_day``, with bin_day_core beside it), or this
repo's, which matches it.
"""

import json
from datetime import date
from pathlib import Path

import pytest

MANIFEST = json.loads((Path(__file__).resolve().parents[1] / "plugin.json").read_text())


@pytest.fixture
def weekly_refuse(client):
    """A Refuse bin every week from today, saved on Bin Day Core's page: a
    schedule entered by hand needs no network."""
    form = {
        "source": "schedule",
        "schedule-0-label": "Refuse",
        "schedule-0-first_date": date.today().isoformat(),
        "schedule-0-every_weeks": "1",
    }
    assert client.post("/plugins/bin_day_core/save", data=form).status_code == 302


def render(client, **query):
    resp = client.get("/_test/render", query_string={"plugin": "bin_day", **query})
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


@pytest.mark.parametrize("size", MANIFEST["supports"]["sizes"])
def test_widget_renders(client, weekly_refuse, size):
    body = render(client, size=size)
    assert 'data-plugin="bin_day"' in body
    assert "Refuse" in body


@pytest.mark.parametrize("fragment", [f["id"] for f in MANIFEST["fragments"]])
def test_each_fragment_renders(client, weekly_refuse, fragment):
    body = render(client, size="sm", fragment=fragment)
    assert 'data-plugin="bin_day"' in body
    assert "Refuse" in body
