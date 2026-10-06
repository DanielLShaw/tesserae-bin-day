// Bin Day: which bins are collected in the next 7 days, from bin_day_core's
// payload (ctx.data = {days: [{date, days_until, streams}], next_change_at}).
//
// Layout follows ctx.cell.size:
//   xs      the next collection day: its bins as chips, a big day count
//   sm      one row per collection day (at most two): chips, then the day label.
//           A row has ROW_SLOTS chips, the last becoming "+N" if more. When the
//           upcoming day has BUSY_FROM or more bins it gets the whole cell
//           instead: its label above a grid of up to GRID_SLOTS chips.
//   md      one column per collection day (up to MD_DAYS, MD_BINS bins in
//           all): count and short date, then a wheelie bin per collection with
//           its name. A later day that doesn't fit gets the slots left, ending
//           "+N". A busier upcoming day fills md alone.
//   lg      the upcoming day as hero (big count, full date, large named bins),
//           later days as a strip below: a chip for every bin, then names
//           (only for a few bins, and they give way first), then when
// Bins and chips show up to their slot count, the last slot becoming "+N".
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
const HEX_COLOUR = /^#[0-9a-f]{6}$/i;
const ICON_NAME = /^[a-z0-9-]+$/;
const ENTITIES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

const escapeHtml = (text) => String(text).replace(/[&<>"']/g, (c) => ENTITIES[c]);
const safeColour = (value) => (HEX_COLOUR.test(value) ? value : "var(--surface-sunken)");

export function dayLabel(daysUntil) {
  if (daysUntil === 0) return "Today";
  if (daysUntil === 1) return "Tomorrow";
  return `${daysUntil} days`;
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

export function xsCount(daysUntil) {
  if (daysUntil === 0) return { number: "", unit: "Today" };
  return { number: String(daysUntil), unit: daysUntil === 1 ? "day" : "days" };
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

function chip(stream) {
  const colours = `--body:${safeColour(stream.body_colour)};--ink:${safeColour(stream.icon_colour)}`;
  return `<span class="chip" role="img" aria-label="${escapeHtml(stream.label)}" style="${colours}">${iconHtml(stream)}</span>`;
}

// The mockup's wheelie bin: handle and lid in the lid colour, the body in the
// body colour, the icon centred on the body by client.css.
const BIN_SVG = `<svg viewBox="0 0 60 80" aria-hidden="true">
  <rect class="handle" x="22" y="1" width="16" height="5" rx="1.5"/>
  <rect class="lid" x="3" y="7" width="54" height="9" rx="2"/>
  <path class="body" d="M7 18h46l-4 54H11z"/>
  <circle class="wheel" cx="47" cy="73" r="6"/>
</svg>`;

function bin(stream) {
  const colours = [
    `--body:${safeColour(stream.body_colour)}`,
    `--lid:${safeColour(stream.lid_colour)}`,
    `--ink:${safeColour(stream.icon_colour)}`,
  ].join(";");
  const name = escapeHtml(stream.label);
  return `<span class="bin-item"><span class="bin" role="img" aria-label="${name}" style="${colours}">${BIN_SVG}${iconHtml(stream)}</span><span class="bin-label">${name}</span></span>`;
}

function bins(streams, slots) {
  const { shown, extra } = visibleChips(streams, slots);
  const more = extra ? `<span class="more">+${extra}</span>` : "";
  return `<div class="bins">${shown.map(bin).join("")}${more}</div>`;
}

function chips(streams, slots, layout, style = "") {
  const { shown, extra } = visibleChips(streams, slots);
  const more = extra ? `<span class="more">+${extra}</span>` : "";
  return `<div class="chips${layout}"${style}>${shown.map(chip).join("")}${more}</div>`;
}

// Chips shrink when a row is full; ``small`` covers every row in the cell so
// the rows keep matching sizes.
const rowChips = (streams, small) => chips(streams, ROW_SLOTS, small ? " many" : "");

// The busy grid passes its shape to client.css, so a single line of chips
// can grow to use the height a second line would have taken.
function gridChips(streams) {
  const used = Math.min(streams.length, GRID_SLOTS);
  const shape = ` style="--per-line:${Math.min(used, GRID_PER_LINE)};--lines:${Math.ceil(used / GRID_PER_LINE)}"`;
  return chips(streams, GRID_SLOTS, " grid", shape);
}

function errorBody(message) {
  return `<div class="notice is-error">
    <i class="ph-bold ph-warning-circle" aria-hidden="true"></i>
    <p class="u-muted">${escapeHtml(message)}</p>
  </div>`;
}

function emptyBody() {
  return `<div class="notice">
    <i class="ph-bold ph-calendar-check" aria-hidden="true"></i>
    <p>Nothing this week</p>
  </div>`;
}

function xsBody(day) {
  const { number, unit } = xsCount(day.days_until);
  const big = number ? `<span class="count-number">${escapeHtml(number)}</span>` : "";
  return `${rowChips(day.streams, day.streams.length >= ROW_SLOTS)}<div class="count">${big}<span class="count-unit">${unit}</span></div>`;
}

function smBody(days) {
  const [upcoming] = days;
  if (upcoming.streams.length >= BUSY_FROM) {
    return `<div class="day-stack"><span class="day-label">${escapeHtml(dayLabel(upcoming.days_until))}</span>${gridChips(upcoming.streams)}</div>`;
  }
  const rows = days.slice(0, MAX_ROWS);
  const small = rows.some((day) => day.streams.length >= ROW_SLOTS);
  return rows
    .map(
      (day) =>
        `<div class="day-row">${rowChips(day.streams, small)}<span class="day-label">${escapeHtml(dayLabel(day.days_until))}</span></div>`,
    )
    .join("");
}

function dayColumn(day, locale, slots) {
  return `<div class="day-col">
    <div class="day-head"><span class="day-label">${escapeHtml(dayLabel(day.days_until))}</span><span class="day-date">${escapeHtml(shortDate(day.date, locale))}</span></div>
    ${bins(day.streams, slots)}
  </div>`;
}

// client.css sizes the bins from the layout's shape: --bins across a line,
// --lines of them, --cols day columns, --strip rows below.
function mdBody(days, locale) {
  const [upcoming] = days;
  if (upcoming.streams.length > MD_BINS) {
    const used = Math.min(upcoming.streams.length, HERO_SLOTS);
    return `<div class="day-cols" style="--bins:${Math.ceil(used / 2)};--cols:1;--lines:2">${dayColumn(upcoming, locale, HERO_SLOTS)}</div>`;
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
  const html = columns.map(({ day, slots }) => dayColumn(day, locale, slots)).join("");
  return `<div class="day-cols" style="--bins:${across};--cols:${columns.length};--lines:1">${html}</div>`;
}

function stripRow(day, locale) {
  const names =
    day.streams.length <= STRIP_NAMED_MAX
      ? `<span class="strip-names">${escapeHtml(day.streams.map((stream) => stream.label).join(", "))}</span>`
      : "";
  const when = `${dayLabel(day.days_until)} · ${shortWeekday(day.date, locale)}`;
  return `<div class="strip-row">${chips(day.streams, HERO_SLOTS, "")}${names}<span class="strip-when">${escapeHtml(when)}</span></div>`;
}

function lgBody(days, locale) {
  const [hero, ...later] = days;
  const used = Math.min(hero.streams.length, HERO_SLOTS);
  const lines = used > MD_BINS ? 2 : 1;
  const strip = later.slice(0, STRIP_DAYS);
  const shape = `--bins:${Math.ceil(used / lines)};--lines:${lines};--strip:${strip.length}`;
  return `<div class="hero" style="${shape}">
    <div class="hero-head"><span class="hero-label">${escapeHtml(dayLabel(hero.days_until))}</span><span class="hero-date">${escapeHtml(longDate(hero.date, locale))}</span></div>
    <div class="hero-bins">${bins(hero.streams, HERO_SLOTS)}</div>
  </div>${strip.length ? `<div class="strip">${strip.map((day) => stripRow(day, locale)).join("")}</div>` : ""}`;
}

export default function render(shadow, ctx) {
  const size = SIZES.includes(ctx.cell.size) ? ctx.cell.size : "sm";
  const data = ctx.data;
  let body;
  if (data?.error) body = errorBody(data.error);
  else if (!Array.isArray(data?.days)) body = errorBody("Couldn't load bin collections.");
  else if (!data.days.length) body = emptyBody();
  else if (size === "xs") body = xsBody(data.days[0]);
  else if (size === "md") body = mdBody(data.days, ctx.locale);
  else if (size === "lg") body = lgBody(data.days, ctx.locale);
  else body = smBody(data.days);
  shadow.innerHTML = `${STYLESHEETS}
  <div class="w bin-day size-${size}" data-widget="bin_day">
    <div class="w-body">${body}</div>
  </div>`;
}
