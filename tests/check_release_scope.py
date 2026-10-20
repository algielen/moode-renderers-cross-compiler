"""Fail closed if a public download bundle contains deferred components."""

import json
from pathlib import Path
import sys


def check(root, version="10.2.0"):
    root = Path(root)
    available = {p.stem: p for p in (Path(__file__).resolve().parent.parent / "profiles").glob("*.json")}
    if version not in available:
        raise ValueError("Unknown release profile")
    profile = json.loads(available[version].read_text())
    expected = {renderer: [p["name"] for p in config["packages"]]
                for renderer, config in profile["renderers"].items() if renderer in {"librespot", "qobuz"}}
    if {path.name for path in root.iterdir()} != set(expected):
        raise ValueError("Release must contain only approved renderer directories")
    for renderer, names in expected.items():
        manifest = json.loads((root / renderer / "manifest.json").read_text())
        if manifest["profile"]["moode_version"] != version:
            raise ValueError("Unexpected release profile")
        if [package["name"] for package in manifest["packages"]] != names:
            raise ValueError("Unexpected release package")
        if any("shairport" in path.name or "nqptp" in path.name for path in (root / renderer).rglob("*")):
            raise ValueError("Deferred AirPlay artifact in release")


if __name__ == "__main__":
    check(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "10.2.0")
