"""Fixtures that boot a real Tesserae app with this repo's plugins installed.

The plugins are standalone folders, so integration tests borrow a Tesserae
app from the pinned checkout in .tesserae/ (or $TESSERAE_SRC) and stage the
plugin folders (as symlinks) into the app's ``authored`` directory under a per-test data
root. Nothing is written into the checkout. Without a checkout these tests
skip; the pure-logic tests still run.
"""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

import pytest

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


class FakeHA:
    """A minimal Home Assistant REST API on a local port: entity states and
    calendar events. Requests need ``Authorization: Bearer test-token``.

    ``fail_with`` makes calendar requests answer with that HTTP status;
    ``stop()`` makes the server unreachable. Calendar requests are recorded
    in ``requests`` as ``(entity_id, query, headers)``.
    """

    TOKEN = "test-token"

    def __init__(self):
        self.calendars = {}
        self.names = {"sensor.outside_temperature": "Outside temperature"}
        self.fail_with = None
        self.requests = []
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server.server_port}"

    def add_calendar(self, entity_id, name, events):
        self.calendars[entity_id] = events
        self.names[entity_id] = name

    def stop(self):
        self.server.shutdown()
        self.server.server_close()

    def _state(self, entity_id):
        return {
            "entity_id": entity_id,
            "state": "off",
            "attributes": {"friendly_name": self.names[entity_id]},
        }

    def _handler(self):
        ha = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, status, body=None):
                payload = json.dumps(body).encode() if body is not None else b""
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_GET(self):
                if self.headers.get("Authorization") != f"Bearer {ha.TOKEN}":
                    return self._send(401, {"message": "Unauthorized"})
                url = urlsplit(self.path)
                path = unquote(url.path)
                if path == "/api/states":
                    return self._send(200, [ha._state(e) for e in ha.names])
                if path.startswith("/api/states/"):
                    entity_id = path.removeprefix("/api/states/")
                    if entity_id in ha.names:
                        return self._send(200, ha._state(entity_id))
                    return self._send(404, {"message": "Entity not found."})
                if path.startswith("/api/calendars/"):
                    entity_id = path.removeprefix("/api/calendars/")
                    ha.requests.append((entity_id, parse_qs(url.query), dict(self.headers)))
                    if ha.fail_with:
                        return self._send(ha.fail_with)
                    if entity_id not in ha.calendars:
                        return self._send(400)  # what HA answers for an unknown entity
                    return self._send(200, ha.calendars[entity_id])
                return self._send(404)

        return Handler


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
