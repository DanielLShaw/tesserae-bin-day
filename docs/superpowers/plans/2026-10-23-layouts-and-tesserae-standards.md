# Bin Day layouts in Tesserae's standard form: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every Bin Day layout Tesserae's title bar, the owner's top-left order (title bar, bins, days left and date), Tesserae's type sizes and tokens, translatable text, and two new options (title, bin names).

**Architecture:** All layout work is in the display widget: `bin_day/client.js` builds the markup per size, `bin_day/client.css` lays it out with Tesserae tokens, `bin_day/plugin.json` declares the options. Markup order is tested in Node (`tests/js/client.test.js`); geometry, fit and token behaviour in Chromium (`tests/test_widget_browser.py`). Bin Day Core is untouched.

**Tech stack:** vanilla ES module + CSS in a shadow root; Tesserae's `spectra-widgets.css` classes and `--*` tokens; pytest + Playwright; Node's test runner.

**Spec:** `docs/superpowers/specs/2026-10-23-layouts-and-tesserae-standards-design.md`. Read it first; this plan only adds the decisions it leaves open.

## Global constraints

- Owner's rules, from the spec: priority bin colour > days until > bin name > date; always top-aligned (only LG's later-days strip sits at the bottom); left-aligned; follow Tesserae's standards; no alignment options.
- Test first. Watch each new test fail for the stated reason before writing code.
- `uv run pytest` keeps 100% line and branch coverage (gate 95%). `npm test` gates `bin_day/client.js` at 95% lines, 90% branches, 95% functions.
- Everything passes on Tesserae 0.436.1 (`.tesserae/`, the default) and on 0.466.1:
  `TESSERAE_SRC=$SP/tesserae-466 PYTHONPATH=$SP/tesserae-466 uv run pytest --no-cov`,
  where `SP=/private/tmp/claude-504/-Users-dshaw-Documents-GitHub-tesserae-bin-day/76d3f943-9ca4-4d3a-ad44-3fa6919997df/scratchpad`.
- Don't copy code from Tesserae's bundled widgets or Tesserae Studio (AGPL). Linking `spectra-widgets.css` and using its classes is intended.
- The release package holds only `bin_day/` and `bin_day_core/` (`tests/test_release.py`).
- Lint: `uv run ruff check . && uv run ruff format --check . && node --check bin_day/client.js`.
- **Commit only when the owner says.** Each task ends with its changes ready to commit; the commit step is "ask, then commit", as Dan Shaw (repo-local config), message ending `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`.
- Words the widget draws go through `t(key, fallback)` (Task 1) from the moment it exists.

## Review focus

The inputs most likely to bite that no task's main tests cover. Each has its test in the owning task:

1. A cell saved before these options existed (no `show_title`, `title` or `show_names` keys) shows the title bar reading "Bins" and the bin names. Task 2 and Task 5.
2. A title containing markup or quotes (`<b>"Bins" & co</b>`) is shown as text, never as HTML. Task 2.
3. A title that is only spaces counts as empty and shows "Bins". Task 2.
4. A very long title (60 characters) stays on one line, ends in an ellipsis, and nothing in a 205×165 cell overflows. Task 2.
5. The empty and error tiles, with the title bar, fit an XS 180×180 cell, including a 300-character error. Task 3.

---

### Task 0: Commit the work already done (owner's go-ahead)

The uncommitted work the spec builds on: Small cells show Wheelie bins, SM day labels never cut short, and Auto following a theme set on the cell. It passes everything on both Tesserae versions.

- [ ] **Step 1:** Ask the owner whether to commit it as one commit, or split it. Splitting needs partial staging through `git hash-object -w` and `git update-index --cacheinfo`, since interactive staging isn't available.
- [ ] **Step 2:** Commit as agreed. The message lists the three changes and the test totals: 505 pytest cases at 100% coverage, passing on 0.436.1 and 0.466.1, and 71 client tests.

### Task 1: Translatable text

**Files:**
- Create: `bin_day/strings/en.json`
- Modify: `bin_day/plugin.json` (add `"locales": ["en"]`), `bin_day/client.js`
- Test: `tests/js/client.test.js`

**Interfaces:**
- Produces: `words(ctx) -> (key, fallback) => string`, which calls `ctx.t(key, fallback)` when the host provides it, else returns `fallback`. `dayLabel(daysUntil, t = (k, f) => f)` and `xsCount(daysUntil, t = (k, f) => f)` keep their exports and gain the optional `t`.
- `bin_day/strings/en.json`, exactly:
  ```json
  {
    "today": "Today",
    "tomorrow": "Tomorrow",
    "n_days": "{n} days",
    "unit_day": "day",
    "unit_days": "days",
    "nothing_this_week": "Nothing this week",
    "load_failed": "Couldn't load bin collections."
  }
  ```
  Day counts fill `{n}` with `.replace("{n}", String(n))`, Tesserae's convention. Task 2 adds `"title": "Bins"`.

- [ ] **Step 1: Write the failing tests.**
  - `test("every word the widget draws comes from strings/en.json, with the same English")`: render every state (XS, SM, SM busy, small cells with wheelie bins, MD, LG with a strip, Today, Tomorrow, 6 days, empty, missing data, a server error) with a `ctx.t` that records `(key, fallback)`. Assert every recorded key is in `en.json` with `en.json[key] === fallback`, and that every `en.json` key was recorded.
  - `test("a translation replaces the widget's words")`: `ctx.t` backed by `{tomorrow: "Demain", n_days: "{n} jours", unit_day: "jour", unit_days: "jours", nothing_this_week: "Rien cette semaine"}`. SM with TOMORROW and MONDAY includes "Demain" and "6 jours". XS with MONDAY includes `>jours<`. Empty includes "Rien cette semaine".
- [ ] **Step 2:** Run `node --test tests/js/client.test.js`. Expected: both fail. No key is recorded, and the English text comes out unchanged.
- [ ] **Step 3:** Implement `words`, create `en.json`, route the seven words through `t`, and add `locales`.
- [ ] **Step 4:** Run `npm test` and `uv run pytest --no-cov tests/test_manifests.py`. Expected: everything passes, and the manifest still validates on both versions.
- [ ] **Step 5:** Ask the owner, then commit.

### Task 2: Tesserae's title bar, with Title and Show title row

**Files:**
- Modify: `bin_day/plugin.json`, `bin_day/strings/en.json` (`"title": "Bins"`), `bin_day/client.js`
- Test: `tests/js/client.test.js`, `tests/test_manifests.py`, `tests/test_widget_browser.py`

**Interfaces:**
- Consumes: `words(ctx)` (Task 1).
- Produces: `titleBar(options, t) -> string`, empty when `options.show_title === false`. Otherwise exactly
  `<div class="w-title"><i class="ph-bold ph-trash" aria-hidden="true"></i><h3>${escapeHtml(text)}</h3></div>`,
  where `text` is `options.title.trim()` if non-empty, else `t("title", "Bins")`. `render` puts it inside `.w`, before `.w-body`, in every state, including empty and error.
- New options, placed first in `cell_options` in this order:
  - `{"name": "show_title", "type": "boolean", "label": "Show title row", "default": true, "help": "Off hides the title bar: its icon and text."}`
  - `{"name": "title", "type": "string", "label": "Title", "default": "", "help": "The title bar's text. Leave empty for Bins.", "show_if": {"show_title": true}}`

  The default is empty, not "Bins", so the word can be translated. This settles the spec's "Empty means Bins".

- [ ] **Step 1: Write the failing tests.**
  - Node:
    - `"a title bar reading Bins tops every layout by default"`: sizes xs, sm, md, lg and states empty and error, with `options: {}` (review focus 1). The `.w-title` appears before `.w-body` and contains `<h3>Bins</h3>`.
    - `"the title bar shows the Title option's text"`.
    - `"a title is shown as text, never markup"`: `<b>"Bins" & co</b>` gives `&lt;b&gt;&quot;Bins&quot; &amp; co&lt;/b&gt;` (review focus 2).
    - `"a title of only spaces reads Bins"` (review focus 3).
    - `"Show title row off drops the title bar"`.
  - Manifest: `test_title_options_come_first_and_title_shows_only_with_its_row` asserts:
    - the first two option names are `["show_title", "title"]`;
    - `show_title` defaults to `True`;
    - `title` defaults to `""`, with `show_if == {"show_title": True}`.
  - Browser: `test_a_long_title_stays_on_one_line_and_the_cell_still_fits`. At 205×165, with a 60-character title and small cells on wheelie bins: the `h3` is one line high (its height is at most 1.6× its font size), `scrollWidth > clientWidth` (cut short with an ellipsis), and every drawn element is within the cell (review focus 4).
- [ ] **Step 2:** Run the tests. Expected: they fail, with no `.w-title` in the markup and no such options.
- [ ] **Step 3:** Implement `titleBar`, the options and the `en.json` key.
- [ ] **Step 4:** Run `npm test` and `uv run pytest --no-cov tests/test_manifests.py tests/test_widget_browser.py`. Expected: everything passes. Existing fit tests may now fail where the title bar takes space; Task 3 owns those, so it's acceptable only if Task 3 follows straight on. Note any failures.
- [ ] **Step 5:** Ask the owner, then commit.

### Task 3: The owner's order, top and left, in every layout

**Files:**
- Modify: `bin_day/client.js` (`xsBody`, `smBody`, `nextBody`, `dayColumn`, `mdBody`, `lgBody`, `emptyBody`, `errorBody`), `bin_day/client.css`
- Test: `tests/js/client.test.js`, `tests/test_widget_browser.py`

**Interfaces:**
- Consumes: `titleBar` (Task 2).
- Removes: in `nextBody`, the beside or above choice (`HEAD_SHARE`, `BIN_PITCH`, the `beside`/`above` classes, the `.next.beside` and `.next.above` rules, and the Node test "the count goes beside the bins or above them"). The names-drop rule (`NAME_MIN`, `.no-names`) stays.
- Markup order, top to bottom, after the title bar:
  - **XS chips:** chips, then count.
  - **SM rows:** each row is chips, then label, with the label straight after the chips. Narrow cells (4:3 or narrower) stack the label under the chips instead of above them.
  - **SM busy:** chip grid, then label.
  - **Small cells, wheelie bins:** bins, then `.next-head` (count and date).
  - **MD:** each column is bins, then `.day-head`.
  - **LG:** `.hero-bins`, then `.hero-head`; `.strip` stays last.
  - **Empty and error:** the notice.
- CSS:
  - `.bin-day .w-body`: `justify-content: flex-start`.
  - SM rows: `justify-content: flex-start`. The stacked rule uses `flex-direction: column`.
  - `.next-bins` and the notices align to the start, not the centre.
  - LG: the strip takes `margin-top: auto`.
  - Keep the 4:3 aspect rule; the spec leaves it to the builder, and it already works.
  - The short-cell rule that drops the date (`@container (max-height: 130px)`) moves from `.next.above .next-date` to `.next .next-date`.

- [ ] **Step 1: Write the failing tests.**
  - Node: the markup order above, one test per layout, by comparing `indexOf` of the class names. Update the existing MD test that asserts the date comes before the first bin name; it now comes after.
  - Browser `test_every_layout_reads_title_then_bins_then_days_from_the_top_left`, parametrised over these cells:
    - XS 180×180, chips;
    - SM 380×240, chips;
    - SM 380×240, busy day;
    - wheelie bins at 205×165, 180×180 and 380×240;
    - MD 640×400 and LG 1200×800;
    - empty and error at 180×180 and 380×240, including a 300-character error (review focus 5).

    It asserts:
    - the title bar's top and left equal the content box's top and left (the cell's box less `.w`'s computed padding), within 2px;
    - the first bin or chip starts below the title bar, the day text starts at or below the bins' bottom (SM rows instead: the label's left lies beyond the chips' right, by at most 32px), and each block's left equals the title's left within 2px;
    - consecutive blocks are at most 24px apart;
    - LG's strip ends within 2px of the content box's bottom;
    - every drawn element is within the cell.
- [ ] **Step 2:** Run the tests. Expected: they fail on order and centring.
- [ ] **Step 3:** Implement the markup order and the CSS.
- [ ] **Step 4:** Run `npm test` and `uv run pytest --no-cov tests/test_widget_browser.py`. Expected: everything passes, including `test_sm_day_labels_are_never_cut_short`, the small-cell fit tests and the cell-theme tests.
- [ ] **Step 5:** Render `uv run preview/shoot.py -s next-week -s busy-day -s wheelie-small -s wheelie-small-one -s empty -s error -d 205x165` and look at the contact sheet before asking the owner, then commit.

### Task 4: Text sizes from Tesserae's type tokens

**Files:**
- Modify: `bin_day/client.js` (count markup), `bin_day/client.css`
- Test: `tests/test_widget_browser.py`, `tests/js/client.test.js`

**Interfaces:**
- Count markup, used by XS chips and small cells: `<div class="stat-value count">${number}<span class="unit">${unit}</span></div>`. Today drops the unit span and the number, and the word itself is the value: `<div class="stat-value count">Today</div>`. Update the Node tests that look for `count-number` and `count-unit`.
- Text sizes. Every other Bin Day `clamp()` text size goes; the sizes of chips, bins and "+N" stay as they are.

  | Text | Size |
  | --- | --- |
  | XS chips count | `.stat-value` (`--fs-display`), unit 0.4em (the shared rule) |
  | Small cells count | `--fs-value`, unit 0.4em, so it stays under the bins' height |
  | SM day labels (rows and busy) | `--fs-value`; `@container (max-width: 240px)`: `--fs-lead` |
  | MD day labels | `--fs-lead` |
  | MD and small-cell dates | `--fs-label`, `--text-secondary` |
  | Bin names | `--fs-label` |
  | LG hero label | `--fs-display` |
  | LG hero date | `--fs-lead`, `--text-secondary` |
  | LG strip names and when | `--fs-body` |
  | Empty message | `--fs-lead` |
  | Error message | `--fs-body` |
  | Empty and error icon | `--icon-lg` |

- [ ] **Step 1: Write the failing tests** (browser).
  - `test_the_count_follows_the_styles_display_size`: XS 180×180, chips. The `.stat-value` font size with `style=display`, divided by the size with `style=standard`, is 1.3 (3.9em / 3em) within 0.02.
  - `test_dates_and_names_follow_the_styles_label_size`: MD 640×400. With `style=elegant` over `style=standard`, the ratio for `.day-date` and for `.bin-label` is 0.925 (0.74 / 0.8) within 0.02.

  `show()` needs a `style` argument; `/_test/render` takes `&style=`.
- [ ] **Step 2:** Run them. Expected: they fail; the ratios are 1.0, since today's sizes ignore the style.
- [ ] **Step 3:** Implement the table.
- [ ] **Step 4:** Run `npm test` and `uv run pytest --no-cov tests/test_widget_browser.py`. Expected: everything passes, including the small-cell rules that the bins are taller than the count, a single bin fills at least half the cell, and labels are never cut short. If a fit test fails, change spacing first; change a token only if spacing can't fix it, and say so.
- [ ] **Step 5:** Ask the owner, then commit.

### Task 5: Show bin names

**Files:**
- Modify: `bin_day/plugin.json`, `bin_day/client.js` (`bin`, `bins`, `stripRow`, `nextBody`), `bin_day/client.css`
- Test: `tests/js/client.test.js`, `tests/test_manifests.py`, `tests/test_widget_browser.py`

**Interfaces:**
- The option, after `small_cells`: `{"name": "show_names", "type": "boolean", "label": "Show bin names", "default": true, "help": "Off hides the names under wheelie bins, and in LG's list of later days. The bins grow into the space."}`.
- `bins(streams, slots, named = true)` and `bin(stream, named)`: with `named` false there is no `.bin-label` span, but the bin's `aria-label` keeps the name. In small cells, `named` is `options.show_names !== false && <the existing NAME_MIN rule>`. LG strip rows drop `.strip-names` when names are off.
- CSS: when there are no names, bins size without the name's height. Generalise the existing `.next.no-names` rule to a `.no-names` class on `.w`.

- [ ] **Step 1: Write the failing tests.**
  - Node:
    - `"Show bin names off drops every name but keeps each bin's label for screen readers"`: md, lg (hero and strip), xs with wheelie bins. There is no `bin-label` or `strip-names`, and `aria-label="Refuse"` is still present.
    - `"names show when the option was never set"` (review focus 1).
  - Manifest: `show_names` defaults to `True` and follows `small_cells`.
  - Browser: `test_bins_grow_when_names_are_hidden`. At MD 640×400, the first bin is taller with `show_names=false` than without it.
- [ ] **Step 2:** Run them. Expected: they fail.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run `npm test` and `uv run pytest --no-cov tests/test_manifests.py tests/test_widget_browser.py`. Expected: everything passes.
- [ ] **Step 5:** Ask the owner, then commit.

### Task 6: Theme inks, stroke tokens, breakpoints and style-driven dividers

**Files:**
- Modify: `bin_day/client.css`
- Test: `tests/test_widget_browser.py`

**Interfaces:**
- `--mono-ink: var(--text-primary); --mono-paper: var(--surface);`. Remove both `#000000` and `#ffffff` and their `identity` comments.
- Every fixed `2px`, `stroke-width: 2` and `0 0 0 2px` becomes `var(--stroke-1)`. The chip outline becomes `max(var(--stroke-1), calc(var(--chip) * 0.05))`.
- `@container (max-width: 280px)` becomes `360px`.
- `.day-col + .day-col` takes `border-left: var(--row-rule-w, 0px) solid var(--text-muted)`, and `.strip` takes `border-top` the same way. Keep their padding, so spacing still separates them.

- [ ] **Step 1: Write the failing tests** (browser).
  - `test_black_and_white_inks_come_from_the_theme`: MD 640×400, `colours=mono`, `theme=dark`. The computed `fill` of a solid bin's `.body` equals `.w`'s computed `color` (its `--text-primary`), and a white bin's body equals `.w`'s background colour.
  - `test_dividers_follow_the_style`: MD with two day columns, and LG with a strip. The second column's `border-left-width` and the strip's `border-top-width` are `0px` with `style=standard`, `2px` with `style=mono` and `4px` with `style=destijl`.
  - `test_narrow_notices_stack_their_icon_above_the_text`: at 300×200 with nothing this week, the icon's bottom is at or above the text's top.
- [ ] **Step 2:** Run them. Expected: they fail. The fill is black on the dark theme, the dividers are always 2px, and a 300px-wide notice sits side by side.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run `uv run pytest --no-cov tests/test_widget_browser.py tests/test_preview_scenarios.py` and `npm test`. Expected: everything passes.
- [ ] **Step 5:** Ask the owner, then commit.

### Task 7: Docs, pictures and the checks the spec calls "done"

**Files:**
- Modify: `README.md` (cell options table: add Show title row, Title, Show bin names; the option count in "It has … options"), `docs/development.md` (the test table rows for `test_widget_browser.py` and `client.test.js`), `preview/scenarios.py`, `docs/images/*`
- Test: `tests/test_preview_scenarios.py`

**Interfaces:**
- `Scenario` gains `show_title: bool = True`, `title: str = ""` and `show_names: bool = True`, and `options` passes them through. Add a scenario `no-names` (the `solid-bins` bins with `show_names=False`), and one `custom-title` (`title="Bin day"`).

- [ ] **Step 1:** Add the scenarios, then run `uv run pytest --no-cov tests/test_preview_scenarios.py`. Expected: everything passes.
- [ ] **Step 2:** Run `uv run preview/shoot.py --docs` and check that every changed image shows the title bar and the new order. Update the README text and alt text where the pictures changed.
- [ ] **Step 3:** Verify:
  - `uv run pytest` passes at 100% coverage;
  - the 0.466.1 run passes;
  - `npm test` and lint pass;
  - `uv run --with jsonschema python -I $SP/lint_bin_day.py $SP/studio/server $PWD $SP/tesserae-466/schema/plugin.schema.json` reports no errors for `bin_day`;
  - `uv run --with pillow python $SP/matrix_shots.py $PWD $SP/matrix`, run with the 0.466.1 environment variables: in its sheets, the title bar shows each style's decoration and nothing overflows.
- [ ] **Step 4:** Render the contact sheet at 205×165 and each standard size for the owner, and show it to them.
- [ ] **Step 5:** Ask the owner, then commit.
