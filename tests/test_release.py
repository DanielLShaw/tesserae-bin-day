"""The release tarball: Tesserae's installer refuses any root folder without a
plugin.json, so every other root folder must be export-ignored."""

import subprocess

from conftest import REPO


def export_ignored():
    lines = (REPO / ".gitattributes").read_text().splitlines()
    return {line.split()[0].rstrip("/") for line in lines if line.endswith(" export-ignore")}


def root_folders():
    """Root folders with files git would ship: tracked, or new and not ignored."""
    files = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    return {path.split("/")[0] for path in files if "/" in path}


def test_every_root_folder_is_a_plugin_or_left_out_of_the_tarball():
    shipped = root_folders() - export_ignored()
    assert shipped == {"bin_day", "bin_day_core"}
    assert all((REPO / folder / "plugin.json").is_file() for folder in shipped)


def test_each_plugins_smoke_test_ships_and_the_root_conftest_does_not():
    paths = ["bin_day/tests/test_smoke.py", "bin_day_core/tests/test_smoke.py", "conftest.py"]
    out = subprocess.run(
        ["git", "check-attr", "export-ignore", *paths],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    assert [line.rsplit(": ", 1)[1] for line in out] == ["unspecified", "unspecified", "set"]
