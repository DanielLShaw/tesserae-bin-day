"""Screenshot the bin_day widget for every scenario at every size.

    uv run preview/shoot.py                         all scenarios, all sizes, light theme
    uv run preview/shoot.py -s today -z xs -z sm    some scenarios and sizes
    uv run preview/shoot.py -t light -t dark -t paper   several themes
    uv run preview/shoot.py --e6                    also simulate the E1002's inks
    uv run preview/shoot.py -d 400x240 -d 150x200   cells of any size (WxH)
    uv run preview/shoot.py --docs                  the images in docs/images/

Writes screenshots/<scenario>/<size>.png (``<size>-<theme>.png`` for themes
other than light) and screenshots/index.html, a contact sheet of the lot.
A -d WxH cell is saved as ``<W>x<H>.png``; Tesserae picks its size class from
its dimensions, as it does on a real panel.
With --e6, each shot also gets an ``-e6`` twin: Tesserae's own quantiser
maps it to the six Spectra 6 inks the reTerminal E1002 prints (Floyd-
Steinberg, as its packer does), shown in the inks' measured colours.
A full run (no -s/-z/-t/-d/--e6) replaces the whole folder, so it holds only the
latest shots; narrower runs update just the shots they take. Shots are
rendered into a staging folder first, so a failed run changes nothing.
--docs instead renders each docs scenario at LG and SM into
docs/images/<scenario>-<size>.png for docs/bin-colours.md; those images are
committed.

Boots a real Tesserae app from the pinned checkout in .tesserae/ with this
repo's plugins installed, saves each scenario's config from preview/scenarios.py, pins
its clock and renders through /_test/render, as the tests do.
"""

import argparse
import html
import json
import logging
import os
import re
import secrets
import shutil
import sys
import tempfile
import threading
from pathlib import Path
from urllib.parse import quote

from scenarios import SCENARIOS
from werkzeug.serving import make_server

REPO = Path(__file__).resolve().parent.parent
TESSERAE_SRC = Path(os.environ.get("TESSERAE_SRC", REPO / ".tesserae")).expanduser()
DOCS_IMAGES = REPO / "docs" / "images"
DOCS_SIZES = ("lg", "sm")
SIZES = ("xs", "sm", "md", "lg")
DIMS = re.compile(r"^(\d{2,4})x(\d{2,4})$")
INSTALL_HINT = "uv run playwright install chromium --only-shell"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    names = [s.name for s in SCENARIOS]
    parser.add_argument("-s", "--scenario", action="append", choices=names, help="repeatable")
    parser.add_argument("-z", "--size", action="append", choices=SIZES, help="repeatable")
    parser.add_argument("-t", "--theme", action="append", help="repeatable; default light")
    parser.add_argument("-o", "--out", type=Path, default=REPO / "screenshots")
    parser.add_argument("--e6", action="store_true", help="add Spectra 6 panel simulations")
    parser.add_argument("-d", "--dims", action="append", type=_dims, help="WxH; repeatable")
    parser.add_argument("--docs", action="store_true", help="render docs/images/ only")
    return parser.parse_args()


def _dims(value):
    if not DIMS.match(value):
        raise argparse.ArgumentTypeError(f"{value!r} is not WxH, such as 400x240")
    return value


def boot_app():
    """A Tesserae app with this repo's plugins, in a throwaway data root."""
    if not (TESSERAE_SRC / "app" / "app_factory.py").is_file():
        sys.exit(f"No Tesserae checkout at {TESSERAE_SRC}. See README.md, Setup.")
    from app.app_factory import create_app

    # Throwaway data root: a random secret key keeps Tesserae from warning.
    os.environ.setdefault("TESSERAE_SECRET_KEY", secrets.token_hex(32))
    data_root = Path(tempfile.mkdtemp(prefix="bin-day-shots-"))
    (data_root / "authored").mkdir()
    for folder in ("bin_day_core", "bin_day"):
        (data_root / "authored" / folder).symlink_to(REPO / folder, target_is_directory=True)
    app = create_app(testing=True, data_root=data_root, plugins_dir=TESSERAE_SRC / "plugins")
    core = app.config["PLUGIN_REGISTRY"].get("bin_day_core").server_module
    return app, core, data_root


def _installed_headless_shells():
    """Playwright headless-shell builds already on this machine, newest first."""
    roots = [os.environ.get("PLAYWRIGHT_BROWSERS_PATH"), "~/Library/Caches/ms-playwright"]
    roots.append("~/.cache/ms-playwright")
    found = []
    for root in filter(None, roots):
        for build in Path(root).expanduser().glob("chromium_headless_shell-*"):
            found += [
                p for p in build.rglob("*headless*shell") if p.is_file() and os.access(p, os.X_OK)
            ]
    return sorted(found, key=lambda p: p.parts, reverse=True)


def launch_browser(playwright):
    from playwright.sync_api import Error as PlaywrightError

    if os.environ.get("BIN_DAY_CHROMIUM"):
        return playwright.chromium.launch(executable_path=os.environ["BIN_DAY_CHROMIUM"])
    try:
        return playwright.chromium.launch()
    except PlaywrightError as err:
        if "Executable doesn't exist" not in str(err):
            raise
    shells = _installed_headless_shells()
    if not shells:
        sys.exit(f"Playwright has no Chromium to drive. Install it with:\n  {INSTALL_HINT}")
    print(f"note: Playwright's own Chromium build is missing; using {shells[0]}")
    print(f"      (install the matching build with: {INSTALL_HINT})")
    return playwright.chromium.launch(executable_path=str(shells[0]))


def shot_name(view, theme):
    """A view is a size class ("sm") or cell dimensions ("400x240")."""
    return f"{view}.png" if theme == "light" else f"{view}-{theme}.png"


def render_query(view):
    match = DIMS.match(view)
    return f"size=sm&w={match[1]}&h={match[2]}" if match else f"size={view}"


def simulate_e6(png_path, out_path):
    """What the E1002 prints: ``png_path`` dithered to the six Spectra 6 inks
    as Tesserae's packer does, each ink drawn in its measured colour."""
    import numpy as np
    from app.quantizer import WAVESHARE_E6_CALIBRATED_PALETTE, WAVESHARE_E6_PALETTE, quantize
    from PIL import Image

    inks = np.array(quantize(Image.open(png_path), palette=WAVESHARE_E6_PALETTE))
    printed = inks.copy()
    for nominal, measured in zip(
        WAVESHARE_E6_PALETTE, WAVESHARE_E6_CALIBRATED_PALETTE, strict=True
    ):
        printed[(inks == nominal).all(axis=-1)] = measured
    Image.fromarray(printed).save(out_path)


def _themes_present(out):
    """Themes with shots in ``out``: light first, then the rest by name."""
    names = {p.stem.split("-", 1)[1] for p in out.glob("*/*-*.png")}
    return ["light", *sorted(names - {"light"})]


def _views_present(out):
    """The size classes, then any WxH cells with shots in ``out``, smallest first."""
    dims = {p.stem.split("-", 1)[0] for p in out.glob("*/*.png")}
    dims = sorted((d for d in dims if DIMS.match(d)), key=lambda d: [int(n) for n in d.split("x")])
    return [*SIZES, *dims]


def write_contact_sheet(out):
    """index.html: every scenario's shots in ``out``, one row per scenario."""
    themes = _themes_present(out)
    views = _views_present(out)
    heads = "".join(f"<th>{view} · {theme}</th>" for theme in themes for view in views)
    rows = []
    for scenario in SCENARIOS:
        cells = "".join(
            f'<td><img src="{scenario.name}/{shot_name(view, theme)}" alt="{view} {theme}"></td>'
            if (out / scenario.name / shot_name(view, theme)).exists()
            else "<td></td>"
            for theme in themes
            for view in views
        )
        description = html.escape(scenario.description)
        rows.append(f"<tr><th>{scenario.name}<p>{description}</p></th>{cells}</tr>")
    (out / "index.html").write_text(
        "<!doctype html><meta charset=utf-8><title>Bin Day screenshots</title><style>"
        "body{font:14px system-ui;margin:16px}td,th{vertical-align:top;padding:8px;text-align:left}"
        "th p{font-weight:400;max-width:16em;color:#555}img{display:block;max-width:420px;"
        "outline:1px solid #ccc}</style>"
        f"<table><tr><th>Scenario</th>{heads}</tr>{''.join(rows)}</table>\n",
        encoding="utf-8",
    )


def shoot(stage, scenarios, views, themes, e6=False):
    """Render every requested shot into ``stage``; returns how many."""
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    app, core, data_root = boot_app()
    server = make_server("127.0.0.1", 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}/_test/render?plugin=bin_day"

    from playwright.sync_api import sync_playwright

    count = 0
    try:
        with sync_playwright() as playwright:
            browser = launch_browser(playwright)
            page = browser.new_page()
            for scenario in scenarios:
                with app.app_context():
                    core.save_config(scenario.config)
                core._now = lambda now=scenario.now: now
                folder = stage / scenario.name
                folder.mkdir(parents=True)
                opts = quote(json.dumps(scenario.options))
                for theme in themes:
                    for view in views:
                        shown_theme = scenario.theme or theme
                        page.goto(
                            f"{base}&{render_query(view)}&theme={quote(shown_theme)}&opts={opts}"
                        )
                        page.wait_for_function("window.__tesseraeComposed === true")
                        page.evaluate("document.fonts.ready")
                        shot = folder / shot_name(view, theme)
                        page.locator(".cell").first.screenshot(path=shot)
                        count += 1
                        if e6:
                            simulate_e6(shot, shot.with_name(f"{shot.stem}-e6.png"))
            browser.close()
    finally:
        server.shutdown()
        shutil.rmtree(data_root, ignore_errors=True)
    return count


def shoot_docs():
    """docs/images/<scenario>-<size>.png: each docs scenario at LG and SM."""
    scenarios = [s for s in SCENARIOS if s.docs]
    stage = Path(tempfile.mkdtemp(prefix="bin-day-stage-"))
    try:
        count = shoot(stage, scenarios, DOCS_SIZES, ["light"])
        DOCS_IMAGES.mkdir(parents=True, exist_ok=True)
        for scenario in scenarios:
            for size in DOCS_SIZES:
                shutil.copyfile(
                    stage / scenario.name / f"{size}.png",
                    DOCS_IMAGES / f"{scenario.name}-{size}.png",
                )
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    print(f"{count} images in {DOCS_IMAGES}")


def main():
    args = parse_args()
    if args.docs:
        return shoot_docs()
    scenarios = [s for s in SCENARIOS if not args.scenario or s.name in args.scenario]
    views = [*(args.size or ([] if args.dims else SIZES)), *(args.dims or [])]
    themes = args.theme or ["light"]
    full_run = not (args.scenario or args.size or args.theme or args.dims or args.e6)

    # Render into a staging folder so a failed run leaves the last shots intact.
    stage = Path(tempfile.mkdtemp(prefix="bin-day-stage-"))
    try:
        count = shoot(stage, scenarios, views, themes, e6=args.e6)
        if full_run and args.out.exists():
            shutil.rmtree(args.out)
        shutil.copytree(stage, args.out, dirs_exist_ok=True)
    finally:
        shutil.rmtree(stage, ignore_errors=True)

    write_contact_sheet(args.out)
    print(f"{count} screenshots in {args.out}; open {args.out / 'index.html'} to compare.")


if __name__ == "__main__":
    main()
