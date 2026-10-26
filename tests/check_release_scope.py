"""Fail closed if a public download bundle contains deferred components."""

import json
from pathlib import Path
import sys
from release_policy import cleared


def check(root, version="10.2.0"):
    root = Path(root)
    available = {p.stem: p for p in (Path(__file__).resolve().parent.parent / "profiles").glob("*.json")}
    if version not in available:
        raise ValueError("Unknown release profile")
    profile = json.loads(available[version].read_text())
    expected = {renderer: [p["name"] for p in config["packages"]]
                for renderer, config in profile["renderers"].items() if renderer in {"librespot", "qobuz"}}
    actual = {path.name for path in root.iterdir()}
    if not actual or not actual <= set(expected):
        raise ValueError("Release must contain only approved renderer directories")
    for renderer, names in expected.items():
        if renderer not in actual:
            continue
        manifest = json.loads((root / renderer / "manifest.json").read_text())
        if manifest["profile"]["moode_version"] != version:
            raise ValueError("Unexpected release profile")
        if [package["name"] for package in manifest["packages"]] != names:
            raise ValueError("Unexpected release package")
        for actual_package, expected_package in zip(manifest["packages"], profile["renderers"][renderer]["packages"]):
            if any(actual_package.get(field) != value for field, value in expected_package.items()):
                raise ValueError("Unexpected release package recipe")
        if not cleared(profile, renderer):
            raise ValueError("Package recipe does not have release license clearance")
        if any("shairport" in path.name or "nqptp" in path.name for path in (root / renderer).rglob("*")):
            raise ValueError("Deferred AirPlay artifact in release")


if __name__ == "__main__":
    check(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "10.2.0")
