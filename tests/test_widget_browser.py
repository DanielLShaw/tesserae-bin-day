"""The widget laid out in a real browser, at the cell sizes a dashboard gives it."""

import json
import re
from datetime import datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

import pytest
from playwright.sync_api import expect

TUE_8AM = datetime(2026, 10, 6, 8, 0, tzinfo=ZoneInfo("Europe/London"))


def bin_(label, first_date, icon=""):
    return {
        "label": label,
        "first_date": first_date,
        "every_weeks": 2,
        "icon": icon,
        "body_colour": "",
        "lid_colour": "",
        "hide": False,
    }


# On Tue 6 Oct: Refuse and Green tomorrow, Recycling in 6 days.
LIVERPOOL = [
    bin_("Refuse", "2026-10-07"),
    bin_("Green", "2026-10-07", icon="leaf"),
    bin_("Recycling", "2026-10-12"),
]
THREE_TOMORROW = [*LIVERPOOL, bin_("Glass", "2026-10-07", icon="wine")]


@pytest.fixture
def bins(app, registry, monkeypatch):
    """Saves these bins as the schedule, on Tue 6 Oct 2026 at 8am."""
    core = registry.get("bin_day_core").server_module
    monkeypatch.setattr(core, "_now", lambda: TUE_8AM)

    def save(streams):
        with app.app_context():
            core.save_config(
                {"source": "schedule", "calendar": "", "schedule": streams, "mappings": {}}
            )

    return save


def show(tab, w, h, **options):
    """Renders the widget in a w by h cell, as a dashboard would."""
    opts = quote(json.dumps(options))
    tab.goto(f"{tab.base_url}/_test/render?plugin=bin_day&size=sm&w={w}&h={h}&opts={opts}")
    tab.wait_for_function("window.__tesseraeComposed === true")
    tab.evaluate("document.fonts.ready")


@pytest.mark.parametrize("streams", [LIVERPOOL, THREE_TOMORROW], ids=["two", "three"])
@pytest.mark.parametrize("w, h", [(380, 240), (300, 200), (230, 160), (210, 170)])
def test_sm_day_labels_are_never_cut_short(tab, bins, streams, w, h):
    bins(streams)
    show(tab, w, h)
    labels = tab.locator(".day-label")
    assert labels.all_inner_texts() == ["Tomorrow", "6 days"]
    for label in labels.all():
        assert label.evaluate("el => el.scrollWidth <= el.clientWidth"), label.inner_text()


MONO = re.compile(r"\bmono\b")


def test_auto_colours_follow_a_theme_set_on_the_cell_after_drawing(tab, bins):
    """The dashboard editor applies a cell's own theme by setting data-theme on
    the cell, without drawing the widget again."""
    bins(LIVERPOOL)
    show(tab, 380, 240)
    widget, cell = tab.locator(".bin-day"), tab.locator(".cell").first
    expect(widget).not_to_have_class(MONO)
    cell.evaluate("cell => cell.setAttribute('data-theme', 'paper')")
    expect(widget).to_have_class(MONO)
    expect(tab.locator("#bin-hatch")).to_have_count(1)
    cell.evaluate("cell => cell.removeAttribute('data-theme')")
    expect(widget).not_to_have_class(MONO)


def test_a_chosen_colour_set_ignores_the_cells_theme(tab, bins):
    bins(LIVERPOOL)
    show(tab, 380, 240, colours="colour")
    tab.locator(".cell").first.evaluate("cell => cell.setAttribute('data-theme', 'paper')")
    tab.wait_for_timeout(100)
    expect(tab.locator(".bin-day")).not_to_have_class(MONO)


# Small cells with wheelie bins: the next collection, bins first.
WHEELIE_BINS = {"small_cells": "bins"}
ONE_TOMORROW = [bin_("Refuse", "2026-10-07")]
FIVE_TOMORROW = [*THREE_TOMORROW, bin_("Food", "2026-10-07", icon="fork-knife")]
SMALL_CELLS = [(205, 165), (180, 180), (380, 240), (230, 160), (200, 110), (150, 250)]


def box(locator):
    b = locator.bounding_box()
    return b["x"], b["y"], b["x"] + b["width"], b["y"] + b["height"]


def within(inner, outer):
    return all(
        [inner[0] >= outer[0] - 1, inner[1] >= outer[1] - 1]
        + [inner[2] <= outer[2] + 1, inner[3] <= outer[3] + 1]
    )


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


@pytest.mark.parametrize(
    "streams", [ONE_TOMORROW, LIVERPOOL, THREE_TOMORROW, FIVE_TOMORROW], ids=[1, 2, 3, 5]
)
@pytest.mark.parametrize("w, h", SMALL_CELLS)
def test_small_cell_wheelie_bins_fit_with_the_bins_biggest(tab, bins, streams, w, h):
    bins(streams)
    show(tab, w, h, **WHEELIE_BINS)
    expect(tab.locator(".next")).to_be_visible(timeout=3000)
    cell = box(tab.locator(".cell").first)
    drawn = tab.locator(".next :is(.bin, .more, .count, .next-date, .bin-label):visible")
    for element in drawn.all():
        assert within(box(element), cell), element.evaluate("el => el.outerHTML.slice(0, 60)")
    count, first_bin = box(tab.locator(".next .count")), box(tab.locator(".next .bin").first)
    assert not overlap(count, first_bin)
    assert first_bin[3] - first_bin[1] > count[3] - count[1]


@pytest.mark.parametrize("w, h", [(205, 165), (180, 180), (380, 240)])
def test_one_small_cell_wheelie_bin_fills_much_of_the_cell(tab, bins, w, h):
    bins(ONE_TOMORROW)
    show(tab, w, h, **WHEELIE_BINS)
    first_bin = box(tab.locator(".next .bin"))
    assert first_bin[3] - first_bin[1] >= 0.5 * h


def test_a_long_title_stays_on_one_line_and_the_cell_still_fits(tab, bins):
    bins(ONE_TOMORROW)
    show(tab, 205, 165, title="Collections for the house at the end of the lane, every week", **WHEELIE_BINS)
    heading = tab.locator(".w-title h3")
    size = float(heading.evaluate("el => parseFloat(getComputedStyle(el).fontSize)"))
    assert heading.bounding_box()["height"] <= 1.6 * size
    assert heading.evaluate("el => el.scrollWidth > el.clientWidth")
    cell = box(tab.locator(".cell").first)
    drawn = tab.locator(".w-title, .next :is(.bin, .more, .count, .next-date, .bin-label):visible")
    for element in drawn.all():
        assert within(box(element), cell), element.evaluate("el => el.outerHTML.slice(0, 60)")
