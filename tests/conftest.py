"""Fixtures that boot a real Tesserae app with this repo's plugins installed.

The plugins are standalone folders, so integration tests borrow a Tesserae
app from the pinned checkout in .tesserae/ (or $TESSERAE_SRC) and stage the
plugin folders (as symlinks) into the app's ``authored`` directory under a per-test data
root. Nothing is written into the checkout. Without a checkout these tests
skip; the pure-logic tests still run.
"""

import os
from pathlib import Path

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
