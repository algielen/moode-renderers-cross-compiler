"""Plan renderer shards and bind aggregate verification to release downloads."""

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RENDERERS = ("librespot", "airplay", "qobuz")


def profiles():
    return {p.stem: json.loads(p.read_text()) for p in (ROOT / "profiles").glob("*.json")}


def matrix(versions, available):
    if not isinstance(versions, list) or any(not isinstance(v, str) for v in versions):
        raise ValueError("Versions must be an array of strings")
    if len(set(versions)) != len(versions) or set(versions) - set(available):
        raise ValueError("Duplicate or unknown profile version")
    if any(set(available[v]["renderers"]) - set(RENDERERS) for v in versions):
        raise ValueError("Unknown renderer in selected profile")
    result = []
    for renderer in RENDERERS:
        selected = sorted(v for v in versions if renderer in available[v]["renderers"])
        if selected:
            result.append({"renderer": renderer, "versions": selected})
    return {"include": result}


def checksums(directory):
    if directory.is_symlink() or any(p.is_symlink() or not p.is_file() for p in directory.iterdir()):
        raise ValueError("Release directory must contain regular files only")
    result = {}
    for line in (directory / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        if Path(name).name != name or name in result or not re.fullmatch("[0-9a-f]{64}", digest):
            raise ValueError("Malformed checksum record")
        result[name] = digest
    if {p.name for p in directory.iterdir()} != set(result) | {"SHA256SUMS"}:
        raise ValueError("Unapproved files outside checksum inventory")
    for name, digest in result.items():
        with (directory / name).open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != digest:
                raise ValueError("Payload differs from checksum inventory")
    return result


def expected_files(packages):
    names = {"build.log", "manifest.json"}
    for package in packages:
        name = package["name"]
        prefix = f"{name}_{package['package_version']}"
        names.update((name, prefix + "_arm64.deb", prefix + "_sources.tar.gz", prefix + "_notices.tar.gz"))
        if package["build_system"] == "shairport":
            names.add(prefix + "_debian.tar.xz")
    return names


def recipe(profile, package):
    return {"target": profile["target"], "distribution": profile["distribution"], "package": package}


def report(root, renderer, versions, commit, available):
    expected = next((s for s in matrix(versions, available)["include"] if s["renderer"] == renderer), None)
    if expected is None or expected["versions"] != sorted(versions):
        raise ValueError("Empty shard or unavailable renderer")
    wanted = {Path(v) / renderer / "manifest.json" for v in versions}
    if {p.relative_to(root) for p in Path(root).rglob("manifest.json")} != wanted:
        raise ValueError("Missing or unexpected build outputs")
    builds = []
    for version in expected["versions"]:
        directory = Path(root) / version / renderer
        manifest = json.loads((directory / "manifest.json").read_text())
        profile = available[version]
        packages = profile["renderers"][renderer]["packages"]
        selected = {**{key: value for key, value in profile.items() if key != "renderers"},
                    "renderer": renderer, **profile["renderers"][renderer]}
        if manifest["profile"] != selected:
            raise ValueError("Manifest does not match the selected profile")
        files = checksums(directory)
        builds.append({"version": version, "renderer": renderer, "files": files,
                       "packages": [{"recipe": recipe(profile, p), "binary_sha256": files[p["name"]]}
                                    for p in packages]})
    return {"schema": 1, "commit": commit, "renderer": renderer,
            "versions": expected["versions"], "builds": builds}


def aggregate(reports, versions, commit, available, release=False, release_profile="10.2.0"):
    shards = matrix(versions, available)["include"]
    expected_shards = {s["renderer"]: s["versions"] for s in shards}
    expected_pairs = {(v, s["renderer"]) for s in shards for v in s["versions"]}
    if release:
        required = {(release_profile, renderer) for renderer in ("librespot", "qobuz")
                    if renderer in available.get(release_profile, {}).get("renderers", {})}
        if not required or not required <= expected_pairs:
            raise ValueError("Missing default release coverage")
    seen_renderers, seen_pairs, binaries, builds = set(), set(), {}, []
    for item in reports:
        renderer = item["renderer"]
        if item["schema"] != 1 or item["commit"] != commit:
            raise ValueError("Wrong report schema or commit")
        if renderer in seen_renderers or renderer not in expected_shards:
            raise ValueError("Duplicate or unexpected shard")
        seen_renderers.add(renderer)
        if item["versions"] != expected_shards[renderer]:
            raise ValueError("Wrong declared shard coverage")
        shard_pairs = set()
        for build in item["builds"]:
            pair = (build["version"], build["renderer"])
            if pair not in expected_pairs or pair[1] != renderer or pair in seen_pairs:
                raise ValueError("Duplicate or unexpected build")
            seen_pairs.add(pair)
            shard_pairs.add(pair)
            profile = available[pair[0]]
            packages = profile["renderers"][renderer]["packages"]
            files = build["files"]
            if set(files) != expected_files(packages) or any(
                    not isinstance(h, str) or not re.fullmatch("[0-9a-f]{64}", h) for h in files.values()):
                raise ValueError("Missing or malformed file hashes")
            if len(build["packages"]) != len(packages):
                raise ValueError("Unexpected package count")
            for evidence, package in zip(build["packages"], packages):
                expected_recipe = recipe(profile, package)
                digest = files[package["name"]]
                if evidence["recipe"] != expected_recipe or evidence["binary_sha256"] != digest:
                    raise ValueError("Recipe or binary evidence mismatch")
                key = json.dumps(expected_recipe, sort_keys=True)
                if binaries.setdefault(key, digest) != digest:
                    raise ValueError("Binary differs for equivalent recipe across shards")
            builds.append(build)
        if shard_pairs != {(v, renderer) for v in expected_shards[renderer]}:
            raise ValueError("Missing build coverage within shard")
    if seen_renderers != set(expected_shards) or seen_pairs != expected_pairs:
        raise ValueError("Missing shard or build coverage")
    return {"schema": 1, "commit": commit, "builds": builds}


def bind(root, approval, commit, release_profile="10.2.0"):
    from check_redistribution import check
    from check_release_scope import check as check_scope
    if approval["schema"] != 1 or approval["commit"] != commit:
        raise ValueError("Wrong approval commit or schema")
    check(root)
    check_scope(root, release_profile)
    for directory in Path(root).iterdir():
        renderer = directory.name
        matching = [b for b in approval["builds"] if (b["version"], b["renderer"]) == (release_profile, renderer)]
        if len(matching) != 1 or checksums(Path(root) / renderer) != matching[0]["files"]:
            raise ValueError("Release files differ from aggregate-approved downloads")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("report", "aggregate", "bind"))
    parser.add_argument("root", type=Path)
    parser.add_argument("--versions-json")
    parser.add_argument("--renderer", choices=RENDERERS)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--release", action="store_true")
    parser.add_argument("--release-profile", default="10.2.0")
    args = parser.parse_args()
    if args.command == "bind":
        bind(args.root, json.loads(args.approval.read_text()), args.commit, args.release_profile)
        return
    versions = json.loads(args.versions_json)
    if args.command == "report":
        result = report(args.root, args.renderer, versions, args.commit, profiles())
    else:
        reports = [json.loads(p.read_text()) for p in sorted(args.root.rglob("verification-*.json"))]
        result = aggregate(reports, versions, args.commit, profiles(), args.release, args.release_profile)
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
