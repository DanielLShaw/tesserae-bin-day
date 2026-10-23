// Bin Day: which bins are collected in the next 7 days, from bin_day_core's
// payload (ctx.data = {days: [{date, days_until, streams}], next_change_at}).
//
// Layout follows ctx.cell.size:
// Every layout reads from the top left: Tesserae's title bar, then the bins,
// then the days left and the date (the owner's order).
//   xs, sm  with the Small cells show option on Wheelie bins: the next
//           collection day, its bins drawn as large as fit (up to
//           SMALL_SLOTS), then the count and short date. Names drop when the
//           bins are too narrow for them.
//   xs      the next collection day: its bins as chips, then a big day count
//   sm      one row per collection day (at most two): chips, then the day label.
//           A row has ROW_SLOTS chips, the last becoming "+N" if more. When the
//           upcoming day has BUSY_FROM or more bins it gets the whole cell
//           instead: a grid of up to GRID_SLOTS chips, then its label.
//   md      one column per collection day (up to MD_DAYS, MD_BINS bins in
//           all): a wheelie bin per collection with its name, then the count
//           and short date. A later day that doesn't fit gets the slots left,
//           ending "+N". A busier upcoming day fills md alone.
//   lg      the upcoming day as hero (large named bins, then the count and
//           full date), later days as a strip at the bottom: a chip for every
//           bin, then names (only for a few bins, and they give way first),
//           then when
// Bins and chips show up to their slot count, the last slot becoming "+N".
// Black & white: each bin takes the fill the server chose (solid, hatched,
// white, dotted or cross-hatched; refuse solid, garden hatched, recycling
// white, others by colour). The Colours option picks it, or Auto follows a
// theme whose accents are all black, white or grey (paper, newsprint).
// Bin colours arrive as hex from the server (they are the colours of real
// bins); everything else paints from Spectra tokens in client.css.

const STYLESHEETS = `
  <link rel="stylesheet" href="/static/style/spectra-widgets.css">
  <link rel="stylesheet" href="/plugins/bin_day/client.css">`;

const SIZES = ["xs", "sm", "md", "lg"];
const ROW_SLOTS = 3; // chips in an xs or sm row
const MAX_ROWS = 2; // collection days in the sm row layout
const BUSY_FROM = 4; // bins on the upcoming day that switch sm to its grid
const GRID_PER_LINE = 6;
const GRID_SLOTS = GRID_PER_LINE * 2; // chips in that grid
const MD_DAYS = 3; // day columns in md
const MD_BINS = 6; // bins across md's columns before a later day is left off
const MD_COL_MIN = 2; // bin widths a column claims, so its heading fits
const MD_PARTIAL_MIN = 2; // slots a later day needs for a column: a bin and +N
const HERO_SLOTS = 12; // bins for one busy day (md) or the lg hero, in two lines
const STRIP_DAYS = 3; // later days in the lg strip
const STRIP_NAMED_MAX = 3; // bins in a strip row that still get their names
const SMALL_SLOTS = 4; // wheelie bins in a small cell: four, or three and +N
const NAME_MIN = 72; // px of the cell's width each bin needs to carry its name
const HEX_COLOUR = /^#[0-9a-f]{6}$/i;
const ICON_NAME = /^[a-z0-9-]+$/;
const MONO_FILLS = ["solid", "hatched", "white", "dotted", "crosshatch"];
const GREY_SPREAD = 8; // max RGB channel spread for a colour to count as grey
const ENTITIES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

const escapeHtml = (text) => String(text).replace(/[&<>"']/g, (c) => ENTITIES[c]);
const safeColour = (value) => (HEX_COLOUR.test(value) ? value : "var(--surface-sunken)");

// The widget's own words come through the host's translations
// (strings/<locale>.json) when it has them, else the English given here.
const english = (key, fallback) => fallback;
const words = (ctx) => (typeof ctx?.t === "function" ? (key, fallback) => ctx.t(key, fallback) : english);

export function dayLabel(daysUntil, t = english) {
  if (daysUntil === 0) return t("today", "Today");
  if (daysUntil === 1) return t("tomorrow", "Tomorrow");
  return t("n_days", "{n} days").replace("{n}", String(daysUntil));
}

// Bin days are calendar dates, so they are formatted in UTC: the browser's
// own timezone can never shift one to the day before. Plain English reads
// UK style ("Wed 7 Oct"), the way UK councils write it.
function formatDate(iso, locale, options) {
  const [year, month, day] = iso.split("-").map(Number);
  const tag = !locale || locale === "en" ? "en-GB" : locale;
  return new Intl.DateTimeFormat(tag, { ...options, timeZone: "UTC" }).format(
    new Date(Date.UTC(year, month - 1, day)),
  );
}

export const shortDate = (iso, locale) =>
  formatDate(iso, locale, { weekday: "short", day: "numeric", month: "short" });
export const longDate = (iso, locale) =>
  formatDate(iso, locale, { weekday: "long", day: "numeric", month: "long" });
export const shortWeekday = (iso, locale) => formatDate(iso, locale, { weekday: "short" });

function parseColour(text) {
  const value = String(text).trim().toLowerCase();
  const hex = value.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/);
  if (hex) {
    const digits = hex[1].length === 3 ? [...hex[1]].map((c) => c + c).join("") : hex[1];
    return [0, 2, 4].map((i) => parseInt(digits.slice(i, i + 2), 16));
  }
  const rgb = value.match(/^rgba?\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)/);
  return rgb ? rgb.slice(1, 4).map(Number) : null;
}

// True when every colour is black, white or a grey.
export function isMonoPalette(colours) {
  const rgbs = colours.map(parseColour);
  return rgbs.length > 0 && rgbs.every((rgb) => rgb && Math.max(...rgb) - Math.min(...rgb) <= GREY_SPREAD);
}

function themeAccents(shadow) {
  if (!shadow.host || typeof globalThis.getComputedStyle !== "function") return [];
  const style = globalThis.getComputedStyle(shadow.host);
  return [1, 2, 3, 4, 5, 6].map((n) => style.getPropertyValue(`--accent-${n}`));
}

const followsTheme = (options) => !["mono", "colour", "eink"].includes(options?.colours);

function isMono(shadow, options) {
  if (!followsTheme(options)) return options.colours === "mono";
  return isMonoPalette(themeAccents(shadow));
}

// The dashboard editor applies a cell's own theme by setting data-theme on
// the cell without drawing the widget again, so Auto watches for it.
const themeWatchers = new WeakMap();

function watchCellTheme(shadow, ctx) {
  themeWatchers.get(shadow)?.disconnect();
  themeWatchers.delete(shadow);
  const cell = shadow.host?.closest?.(".cell");
  if (!cell || !followsTheme(ctx.cell.options)) return;
  const watcher = new MutationObserver(() => render(shadow, ctx));
  watcher.observe(cell, { attributes: true, attributeFilter: ["data-theme"] });
  themeWatchers.set(shadow, watcher);
}

// The patterns bin bodies fill with in black and white, one of each.
const PATTERNS = `<svg class="defs" aria-hidden="true"><defs>
  <pattern id="bin-hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
    <rect width="5" height="5" class="hatch-paper"/><rect width="1.6" height="5" class="hatch-ink"/>
  </pattern>
  <pattern id="bin-dots" width="5" height="5" patternUnits="userSpaceOnUse">
    <rect width="5" height="5" class="hatch-paper"/><circle cx="2.5" cy="2.5" r="1.1" class="hatch-ink"/>
  </pattern>
  <pattern id="bin-cross" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
    <rect width="5" height="5" class="hatch-paper"/><rect width="1.2" height="5" class="hatch-ink"/><rect width="5" height="1.2" class="hatch-ink"/>
  </pattern>
</defs></svg>`;

const monoAttr = (stream) =>
  `data-mono="${MONO_FILLS.includes(stream.mono_fill) ? stream.mono_fill : "white"}"`;

export function xsCount(daysUntil, t = english) {
  if (daysUntil === 0) return { number: "", unit: t("today", "Today") };
  return {
    number: String(daysUntil),
    unit: daysUntil === 1 ? t("unit_day", "day") : t("unit_days", "days"),
  };
}

// Every stream gets a chip while they fit the slots; beyond that, the last
// slot becomes a "+N" badge for the rest.
export function visibleChips(streams, slots) {
  if (streams.length <= slots) return { shown: streams, extra: 0 };
  const shown = streams.slice(0, slots - 1);
  return { shown, extra: streams.length - shown.length };
}

const iconHtml = (stream) =>
  ICON_NAME.test(stream.icon ?? "") ? `<i class="ph-bold ph-${stream.icon}" aria-hidden="true"></i>` : "";

// A chip takes the lid colour: the body's unless the bin is one of a set
// told apart by lid (all black, with blue, red and pink lids), which people
// name by their lids.
function chip(stream) {
  const colours = `--fill:${safeColour(stream.lid_colour)};--ink:${safeColour(stream.chip_icon_colour)}`;
  return `<span class="chip" ${monoAttr(stream)} role="img" aria-label="${escapeHtml(stream.label)}" style="${colours}">${iconHtml(stream)}</span>`;
}

// The mockup's wheelie bin: handle and lid in the lid colour, the body in the
// body colour, the icon centred on the body by client.css.
const BIN_SVG = `<svg viewBox="0 0 60 80" aria-hidden="true">
  <rect class="handle" x="22" y="1" width="16" height="5" rx="1.5"/>
  <rect class="lid" x="3" y="7" width="54" height="9" rx="2"/>
  <path class="body" d="M7 18h46l-4 54H11z"/>
  <circle class="wheel" cx="47" cy="73" r="6"/>
</svg>`;

// A bin with its name under it, or without (Show bin names off): its
// aria-label names it for screen readers either way.
function bin(stream, named = true) {
  const colours = [
    `--body:${safeColour(stream.body_colour)}`,
    `--lid:${safeColour(stream.lid_colour)}`,
    `--ink:${safeColour(stream.icon_colour)}`,
  ].join(";");
  const name = escapeHtml(stream.label);
  return `<span class="bin-item"><span class="bin" ${monoAttr(stream)} role="img" aria-label="${name}" style="${colours}">${BIN_SVG}${iconHtml(stream)}</span>${named ? `<span class="bin-label">${name}</span>` : ""}</span>`;
}

// "+N" for the bins that don't fit. Its text is in a child, so the badge box
// sizes in the same em as the chips or bins beside it.
const moreBadge = (extra) => `<span class="more"><span>+${extra}</span></span>`;

function bins(streams, slots, named = true) {
  const { shown, extra } = visibleChips(streams, slots);
  const more = extra ? moreBadge(extra) : "";
  return `<div class="bins">${shown.map((stream) => bin(stream, named)).join("")}${more}</div>`;
}

function chips(streams, slots, layout, style = "") {
  const { shown, extra } = visibleChips(streams, slots);
  const more = extra ? moreBadge(extra) : "";
  return `<div class="chips${layout}"${style}>${shown.map(chip).join("")}${more}</div>`;
}

// Chips shrink when a row is full; ``small`` covers every row in the cell so
// the rows keep matching sizes.
// --n tells client.css how many chips share the row's width.
const rowChips = (streams, small) =>
  chips(streams, ROW_SLOTS, small ? " many" : "", ` style="--n:${Math.min(streams.length, ROW_SLOTS)}"`);

// The busy grid passes its shape to client.css, so a single line of chips
// can grow to use the height a second line would have taken.
function gridChips(streams) {
  const used = Math.min(streams.length, GRID_SLOTS);
  const shape = ` style="--per-line:${Math.min(used, GRID_PER_LINE)};--lines:${Math.ceil(used / GRID_PER_LINE)}"`;
  return chips(streams, GRID_SLOTS, " grid", shape);
}

// Tesserae's standard title bar (widget-design-system.md §4): the shared
// .w-title, sized, cased and decorated by spectra-widgets.css and the style.
function titleBar(options, t) {
  if (options?.show_title === false) return "";
  const text = String(options?.title ?? "").trim() || t("title", "Bins");
  return `<div class="w-title"><i class="ph-bold ph-trash" aria-hidden="true"></i><h3>${escapeHtml(text)}</h3></div>`;
}

function errorBody(message) {
  return `<div class="notice is-error">
    <i class="ph-bold ph-warning-circle" aria-hidden="true"></i>
    <p class="u-muted">${escapeHtml(message)}</p>
  </div>`;
}

function emptyBody(t) {
  return `<div class="notice">
    <i class="ph-bold ph-calendar-check" aria-hidden="true"></i>
    <p>${escapeHtml(t("nothing_this_week", "Nothing this week"))}</p>
  </div>`;
}

// The days left as Tesserae's big number: the number large, its unit smaller
// (.stat-value and .unit in spectra-widgets.css). Today is the value itself.
function countHtml(daysUntil, t) {
  const { number, unit } = xsCount(daysUntil, t);
  const value = number ? `${escapeHtml(number)}<span class="unit">${escapeHtml(unit)}</span>` : escapeHtml(unit);
  return `<div class="stat-value count">${value}</div>`;
}

function xsBody(day, t) {
  return `${rowChips(day.streams, day.streams.length >= ROW_SLOTS)}${countHtml(day.days_until, t)}`;
}

// The next collection in a small cell: its bins, then the count and date.
// Names drop when Show bin names is off, or the cell (w wide) gives each bin
// less than NAME_MIN.
function nextBody(day, { w, options }, locale, t) {
  const slots = Math.min(day.streams.length, SMALL_SLOTS);
  const named = options?.show_names !== false && (!(w > 0) || w / slots >= NAME_MIN);
  // Should the date wrap, its day and month stay together.
  const date = shortDate(day.date, locale).replace(/ (?=\S+$)/, "\u00a0");
  return `<div class="next${named ? "" : " no-names"}" style="--bins:${slots}">
    ${bins(day.streams, SMALL_SLOTS, named)}
    <div class="next-head">${countHtml(day.days_until, t)}<span class="next-date">${escapeHtml(date)}</span></div>
  </div>`;
}

function smBody(days, t) {
  const [upcoming] = days;
  if (upcoming.streams.length >= BUSY_FROM) {
    return `<div class="day-stack">${gridChips(upcoming.streams)}<span class="day-label">${escapeHtml(dayLabel(upcoming.days_until, t))}</span></div>`;
  }
  const rows = days.slice(0, MAX_ROWS);
  const small = rows.some((day) => day.streams.length >= ROW_SLOTS);
  return rows
    .map(
      (day) =>
        `<div class="day-row">${rowChips(day.streams, small)}<span class="day-label">${escapeHtml(dayLabel(day.days_until, t))}</span></div>`,
    )
    .join("");
}

function dayColumn(day, locale, slots, t, named) {
  return `<div class="day-col">
    ${bins(day.streams, slots, named)}
    <div class="day-head"><span class="day-label">${escapeHtml(dayLabel(day.days_until, t))}</span><span class="day-date">${escapeHtml(shortDate(day.date, locale))}</span></div>
  </div>`;
}

// client.css sizes the bins from the layout's shape: --bins across a line,
// --lines of them, --cols day columns, --strip rows below.
function mdBody(days, locale, t, named) {
  const cols = `day-cols${named ? "" : " no-names"}`;
  const [upcoming] = days;
  if (upcoming.streams.length > MD_BINS) {
    const used = Math.min(upcoming.streams.length, HERO_SLOTS);
    return `<div class="${cols}" style="--bins:${Math.ceil(used / 2)};--cols:1;--lines:2">${dayColumn(upcoming, locale, HERO_SLOTS, t, named)}</div>`;
  }
  const columns = [{ day: upcoming, slots: MD_BINS }];
  let left = MD_BINS - upcoming.streams.length;
  for (const day of days.slice(1, MD_DAYS)) {
    if (day.streams.length <= left) {
      columns.push({ day, slots: MD_BINS });
      left -= day.streams.length;
      continue;
    }
    if (left >= MD_PARTIAL_MIN) columns.push({ day, slots: left });
    break;
  }
  const across = columns.reduce(
    (sum, { day, slots }) => sum + Math.max(Math.min(day.streams.length, slots), MD_COL_MIN),
    0,
  );
  const html = columns.map(({ day, slots }) => dayColumn(day, locale, slots, t, named)).join("");
  return `<div class="${cols}" style="--bins:${across};--cols:${columns.length};--lines:1">${html}</div>`;
}

function stripRow(day, locale, t, named) {
  const names =
    named && day.streams.length <= STRIP_NAMED_MAX
      ? `<span class="strip-names">${escapeHtml(day.streams.map((stream) => stream.label).join(", "))}</span>`
      : "";
  const when = `${dayLabel(day.days_until, t)} · ${shortWeekday(day.date, locale)}`;
  return `<div class="strip-row">${chips(day.streams, HERO_SLOTS, "")}${names}<span class="strip-when">${escapeHtml(when)}</span></div>`;
}

function lgBody(days, locale, t, named) {
  const [hero, ...later] = days;
  const used = Math.min(hero.streams.length, HERO_SLOTS);
  const lines = used > MD_BINS ? 2 : 1;
  const strip = later.slice(0, STRIP_DAYS);
  const shape = `--bins:${Math.ceil(used / lines)};--lines:${lines};--strip:${strip.length}`;
  return `<div class="hero${named ? "" : " no-names"}" style="${shape}">
    <div class="hero-bins">${bins(hero.streams, HERO_SLOTS, named)}</div>
    <div class="hero-head"><span class="hero-label">${escapeHtml(dayLabel(hero.days_until, t))}</span><span class="hero-date">${escapeHtml(longDate(hero.date, locale))}</span></div>
  </div>${strip.length ? `<div class="strip">${strip.map((day) => stripRow(day, locale, t, named)).join("")}</div>` : ""}`;
}

export default function render(shadow, ctx) {
  const size = SIZES.includes(ctx.cell.size) ? ctx.cell.size : "sm";
  const data = ctx.data;
  const t = words(ctx);
  const named = ctx.cell.options?.show_names !== false;
  let body;
  if (data?.error) body = errorBody(data.error);
  else if (!Array.isArray(data?.days)) body = errorBody(t("load_failed", "Couldn't load bin collections."));
  else if (!data.days.length) body = emptyBody(t);
  else if ((size === "xs" || size === "sm") && ctx.cell.options?.small_cells === "bins") {
    body = nextBody(data.days[0], ctx.cell, ctx.locale, t);
  } else if (size === "xs") body = xsBody(data.days[0], t);
  else if (size === "md") body = mdBody(data.days, ctx.locale, t, named);
  else if (size === "lg") body = lgBody(data.days, ctx.locale, t, named);
  else body = smBody(data.days, t);
  const mono = isMono(shadow, ctx.cell.options);
  shadow.innerHTML = `${STYLESHEETS}
  <div class="w bin-day size-${size}${mono ? " mono" : ""}" data-widget="bin_day">
    ${mono ? PATTERNS : ""}${titleBar(ctx.cell.options, t)}<div class="w-body">${body}</div>
  </div>`;
  watchCellTheme(shadow, ctx);
}
