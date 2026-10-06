// bin_day/client.js: labels, chip overflow and the XS / SM / empty / error layouts.
import assert from "node:assert/strict";
import { describe, test } from "node:test";

import render, { dayLabel, xsCount, visibleChips } from "../../bin_day/client.js";

const stream = (label, icon, body = "#111111", ink = "#ffffff") => ({
  id: "other",
  label,
  icon,
  body_colour: body,
  lid_colour: body,
  icon_colour: ink,
});

const REFUSE = stream("Refuse", "trash");
const GREEN = stream("Green", "leaf", "#13803a");
const RECYCLING = stream("Recycling", "recycle", "#1f4fd1");
const TOMORROW = { date: "2026-10-07", days_until: 1, streams: [REFUSE, GREEN] };
const MONDAY = { date: "2026-10-12", days_until: 6, streams: [RECYCLING] };
const LATER = { date: "2026-10-13", days_until: 7, streams: [REFUSE] };

function draw(size, data) {
  const shadow = { innerHTML: "" };
  render(shadow, { cell: { size, options: {} }, data });
  return shadow.innerHTML;
}

const count = (html, needle) => html.split(needle).length - 1;

describe("day labels", () => {
  test("0 is Today, 1 is Tomorrow, otherwise N days", () => {
    assert.deepEqual([0, 1, 2, 7].map(dayLabel), ["Today", "Tomorrow", "2 days", "7 days"]);
  });

  test("XS shows a number and unit, or Today", () => {
    assert.deepEqual(xsCount(0), { number: "", unit: "Today" });
    assert.deepEqual(xsCount(1), { number: "1", unit: "day" });
    assert.deepEqual(xsCount(6), { number: "6", unit: "days" });
  });
});

const bins = (n) => Array.from({ length: n }, (_, i) => stream(`Bin ${i}`, null));

describe("chip overflow", () => {
  test("streams that fit the slots are all shown", () => {
    assert.deepEqual(visibleChips(bins(3), 3), { shown: bins(3), extra: 0 });
    assert.deepEqual(visibleChips(bins(12), 12), { shown: bins(12), extra: 0 });
  });

  test("more than fit fill all but the last slot, which says +N", () => {
    assert.deepEqual(visibleChips(bins(4), 3), { shown: bins(2), extra: 2 });
    assert.deepEqual(visibleChips(bins(13), 12), { shown: bins(11), extra: 2 });
  });
});

describe("render", () => {
  test("links the shared widget styles and its own stylesheet", () => {
    const html = draw("sm", { days: [TOMORROW] });
    assert.ok(html.includes('href="/static/style/spectra-widgets.css"'));
    assert.ok(html.includes('href="/plugins/bin_day/client.css"'));
    assert.ok(html.includes("size-sm"));
  });

  test("is idempotent: rendering twice replaces rather than appends", () => {
    const shadow = { innerHTML: "" };
    const ctx = { cell: { size: "sm", options: {} }, data: { days: [TOMORROW] } };
    render(shadow, ctx);
    const first = shadow.innerHTML;
    render(shadow, ctx);
    assert.equal(shadow.innerHTML, first);
  });

  test("error tile shows the escaped message with a warning icon", () => {
    const html = draw("sm", { error: "Bad <schedule>" });
    assert.ok(html.includes("ph-warning-circle"));
    assert.ok(html.includes("Bad &lt;schedule&gt;"));
    assert.equal(count(html, 'class="chip"'), 0);
  });

  test("missing data is shown as an error, not a blank cell", () => {
    assert.ok(draw("sm", null).includes("ph-warning-circle"));
  });

  test("data without a days list is an error, not an empty week", () => {
    const html = draw("sm", {});
    assert.ok(html.includes("ph-warning-circle"));
    assert.ok(!html.includes("Nothing this week"));
  });

  test("an unknown size falls back to the row layout", () => {
    const html = draw('huge" onload="x', { days: [TOMORROW] });
    assert.ok(html.includes("size-sm"));
    assert.equal(count(html, 'class="day-row"'), 1);
  });

  for (const size of ["xs", "sm", "md", "lg"]) {
    test(`empty window says Nothing this week at ${size}`, () => {
      const html = draw(size, { days: [] });
      assert.ok(html.includes("ph-calendar-check"));
      assert.ok(html.includes("Nothing this week"));
    });
  }

  test("XS shows only the next collection day with a big count", () => {
    const html = draw("xs", { days: [TOMORROW, MONDAY] });
    assert.equal(count(html, 'class="chip"'), 2);
    assert.ok(html.includes('<span class="count-number">1</span>'));
    assert.ok(html.includes('<span class="count-unit">day</span>'));
    assert.ok(!html.includes("Recycling"));
  });

  test("SM shows one row per day, at most two, with day labels", () => {
    const html = draw("sm", { days: [TOMORROW, MONDAY, LATER] });
    assert.equal(count(html, 'class="day-row"'), 2);
    assert.ok(html.includes("Tomorrow"));
    assert.ok(html.includes("6 days"));
    assert.ok(!html.includes("7 days"));
  });

  test("MD and LG use the row layout until the bin shapes land", () => {
    for (const size of ["md", "lg"]) {
      assert.equal(count(draw(size, { days: [TOMORROW, MONDAY] }), 'class="day-row"'), 2);
    }
  });

  test("chips carry the stream's colours, icon and name", () => {
    const html = draw("sm", { days: [{ ...MONDAY, streams: [RECYCLING] }] });
    assert.ok(html.includes("--body:#1f4fd1"));
    assert.ok(html.includes("--ink:#ffffff"));
    assert.ok(html.includes('class="ph-bold ph-recycle"'));
    assert.ok(html.includes('aria-label="Recycling"'));
  });

  test("a stream with no icon gets a plain chip, never a generic bin", () => {
    const html = draw("sm", { days: [{ ...MONDAY, streams: [stream("Brown bin", null, "#7a4a21")] }] });
    assert.equal(count(html, 'class="chip"'), 1);
    assert.ok(!html.includes("ph-trash"));
    assert.ok(!html.includes("<i"));
  });

  test("SM shrinks the chips for three bins on a day", () => {
    const three = draw("sm", { days: [{ ...MONDAY, streams: [REFUSE, GREEN, RECYCLING] }] });
    assert.ok(three.includes('class="chips many"'));
    assert.equal(count(three, 'class="chip"'), 3);
  });

  test("when either SM row is full, both rows use the smaller chips", () => {
    const html = draw("sm", { days: [{ ...TOMORROW, streams: [REFUSE] }, { ...MONDAY, streams: bins(5) }] });
    assert.equal(count(html, 'class="chips many"'), 2);
  });

  test("XS has room for three chips; four collapse to two and +N", () => {
    const four = draw("xs", { days: [{ ...MONDAY, streams: bins(4) }] });
    assert.equal(count(four, 'class="chip"'), 2);
    assert.ok(four.includes('<span class="more">+2</span>'));
  });

  describe("SM busy mode: the upcoming day has four or more bins", () => {
    const busyDay = (n) => ({ ...TOMORROW, streams: bins(n) });

    test("shows only the upcoming day, its label above every bin", () => {
      const html = draw("sm", { days: [busyDay(5), MONDAY] });
      assert.equal(count(html, 'class="day-stack"'), 1);
      assert.equal(count(html, 'class="day-row"'), 0);
      assert.ok(html.indexOf("Tomorrow") < html.indexOf('class="chip"'));
      assert.equal(count(html, 'class="chip"'), 5);
      assert.ok(!html.includes("6 days"));
      assert.ok(!html.includes('class="more"'));
    });

    test("a busy second day stays a row, its last slot +N", () => {
      const html = draw("sm", { days: [TOMORROW, { ...MONDAY, streams: bins(5) }] });
      assert.equal(count(html, 'class="day-row"'), 2);
      assert.equal(count(html, 'class="day-stack"'), 0);
      assert.ok(html.includes("6 days"));
      assert.equal(count(html, 'class="chip"'), 4); // two for tomorrow, two for the busy day
      assert.ok(html.includes('<span class="more">+3</span>'));
    });

    test("three bins a day keeps the two-row layout", () => {
      const html = draw("sm", { days: [{ ...TOMORROW, streams: bins(3) }, MONDAY] });
      assert.equal(count(html, 'class="day-row"'), 2);
      assert.equal(count(html, 'class="day-stack"'), 0);
    });

    test("the grid is told its chips per line and lines, so one line can grow", () => {
      assert.ok(draw("sm", { days: [busyDay(5)] }).includes("--per-line:5;--lines:1"));
      assert.ok(draw("sm", { days: [busyDay(7)] }).includes("--per-line:6;--lines:2"));
      assert.ok(draw("sm", { days: [busyDay(14)] }).includes("--per-line:6;--lines:2"));
    });

    test("twelve bins all fit with no +N", () => {
      const html = draw("sm", { days: [busyDay(12)] });
      assert.equal(count(html, 'class="chip"'), 12);
      assert.ok(!html.includes('class="more"'));
    });

    test("thirteen or more end with +N", () => {
      const html = draw("sm", { days: [busyDay(14)] });
      assert.equal(count(html, 'class="chip"'), 11);
      assert.ok(html.includes('<span class="more">+3</span>'));
    });
  });

  test("names and icons from data cannot break out of the markup", () => {
    const evil = stream('"><script>x</script>', 'trash" onerror="x');
    const html = draw("sm", { days: [{ ...MONDAY, streams: [evil] }] });
    assert.ok(!html.includes("<script>"));
    assert.ok(!html.includes('onerror="'));
  });

  test("colours from data cannot inject extra CSS", () => {
    const evil = stream("Bin", null, "red;background:url(x)", "#fff;x:y");
    const html = draw("sm", { days: [{ ...MONDAY, streams: [evil] }] });
    assert.ok(!html.includes("url(x)"));
    assert.ok(!html.includes("x:y"));
  });
});
