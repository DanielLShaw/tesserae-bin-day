"""Screenshot the bin_day widget for every scenario at every size.

    uv run preview/shoot.py                         all scenarios, all sizes, light theme
    uv run preview/shoot.py -s today -z xs -z sm    some scenarios and sizes
    uv run preview/shoot.py -t light -t dark -t paper   several themes
    uv run preview/shoot.py --e6                    also simulate the E1002's inks

Writes screenshots/<scenario>/<size>.png (``<size>-<theme>.png`` for themes
other than light) and screenshots/index.html, a contact sheet of the lot.
With --e6, each shot also gets an ``-e6`` twin: Tesserae's own quantiser
maps it to the six Spectra 6 inks the reTerminal E1002 prints (Floyd-
Steinberg, as its packer does), shown in the inks' measured colours.
A full run (no -s/-z/-t) replaces the whole folder, so it holds only the
latest shots; narrower runs update just the shots they take. Shots are
rendered into a staging folder first, so a failed run changes nothing.

Boots a real Tesserae app from the pinned checkout in .tesserae/ with this
repo's plugins installed, saves each scenario's config from preview/scenarios.py, pins its
clock and renders through /_test/render, as the tests do.
"""

import argparse
import html
import json
import logging
import os
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
SIZES = ("xs", "sm", "md", "lg")
INSTALL_HINT = "uv run playwright install chromium --only-shell"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    names = [s.name for s in SCENARIOS]
    parser.add_argument("-s", "--scenario", action="append", choices=names, help="repeatable")
    parser.add_argument("-z", "--size", action="append", choices=SIZES, help="repeatable")
    parser.add_argument("-t", "--theme", action="append", help="repeatable; default light")
    parser.add_argument("-o", "--out", type=Path, default=REPO / "screenshots")
    parser.add_argument("--e6", action="store_true", help="add Spectra 6 panel simulations")
    return parser.parse_args()


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


def shot_name(size, theme):
    return f"{size}.png" if theme == "light" else f"{size}-{theme}.png"


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


def write_contact_sheet(out):
    """index.html: every scenario's shots in ``out``, one row per scenario."""
    themes = _themes_present(out)
    heads = "".join(f"<th>{size} · {theme}</th>" for theme in themes for size in SIZES)
    rows = []
    for scenario in SCENARIOS:
        cells = "".join(
            f'<td><img src="{scenario.name}/{shot_name(size, theme)}" alt="{size} {theme}"></td>'
            if (out / scenario.name / shot_name(size, theme)).exists()
            else "<td></td>"
            for theme in themes
            for size in SIZES
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


def shoot(stage, scenarios, sizes, themes, e6=False):
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
                    for size in sizes:
                        page.goto(f"{base}&size={size}&theme={quote(theme)}&opts={opts}")
                        page.wait_for_function("window.__tesseraeComposed === true")
                        page.evaluate("document.fonts.ready")
                        shot = folder / shot_name(size, theme)
                        page.locator(".cell").first.screenshot(path=shot)
                        count += 1
                        if e6:
                            simulate_e6(shot, shot.with_name(f"{shot.stem}-e6.png"))
            browser.close()
    finally:
        server.shutdown()
        shutil.rmtree(data_root, ignore_errors=True)
    return count


def main():
    args = parse_args()
    scenarios = [s for s in SCENARIOS if not args.scenario or s.name in args.scenario]
    sizes = args.size or list(SIZES)
    themes = args.theme or ["light"]
    full_run = not (args.scenario or args.size or args.theme or args.e6)

    # Render into a staging folder so a failed run leaves the last shots intact.
    stage = Path(tempfile.mkdtemp(prefix="bin-day-stage-"))
    try:
        count = shoot(stage, scenarios, sizes, themes, e6=args.e6)
        if full_run and args.out.exists():
            shutil.rmtree(args.out)
        shutil.copytree(stage, args.out, dirs_exist_ok=True)
    finally:
        shutil.rmtree(stage, ignore_errors=True)

    write_contact_sheet(args.out)
    print(f"{count} screenshots in {args.out}; open {args.out / 'index.html'} to compare.")


if __name__ == "__main__":
    main()
