// Bin Day: which bins are collected in the next 7 days, from bin_day_core's
// payload (ctx.data = {days: [{date, days_until, streams}], next_change_at}).
//
// Layout follows ctx.cell.size:
//   xs      the next collection day: its bins as chips, a big day count
//   sm      one row per collection day (at most two): chips, then the day label.
//           A row has ROW_SLOTS chips, the last becoming "+N" if more. When the
//           upcoming day has BUSY_FROM or more bins it gets the whole cell
//           instead: its label above a grid of up to GRID_SLOTS chips.
//   md, lg  the sm layouts for now; bin-shape layouts come in milestone 5
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

function chip(stream) {
  const icon = ICON_NAME.test(stream.icon ?? "")
    ? `<i class="ph-bold ph-${stream.icon}" aria-hidden="true"></i>`
    : "";
  const colours = `--body:${safeColour(stream.body_colour)};--ink:${safeColour(stream.icon_colour)}`;
  return `<span class="chip" role="img" aria-label="${escapeHtml(stream.label)}" style="${colours}">${icon}</span>`;
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

export default function render(shadow, ctx) {
  const size = SIZES.includes(ctx.cell.size) ? ctx.cell.size : "sm";
  const data = ctx.data;
  let body;
  if (data?.error) body = errorBody(data.error);
  else if (!Array.isArray(data?.days)) body = errorBody("Couldn't load bin collections.");
  else if (!data.days.length) body = emptyBody();
  else if (size === "xs") body = xsBody(data.days[0]);
  else body = smBody(data.days);
  shadow.innerHTML = `${STYLESHEETS}
  <div class="w bin-day size-${size}" data-widget="bin_day">
    <div class="w-body">${body}</div>
  </div>`;
}
