"""Pinned ARM64 build recipes. Nothing here executes target binaries."""

import hashlib
import io
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

DEBIAN_AIRPLAY_URL = "https://deb.debian.org/debian/pool/main/s/shairport-sync/shairport-sync_5.1~dev~git20260518-1.debian.tar.xz"
DEBIAN_AIRPLAY_SHA256 = "0de7ff590298c3b1384ef37e6676fb898d8d2a22f34e62801461f1182aed0fc0"


def run(command, **kwargs):
    print("+ " + shlex.join(map(str, command)), flush=True)
    return subprocess.run(list(map(str, command)), check=True, **kwargs)


def capture(command, **kwargs):
    return subprocess.check_output(list(map(str, command)), text=True, **kwargs).strip()


def package_filename(package):
    return f"{package['name']}_{package['package_version']}_arm64.deb"


def checkout(package):
    source = Path("/cache/sources") / package["source_commit"]
    if not (source / ".git").exists():
        source.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".checkout-", dir=source.parent) as directory:
            repo = Path(directory) / "source"
            run(["git", "init", "--quiet", repo])
            run(["git", "-C", repo, "remote", "add", "origin", package["source_url"]])
            run(["git", "-C", repo, "fetch", "--depth=1", "origin", package["source_commit"]])
            run(["git", "-C", repo, "checkout", "--detach", "FETCH_HEAD"])
            repo.rename(source)
    if capture(["git", "-C", source, "rev-parse", "HEAD"]) != package["source_commit"]:
        raise ValueError("Cached source commit mismatch")
    if capture(["git", "-C", source, "status", "--porcelain", "--untracked-files=all"]):
        raise ValueError("Cached sources have been modified; use a fresh cache volume")
    return source


def build_environment(source, package, jobs):
    env = os.environ.copy()
    env.update(package.get("build_env", {}))
    env["RUSTUP_TOOLCHAIN"] = package.get("rust_toolchain", env["RUSTUP_TOOLCHAIN"])
    env.update(CARGO_BUILD_JOBS=str(jobs), DEB_BUILD_OPTIONS=f"parallel={jobs} nocheck",
               DEB_BUILD_PROFILES="nocheck", DEB_HOST_ARCH="arm64")
    env["SOURCE_DATE_EPOCH"] = capture(["git", "-C", source, "show", "-s", "--format=%ct", "HEAD"])
    return env


def stage_binary(source, package, binary, root, work, env, extra_depends=""):
    """Package a daemon with cross-derived dependencies and no auto-start."""
    name = package["name"]
    installed = root / "usr/bin" / name
    installed.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(binary, installed)
    installed.chmod(0o755)
    run(["aarch64-linux-gnu-strip", installed])
    debian = work / "debian"
    debian.mkdir(exist_ok=True)
    (debian / "control").write_text(f"Source: {name}\n\nPackage: {name}\nArchitecture: any\nDescription: moOde renderer\n")
    output = capture(["dpkg-shlibdeps", "-O", "-l/usr/lib/aarch64-linux-gnu",
                      "-l/lib/aarch64-linux-gnu", "-e" + str(installed)], cwd=work, env=env)
    depends = next(line.split("=", 1)[1] for line in output.splitlines() if line.startswith("shlibs:Depends="))
    if extra_depends:
        depends += ", " + extra_depends
    control = root / "DEBIAN"
    control.mkdir()
    (control / "control").write_text(
        f"Package: {name}\nVersion: {package['package_version']}\nArchitecture: arm64\n"
        "Maintainer: moOde renderer cross-compiler <noreply@github.com>\n"
        f"Section: sound\nPriority: optional\nDepends: {depends}\n"
        f"Description: {name} renderer for moOde audio player\n")
    doc = root / "usr/share/doc" / name
    doc.mkdir(parents=True, exist_ok=True)
    for filename in ["LICENSE", "LICENSE.md", "COPYING", "README.md"]:
        if (source / filename).is_file():
            shutil.copy2(source / filename, doc / filename)
    if name == "nqptp":
        unit = root / "lib/systemd/system/nqptp.service"
        unit.parent.mkdir(parents=True, exist_ok=True)
        unit.write_text("[Unit]\nDescription=NQPTP -- Not Quite PTP\nWants=network-online.target\n"
                        "After=network.target network-online.target\nBefore=shairport-sync.service\n\n"
                        "[Service]\nExecStart=/usr/bin/nqptp\nUser=root\nGroup=root\n\n"
                        "[Install]\nWantedBy=multi-user.target\n")
        for script in ["postinst", "postrm"]:
            path = control / script
            path.write_text("#!/bin/sh\nset -e\nif [ -d /run/systemd/system ]; then\n"
                            "    systemctl daemon-reload\nfi\n")
            path.chmod(0o755)
    deb = work / package_filename(package)
    run(["dpkg-deb", "--root-owner-group", "--build", root, deb], env=env)
    return deb


def build_cargo(source, package, profile, stage, work, env):
    for directory in ["registry", "git"]:
        dest = Path("/cache") / directory
        dest.mkdir(exist_ok=True)
        link = Path("/usr/local/cargo") / directory
        if not link.exists():
            link.symlink_to(dest, target_is_directory=True)
    if package["name"] != "librespot":
        env["CARGO_TARGET_DIR"] = "/cache/targets/" + package["source_commit"]
    workspace = source / package["workspace"]
    args = ["cargo", "build", "--release", "--locked", "--target", profile["target"],
            "--package", package["cargo_package"]]
    if package["features"]:
        args += ["--features", ",".join(package["features"])]
    run(args, cwd=workspace, env=env)
    deb = stage / package_filename(package)
    if package["build_system"] == "cargo-deb":
        run(["cargo", "deb", "--no-build", "--target", profile["target"],
             "--package", package["cargo_package"], "--deb-version", package["package_version"],
             "--output", deb], cwd=workspace, env=env)
    else:
        binary = Path(env["CARGO_TARGET_DIR"]) / profile["target"] / "release" / package["name"]
        built = stage_binary(source, package, binary, work / "root", work, env)
        shutil.copy2(built, deb)
    return {"rustc": capture(["rustc", "--version"], env=env),
            "cargo_lock_sha256": hashlib.sha256((workspace / "Cargo.lock").read_bytes()).hexdigest(),
            "default_features": True, "features": package["features"], "build_env": package.get("build_env", {})}


def debian_airplay():
    archive = Path("/cache") / (DEBIAN_AIRPLAY_SHA256 + ".tar.xz")
    if not archive.exists():
        with urllib.request.urlopen(DEBIAN_AIRPLAY_URL, timeout=60) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != DEBIAN_AIRPLAY_SHA256:
            raise ValueError("AirPlay Debian packaging archive checksum mismatch")
        archive.write_bytes(data)
    data = archive.read_bytes()
    if hashlib.sha256(data).hexdigest() != DEBIAN_AIRPLAY_SHA256:
        raise ValueError("Cached AirPlay Debian packaging archive checksum mismatch")
    return data


def build_native(source, package, stage, work, env, jobs):
    # Sources stay pristine. Native packages are cached against recipe + toolchain.
    key = hashlib.sha256(json.dumps(package, sort_keys=True).encode() + Path(__file__).read_bytes()
                         + (Path(__file__).parent / "toolchain-packages.tsv").read_bytes()).hexdigest()
    cache = Path("/cache/native") / key
    cache.mkdir(parents=True, exist_ok=True)
    cached = cache / package_filename(package)
    if not cached.exists():
        tag = "refs/tags/" + package["source_tag"]
        run(["git", "-C", source, "fetch", "--depth=1", "origin", f"{tag}:{tag}"])
        if capture(["git", "-C", source, "rev-parse", tag + "^{commit}"]) != package["source_commit"]:
            raise ValueError("Upstream tag no longer matches the pinned commit")
        tree = work / "source"
        shutil.copytree(source, tree)
        if package["build_system"] == "shairport":
            with tarfile.open(fileobj=io.BytesIO(debian_airplay()), mode="r:xz") as archive:
                archive.extractall(tree, filter="data")
            rules_path = tree / "debian/rules"
            rules = rules_path.read_text()
            if package["source_tag"] == "5.0.4":
                # This release ships its man page but does not regenerate it.
                rules = rules.replace("execute_after_dh_auto_clean:\n\trm -f man/shairport-sync.1 man/shairport-sync.html\n", "")
            for option in ["libdaemon", "jack", "pulseaudio", "pipewire", "convolution"]:
                rules = rules.replace("--with-" + option + " ", "--without-" + option + " ")
            rules_path.write_text(rules)
            # Local rebuilding, with the exact moOde package version.
            env.update(DEBFULLNAME="moOde renderer cross-compiler", DEBEMAIL="noreply@github.com")
            run(["dch", "--force-bad-version", "--newversion", package["package_version"], "Cross-build for moOde."], cwd=tree, env=env)
            run(["dpkg-buildpackage", "--host-arch=arm64", "-b", "-us", "-uc", "-d"], cwd=tree, env=env)
            built = work / package_filename(package)
        else:
            run(["autoreconf", "-fi"], cwd=tree, env=env)
            run(["./configure", "--host=aarch64-linux-gnu", "--build=x86_64-linux-gnu", "--prefix=/usr"], cwd=tree, env=env)
            run(["make", f"-j{jobs}"], cwd=tree, env=env)
            built = stage_binary(source, package, tree / "nqptp", work / "root", work, env)
        temporary = cache / (cached.name + ".partial")
        shutil.copy2(built, temporary)
        temporary.replace(cached)
    else:
        print(f"Reusing cached native package: {package['name']} {package['package_version']}")
    shutil.copy2(cached, stage / cached.name)
    return {"debian_packaging_sha256": DEBIAN_AIRPLAY_SHA256} if package["build_system"] == "shairport" else {}


def inspect_package(package, stage, work):
    deb = stage / package_filename(package)
    extracted = work / "extracted"
    run(["dpkg-deb", "-x", deb, extracted])
    binary = stage / package["name"]
    shutil.copy2(extracted / "usr/bin" / package["name"], binary)
    if "AArch64" not in capture(["aarch64-linux-gnu-readelf", "-h", binary]):
        raise ValueError("Expected an AArch64 ELF binary")
    if "/lib/ld-linux-aarch64.so.1" not in capture(["aarch64-linux-gnu-readelf", "-l", binary]):
        raise ValueError("Unexpected ARM64 interpreter")
    version = capture(["dpkg-deb", "-f", deb, "Version"])
    arch = capture(["dpkg-deb", "-f", deb, "Architecture"])
    depends = capture(["dpkg-deb", "-f", deb, "Depends"])
    if (version, arch) != (package["package_version"], "arm64") or not depends:
        raise ValueError("Incorrect Debian package metadata")
    print(f"Verified {package['name']}: {version}; dependencies: {depends}")
    return {"depends": depends, "dynamic_libraries": re.findall(r"Shared library: \[(.*?)\]",
            capture(["aarch64-linux-gnu-readelf", "-d", binary]))}


def build_package(package, profile, stage, jobs):
    source = checkout(package)
    env = build_environment(source, package, jobs)
    with tempfile.TemporaryDirectory(prefix="moode-package-") as directory:
        work = Path(directory)
        if package["build_system"].startswith("cargo"):
            details = build_cargo(source, package, profile, stage, work, env)
        else:
            details = build_native(source, package, stage, work, env, jobs)
        details.update(inspect_package(package, stage, work))
    return {**package, **details}
