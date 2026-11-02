"""Fixtures that boot a real Tesserae app with this repo's plugins installed.

The plugins are standalone folders, so integration tests borrow a Tesserae
app from the pinned checkout in .tesserae/ (or $TESSERAE_SRC) and stage the
plugin folders (as symlinks) into the app's ``authored`` directory under a per-test data
root. Nothing is written into the checkout. Without a checkout these tests
skip; the pure-logic tests still run.
"""

import os
import threading
from pathlib import Path

import pytest

from preview.fake_ha import FakeHA

REPO = Path(__file__).resolve().parent.parent
PLUGIN_FOLDERS = ("bin_day_core", "bin_day")
TESSERAE_SRC = Path(os.environ.get("TESSERAE_SRC", REPO / ".tesserae")).expanduser()
HAVE_TESSERAE = (TESSERAE_SRC / "app" / "app_factory.py").is_file()


@pytest.fixture
def app(tmp_path):
    if not HAVE_TESSERAE:
        pytest.skip(f"No Tesserae checkout at {TESSERAE_SRC}; see README.md, Setup.")
    from app.app_factory import create_app

    authored = tmp_path / "authored"
    authored.mkdir()
    for folder in PLUGIN_FOLDERS:
        # Symlinked, not copied, so coverage maps the loaded files to the repo.
        (authored / folder).symlink_to(REPO / folder, target_is_directory=True)
    return create_app(testing=True, data_root=tmp_path, plugins_dir=TESSERAE_SRC / "plugins")


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def registry(app):
    return app.config["PLUGIN_REGISTRY"]


@pytest.fixture
def fake_ha():
    ha = FakeHA()
    yield ha
    ha.stop()


@pytest.fixture
def ha_connected(app, fake_ha):
    """Home Assistant Core pointed at the fake HA."""
    app.config["SETTINGS_STORE"].patch_section(
        "plugins", {"ha_core": {"base_url": fake_ha.url, "token": FakeHA.TOKEN}}
    )
    return fake_ha


# ---- a real browser, for the admin page's scripts -----------------------------


def _installed_headless_shells():
    roots = [os.environ.get("PLAYWRIGHT_BROWSERS_PATH"), "~/Library/Caches/ms-playwright"]
    roots.append("~/.cache/ms-playwright")
    found = []
    for root in filter(None, roots):
        for build in Path(root).expanduser().glob("chromium_headless_shell-*"):
            found += [
                p for p in build.rglob("*headless*shell") if p.is_file() and os.access(p, os.X_OK)
            ]
    return sorted(found, key=lambda p: p.parts, reverse=True)


@pytest.fixture(scope="session")
def browser():
    """Headless Chromium via Playwright, or skip when none is installed."""
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as playwright:
        try:
            chromium = playwright.chromium.launch()
        except sync_api.Error:
            shells = _installed_headless_shells()
            if not shells:
                pytest.skip(
                    "no Chromium for Playwright: uv run playwright install chromium --only-shell"
                )
            chromium = playwright.chromium.launch(executable_path=str(shells[0]))
        yield chromium
        chromium.close()


@pytest.fixture
def live_url(app):
    """The test app served over HTTP on a free local port."""
    from werkzeug.serving import make_server

    server = make_server("127.0.0.1", 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


@pytest.fixture
def tab(browser, live_url):
    """A browser tab; ``tab.base_url`` is the live test app."""
    context = browser.new_context()
    tab = context.new_page()
    tab.base_url = live_url
    yield tab
    context.close()
