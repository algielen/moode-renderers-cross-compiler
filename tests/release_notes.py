"""Render draft notes from the selected profile, excluding deferred renderers."""

import argparse
from pathlib import Path
from ci_verification import profiles
from release_policy import cleared, identity, key, load


def render(profile, template, limited=False, renderers=None):
    renderers = set(renderers) if renderers is not None else {
        r for r in profile["renderers"] if cleared(profile, r)}
    packages = []
    for renderer, label in (("librespot", "Spotify Connect"), ("qobuz", "Qobuz Connect")):
        if renderer not in renderers:
            continue
        if not cleared(profile, renderer):
            raise ValueError("Cannot describe an uncleared package as a release download")
        for package in profile["renderers"].get(renderer, {}).get("packages", []):
            packages.append(f"- {label}: {package['name']} {package['package_version']}.")
        recipes = [identity(profile, p) for p in profile["renderers"][renderer]["packages"]]
        matching = [version for version, candidate in profiles().items() if renderer in candidate["renderers"] and
                    [identity(candidate, p) for p in candidate["renderers"][renderer]["packages"]] == recipes]
        packages.append("  Matching package recipes: " + ", ".join(sorted(matching, key=lambda v: tuple(map(int, v.split('.'))))) + ".")
    reused = []
    for renderer, config in profile["renderers"].items():
        if renderer in renderers:
            continue
        for package in config["packages"]:
            receipt = next((p for p in load()["published"] if key(p["recipe"]) == key(identity(profile, package))), None)
            if receipt:
                reused.append(f"Unchanged {package['name']}: use [{receipt['release']}](https://github.com/algielen/moode-renderers-cross-compiler/releases/tag/{receipt['release']}).")
    notes = template.replace("@MOODE_PROFILE@", profile["moode_version"]).replace("@PACKAGES@", "\n".join(packages))
    notes = notes.replace("@REUSED_PACKAGES@", "\n".join(reused))
    if limited:
        notes += f"\nThis draft was produced by a limited moOde {profile['moode_version']} workflow smoke test. Full compatibility-matrix validation is still pending.\n"
    return notes


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limited", action="store_true")
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    template = (Path(__file__).resolve().parent.parent / "docs/release-notes.md").read_text()
    args.output.write_text(render(profiles()[args.profile], template, args.limited,
                                 {p.name for p in args.artifacts.iterdir()}))
