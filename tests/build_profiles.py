"""Cross-build every profile using one cache; check equivalent recipes agree."""

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("cli", ROOT / "compiler/cli.py")
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)

reference_hashes = {}
for profile in cli.profiles():
    version = profile["moode_version"]
    output = Path("/out") / version
    subprocess.run([sys.executable, str(ROOT / "compiler/cli.py"), "build",
                    "--pi-model", "3b+", "--moode-version", version,
                    "--output", str(output)], check=True)
    manifest = json.loads((output / "manifest.json").read_text())
    if manifest["profile"] != profile:
        raise RuntimeError(f"Build manifest does not match profile {version}")
    subprocess.run(["sha256sum", "-c", "SHA256SUMS"], cwd=output, check=True)
    # Profiles sharing source, flags and platform should export the same binary.
    recipe = tuple(profile[key] for key in ["source_commit", "target", "package_version"]) + tuple(profile["features"])
    digest = hashlib.sha256((output / "librespot").read_bytes()).hexdigest()
    if reference_hashes.setdefault(recipe, digest) != digest:
        raise RuntimeError(f"Binary differs for equivalent recipe in {version}")
    print(f"Verified {version} ({', '.join(profile['aliases'])})", flush=True)
