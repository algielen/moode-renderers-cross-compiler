"""Export compiler-image source inputs in a disposable container, never on the host.

Run with --entrypoint python3 IMAGE /opt/compiler/image_sources.py --output /out.
SOURCE-MANIFEST.json is written only when every source download has succeeded.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.parse
import urllib.request


def download(url, path, sha1=None, sha256=None):
    if path.is_file() and (sha1 or sha256):
        with path.open("rb") as stream:
            algorithm, expected = ("sha256", sha256) if sha256 else ("sha1", sha1)
            if hashlib.file_digest(stream, algorithm).hexdigest() == expected:
                return
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as response, path.with_suffix(path.suffix + ".partial").open("wb") as stream:
                shutil.copyfileobj(response, stream)
            temporary = path.with_suffix(path.suffix + ".partial")
            for algorithm, expected in (("sha1", sha1), ("sha256", sha256)):
                if expected:
                    with temporary.open("rb") as stream:
                        if hashlib.file_digest(stream, algorithm).hexdigest() != expected:
                            raise ValueError(f"Source checksum mismatch: {url}")
            temporary.replace(path)
            return
        except OSError:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def api(path):
    for attempt in range(4):
        try:
            with urllib.request.urlopen("https://snapshot.debian.org/mr/" + path, timeout=60) as response:
                return json.load(response)
        except OSError:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def source_requirements(rows):
    result = set()
    for binary, version, source, source_version, built_using, static_built_using in rows:
        result.add((source, source_version))
        for field in (built_using, static_built_using):
            if not field:
                continue
            for requirement in field.split(","):
                match = re.fullmatch(r"\s*([a-z0-9+.-]+)\s+\(=\s*([^\s)]+)\)\s*", requirement)
                if not match:
                    raise ValueError(f"Unrecognized Built-Using field: {requirement}")
                result.add(match.groups())
    return sorted(result)


def debian_sources(output):
    fields = ["binary:Package", "Version", "source:Package", "source:Version", "Built-Using", "Static-Built-Using"]
    fmt = "\t".join("${" + field + "}" for field in fields) + "\n"
    rows = [line.split("\t") for line in subprocess.check_output(["dpkg-query", "-W", "-f=" + fmt], text=True).splitlines()]
    (output / "debian-packages.json").write_text(json.dumps([dict(zip(fields, row)) for row in rows], indent=2) + "\n")
    for name, version in source_requirements(rows):
        print(f"Collecting Debian source: {name} {version}", flush=True)
        directory = output / "debian" / (name + "_" + urllib.parse.quote(version, safe=""))
        directory.mkdir(parents=True, exist_ok=True)
        query = "package/" + urllib.parse.quote(name, safe="") + "/" + urllib.parse.quote(version, safe="") + "/srcfiles"
        files = api(query)["result"]
        if not files:
            raise ValueError(f"Missing Debian source: {name} {version}")
        for item in files:
            info = api("file/" + item["hash"] + "/info")["result"][0]
            filename = info["name"]
            if Path(filename).name != filename or "\\" in filename:
                raise ValueError("Invalid source filename")
            download("https://snapshot.debian.org/file/" + item["hash"], directory / filename, sha1=item["hash"])
        # Verify the content SHA-256s declared by the source control file as well.
        dscs = list(directory.glob("*.dsc"))
        if len(dscs) != 1:
            raise ValueError("Expected exactly one Debian source control file")
        text = dscs[0].read_text()
        section = re.search(r"^Checksums-Sha256:\n((?: [^\n]+\n)+)", text, re.MULTILINE)
        if not section:
            raise ValueError("Missing source SHA-256 checksums")
        # Snapshot indexes a blob under several historical filenames. The .dsc
        # specifies the names required to reconstruct this particular version.
        blobs = {}
        for path in directory.iterdir():
            if path.is_file():
                with path.open("rb") as stream:
                    blobs[hashlib.file_digest(stream, "sha256").hexdigest()] = path
        for line in section[1].splitlines():
            expected, size, filename = line.split()
            if Path(filename).name != filename:
                raise ValueError("Invalid source checksum filename")
            path = directory / filename
            if not path.exists() and expected in blobs:
                shutil.copy2(blobs[expected], path)
            with path.open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != expected or path.stat().st_size != int(size):
                    raise ValueError(f"Debian source checksum mismatch: {filename}")


def cargo_sources(output, name, version, url):
    directory = output / name
    directory.mkdir(exist_ok=True)
    archive = directory / "upstream.tar.gz"
    download(url, archive)
    with tempfile.TemporaryDirectory() as extraction:
        with tarfile.open(archive) as tar:
            tar.extractall(extraction, filter="data")
        roots = list(Path(extraction).iterdir())
        if len(roots) != 1 or not (roots[0] / "Cargo.lock").is_file():
            raise ValueError(f"Missing locked {name} source")
        tree = directory / "source"
        shutil.copytree(roots[0], tree, dirs_exist_ok=True)
    with tempfile.TemporaryDirectory() as cargo_home:
        env = dict(os.environ, CARGO_HOME=cargo_home)
        config = subprocess.check_output(["cargo", "vendor", "--locked", "--versioned-dirs", str(directory / "vendor")],
                                         cwd=tree, env=env, text=True)
        config_path = directory / "cargo-vendor-config.toml"
        config_path.write_text(config)
        subprocess.run(["cargo", "--config", str(config_path), "metadata", "--offline", "--locked", "--format-version", "1"],
                       cwd=tree, env=dict(env, CARGO_HOME=cargo_home + "/empty"), check=True, stdout=subprocess.DEVNULL)
    (directory / "cargo-vendor-config.toml").write_text(config.replace(str(directory / "vendor"), "vendor"))
    (directory / "version.txt").write_text(version + "\n")


def component_notices(output):
    from compliance import inline_notice_files, notice_files

    for name in ("cargo-deb", "rustup"):
        source = output / name
        for path in notice_files(source):
            destination = output / "notices" / path.relative_to(output)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
        for path in inline_notice_files(source):
            destination = output / "notices/inline" / path.relative_to(output)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)


def collect(output, resume=False):
    output = output.resolve()
    if (output / "SOURCE-MANIFEST.json").exists():
        raise ValueError("Output already contains completed materials; use another directory")
    if any(output.iterdir()) and not resume:
        raise ValueError("Use a new empty output directory")
    debian_sources(output)
    compiler = Path(__file__).resolve().parent
    shutil.copytree(compiler, output / "build-scripts/compiler", dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("Dockerfile", "LICENSE"):
        shutil.copy2(compiler.parent / name, output / "build-scripts" / name)
    for name in ("profiles", "tests"):
        shutil.copytree(compiler.parent / name, output / "build-scripts" / name, dirs_exist_ok=True)
    (output / "build-scripts/docs").mkdir(exist_ok=True)
    shutil.copy2(compiler / "THIRD-PARTY.md", output / "build-scripts/docs/licensing.md")
    for copyright_file in Path("/usr/share/doc").glob("*/copyright"):
        dest = output / "notices/debian" / copyright_file.parent.name / "copyright"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(copyright_file, dest)
    shutil.copytree("/usr/share/common-licenses", output / "notices/common-licenses", dirs_exist_ok=True)
    toolchains = subprocess.check_output(["rustup", "toolchain", "list"], text=True).splitlines()
    for toolchain in toolchains:
        toolchain = toolchain.split()[0]
        version = subprocess.check_output(["rustc", "+" + toolchain, "--version"], text=True).split()[1]
        name = f"rustc-{version}-src.tar.xz"
        url = "https://static.rust-lang.org/dist/" + name
        with urllib.request.urlopen(url + ".sha256", timeout=60) as response:
            checksum = response.read().decode().split()[0]
        download(url, output / name, sha256=checksum)
        sysroot = Path(subprocess.check_output(["rustc", "+" + toolchain, "--print", "sysroot"], text=True).strip())
        shutil.copytree(sysroot / "share/doc/rust", output / "notices" / toolchain, dirs_exist_ok=True)
    cargo_version = subprocess.check_output(["cargo", "deb", "--version"], text=True).split()[1]
    cargo_sources(output, "cargo-deb", cargo_version,
                  f"https://static.crates.io/crates/cargo-deb/cargo-deb-{cargo_version}.crate")
    rustup_version = subprocess.check_output(["rustup", "--version"], text=True)
    rustup = rustup_version.split()[1]
    prefix = re.search(r"\(([0-9a-f]+) ", rustup_version)[1]
    refs = subprocess.check_output(["git", "ls-remote", "--tags", "https://github.com/rust-lang/rustup.git",
                                    f"refs/tags/{rustup}", f"refs/tags/{rustup}^{{}}"], text=True).splitlines()
    commit = next((line.split()[0] for line in refs if line.endswith("^{}")), refs[0].split()[0] if refs else "")
    if not commit.startswith(prefix):
        raise ValueError("Rustup source tag does not match the installed binary commit")
    cargo_sources(output, "rustup", rustup, f"https://github.com/rust-lang/rustup/archive/{commit}.tar.gz")
    (output / "rustup/commit.txt").write_text(commit + "\n")
    component_notices(output)
    (output / "SOURCE.txt").write_text(
        "Compiler image source supplement. Debian directories contain exact source package inputs,\n"
        "including Built-Using and Static-Built-Using declarations. Retain all original notices.\n"
        "Rust source distributions include their bundled dependencies. cargo-deb/ and rustup/\n"
        "contain upstream sources and the complete locked Cargo vendor closure.\n"
        "This inventory is collection evidence, not an assertion of license approval.\n"
        "Record the inspected OCI digest alongside SOURCE-MANIFEST.json when publishing.\n")
    hashes = {}
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name not in ("SOURCE-MANIFEST.json", ".SOURCE-MANIFEST.partial"):
            with path.open("rb") as stream:
                hashes[path.relative_to(output).as_posix()] = hashlib.file_digest(stream, "sha256").hexdigest()
    marker = output / ".SOURCE-MANIFEST.partial"
    marker.write_text(json.dumps(hashes, indent=2) + "\n")
    marker.replace(output / "SOURCE-MANIFEST.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("/out"))
    parser.add_argument("--resume", action="store_true", help="Revalidate and reuse interrupted Debian downloads")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    collect(args.output, args.resume)
