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
    for renderer in profile["renderers"]:
        selected = cli.select_profile(version, "3b+", renderer)
        output = Path("/out") / version / renderer
        subprocess.run([sys.executable, str(ROOT / "compiler/cli.py"), "build",
                        "--pi-model", "3b+", "--moode-version", version, "--renderer", renderer,
                        "--output", str(output)], check=True)
        manifest = json.loads((output / "manifest.json").read_text())
        if manifest["profile"] != selected:
            raise RuntimeError(f"Build manifest does not match profile {version}/{renderer}")
        subprocess.run(["sha256sum", "-c", "SHA256SUMS"], cwd=output, check=True)
        for package in selected["packages"]:
            recipe = (selected["target"], selected["distribution"], json.dumps(package, sort_keys=True))
            digest = hashlib.sha256((output / package["name"]).read_bytes()).hexdigest()
            if reference_hashes.setdefault(recipe, digest) != digest:
                raise RuntimeError(f"Binary differs for equivalent recipe in {version}/{renderer}")
        print(f"Verified {version}/{renderer} ({', '.join(profile['aliases'])})", flush=True)
