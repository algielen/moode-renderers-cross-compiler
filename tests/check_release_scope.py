"""Fail closed if a public download bundle contains deferred components."""

import json
from pathlib import Path
import sys


def check(root):
    root = Path(root)
    expected = {"librespot": "librespot", "qobuz": "pibuz"}
    if {path.name for path in root.iterdir()} != set(expected):
        raise ValueError("Release must contain only librespot and qobuz directories")
    for renderer, name in expected.items():
        manifest = json.loads((root / renderer / "manifest.json").read_text())
        if manifest["profile"]["moode_version"] != "10.3.6":
            raise ValueError("Unexpected release profile")
        if [package["name"] for package in manifest["packages"]] != [name]:
            raise ValueError("Unexpected release package")
        if any("shairport" in path.name or "nqptp" in path.name for path in (root / renderer).rglob("*")):
            raise ValueError("Deferred AirPlay artifact in release")


if __name__ == "__main__":
    check(sys.argv[1])
