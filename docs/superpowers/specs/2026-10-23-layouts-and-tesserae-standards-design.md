# Bin Day layouts in Tesserae's standard form

23 October 2026. Agreed with the owner in conversation. This replaces an
earlier idea of per-cell title and bin alignment options, which the owner
dropped in favour of the fixed rules below.

## Why

Bin Day sits on the owner's reTerminal E1002 dashboard (800×480, Spectra 6
colour e-ink) beside Tesserae's bundled widgets. Every one of those has
Tesserae's standard title bar and type sizes. Bin Day has neither, so the
decorations styles add to title bars (Display's rule, Mono's and Bauhaus's
marker) never show on it, and its text doesn't scale like its neighbours'.
The owner reads Bin Day in a small corner cell (about 205×165) from across a
kitchen.

Bin Day is about to go to the Tesserae community catalog for review.
Reviewers judge widgets against Tesserae's own standards, so Bin Day should
follow them wherever they apply:

- `docs/widget-design-system.md` (the cross-widget rulebook)
- `docs/widgets.md` (the widget authoring contract)
- `static/style/spectra-widgets.css` and `spectra-tokens.css` (the classes
  and tokens those documents describe)

All are in the Tesserae checkout (`.tesserae/`, or a newer release).

## Starting point

`main` has uncommitted work that passes every test on Tesserae 0.436.1 and
0.466.1 (505 pytest cases at 100% line and branch coverage, 71 client tests).
Build on it rather than starting again:

- **Small cells show** cell option (`small_cells`: `chips` or `bins`) and the
  small-cell wheelie layout (`nextBody` in `bin_day/client.js`, the `.next`
  rules in `client.css`). It currently puts the count beside or above the
  bins, whichever leaves them bigger; that choice goes (see below).
- SM day labels are never cut short: chips narrow instead.
- Auto colours re-draw when the dashboard editor sets a theme on the cell
  (`watchCellTheme`).
- `tests/test_widget_browser.py` renders the widget in Chromium at real cell
  sizes and checks fit, overlap and size; `preview/scenarios.py` has
  `wheelie-small`, `wheelie-small-one` and `wheelie-small-busy`.

## The owner's rules

1. **Priority, highest first:** bin colour, days until the collection, bin
   type (its name), collection date. When space is short, drop or shrink in
   reverse order. The bins' colour always shows.
2. **Always top-aligned.** From the top: the title bar, then the bins (with
   their names), then the days left and the date. Spare space falls at the
   bottom.
   **One exception:** LG's strip of later days stays at the bottom of the
   cell.
3. **Follow Tesserae's standards** wherever they apply.
4. **No alignment options.**
5. **Left-aligned.** Everything lines up on the left under the title bar, as
   in Tesserae's own widgets. Nothing is centred or pushed to the right edge.

## Layouts

Every layout starts with the title bar when it is shown.

- **XS, chips:** the next collection's chips, then its count ("1 day") under
  them.
- **SM, chips:** up to two rows, each the day's chips then its label
  ("Tomorrow") straight after them (no longer at the right edge), the rows
  together at the top. Where today's narrow
  cells stack a row's label above its chips, the chips now come first and the
  label under them. A busy day (four or more bins): the chip grid, then the
  label under it.
- **XS and SM with Small cells show on Wheelie bins:** the next collection's
  bins with their names, then the count and short date under them, on the left
  rather than centred as now. The count no longer goes beside the bins. When a cell is short the date goes first,
  then the names (unless hidden anyway), and the count shrinks before the
  bins do. The count is never taller than the bins.
- **MD:** a column per collection day, as now, each with its bins and names,
  then the day label and short date under them.
- **LG:** the upcoming day's bins large, with names, then the day label and
  full date under them. The strip of later days stays at the bottom.
- **Nothing this week, and error tiles:** after the title bar, at the top and
  on the left like everything else, rather than centred as now (from rules 2
  and 5).

## Cell options

Added to `bin_day/plugin.json`, beside the existing Collection done by,
Colours and Small cells show:

| Option | Type | Default | Behaviour |
| --- | --- | --- | --- |
| Show title row | boolean | on | Off drops the title bar in every layout. |
| Title | string | "Bins" | The title bar's text. Shown in the editor only while Show title row is on (`show_if`). Empty means "Bins". |
| Show bin names | boolean | on | Off hides the names under wheelie bins in every layout, and the names in LG's strip. The bins grow into the space. |

Cells saved before these existed have none of the keys, and must behave as
the defaults. The title bar's icon is `ph-trash`, the widget's own icon; it
has no right-hand meta.

## Tesserae standards to follow

1. **Title bar** (`widget-design-system.md` §4): the shared `.w-title`
   element with `<i class="ph-bold ph-trash">` and an `<h3>`. The shared
   stylesheet keeps it the same size at any cell zoom and cases it from
   `--label-transform`; don't override either.
2. **Type sizes** (§3, `spectra-tokens.css`): text sizes come from the `--fs-*`
   tokens, which are relative to the widget's base size, not from Bin Day's
   own `clamp()` values. The count follows the shared big-number pattern:
   `.stat-value` (`--fs-display`) with the unit in `.unit` (0.4em, secondary
   colour), so "4" is large and "days" smaller. Day labels, dates and names
   take the nearest tokens. Bins and chips are shapes, not text, and keep
   sizing to the space they have; the icons inside them scale with them.
3. **Black and white** (§10): the ink and paper come from the theme
   (`--text-primary` and the background or surface token), not fixed
   `#000000` and `#ffffff`. Paper and Newsprint look the same as now; forcing
   Black & white on a dark theme follows that theme. Real bin colours stay as
   they are (the manifest declares `design.palette: "extended"`).
4. **Stroke widths** (§10): `--stroke-1` and its siblings instead of fixed
   `2px` and `stroke-width: 2`.
5. **Icons** (§8): bold weight only (already). Title-bar and notice icons take
   the `--icon-*` sizes. Icons inside bins and chips keep scaling with their
   shape, since they are part of the drawing.
6. **Breakpoints** (§9): width-based rules use the shared compact (360px) and
   tiny (240px) container widths. Bin Day's own `280px` rule moves to one of
   them.
7. **Translatable text** (`widgets.md`, Locales & strings): add
   `"locales": ["en"]` and `bin_day/strings/en.json`, and draw the widget's
   own words through `ctx.t(key, fallback)`: Today, Tomorrow, the day counts,
   the units, Nothing this week, Couldn't load bin collections, and the default
   title. Dates already use `Intl` with `ctx.locale`.
8. **Options that only apply sometimes** (`widgets.md`, `show_if`): Title
   shows only while Show title row is on. Hosts older than 0.452 ignore
   `show_if` and show every field, which is fine.
9. **Shared classes** (`widgets.md`, Shared baseline): use the shared ones
   where they fit (`.stat-value`, `.unit`, `.u-muted`, `.u-label`) rather than
   look-alikes.
10. **No internal borders** (`spectra-widgets.css` header; `widgets.md`, E-ink
    considerations): MD's lines between day columns and LG's line above the
    strip take their width from `--row-rule-w`, which is 0 in the Standard
    style and 2 to 4px in styles that draw rules. So on Standard they
    disappear, and spacing separates the days instead (writer's call, from
    rule 3).

## Non-goals

- Splitting the widget into separately placeable parts for canvas dashboards
  (`fragments`, `data_schema`). Only 10 and 13 of Tesserae's 44 bundled widgets
  do. This can be separate work later.
- `requires:` stays out of the manifest, as decided at the start of the
  project; the catalog PR explains why.
- Translating Bin Day Core's admin page, or the error messages Bin Day Core
  sends. They stay in English.
- Smoke tests inside the plugin folders. Tests stay at the repo root, left out
  of the release package.

## Anti-goals

- In small cells, a count bigger than the bins.
- Changing a bin's real colours to follow the theme.
- Day labels cut short (`test_sm_day_labels_are_never_cut_short` stays).
- Saved cells changing in ways their owners didn't ask for, beyond gaining the
  title bar and the new order.

## Constraints

- Test first: watch each test fail before writing the code that passes it.
  `uv run pytest` must keep 100% line and branch coverage of `bin_day/` and
  `bin_day_core/` (the gate is 95%); `npm test` gates client.js at 95% lines,
  90% branches and 95% functions.
- Layout behaviour (order, top alignment, what fits, what drops) is tested in
  `tests/test_widget_browser.py`, in a real browser at real cell sizes,
  including about 205×165 and the standard XS, SM, MD and LG sizes.
- Everything passes on Tesserae 0.436.1 (pinned in `.tesserae/`) and 0.466.1.
- Don't copy code from Tesserae's bundled widgets or Tesserae Studio
  (AGPL; Bin Day is MIT). Linking `spectra-widgets.css` and using its classes
  is how Tesserae intends widgets to share them.
- The release package must still hold only `bin_day/` and `bin_day_core/`
  (`tests/test_release.py`).
- Update the README's cell options table and pictures
  (`uv run preview/shoot.py --docs`) and the test table in
  `docs/development.md`.
- Commit only when the owner says.

## Left to the builder

- Which `--fs-*` token each text role takes, and spacing tokens.
- How the shared stat classes and Bin Day's own classes combine.
- Whether SM's stacked rows keep switching on the cell's shape (4:3) or move
  to a width breakpoint.
- How the tests are organised.

## Done when

- The owner's rules hold in every layout, shown by browser tests and by
  screenshots at about 205×165 and each standard size.
- Tesserae Studio's linter reports no errors on `bin_day`.
- Across all themes and styles (Tesserae's `/_test/matrix` set, plus Paper and
  Newsprint), the title bar shows each style's decoration and nothing
  overflows.
- The full suites pass on both Tesserae versions.
