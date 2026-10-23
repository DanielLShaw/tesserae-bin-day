// bin_day/client.js: labels, chip overflow and the XS / SM / empty / error layouts.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, test } from "node:test";

import render, {
  dayLabel,
  isMonoPalette,
  longDate,
  shortDate,
  shortWeekday,
  visibleChips,
  xsCount,
} from "../../bin_day/client.js";

const stream = (label, icon, body = "#111111", ink = "#ffffff") => ({
  id: "other",
  label,
  icon,
  body_colour: body,
  lid_colour: body,
  icon_colour: ink,
  chip_icon_colour: ink,
});

const REFUSE = stream("Refuse", "trash");
const GREEN = stream("Green", "leaf", "#13803a");
const RECYCLING = stream("Recycling", "recycle", "#1f4fd1");
const TOMORROW = { date: "2026-10-07", days_until: 1, streams: [REFUSE, GREEN] };
const MONDAY = { date: "2026-10-12", days_until: 6, streams: [RECYCLING] };
const LATER = { date: "2026-10-13", days_until: 7, streams: [REFUSE] };

function draw(size, data, locale = "en") {
  const shadow = { innerHTML: "" };
  render(shadow, { cell: { size, options: {} }, data, locale });
  return shadow.innerHTML;
}

// A collection day ``daysUntil`` days after Tue 6 Oct 2026.
const on = (daysUntil, streams) => ({
  date: new Date(Date.UTC(2026, 9, 6 + daysUntil)).toISOString().slice(0, 10),
  days_until: daysUntil,
  streams,
});

const count = (html, needle) => html.split(needle).length - 1;
// The widget's body, below its title bar.
const body = (html) => html.slice(html.indexOf('class="w-body"'));

describe("day labels", () => {
  test("0 is Today, 1 is Tomorrow, otherwise N days", () => {
    assert.deepEqual([0, 1, 2, 7].map((n) => dayLabel(n)), ["Today", "Tomorrow", "2 days", "7 days"]);
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

  test("chips carry the stream's colours, icon and name", () => {
    const html = draw("sm", { days: [{ ...MONDAY, streams: [RECYCLING] }] });
    assert.ok(html.includes("--fill:#1f4fd1"));
    assert.ok(html.includes("--ink:#ffffff"));
    assert.ok(html.includes('class="ph-bold ph-recycle"'));
    assert.ok(html.includes('aria-label="Recycling"'));
  });

  test("a chip shows the lid colour, the one lid-coded bins are named by", () => {
    const blueLid = {
      ...stream("Recycling", "recycle", "#4d4d4d"),
      lid_colour: "#f5c400",
      chip_icon_colour: "#000000",
    };
    const html = draw("sm", { days: [{ ...MONDAY, streams: [blueLid] }] });
    assert.ok(html.includes('style="--fill:#f5c400;--ink:#000000"'));
  });

  test("a stream with no icon gets a plain chip, never a generic bin", () => {
    const html = draw("sm", { days: [{ ...MONDAY, streams: [stream("Brown bin", null, "#7a4a21")] }] });
    assert.equal(count(html, 'class="chip"'), 1);
    assert.ok(!body(html).includes("ph-trash"));
    assert.ok(!body(html).includes("<i"));
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

describe("dates", () => {
  test("plain English reads UK style", () => {
    assert.equal(shortDate("2026-10-07", "en"), "Wed 7 Oct");
    assert.equal(longDate("2026-10-07", "en"), "Wednesday 7 October");
    assert.equal(shortWeekday("2026-10-07", "en"), "Wed");
  });

  test("other locales use their own conventions", () => {
    assert.equal(shortDate("2026-10-07", "en-US"), "Wed, Oct 7");
    assert.equal(longDate("2026-10-07", "fr"), "mercredi 7 octobre");
  });

  test("a date stays the same calendar day in a browser west of UTC", () => {
    const saved = process.env.TZ;
    process.env.TZ = "America/Los_Angeles";
    try {
      assert.equal(shortDate("2026-10-07", "en"), "Wed 7 Oct");
    } finally {
      process.env.TZ = saved;
    }
  });
});

describe("MD: one column per collection day", () => {
  test("each column has the count and short date above its labelled bins", () => {
    const html = draw("md", { days: [TOMORROW, MONDAY] });
    assert.equal(count(html, 'class="day-col"'), 2);
    for (const text of ["Tomorrow", "Wed 7 Oct", "6 days", "Mon 12 Oct"]) {
      assert.ok(html.includes(text), text);
    }
    assert.equal(count(html, 'class="bin"'), 3);
    assert.equal(count(html, 'class="bin-label"'), 3);
    assert.ok(html.indexOf("Wed 7 Oct") < html.indexOf('class="bin-label">Refuse<'));
  });

  test("at most three days are shown", () => {
    const html = draw("md", { days: [1, 2, 3, 4].map((n) => on(n, bins(1))) });
    assert.equal(count(html, 'class="day-col"'), 3);
  });

  test("a later day is only added while the total stays at six bins or fewer", () => {
    const html = draw("md", { days: [on(1, bins(2)), on(2, bins(3)), on(3, bins(2))] });
    assert.equal(count(html, 'class="day-col"'), 2);
    assert.equal(count(html, 'class="bin"'), 5);
  });

  test("a later day that doesn't fit gets the slots left, ending with +N", () => {
    const html = draw("md", { days: [on(1, bins(1)), on(6, bins(14))] });
    assert.equal(count(html, 'class="day-col"'), 2);
    assert.equal(count(html, 'class="bin"'), 5); // one tomorrow, four on day 6
    assert.ok(html.includes('<span class="more">+10</span>'));
    assert.ok(html.includes("--bins:7;--cols:2")); // tomorrow claims 2, day 6 its 5 slots
  });

  test("two slots left is the least a partial column gets: one bin and +N", () => {
    const html = draw("md", { days: [on(1, bins(4)), on(3, bins(3))] });
    assert.equal(count(html, 'class="day-col"'), 2);
    assert.equal(count(html, 'class="bin"'), 5);
    assert.ok(html.includes('<span class="more">+2</span>'));
  });

  test("a busy upcoming day fills MD alone, with +N beyond twelve bins", () => {
    const seven = draw("md", { days: [on(1, bins(7)), on(3, bins(1))] });
    assert.equal(count(seven, 'class="day-col"'), 1);
    assert.equal(count(seven, 'class="bin"'), 7);
    assert.ok(!seven.includes('class="more"'));
    const fourteen = draw("md", { days: [on(1, bins(14))] });
    assert.equal(count(fourteen, 'class="bin"'), 11);
    assert.ok(fourteen.includes('<span class="more">+3</span>'));
  });

  test("each column claims at least two bins of width, for its heading", () => {
    // Tomorrow has two bins, Monday one: 2 + 2 bin widths across two columns.
    const html = draw("md", { days: [TOMORROW, MONDAY] });
    assert.ok(html.includes("--bins:4;--cols:2"));
    const busySecond = draw("md", { days: [on(1, bins(1)), on(6, bins(5))] });
    assert.ok(busySecond.includes("--bins:7;--cols:2"));
  });
});

describe("LG: the upcoming day as hero, later days in a strip", () => {
  test("the hero has the big label, full date and labelled bins", () => {
    const html = draw("lg", { days: [TOMORROW, MONDAY] });
    assert.ok(html.includes('class="hero-label">Tomorrow<'));
    assert.ok(html.includes("Wednesday 7 October"));
    assert.equal(count(html, 'class="bin"'), 2);
    assert.equal(count(html, 'class="bin-label"'), 2);
  });

  test("each later day is a strip row: chips, names and when", () => {
    const html = draw("lg", { days: [TOMORROW, { ...MONDAY, streams: [RECYCLING, GREEN] }] });
    assert.equal(count(html, 'class="strip-row"'), 1);
    assert.equal(count(html, 'class="chip"'), 2);
    assert.ok(html.includes('class="strip-names">Recycling, Green<'));
    assert.ok(html.includes('class="strip-when">6 days · Mon<'));
  });

  test("strip rows show every bin's chip before any +N, up to twelve", () => {
    const five = draw("lg", { days: [TOMORROW, on(6, bins(5))] });
    assert.equal(count(five, 'class="chip"'), 5);
    assert.ok(!five.includes('class="more"'));
    const thirteen = draw("lg", { days: [TOMORROW, on(6, bins(13))] });
    assert.equal(count(thirteen, 'class="chip"'), 11);
    assert.ok(thirteen.includes('<span class="more">+2</span>'));
  });

  test("a strip row with more than three bins drops its names, keeping chips and when", () => {
    const four = draw("lg", { days: [TOMORROW, on(6, bins(4))] });
    assert.equal(count(four, 'class="strip-names"'), 0);
    assert.ok(four.includes('class="strip-when">6 days · Mon<'));
    const three = draw("lg", { days: [TOMORROW, on(6, bins(3))] });
    assert.ok(three.includes('class="strip-names">Bin 0, Bin 1, Bin 2<'));
  });

  test("the strip shows at most three later days", () => {
    const html = draw("lg", { days: [1, 2, 3, 4, 5].map((n) => on(n, bins(1))) });
    assert.equal(count(html, 'class="strip-row"'), 3);
  });

  test("with nothing later there is no strip", () => {
    assert.equal(count(draw("lg", { days: [TOMORROW] }), 'class="strip"'), 0);
  });

  test("a busy hero shows up to twelve bins, then +N", () => {
    const html = draw("lg", { days: [on(1, bins(14))] });
    assert.equal(count(html, 'class="bin"'), 11);
    assert.ok(html.includes('<span class="more">+3</span>'));
  });
});

describe("bin shapes", () => {
  test("a bin fills its lid and body separately and carries its icon and name", () => {
    const lidded = { ...RECYCLING, lid_colour: "#000000" };
    const html = draw("md", { days: [{ ...MONDAY, streams: [lidded] }] });
    assert.ok(html.includes("--body:#1f4fd1"));
    assert.ok(html.includes("--lid:#000000"));
    assert.ok(html.includes("--ink:#ffffff"));
    assert.ok(html.includes('class="lid"'));
    assert.ok(html.includes('class="body"'));
    assert.ok(html.includes('class="ph-bold ph-recycle"'));
    assert.ok(html.includes('aria-label="Recycling"'));
  });

  test("a stream with no icon gets a plain bin, never a generic one", () => {
    const html = draw("md", { days: [{ ...MONDAY, streams: [stream("Brown bin", null, "#7a4a21")] }] });
    assert.equal(count(html, 'class="bin"'), 1);
    assert.ok(!body(html).includes("<i"));
  });

  for (const size of ["md", "lg"]) {
    test(`names, icons and colours cannot break out of the ${size} markup`, () => {
      const evil = stream('"><script>x</script>', 'trash" onerror="x', "red;x:url(y)");
      const html = draw(size, { days: [{ ...TOMORROW, streams: [evil] }, { ...MONDAY, streams: [evil] }] });
      assert.ok(!html.includes("<script>"));
      assert.ok(!html.includes('onerror="'));
      assert.ok(!html.includes("url(y)"));
    });
  }
});

describe("mono rendering", () => {
  // A shadow root whose host reads these six accent colours from the theme.
  function drawThemed(size, data, options, accents) {
    const saved = globalThis.getComputedStyle;
    globalThis.getComputedStyle = () => ({
      getPropertyValue: (name) => accents[Number(name.at(-1)) - 1] ?? "",
    });
    try {
      const shadow = { innerHTML: "", host: {} };
      render(shadow, { cell: { size, options }, data, locale: "en" });
      return shadow.innerHTML;
    } finally {
      globalThis.getComputedStyle = saved;
    }
  }
  const PAPER = Array(6).fill("#000000");
  const LIGHT = ["#A84B2A", "#9A7414", "#4F6F36", "#256E6B", "#3F5A88", "#7E4068"];
  const isMonoHtml = (html) => /class="w bin-day size-\w+ mono"/.test(html);

  test("a palette of only black, white and greys is mono", () => {
    const greys = ["#000000", "#000", "rgb(0, 0, 0)", " #FFFFFF ", "#888888", "#7f8080"];
    assert.equal(isMonoPalette(greys), true);
  });

  test("any colour, or nothing readable, is not mono", () => {
    assert.equal(isMonoPalette(["#000000", "#A84B2A"]), false);
    assert.equal(isMonoPalette([]), false);
    assert.equal(isMonoPalette(["", "var(--x)"]), false);
  });

  test("Auto follows a black and white theme", () => {
    assert.ok(isMonoHtml(drawThemed("sm", { days: [TOMORROW] }, { colours: "auto" }, PAPER)));
  });

  test("Auto stays in colour on a colourful theme", () => {
    assert.ok(!isMonoHtml(drawThemed("sm", { days: [TOMORROW] }, { colours: "auto" }, LIGHT)));
  });

  test("Black & white forces mono on any theme", () => {
    assert.ok(isMonoHtml(drawThemed("sm", { days: [TOMORROW] }, { colours: "mono" }, LIGHT)));
  });

  test("Colour keeps the bin colours even on a black and white theme", () => {
    assert.ok(!isMonoHtml(drawThemed("sm", { days: [TOMORROW] }, { colours: "colour" }, PAPER)));
  });

  test("Colour for e-ink keeps the bin colours even on a black and white theme", () => {
    assert.ok(!isMonoHtml(drawThemed("sm", { days: [TOMORROW] }, { colours: "eink" }, PAPER)));
  });

  test("with no theme to read, Auto renders in colour", () => {
    assert.ok(!isMonoHtml(draw("sm", { days: [TOMORROW] })));
  });

  test("mono markup carries the patterns the bins fill with", () => {
    const html = drawThemed("md", { days: [TOMORROW] }, { colours: "mono" }, LIGHT);
    for (const id of ["bin-hatch", "bin-dots", "bin-cross"]) {
      assert.ok(html.includes(`<pattern id="${id}"`), id);
    }
  });

  test("every chip and bin carries its black-and-white fill", () => {
    const dotted = { ...REFUSE, mono_fill: "dotted" };
    for (const size of ["sm", "md"]) {
      const html = draw(size, { days: [{ ...TOMORROW, streams: [dotted] }] });
      assert.ok(html.includes('data-mono="dotted"'), size);
    }
  });

  test("a missing or unknown fill is white, and cannot break out of the markup", () => {
    const evil = { ...REFUSE, mono_fill: 'solid" onload="x' };
    const html = draw("sm", { days: [{ ...TOMORROW, streams: [evil, REFUSE] }] });
    assert.equal(count(html, 'data-mono="white"'), 2);
    assert.ok(!html.includes('onload="'));
  });
});

describe("small cells with wheelie bins", () => {
  // A cell w by h with the Small cells show option set to Wheelie bins.
  function drawBins(size, data, { w, h } = {}) {
    const shadow = { innerHTML: "" };
    render(shadow, { cell: { size, w, h, options: { small_cells: "bins" } }, data, locale: "en" });
    return shadow.innerHTML;
  }
  const arrangement = (html) => html.match(/class="next (beside|above)/)?.[1];

  for (const size of ["xs", "sm"]) {
    test(`${size} draws the next collection's bins with its count and date`, () => {
      const html = drawBins(size, { days: [TOMORROW, MONDAY] });
      assert.equal(count(html, 'class="bin"'), 2);
      assert.equal(count(html, 'class="chip"'), 0);
      assert.ok(html.includes('<span class="count-number">1</span>'));
      assert.ok(html.includes('<span class="count-unit">day</span>'));
      // the day and month stay together if the date wraps
      assert.ok(html.includes('<span class="next-date">Wed 7\u00a0Oct</span>'));
      assert.ok(html.includes('class="bin-label">Refuse<'));
      assert.ok(!html.includes("Recycling"));
    });
  }

  test("a collection today says Today, with no number", () => {
    const html = drawBins("xs", { days: [{ ...TOMORROW, days_until: 0 }] });
    assert.equal(count(html, 'class="bin"'), 2);
    assert.ok(html.includes('<span class="count-unit">Today</span>'));
    assert.ok(!html.includes("count-number"));
  });

  test("small cells show chips unless wheelie bins are chosen", () => {
    for (const options of [{}, { small_cells: "chips" }, { small_cells: "nonsense" }]) {
      const shadow = { innerHTML: "" };
      render(shadow, { cell: { size: "xs", options }, data: { days: [TOMORROW] }, locale: "en" });
      assert.equal(count(shadow.innerHTML, 'class="bin"'), 0);
      assert.equal(count(shadow.innerHTML, 'class="chip"'), 2);
    }
  });

  test("MD and LG are the same whichever small cells show", () => {
    for (const size of ["md", "lg"]) {
      assert.equal(drawBins(size, { days: [TOMORROW, MONDAY] }), draw(size, { days: [TOMORROW, MONDAY] }));
    }
  });

  test("up to four bins are drawn; five or more are three and +N", () => {
    const four = drawBins("sm", { days: [{ ...TOMORROW, streams: bins(4) }] });
    assert.equal(count(four, 'class="bin"'), 4);
    assert.ok(!four.includes('class="more"'));
    const six = drawBins("sm", { days: [{ ...TOMORROW, streams: bins(6) }] });
    assert.equal(count(six, 'class="bin"'), 3);
    assert.ok(six.includes('<span class="more">+3</span>'));
  });

  test("the count goes beside the bins or above them, whichever leaves the bins bigger", () => {
    const one = { days: [{ ...TOMORROW, streams: [REFUSE] }] };
    const two = { days: [TOMORROW] };
    assert.equal(arrangement(drawBins("sm", one, { w: 205, h: 165 })), "beside");
    assert.equal(arrangement(drawBins("xs", one, { w: 180, h: 180 })), "beside");
    assert.equal(arrangement(drawBins("sm", two, { w: 205, h: 165 })), "above");
    assert.equal(arrangement(drawBins("sm", one, { w: 150, h: 250 })), "above");
    assert.equal(arrangement(drawBins("sm", two, { w: 380, h: 120 })), "beside");
    assert.equal(arrangement(drawBins("sm", one)), "above");
  });

  test("names drop when the bins are too narrow to carry them", () => {
    const four = drawBins("sm", { days: [{ ...TOMORROW, streams: bins(4) }] }, { w: 205, h: 165 });
    assert.ok(/class="next above no-names"/.test(four));
    const three = drawBins("sm", { days: [{ ...TOMORROW, streams: bins(3) }] }, { w: 205, h: 165 });
    assert.ok(/class="next above no-names"/.test(three));
    const roomy = drawBins("sm", { days: [{ ...TOMORROW, streams: bins(3) }] }, { w: 300, h: 200 });
    assert.ok(/class="next above"/.test(roomy));
  });

  test("the bins carry their colours and black-and-white fills as in MD", () => {
    const html = drawBins("xs", { days: [{ ...MONDAY, streams: [{ ...RECYCLING, mono_fill: "dotted" }] }] });
    assert.ok(html.includes("--body:#1f4fd1"));
    assert.ok(html.includes('data-mono="dotted"'));
  });
});

describe("translatable text", () => {
  const EN = new URL("../../bin_day/strings/en.json", import.meta.url);
  const drawWith = (t, size, data, options = {}) => {
    const shadow = { innerHTML: "" };
    render(shadow, { cell: { size, options }, data, locale: "en", t });
    return shadow.innerHTML;
  };
  const busy = { ...TOMORROW, streams: bins(5) };

  test("every word the widget draws comes from strings/en.json, with the same English", () => {
    const asked = new Map();
    const t = (key, fallback) => {
      asked.set(key, fallback);
      return fallback;
    };
    for (const size of ["xs", "sm", "md", "lg"]) drawWith(t, size, { days: [TOMORROW, MONDAY, LATER] });
    drawWith(t, "xs", { days: [MONDAY] });
    drawWith(t, "sm", { days: [{ ...TOMORROW, days_until: 0 }] });
    drawWith(t, "xs", { days: [{ ...TOMORROW, days_until: 0 }] });
    drawWith(t, "sm", { days: [busy] });
    drawWith(t, "xs", { days: [TOMORROW] }, { small_cells: "bins" });
    drawWith(t, "sm", { days: [] });
    drawWith(t, "sm", null);
    drawWith(t, "sm", { error: "Calendar not found" });
    assert.deepEqual(
      [...asked.keys()].sort(),
      ["load_failed", "n_days", "nothing_this_week", "title", "today", "tomorrow", "unit_day", "unit_days"],
    );
    const english = JSON.parse(readFileSync(EN, "utf8"));
    assert.deepEqual(Object.fromEntries([...asked].sort()), Object.fromEntries(Object.entries(english).sort()));
  });

  test("a translation replaces the widget's words", () => {
    const FR = {
      tomorrow: "Demain",
      n_days: "{n} jours",
      unit_day: "jour",
      unit_days: "jours",
      nothing_this_week: "Rien cette semaine",
    };
    const t = (key, fallback) => FR[key] ?? fallback;
    const sm = drawWith(t, "sm", { days: [TOMORROW, MONDAY] });
    assert.ok(sm.includes("Demain"));
    assert.ok(sm.includes("6 jours"));
    assert.ok(drawWith(t, "xs", { days: [MONDAY] }).includes(">jours<"));
    assert.ok(drawWith(t, "sm", { days: [] }).includes("Rien cette semaine"));
  });
});

describe("title bar", () => {
  function drawOpts(size, data, options) {
    const shadow = { innerHTML: "" };
    render(shadow, { cell: { size, options }, data, locale: "en" });
    return shadow.innerHTML;
  }
  const bar = (text) => `<div class="w-title"><i class="ph-bold ph-trash" aria-hidden="true"></i><h3>${text}</h3></div>`;

  test("a title bar reading Bins tops every layout by default", () => {
    const states = [
      ["xs", { days: [TOMORROW] }],
      ["sm", { days: [TOMORROW, MONDAY] }],
      ["md", { days: [TOMORROW, MONDAY] }],
      ["lg", { days: [TOMORROW, MONDAY] }],
      ["sm", { days: [] }],
      ["sm", { error: "Calendar not found" }],
    ];
    for (const [size, data] of states) {
      const html = drawOpts(size, data, {});
      assert.ok(html.includes(bar("Bins")), `${size} ${JSON.stringify(data)}`);
      assert.ok(html.indexOf(bar("Bins")) < html.indexOf('class="w-body"'));
    }
  });

  test("the title bar shows the Title option's text", () => {
    assert.ok(drawOpts("sm", { days: [TOMORROW] }, { title: "Bin day" }).includes(bar("Bin day")));
  });

  test("a title is shown as text, never markup", () => {
    const html = drawOpts("sm", { days: [TOMORROW] }, { title: '<b>"Bins" & co</b>' });
    assert.ok(html.includes(bar("&lt;b&gt;&quot;Bins&quot; &amp; co&lt;/b&gt;")));
  });

  test("a title of only spaces reads Bins", () => {
    assert.ok(drawOpts("sm", { days: [TOMORROW] }, { title: "   " }).includes(bar("Bins")));
  });

  test("Show title row off drops the title bar", () => {
    const html = drawOpts("sm", { days: [TOMORROW] }, { show_title: false, title: "Bin day" });
    assert.ok(!html.includes("w-title"));
  });
});
