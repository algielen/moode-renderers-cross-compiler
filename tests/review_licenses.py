"""Report offered license selections for packages evidenced by actual Cargo builds."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tarfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "compiler"))
from license_policy import select_license


def review(root):
    result = []
    seen = set()
    for manifest_path in sorted(Path(root).rglob("manifest.json")):
        manifest = json.loads(manifest_path.read_text())
        for package in manifest["packages"]:
            if not package["build_system"].startswith("cargo"):
                continue
            key = (package["source_commit"], manifest["profile"]["target"],
                   tuple(sorted((item["package_id"], tuple(sorted(item["features"])), item["role"], tuple(item["kind"]))
                                for item in package["cargo_artifacts"])))
            if key in seen:
                continue
            seen.add(key)
            materials = package["redistribution"]
            source = manifest_path.parent / materials["source_archive"]
            with source.open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != materials["source_sha256"]:
                    raise ValueError("Source archive checksum mismatch")
            with tarfile.open(source, "r|gz") as archive:
                inventory = next(json.load(archive.extractfile(member)) for member in archive
                                 if member.name == "source/dependencies.json")
            built_ids = {artifact["package_id"] for artifact in package["cargo_artifacts"]}
            if not built_ids or built_ids - {item["id"] for item in inventory}:
                raise ValueError("Missing actual-build dependency metadata")
            selected = [{**item, "selected_license": select_license(item["license"]),
                         "roles": sorted({artifact["role"] for artifact in package["cargo_artifacts"]
                                          if artifact["package_id"] == item["id"]})}
                        for item in inventory if item["id"] in built_ids]
            result.append({"name": package["name"], "source_commit": package["source_commit"],
                           "source_sha256": materials["source_sha256"], "built_packages": selected,
                           "review_required": [item["id"] for item in selected if item["selected_license"] is None]})
    return {"status": "proposed selections; not legal clearance", "packages": result}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(review(args.artifacts), indent=2) + "\n")
