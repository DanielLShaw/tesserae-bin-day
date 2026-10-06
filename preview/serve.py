"""Run a local Tesserae with this repo's plugins, to try the widget by hand.

    uv run preview/serve.py                 http://127.0.0.1:8765/
    uv run preview/serve.py --port 9000

Starts Tesserae's own dev server (reload and debugger on) from the pinned
checkout in .tesserae/, listening on this machine only. Its data, including
the admin password, saved schedules and any Home Assistant URL and token you
enter, lives in .devdata/ (gitignored) and survives restarts. bin_day and
bin_day_core are symlinked in as pushed widgets, so code edits show on reload.
"""

import argparse
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA_ROOT = REPO / ".devdata"
TESSERAE_SRC = Path(os.environ.get("TESSERAE_SRC", REPO / ".tesserae")).expanduser()


def link_plugins():
    authored = DATA_ROOT / "authored"
    authored.mkdir(parents=True, exist_ok=True)
    for folder in ("bin_day_core", "bin_day"):
        link = authored / folder
        if not link.is_symlink():
            link.symlink_to(REPO / folder, target_is_directory=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not (TESSERAE_SRC / "app" / "main.py").is_file():
        sys.exit(f"No Tesserae checkout at {TESSERAE_SRC}. See README.md, Setup.")
    link_plugins()
    os.environ["TESSERAE_DATA_ROOT"] = str(DATA_ROOT)
    from app.main import _serve

    _serve(["--dev", "--host", "127.0.0.1", "--port", str(args.port)])


if __name__ == "__main__":
    main()
