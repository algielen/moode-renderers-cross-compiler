"""Container entrypoint: profile selection, cross-build, and read-only Pi checks."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
PROFILE_DIR = ROOT / "profiles"
REQUIRED_OPTIONS = [
    "--name", "--bitrate", "--format", "--dither", "--mixer",
    "--initial-volume", "--volume-ctrl", "--volume-range",
    "--enable-volume-normalisation", "--normalisation-method",
    "--normalisation-gain-type", "--normalisation-pregain",
    "--normalisation-threshold", "--normalisation-attack",
    "--normalisation-release", "--normalisation-knee", "--autoplay",
    "--zeroconf-port", "--cache", "--disable-audio-cache", "--backend",
    "--device", "--onevent",
]


def profiles():
    return [json.loads(path.read_text()) for path in sorted(PROFILE_DIR.glob("*.json"))]


def select_profile(version, model, renderer="librespot"):
    for profile in profiles():
        if version in [profile["moode_version"], *profile["aliases"]]:
            if renderer != profile["renderer"]:
                raise ValueError(f"Unsupported renderer: {renderer}")
            if model not in profile["models"]:
                raise ValueError(f"Unsupported Pi model: {model}. See list-profiles.")
            return profile
    raise ValueError(f"Unsupported moOde release: {version}. See list-profiles.")


def run(command, **kwargs):
    print("+ " + shlex.join(map(str, command)), flush=True)
    return subprocess.run(list(map(str, command)), check=True, **kwargs)


def capture(command, **kwargs):
    return subprocess.check_output(list(map(str, command)), text=True, **kwargs).strip()


def check_help(help_text):
    missing = [option for option in REQUIRED_OPTIONS if option not in help_text]
    if missing:
        raise ValueError("Binary lacks moOde CLI options: " + ", ".join(missing))


def build(args):
    profile = select_profile(args.moode_version, args.pi_model, args.renderer)
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    # Open before doing expensive work; catches permissions and read-only mounts.
    with tempfile.TemporaryFile(dir=out):
        pass
    package = f"librespot_{profile['package_version']}_arm64.deb"
    artifact_names = [package, "librespot", "manifest.json", "SHA256SUMS", "build.log"]
    occupied = [name for name in artifact_names if (out / name).exists()]
    if occupied:
        raise ValueError("Output already contains artifacts; use an empty directory: " + ", ".join(occupied))
    if args.pi_model not in profile["validated_models"]:
        print(f"Note: model {args.pi_model} is compatible with baseline ARM64; see validation status in README.")
    cache = Path("/cache")
    cache.mkdir(exist_ok=True)
    import fcntl
    # One writer per cache. Stable source paths and mtimes let Cargo reuse work.
    with (cache / "build.lock").open("w") as lock, tempfile.TemporaryDirectory(prefix="moode-build-") as work_dir:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("This cache is already in use by another build") from None
        work = Path(work_dir)
        source = cache / "sources" / profile["source_commit"]
        stage = work / "artifacts"
        stage.mkdir()
        log_path = out / "build.failed.log"
        with log_path.open("w") as log:
            command = [sys.executable, __file__, "_compile", "--profile", profile["moode_version"],
                       "--model", args.pi_model, "--source", str(source), "--stage", str(stage),
                       "--jobs", str(args.jobs)]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                print(line, end="", flush=True)
                log.write(line)
            if process.wait():
                raise ValueError(f"Build failed; log saved to {log_path}")
        shutil.copy2(log_path, stage / "build.log")
        entries = []
        for path in sorted(stage.iterdir()):
            entries.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n")
        (stage / "SHA256SUMS").write_text("".join(entries))
        # Finish copying before publishing; SHA256SUMS is the completion marker.
        with tempfile.TemporaryDirectory(prefix=".export-", dir=out) as export_dir:
            export = Path(export_dir)
            for path in stage.iterdir():
                shutil.copy2(path, export / path.name)
            for name in artifact_names:
                if name != "SHA256SUMS":
                    (export / name).replace(out / name)
            (export / "SHA256SUMS").replace(out / "SHA256SUMS")
        log_path.unlink()
    print(f"Built {out / package}")


def compile_renderer(args):
    profile = select_profile(args.profile, args.model)
    source, stage = Path(args.source), Path(args.stage)
    env = os.environ.copy()
    env["CARGO_BUILD_JOBS"] = str(args.jobs)
    # Cache dependencies as well as compiled objects in the optional /cache volume.
    for directory in ["registry", "git"]:
        dest = Path("/cache") / directory
        dest.mkdir(exist_ok=True)
        link = Path("/usr/local/cargo") / directory
        if not link.exists():
            link.symlink_to(dest, target_is_directory=True)
    if not (source / ".git").exists():
        source.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".checkout-", dir=source.parent) as checkout:
            repo = Path(checkout) / "source"
            run(["git", "init", "--quiet", repo])
            run(["git", "-C", repo, "remote", "add", "origin", profile["source_url"]])
            run(["git", "-C", repo, "fetch", "--depth=1", "origin", profile["source_commit"]])
            run(["git", "-C", repo, "checkout", "--detach", "FETCH_HEAD"])
            repo.rename(source)
    commit = capture(["git", "-C", source, "rev-parse", "HEAD"])
    if commit != profile["source_commit"]:
        raise ValueError("Source commit mismatch")
    if capture(["git", "-C", source, "status", "--porcelain", "--untracked-files=all"]):
        raise ValueError("Cached sources have been modified; use a fresh cache volume")
    env["SOURCE_DATE_EPOCH"] = capture(["git", "-C", source, "show", "-s", "--format=%ct", "HEAD"])
    lock_hash = hashlib.sha256((source / "Cargo.lock").read_bytes()).hexdigest()
    run(["cargo", "build", "--release", "--locked", "--target", profile["target"],
         "--features", ",".join(profile["features"])], cwd=source, env=env)
    package_path = stage / f"librespot_{profile['package_version']}_arm64.deb"
    run(["cargo", "deb", "--no-build", "--target", profile["target"],
         "--deb-version", profile["package_version"], "--output", package_path], cwd=source, env=env)
    # Inspect the actual packaged binary (cargo-deb strips debug information).
    extracted = stage.parent / "packaged"
    run(["dpkg-deb", "-x", package_path, extracted])
    shutil.copy2(extracted / "usr/bin/librespot", stage / "librespot")
    binary = stage / "librespot"
    elf = capture(["aarch64-linux-gnu-readelf", "-h", binary])
    if "AArch64" not in elf:
        raise ValueError("Expected an AArch64 ELF binary")
    loader = capture(["aarch64-linux-gnu-readelf", "-l", binary])
    if "/lib/ld-linux-aarch64.so.1" not in loader:
        raise ValueError("Unexpected ARM64 interpreter")
    dynamic = capture(["aarch64-linux-gnu-readelf", "-d", binary])
    version = capture(["dpkg-deb", "-f", package_path, "Version"])
    arch = capture(["dpkg-deb", "-f", package_path, "Architecture"])
    depends = capture(["dpkg-deb", "-f", package_path, "Depends"])
    if (version, arch) != (profile["package_version"], "arm64") or not depends:
        raise ValueError("Incorrect Debian package metadata")
    manifest = {
        "profile": profile, "pi_model": args.model, "source_commit": commit,
        "compiler_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "cargo_lock_sha256": lock_hash, "rustc": capture(["rustc", "--version"]),
        "cargo": capture(["cargo", "--version"]), "cargo_deb": capture(["cargo", "deb", "--version"]),
        "debian_snapshot": env["DEBIAN_SNAPSHOT"], "rustflags": env["RUSTFLAGS"],
        "default_features": True, "features": profile["features"],
        "depends": depends, "dynamic_libraries": re.findall(r"Shared library: \[(.*?)\]", dynamic),
        "toolchain_packages": (Path(__file__).parent / "toolchain-packages.tsv").read_text().splitlines(),
    }
    (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Verified ARM64 package; dependencies: {depends}")


REMOTE_INSPECT = r"""set -eu
printf 'MODEL='; tr -d '\000' < /proc/device-tree/model; printf '\n'
printf 'ARCH='; dpkg --print-architecture
printf 'OS='; . /etc/os-release; printf '%s\n' "$VERSION_CODENAME"
printf 'MOODE='; moodeutl --mooderel
printf 'RENDERER_VERSION='; sqlite3 /var/local/www/db/moode-sqlite3.db "SELECT version FROM cfg_plugin WHERE component='renderer' AND type='spotify-connect';"
dpkg-query -W -f='LIBRARY=${binary:Package} ${Version}\n' libc6 libasound2t64 libssl3t64
"""


def ssh_command(client, command):
    _, stdout, stderr = client.exec_command(command, timeout=60)
    output = stdout.read().decode()
    error = stderr.read().decode()
    status = stdout.channel.recv_exit_status()
    if status:
        raise ValueError(f"Remote check failed ({status}): {error.strip()}")
    return output


def inspect_pi(args):
    import paramiko

    host = os.environ.get("RASPBERRY_IP")
    user = os.environ.get("RASPBERRY_USERNAME")
    if not host or not user:
        raise ValueError("Set RASPBERRY_IP and RASPBERRY_USERNAME (optional PORT and PASSWORD).")
    known_hosts = Path(args.known_hosts)
    known_hosts.parent.mkdir(parents=True, exist_ok=True)
    with paramiko.SSHClient() as client:
        if known_hosts.exists():
            client.load_host_keys(str(known_hosts))
        if args.accept_new_host_key:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        port = int(os.environ.get("RASPBERRY_PORT", "22"))
        # Try all DNS addresses, including IPv4 after unreachable link-local IPv6.
        connection = socket.create_connection((host, port), timeout=15)
        try:
            client.connect(host, port=port, username=user, sock=connection,
                           password=os.environ.get("RASPBERRY_PASSWORD") or None,
                           timeout=15, banner_timeout=15, auth_timeout=15,
                           look_for_keys=False, allow_agent=False)
        except Exception:
            connection.close()
            raise
        if args.accept_new_host_key:
            client.save_host_keys(str(known_hosts))
        output = ssh_command(client, REMOTE_INSPECT)
        print(output, end="")
        if args.moode_version:
            profile = select_profile(args.moode_version, args.pi_model)
            values = dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
            if values.get("ARCH") != profile["architecture"] or values.get("OS") != profile["distribution"]:
                raise ValueError("Pi architecture/OS does not match the selected profile")
            # moodeutl includes a release date after the version on some images.
            if profile["moode_version"] not in values.get("MOODE", "").split():
                raise ValueError("Pi moOde release does not match the selected profile")
            if values.get("RENDERER_VERSION") != profile["package_version"]:
                raise ValueError("Pi expects a different renderer package version")
            model_patterns = {
                "3b+": "Raspberry Pi 3 Model B Plus", "3b": "Raspberry Pi 3 Model B Rev",
                "3a+": "Raspberry Pi 3 Model A Plus", "4b": "Raspberry Pi 4 Model B",
                "400": "Raspberry Pi 400", "5": "Raspberry Pi 5 Model B",
                "500": "Raspberry Pi 500", "zero2w": "Raspberry Pi Zero 2 W",
                "cm3": "Raspberry Pi Compute Module 3 Rev", "cm3+": "Raspberry Pi Compute Module 3 Plus",
                "cm4": "Raspberry Pi Compute Module 4 Rev", "cm5": "Raspberry Pi Compute Module 5 Rev",
            }
            if model_patterns[args.pi_model] not in values.get("MODEL", ""):
                raise ValueError("Pi model does not match --pi-model")
            print("Selected profile matches the Pi.")
        if args.binary:
            # mktemp, execute informational flags only, and always remove the upload.
            remote_dir = ssh_command(client, "mktemp -d /tmp/moode-cross-check.XXXXXXXX").strip()
            try:
                with client.open_sftp() as sftp:
                    sftp.put(args.binary, remote_dir + "/librespot")
                    sftp.chmod(remote_dir + "/librespot", 0o755)
                binary = shlex.quote(remote_dir + "/librespot")
                print(ssh_command(client, f"{binary} --version"), end="")
                help_text = ssh_command(client, f"{binary} --help")
                check_help(help_text)
                print("Binary runs on the Pi and supports moOde's renderer CLI options.")
            finally:
                ssh_command(client, f"rm -f -- {shlex.quote(remote_dir + '/librespot')}; rmdir -- {shlex.quote(remote_dir)}")


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list-profiles", help="List supported releases and model names")
    build_parser = commands.add_parser("build", help="Cross-compile and export a renderer package")
    build_parser.add_argument("--renderer", choices=["librespot"], default="librespot")
    build_parser.add_argument("--pi-model", required=True)
    build_parser.add_argument("--moode-version", required=True)
    build_parser.add_argument("--output", default="/out")
    build_parser.add_argument("--jobs", type=positive_int, default=positive_int(os.environ.get("CARGO_BUILD_JOBS", "2")))
    inspect_parser = commands.add_parser("inspect-pi", help="Read-only SSH compatibility and optional binary check")
    inspect_parser.add_argument("--known-hosts", default="/cache/known_hosts")
    inspect_parser.add_argument("--accept-new-host-key", action="store_true", help="Trust an unknown host on first use; changed keys are rejected")
    inspect_parser.add_argument("--moode-version")
    inspect_parser.add_argument("--pi-model")
    inspect_parser.add_argument("--binary", help="Upload binary temporarily and run --version/--help")
    internal = commands.add_parser("_compile", help="Internal build worker")
    for argument in ["profile", "model", "source", "stage"]:
        internal.add_argument("--" + argument, required=True)
    internal.add_argument("--jobs", type=positive_int, required=True)
    args = parser.parse_args()
    if args.command == "inspect-pi" and bool(args.moode_version) != bool(args.pi_model):
        parser.error("--moode-version and --pi-model must be supplied together")
    try:
        if args.command == "list-profiles":
            for profile in profiles():
                print(f"{profile['moode_version']} ({', '.join(profile['aliases'])}): "
                      f"{profile['renderer']} {profile['package_version']}, {profile['distribution']} ARM64")
                print("  Pi models: " + ", ".join(profile["models"]))
                print("  Validated models: " + (", ".join(profile["validated_models"]) or "pending"))
        elif args.command == "build":
            build(args)
        elif args.command == "_compile":
            compile_renderer(args)
        else:
            import paramiko
            try:
                inspect_pi(args)
            except paramiko.SSHException as error:
                raise ValueError(f"SSH: {error}") from None
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
