"""Cross-build every profile using one cache; check equivalent recipes agree."""

import hashlib
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("cli", ROOT / "compiler/cli.py")
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)
from check_redistribution import check as check_redistribution

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--versions-json", help="JSON array of moOde versions; omitted builds all profiles")
parser.add_argument("--renderer", choices=("librespot", "airplay", "qobuz"), help="Build only this renderer shard")
args = parser.parse_args()
versions = json.loads(args.versions_json) if args.versions_json is not None else None
if versions is not None:
    if not isinstance(versions, list) or any(not isinstance(v, str) for v in versions):
        parser.error("--versions-json must be a JSON array of version strings")
    unknown = set(versions) - {p["moode_version"] for p in cli.profiles()}
    if unknown:
        parser.error(f"Unknown versions: {sorted(unknown)}")

reference_hashes = {}
for profile in cli.profiles():
    version = profile["moode_version"]
    if versions is not None and version not in versions:
        continue
    for renderer in profile["renderers"]:
        if args.renderer and renderer != args.renderer:
            continue
        selected = cli.select_profile(version, "3b+", renderer)
        output = Path("/out") / version / renderer
        subprocess.run([sys.executable, str(ROOT / "compiler/cli.py"), "build",
                        "--pi-model", "3b+", "--moode-version", version, "--renderer", renderer,
                        "--output", str(output)], check=True)
        manifest = json.loads((output / "manifest.json").read_text())
        if manifest["profile"] != selected:
            raise RuntimeError(f"Build manifest does not match profile {version}/{renderer}")
        subprocess.run(["sha256sum", "-c", "SHA256SUMS"], cwd=output, check=True)
        check_redistribution(output)
        for package in selected["packages"]:
            recipe = (selected["target"], selected["distribution"], json.dumps(package, sort_keys=True))
            digest = hashlib.sha256((output / package["name"]).read_bytes()).hexdigest()
            if reference_hashes.setdefault(recipe, digest) != digest:
                raise RuntimeError(f"Binary differs for equivalent recipe in {version}/{renderer}")
        print(f"Verified {version}/{renderer} ({', '.join(profile['aliases'])})", flush=True)
