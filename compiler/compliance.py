"""Collect build-specific redistribution materials; collection is not license approval."""

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def notice_files(root):
    for path in sorted(root.rglob("*")):
        if path.is_file() and any(word in path.name.lower() for word in
                                  ("license", "licence", "copying", "copyright", "notice", "authors")):
            if ".git" not in path.parts:
                yield path


def inline_notice_files(root):
    """Preserve whole text files so inline notice/license blocks are never truncated."""
    marker = re.compile(rb"copyright|spdx-license-identifier|permission is hereby granted|licensed under|all rights reserved", re.I)
    named = set(notice_files(root))
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path in named or ".git" in path.parts:
            continue
        data = path.read_bytes()
        if b"\0" not in data and marker.search(data):
            yield path


def collect(source, package, profile, stage, work, env, artifacts=None):
    """Archive pristine pinned sources and the entire locked Cargo dependency closure."""
    root = work / "redistribution"
    root.mkdir()
    upstream = root / "upstream"
    shutil.copytree(source, upstream, ignore=shutil.ignore_patterns(".git"))
    compiler = Path(__file__).resolve().parent
    scripts = root / "build-scripts"
    shutil.copytree(compiler, scripts / "compiler", ignore=shutil.ignore_patterns("__pycache__"))
    repository = compiler.parent
    for name in ("profiles", "tests"):
        shutil.copytree(repository / name, scripts / name, ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("Dockerfile", "LICENSE"):
        shutil.copy2(repository / name, scripts / name)
    (scripts / "docs").mkdir()
    audit = repository / "docs/licensing.md"
    if not audit.is_file():
        audit = compiler / "THIRD-PARTY.md"
    shutil.copy2(audit, scripts / "docs/licensing.md")
    (root / "recipe.json").write_text(json.dumps({"package": package, "profile": profile}, indent=2) + "\n")
    inventory = []
    if package["build_system"].startswith("cargo"):
        workspace = source / package["workspace"]
        config = subprocess.check_output(
            ["cargo", "vendor", "--locked", "--versioned-dirs", str(root / "vendor")],
            cwd=workspace, env=env, text=True)
        # Config paths must work after extraction on another machine.
        config = config.replace(str(root / "vendor"), "vendor")
        (root / "cargo-vendor-config.toml").write_text(config)
        metadata_args = ["cargo", "metadata", "--locked", "--format-version", "1"]
        if package["features"]:
            metadata_args += ["--features", ",".join(package["features"])]
        metadata = json.loads(subprocess.check_output(metadata_args, cwd=workspace, env=env, text=True))
        built_ids = {artifact["package_id"] for artifact in artifacts or []}
        if not built_ids:
            raise ValueError("Cargo build supplied no compiler-artifact evidence")
        missing = built_ids - {item["id"] for item in metadata["packages"]}
        if missing:
            raise ValueError("Cargo metadata omits built packages: " + ", ".join(sorted(missing)))
        for item in metadata["packages"]:
            inventory.append({**{key: item.get(key) for key in ("id", "name", "version", "source", "license", "license_file")},
                              "built": item["id"] in built_ids})
        (root / "build-artifacts.json").write_text(json.dumps(artifacts or [], indent=2) + "\n")
        # Rust's standard library is statically linked too. Retain its source and notices.
        sysroot = Path(subprocess.check_output(["rustc", "--print", "sysroot"], env=env, text=True).strip())
        shutil.copytree(sysroot / "lib/rustlib/src/rust", root / "rust-library")
        shutil.copytree(sysroot / "share/doc/rust/licenses", root / "rust-licenses")
        for path in notice_files(sysroot / "share/doc/rust"):
            if path.parent == sysroot / "share/doc/rust":
                shutil.copy2(path, root / "rust-licenses" / path.name)
    (root / "dependencies.json").write_text(json.dumps(inventory, indent=2) + "\n")
    # These are the installed build inputs, not an assertion that each is linked.
    shutil.copy2(compiler / "toolchain-packages.tsv", root / "toolchain-packages.tsv")
    notices = work / "notices"
    notices.mkdir()
    shutil.copytree(Path("/usr/share/common-licenses"), notices / "debian-common-licenses")
    for copyright_file in Path("/usr/share/doc").glob("*/copyright"):
        dest = notices / "debian" / copyright_file.parent.name / "copyright"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(copyright_file, dest)
    for path in notice_files(root):
        dest = notices / path.relative_to(root)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    for path in inline_notice_files(root):
        dest = notices / "inline" / path.relative_to(root)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    archive_name = f"{package['name']}_{package['package_version']}_sources.tar.gz"
    instructions = (
        f"Source for {package['name']} {package['package_version']}: {archive_name}\n"
        "Obtain the companion source archive from the same GitHub release as this binary:\n"
        "https://github.com/algielen/moode-renderers-cross-compiler/releases\n"
        "The binary bundle also includes this archive. Preserve it when redistributing.\n"
        "upstream/ contains the pinned source, vendor/ the locked Rust dependency closure\n"
        "(including host and other-platform dependencies), and build-scripts/ the recipes.\n"
        "Original license terms and notices remain in each source tree; no relicensing is intended.\n"
        "For Cargo packages, MPL-covered files remain under the MPL; their exact source and license texts are retained in vendor/.\n"
        "For an offline Cargo build copy cargo-vendor-config.toml to upstream's workspace/.cargo/config.toml\n"
        "and adjust directory to the extracted vendor directory. Use the target and features in recipe.json.\n"
        "See build-scripts/Dockerfile for system dependencies and toolchains.\n"
        "dependencies.json is a conservative locked dependency inventory, not an exact linked-code SBOM.\n"
        "For Cargo packages, built=true and build-artifacts.json identify packages reported by the actual build,\n"
        "including host tools. Inline notices retain complete original text files under notices/inline/.\n"
    )
    if package["build_system"] == "shairport":
        instructions += f"Also obtain {package['name']}_{package['package_version']}_debian.tar.xz from the same release for the exact Debian packaging input.\n"
    (root / "SOURCE.txt").write_text(instructions)
    (notices / "SOURCE.txt").write_text(instructions)
    with tarfile.open(stage / archive_name, "w:gz") as archive:
        archive.add(root, arcname="source")
    notice_name = f"{package['name']}_{package['package_version']}_notices.tar.gz"
    with tarfile.open(stage / notice_name, "w:gz") as archive:
        archive.add(notices, arcname="notices")
    return notices, {"source_archive": archive_name, "source_sha256": digest(stage / archive_name),
                     "notice_archive": notice_name, "notice_sha256": digest(stage / notice_name)}


def add_package_notices(deb, notices, name, work, env):
    root = work / "with-notices"
    subprocess.run(["dpkg-deb", "--raw-extract", str(deb), str(root)], check=True)
    dest = root / "usr/share/doc" / name / "redistribution"
    shutil.copytree(notices, dest)
    # Existing md5sums describe upstream payloads; refresh for the added files as well.
    import hashlib as hashes
    (root / "DEBIAN/md5sums").write_text("".join(
        f"{hashes.md5(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}\n"
        for path in sorted(root.rglob("*")) if path.is_file() and "DEBIAN" not in path.relative_to(root).parts))
    subprocess.run(["dpkg-deb", "--root-owner-group", "--build", str(root), str(deb)], env=env, check=True)
