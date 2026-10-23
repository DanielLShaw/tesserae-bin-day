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


def show(tab, w, h, style="standard", theme="light", **options):
    """Renders the widget in a w by h cell, as a dashboard would."""
    opts = quote(json.dumps(options))
    look = f"&style={style}&theme={theme}"
    tab.goto(f"{tab.base_url}/_test/render?plugin=bin_day&size=sm&w={w}&h={h}{look}&opts={opts}")
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
def test_one_small_cell_wheelie_bin_takes_the_height_the_title_and_count_leave(tab, bins, w, h):
    bins(ONE_TOMORROW)
    show(tab, w, h, **WHEELIE_BINS)
    head, content = box(tab.locator(".next-head")), content_box(tab)
    assert content[3] - head[3] <= gap_limit(tab)
    first_bin, title = box(tab.locator(".next .bin")), box(tab.locator(".w-title"))
    assert first_bin[3] - first_bin[1] > title[3] - title[1]


def test_a_long_title_stays_on_one_line_and_the_cell_still_fits(tab, bins):
    bins(ONE_TOMORROW)
    long_title = "Collections for the house at the end of the lane, every week"
    show(tab, 205, 165, title=long_title, **WHEELIE_BINS)
    heading = tab.locator(".w-title h3")
    size = float(heading.evaluate("el => parseFloat(getComputedStyle(el).fontSize)"))
    assert heading.bounding_box()["height"] <= 1.6 * size
    assert heading.evaluate("el => el.scrollWidth > el.clientWidth")
    cell = box(tab.locator(".cell").first)
    drawn = tab.locator(".w-title, .next :is(.bin, .more, .count, .next-date, .bin-label):visible")
    for element in drawn.all():
        assert within(box(element), cell), element.evaluate("el => el.outerHTML.slice(0, 60)")


# The owner's order: the title bar, then the bins, then the days left and date,
# all from the top left. LG's later days sit at the bottom.
NOTHING_THIS_WEEK = [bin_("Refuse", "2026-10-20")]
LONG_CALENDAR = "calendar." + "x" * 280


def content_box(tab):
    """The widget's box, less its padding: where its content may go."""
    widget = tab.locator(".bin-day")
    pad = widget.evaluate(
        "el => ['Left', 'Top', 'Right', 'Bottom']"
        ".map(s => parseFloat(getComputedStyle(el)['padding' + s]))"
    )
    left, top, right, bottom = box(widget)
    return left + pad[0], top + pad[1], right - pad[2], bottom - pad[3]


def gap_limit(tab):
    """The widest gap Tesserae's spacing puts between blocks (--space-4), plus rounding."""
    return 1.1 * font_size(tab, ".bin-day") + 2


DRAWN = (
    ".chip, .bin, .more, .count, .day-label, .notice p, .notice i, .bin-label,"
    " .next-date, .day-date, .hero-label, .hero-date, .strip-row"
)

ORDER_CASES = {
    "xs-chips": (180, 180, LIVERPOOL, {}, [".chips .chip", ".count"]),
    "sm-chips": (380, 240, LIVERPOOL, {}, [".day-row .chip"]),
    "sm-busy": (380, 240, FIVE_TOMORROW, {}, [".chips.grid .chip", ".day-label"]),
    "wheelie-205": (205, 165, ONE_TOMORROW, WHEELIE_BINS, [".next .bin-item", ".next-head .count"]),
    "wheelie-180": (180, 180, LIVERPOOL, WHEELIE_BINS, [".next .bin-item", ".next-head .count"]),
    "wheelie-380": (380, 240, LIVERPOOL, WHEELIE_BINS, [".next .bin-item", ".next-head .count"]),
    "md": (640, 400, LIVERPOOL, {}, [".day-col .bin-item", ".day-col .day-label"]),
    "lg": (1200, 800, LIVERPOOL, {}, [".hero .bin-item", ".hero-label"]),
    "empty-180": (180, 180, NOTHING_THIS_WEEK, {}, [".notice i"]),
    "empty-380": (380, 240, NOTHING_THIS_WEEK, {}, [".notice i"]),
    "error-180": (180, 180, None, {}, [".notice i"]),
    "error-380": (380, 240, None, {}, [".notice i"]),
}


@pytest.mark.parametrize("case", list(ORDER_CASES))
def test_every_layout_reads_title_then_bins_then_days_from_the_top_left(
    app, registry, tab, bins, ha_connected, case
):
    w, h, streams, options, blocks = ORDER_CASES[case]
    if streams is None:  # a calendar Home Assistant doesn't have: a 300-character error
        core = registry.get("bin_day_core").server_module
        with app.app_context():
            core.save_config(
                {"source": "calendar", "calendar": LONG_CALENDAR, "schedule": [], "mappings": {}}
            )
    else:
        bins(streams)
    show(tab, w, h, **options)
    content, limit = content_box(tab), gap_limit(tab)
    title = box(tab.locator(".w-title"))
    assert abs(title[0] - content[0]) <= 2 and abs(title[1] - content[1]) <= 2
    previous = title
    for selector in blocks:
        block = box(tab.locator(selector).first)
        assert abs(block[0] - content[0]) <= 2, f"{selector} is not on the left"
        assert -1 <= block[1] - previous[3] <= limit, f"{selector} is not straight below"
        previous = block
    if case == "sm-chips":
        for row in tab.locator(".day-row").all():
            chips, label = box(row.locator(".chips")), box(row.locator(".day-label"))
            assert 0 <= label[0] - chips[2] <= 32
    if case == "lg":
        assert abs(box(tab.locator(".strip"))[3] - content[3]) <= 2
    cell = box(tab.locator(".cell").first)
    drawn = tab.locator(f".w-title, .w-body :is({DRAWN}):visible")
    for element in drawn.all():
        assert within(box(element), cell), element.evaluate("el => el.outerHTML.slice(0, 60)")


def font_size(tab, selector):
    return tab.locator(selector).first.evaluate("el => parseFloat(getComputedStyle(el).fontSize)")


def test_the_count_follows_the_styles_type_scale(tab, bins):
    """A small cell's count is Tesserae's value size (--fs-value), which styles set.
    (At XS, Tesserae itself fixes the big number at 2.4em in bodies 240px wide or less.)"""
    bins(LIVERPOOL)
    show(tab, 380, 240, style="standard", **WHEELIE_BINS)
    standard = font_size(tab, ".stat-value")
    show(tab, 380, 240, style="display", **WHEELIE_BINS)
    assert font_size(tab, ".stat-value") / standard == pytest.approx(2.1 / 1.9, abs=0.02)


@pytest.mark.parametrize("w, h, selector", [(640, 400, ".day-date"), (1200, 800, ".bin-label")])
def test_dates_and_names_follow_the_styles_label_size(tab, bins, w, h, selector):
    """Names follow it wherever their bin is wide enough to carry them (LG)."""
    bins(LIVERPOOL)
    show(tab, w, h, style="standard")
    standard = font_size(tab, selector)
    show(tab, w, h, style="elegant")
    assert font_size(tab, selector) / standard == pytest.approx(0.74 / 0.8, abs=0.02)


def test_bins_grow_when_names_are_hidden(tab, bins):
    bins(LIVERPOOL)
    show(tab, 640, 400)
    named = box(tab.locator(".day-col .bin").first)
    show(tab, 640, 400, show_names=False)
    unnamed = box(tab.locator(".day-col .bin").first)
    assert unnamed[3] - unnamed[1] > named[3] - named[1]


def computed(tab, selector, prop):
    return tab.locator(selector).first.evaluate(f"el => getComputedStyle(el).{prop}")


def test_black_and_white_inks_come_from_the_theme(tab, bins):
    bins(LIVERPOOL)
    show(tab, 640, 400, theme="dark", colours="mono")
    ink, paper = computed(tab, ".bin-day", "color"), computed(tab, ".bin-day", "backgroundColor")
    assert computed(tab, '.bin[data-mono="solid"] .body', "fill") == ink
    assert computed(tab, '.bin[data-mono="white"] .body', "fill") == paper


@pytest.mark.parametrize("style, width", [("standard", "0px"), ("mono", "2px"), ("destijl", "4px")])
def test_dividers_follow_the_style(tab, bins, style, width):
    bins(LIVERPOOL)
    show(tab, 640, 400, style=style)
    assert computed(tab, ".day-col + .day-col", "borderLeftWidth") == width
    show(tab, 1200, 800, style=style)
    assert computed(tab, ".strip", "borderTopWidth") == width


def test_narrow_notices_stack_their_icon_above_the_text(tab, bins):
    bins(NOTHING_THIS_WEEK)
    show(tab, 340, 220)
    assert box(tab.locator(".notice i"))[3] <= box(tab.locator(".notice p"))[1]
