"""Check exported Cargo source resolves with an empty Cargo home and no network."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile


def check(root):
    manifests = sorted(Path(root).rglob("manifest.json"))
    if not manifests:
        raise ValueError("No build manifests")
    seen = set()
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text())
        for package in manifest["packages"]:
            key = (package["source_commit"], package.get("workspace"))
            if key in seen:
                continue
            seen.add(key)
            source = manifest_path.parent / package["redistribution"]["source_archive"]
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                with tarfile.open(source) as archive:
                    archive.extractall(root, filter="data")
                tree = root / "source"
                if not (tree / "build-scripts/docs/licensing.md").is_file():
                    raise ValueError("Missing Docker build input docs/licensing.md")
                if package["build_system"].startswith("cargo"):
                    workspace = tree / "upstream" / package["workspace"]
                    if hashlib.sha256((workspace / "Cargo.lock").read_bytes()).hexdigest() != package["cargo_lock_sha256"]:
                        raise ValueError("Exported Cargo lockfile differs from the build")
                    config = tree / "cargo-vendor-config.toml"
                    config.write_text(config.read_text().replace('directory = "vendor"', f'directory = "{tree / "vendor"}"'))
                    env = dict(os.environ, CARGO_HOME=str(root / "empty-cargo-home"),
                               RUSTUP_TOOLCHAIN=package.get("rust_toolchain", "1.90.0"))
                    subprocess.run(["cargo", "--config", str(config), "metadata", "--offline", "--locked",
                                    "--format-version", "1"], cwd=workspace, env=env, check=True, stdout=subprocess.DEVNULL)
                print("Exported source verified:", package["name"], package["package_version"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts", type=Path)
    check(parser.parse_args().artifacts)
