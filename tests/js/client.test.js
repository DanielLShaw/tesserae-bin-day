// bin_day/client.js: labels, chip overflow and the XS / SM / empty / error layouts.
import assert from "node:assert/strict";
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
    assert.ok(!html.includes("<i"));
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
