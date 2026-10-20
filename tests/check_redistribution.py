"""Check release material integrity before creating a draft (not a license approval)."""

import hashlib
import json
from pathlib import Path
import tarfile


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check(root):
    manifests = sorted(Path(root).rglob("manifest.json"))
    if not manifests:
        raise ValueError("No build manifests")
    for manifest in manifests:
        directory = manifest.parent
        checksums = {}
        for line in (directory / "SHA256SUMS").read_text().splitlines():
            digest, name = line.split("  ", 1)
            if Path(name).name != name or name in checksums:
                raise ValueError("Invalid checksum filename")
            checksums[name] = digest
            if sha256(directory / name) != digest:
                raise ValueError(f"Checksum mismatch: {name}")
        if checksums.get(manifest.name) != sha256(manifest):
            raise ValueError("Manifest is not checksummed")
        for package in json.loads(manifest.read_text())["packages"]:
            materials = package["redistribution"]
            for kind in ("source", "notice"):
                name = materials[kind + "_archive"]
                if Path(name).name != name:
                    raise ValueError("Invalid material filename")
                path = directory / name
                if checksums.get(name) != materials[kind + "_sha256"] or sha256(path) != materials[kind + "_sha256"]:
                    raise ValueError(f"Material checksum mismatch: {name}")
                with tarfile.open(path) as archive:
                    names = archive.getnames()
                    prefix = "source" if kind == "source" else "notices"
                    if prefix + "/SOURCE.txt" not in names:
                        raise ValueError(f"Missing source instructions: {name}")
                    if kind == "source":
                        for required in ("upstream", "build-scripts/compiler/recipes.py", "recipe.json", "dependencies.json"):
                            if prefix + "/" + required not in names:
                                raise ValueError(f"Missing {required}: {name}")
            for name in (package["name"], f"{package['name']}_{package['package_version']}_arm64.deb"):
                if name not in checksums:
                    raise ValueError(f"Missing binary checksum: {name}")
            if package["build_system"] == "shairport":
                name = materials["debian_packaging_archive"]
                if name not in checksums:
                    raise ValueError("Missing Debian packaging archive")


if __name__ == "__main__":
    import sys
    check(sys.argv[1])
