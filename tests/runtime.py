"""Install unique renderer bundles and exercise informational flags only."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, "/opt/compiler")
import cli

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--artifacts", default="/artifacts")
parser.add_argument("--emulator", help="Use qemu-aarch64 for local multiarch container tests")
args = parser.parse_args()
seen = set()
manifests = list(sorted(Path(args.artifacts).rglob("manifest.json")))
if not manifests:
    raise RuntimeError("No renderer manifests found")
for path in manifests:
    manifest = json.loads(path.read_text())
    packages = manifest["profile"]["packages"]
    bundle = tuple((p["name"], p["package_version"]) for p in packages)
    if bundle in seen:
        continue
    seen.add(bundle)
    debs = [str(path.parent / f"{p['name']}_{p['package_version']}_arm64.deb") for p in packages]
    subprocess.run(["apt-get", "install", "-y", "--allow-downgrades", "--no-install-recommends", *debs], check=True)
    for package in packages:
        name = package["name"]
        version = subprocess.check_output(["dpkg-query", "-W", "-f=${Version}", name + ":arm64"], text=True)
        if version != package["package_version"]:
            raise RuntimeError(f"Installed version mismatch for {name}")
        executable = "/usr/bin/" + name
        command = [args.emulator, executable] if args.emulator else [executable]
        version_arg = "-V" if name in ["shairport-sync", "nqptp"] else "--version"
        version_text = subprocess.check_output([*command, version_arg], text=True)
        print(version_text, end="", flush=True)
        if package["package_version"].split("-")[0] not in version_text:
            raise RuntimeError(f"Binary reports an unexpected version: {name}")
        help_text = subprocess.check_output([*command, "-h" if name == "nqptp" else "--help"], text=True)
        if name != "nqptp":
            cli.check_help(help_text, manifest["profile"]["renderer"])
        else:
            if not Path("/lib/systemd/system/nqptp.service").is_file():
                raise RuntimeError("NQPTP systemd unit is missing")
        loader = ([args.emulator, "/lib/ld-linux-aarch64.so.1", "--list", executable]
                  if args.emulator else ["ldd", executable])
        libraries = subprocess.check_output(loader, text=True)
        if "not found" in libraries:
            raise RuntimeError(f"Unresolved libraries for {name}: {libraries}")
    print(f"Installed and checked {bundle}", flush=True)
