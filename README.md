# Bin Day for Tesserae

A [Tesserae](https://github.com/dmellok/tesserae) widget showing which bins are
collected in the next 7 days and how many days until each collection. It
reads a fixed-rule schedule you enter (first collection date, repeat every
N weeks) or a Home Assistant calendar, such as the one the
[Waste Collection Schedule](https://github.com/mampfes/hacs_waste_collection_schedule)
integration creates, through Tesserae's bundled Home Assistant Core plugin.

The repo ships two plugin folders, installed together:

| Folder | Kind | What it does |
| --- | --- | --- |
| `bin_day_core/` | data | Admin page for bin schedules and title mappings; builds each cell's data. No cell of its own. |
| `bin_day/` | widget | The placeable cell: XS, SM, MD and LG layouts plus an empty state. |

Status: in development, not yet in the catalog. Install and setup
instructions for users come with the first release.

## Development

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (installs Python 3.12 and the dev tools for you)
- Node.js 22.8 or newer, for the client tests (no npm packages needed)
- git

### Setup

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
drops below 95%, and prints a missing-lines report. `npm test` runs Node's
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
node --check bin_day/client.js
```

### What the tests cover

| Tests | Covers |
| --- | --- |
| `test_resolve.py` | Event title to icon and colours: user mappings, colour words, material keywords, fallback; Liverpool and Stockport titles; hiding a title |
| `test_schedule.py` | Fixed-rule dates: 1 to 8 weekly cycles and their phase, future start, year boundary, clock changes |
| `test_collections.py` | The 0 to 7 day window, the cutoff time, same-day merge, de-duplication, the `next_change_at` refresh hint |
| `test_palette.py` | Colour names to hex, a black or white icon that contrasts with each fill, and each bin's black-and-white fill |
| `test_config.py` | Parsing and validating the admin form |
| `test_payload.py` | The data a cell receives from `fetch()` |
| `test_calendar.py` | Home Assistant events to dates (all-day and timed, across clock changes), the query range, cache freshness |
| `test_ha_source.py` | The calendar source end to end against a fake Home Assistant: dropdown, query, renamed calendar, not connected, the 1-hour cache and 24-hour fallback |
| `test_plugins_load.py`, `test_manifests.py` | Both plugins load in Tesserae, validate against its schema, offer the source dropdown and daily refresh |
| `test_widget.py` | `fetch()` and `choices()` end to end, including every error tile |
| `test_admin.py`, `test_core_server.py` | The admin page, config storage, timezone and plugin reload |
| `test_preview_scenarios.py` | Each screenshot scenario shows what it is named for |
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
admin password it asks for on first visit, schedules, a Home Assistant URL
and token) lives in `.devdata/` (gitignored); delete that folder to start over.

- Schedules and title mappings: Plugins, Bin Day Core.
- Home Assistant calendars: Settings, Plugins, Home Assistant Core, then your
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
  today/  after-cutoff/  colour-names/  busy-day/  busy-second-day/
  overflow/  overflow-second-day/  black-and-white/  palette-dark/  palette-light/
  empty/  error/
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
takes. Each scenario has its own schedule, mappings and pinned clock; to add
one, add a `Scenario` to `preview/scenarios.py` with the days and icons it
should show, which `test_preview_scenarios.py` checks.

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
tests/                pytest suites; tests/js/ for client.js
preview/              screenshot scenarios and tool, local dev server
```

`tests/`, `preview/` and `.github/` are export-ignored, so the release tarball
holds only the plugin folders and root files.

## Licence

MIT, see [LICENSE](LICENSE).
