# Developing Bin Day

How to set up a development copy of Bin Day, run its tests, try it in a
local Tesserae, and render its screenshots. For installing and using the
widget, see the [README](../README.md).

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (installs Python 3.12 and the dev tools for you)
- Node.js 22.8 or newer, for the client tests (no npm packages needed)
- git

## Setup

The integration tests and the screenshot tool run the plugins inside a real
Tesserae app, so clone the pinned Tesserae release into `.tesserae/`
(gitignored), then install everything:

```sh
git clone --depth 1 --branch v0.436.1 https://github.com/dmellok/tesserae .tesserae
uv sync
```

`uv sync` installs pytest, ruff and the Tesserae checkout (editable) with its
dependencies into `.venv/`. To test against a different checkout, set
`TESSERAE_SRC=/path/to/tesserae`.

## Running the tests

### Everything

```sh
uv run pytest     # Python: unit + integration tests, with branch coverage
npm test          # client.js tests, with coverage
```

`uv run pytest` fails if branch coverage of `bin_day/` and `bin_day_core/`
drops below 95%, and prints a missing-lines report. The admin page's browser
tests drive headless Chromium through Playwright and skip, saying how to
install it, when none is found (see [Screenshots](#screenshots) for the
fallback to an installed build). `npm test` runs Node's
built-in test runner over `tests/js/` and fails below 95% line, 90% branch
or 95% function coverage of `bin_day/client.js`.

### Narrower runs

```sh
uv run pytest tests/test_resolve.py          # one file
uv run pytest -k cutoff                      # tests whose name matches
uv run pytest --no-cov -x                    # no coverage gate, stop at first failure
node --test tests/js/client.test.js          # client tests without coverage
```

Run a subset with `--no-cov`, or the coverage gate fails on the code that
subset doesn't reach.

### Without a Tesserae checkout

The pure-logic tests need nothing but Python:

```sh
uv run --frozen --no-group host pytest --no-cov
```

The integration tests skip with a message pointing here.

### Lint

```sh
uv run ruff check . && uv run ruff format --check .
node --check bin_day/client.js bin_day_core/static/admin.js
```

### What the tests cover

| Tests | Covers |
| --- | --- |
| `test_resolve.py` | Event title to icon and colours: user mappings, colour words, lid colours ("blue lid"), material keywords, fallback; Liverpool and Stockport titles; hiding a title |
| `test_schedule.py` | Fixed-rule dates: 1 to 8 weekly cycles and their phase, future start, year boundary, clock changes |
| `test_collections.py` | The 0 to 7 day window, the cutoff time, same-day merge, de-duplication, the `next_change_at` refresh hint |
| `test_palette.py` | Colour names to hex, a black or white icon that contrasts with each bin and chip fill, and each bin's black-and-white fill |
| `test_config.py` | Parsing and validating the admin form: source, calendar, bins, custom icons and colours, hidden rows |
| `test_payload.py` | The data a cell receives from `fetch()` |
| `test_calendar.py` | Home Assistant events to dates (all-day and timed, across clock changes), the query range, cache freshness |
| `test_ha_source.py` | The calendar source end to end against a fake Home Assistant: the calendar chosen in Core, query, renamed calendar, not connected, the 1-hour cache and 24-hour fallback |
| `test_plugins_load.py`, `test_manifests.py` | Both plugins load in Tesserae, validate against its schema, offer the cutoff and colour options and a daily refresh |
| `test_widget.py` | `fetch()` end to end, including every error tile |
| `test_admin.py`, `test_core_server.py` | The admin page (source, bins, a calendar's bin names, saving and its errors), config storage, timezone and plugin reload |
| `test_admin_browser.py` | The admin page in headless Chromium: switching source, adding, removing and hiding rows, the custom icon and colour fields, listing a newly chosen calendar's bins |
| `test_preview_scenarios.py` | Each screenshot scenario shows what it is named for; the docs have each docs scenario's images |
| `test_release.py` | Every root folder other than the two plugins is left out of the release tarball |
| `tests/js/client.test.js` | Day labels, chip overflow, XS/SM/empty/error layouts, HTML and CSS escaping |

### How the integration tests work

`tests/conftest.py` creates a Tesserae app in testing mode with a throwaway
data folder per test, and symlinks `bin_day/` and `bin_day_core/` into it as
pushed widgets, the same way a developer push installs them. Tests render a
cell through Tesserae's `/_test/render` route and read back the JSON that
`fetch()` handed it. The clock is pinned by patching `_now()` on the
`bin_day_core` server module, so date-dependent results are fixed.

The Home Assistant tests run a small fake Home Assistant HTTP server (the
`FakeHA` class in `tests/conftest.py`) on a local port and point the bundled
Home Assistant Core plugin at it, so the real request code, auth header and
Tesserae's network permission checks all run. It answers like Home Assistant
does, including a 400 for an unknown calendar, and can be told to fail or
stop.

## Trying it by hand

```sh
uv run preview/serve.py      # then open http://127.0.0.1:8765/
```

Runs Tesserae's own dev server from `.tesserae/` with both plugins linked in,
listening on this machine only, with reload on. Everything it stores (the
admin password it asks for on first visit, your bins, a Home Assistant URL
and token) lives in `.devdata/` (gitignored); delete that folder to start over.

- Where the bins come from and how each looks: Widgets menu, Admin pages,
  Bin Day Core.
- Home Assistant calendars: Settings, Widgets, Home Assistant Core, then your
  HA URL and a long-lived access token (HA: your profile, Security).
- Every size at once, with a form for the cell options:
  <http://127.0.0.1:8765/_test/preview?plugin=bin_day>

## Screenshots

```sh
uv run preview/shoot.py
```

Renders the widget in every scenario in `preview/scenarios.py` at every size
(xs 180×180, sm 380×240, md 640×400, lg 1200×800) and writes:

```
screenshots/                 gitignored, always the latest run
  index.html                 contact sheet: one row per scenario
  next-week/xs.png ... lg.png
  dark-mode/  eink-colours/
  today/  after-cutoff/  colour-names/  busy-day/  busy-second-day/
  overflow/  overflow-second-day/  black-and-white/  palette-dark/  palette-light/
  solid-bins/  solid-bins-dark/  solid-bins-mono/  lid-colours/  lid-colours-mono/
  mixed-bins/  set-by-hand/  empty/  error/
```

Open `screenshots/index.html` to compare everything at once. Options, all
repeatable:

```sh
uv run preview/shoot.py -s today -s empty     # only these scenarios
uv run preview/shoot.py -z xs -z sm           # only these sizes
uv run preview/shoot.py -t dark -t paper      # other themes, saved as <size>-<theme>.png
uv run preview/shoot.py --e6                  # also <size>-e6.png: as a Spectra 6 panel prints it
uv run preview/shoot.py -d 400x240 -d 800x480 # cells of any size, saved as <W>x<H>.png
```

A `-d` cell gets the size class Tesserae would give it on a panel (from its
longer side), so `-d 400x240` shows what a quarter of the E1002's 800x480
screen looks like.

`--e6` runs each shot through Tesserae's own quantiser, dithering it to the
six Spectra 6 inks as the reTerminal E1002's packer does, and draws each ink
in its measured colour: a preview of the printed panel. The `palette-dark`
and `palette-light` scenarios lay out every bin colour for checking this.

A full run replaces the folder; a narrower run updates only the shots it
takes. Each scenario has its own bins and pinned clock; to add
one, add a `Scenario` to `preview/scenarios.py` with the days and icons it
should show, which `test_preview_scenarios.py` checks.

`uv run preview/shoot.py --docs` renders each scenario at the sizes in its
`docs` field into `docs/images/`, the images in the README and
[bin-colours.md](bin-colours.md). Unlike `screenshots/`, these are
committed; render them again when a change alters how those bins look.

The tool drives Chromium through Playwright. If Playwright's matching
Chromium build is missing it falls back to the newest one installed and
says so; install the matching build with
`uv run playwright install chromium --only-shell`, or point
`BIN_DAY_CHROMIUM` at a Chromium binary.

## Repository layout

```
bin_day/              display widget (plugin.json, server.py, client.js, client.css)
bin_day_core/         admin + data plugin
  bin_logic/          pure logic, no Tesserae imports; server.py loads it by path
  templates/          admin page
  static/             admin page script and styles
tests/                pytest suites; tests/js/ for client.js
preview/              screenshot scenarios and tool, local dev server
docs/                 bin colours and this guide, with example images
```

`tests/`, `preview/`, `docs/` and `.github/` are export-ignored, so the release tarball
holds only the plugin folders and root files.
