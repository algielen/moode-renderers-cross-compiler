"""Render draft notes from the selected profile, excluding deferred renderers."""

import argparse
from pathlib import Path
from ci_verification import profiles


def render(profile, template, limited=False):
    packages = []
    for renderer, label in (("librespot", "Spotify Connect"), ("qobuz", "Qobuz Connect")):
        for package in profile["renderers"].get(renderer, {}).get("packages", []):
            packages.append(f"- {label}: {package['name']} {package['package_version']}.")
    notes = template.replace("@MOODE_PROFILE@", profile["moode_version"]).replace("@PACKAGES@", "\n".join(packages))
    if limited:
        notes += f"\nThis draft was produced by a limited moOde {profile['moode_version']} workflow smoke test. Full compatibility-matrix validation is still pending.\n"
    return notes


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limited", action="store_true")
    args = parser.parse_args()
    template = (Path(__file__).resolve().parent.parent / "docs/release-notes.md").read_text()
    args.output.write_text(render(profiles()[args.profile], template, args.limited))
