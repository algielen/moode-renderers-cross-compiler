# moOde renderer cross-compiler

Build a moOde renderer on your PC, then copy its Debian package to your Raspberry Pi. The Pi does no compilation.

Supports **librespot (Spotify Connect), moOde 10.2.0–10.3.6, Trixie ARM64**. The compiler runs on an AMD64 Linux container host, including Windows with Docker Desktop or WSL's `wslc`. Plain WSL needs a container engine; WSL alone is insufficient. No host Rust or Python installation is needed.

## Build a renderer

After the first release is published:

```bash
mkdir -p dist
docker run --rm \
  -v "$PWD/dist:/out" \
  ghcr.io/algielen/moode-renderers-cross-compiler:v1 \
  build --pi-model 3b+ --moode-version 10.3.6
```

PowerShell with `wslc` (substitute `docker` if preferred):

```powershell
New-Item -ItemType Directory -Force dist | Out-Null
wslc run --rm `
  -v "${PWD}/dist:/out" `
  ghcr.io/algielen/moode-renderers-cross-compiler:v1 `
  build --pi-model 3b+ --moode-version 10.3.6
```

Set `--moode-version` to your installed release. Release tags such as `r1020`, `r1020fix`, and `r1036` are also accepted. These inputs select the architecture, source commit, dependencies, and package version; they do not build the latest upstream release. See the [release profiles](docs/profiles.md) for the full list. Unsupported releases and models fail before compilation.

Output in `dist/`:

- `librespot_0.8.0-1moode1_arm64.deb`: installable package.
- `librespot`: standalone ARM64 executable.
- `manifest.json`, `SHA256SUMS`, `build.log`: build provenance, checksums, and log.

Use an empty output directory for each build. Failed compilation leaves `build.failed.log` and no success artifacts. Start with two build jobs (default); use `--jobs 4` if the container has sufficient RAM. Allow several GB of disk space for the image and build cache. Source and dependency downloads require Internet access.

For faster rebuilds, add a persistent cache:

```bash
docker run --rm -v "$PWD/dist:/out" -v moode-build-cache:/cache \
  ghcr.io/algielen/moode-renderers-cross-compiler:v1 \
  build --pi-model 3b+ --moode-version 10.3.6 --jobs 4
```

On Linux, exported files are owned by container root; use `sudo chown -R "$(id -u):$(id -g)" dist` if needed.

## Install on the Pi

Verify `SHA256SUMS` on your workstation, then copy the package to your Pi user's home directory:

```bash
cd dist
sha256sum -c SHA256SUMS
scp -P 22 librespot_0.8.0-1moode1_arm64.deb USER@moode.local:
ssh -p 22 USER@moode.local
```

On the Pi:

```bash
cd ~
sudo moodeutl --installpkg spotify
```

Enable Spotify Connect in moOde's Renderer Config. Installation may need Internet access for runtime libraries and may affect active playback. No build tools are installed on the Pi. Spotify playback requires a Premium account.

The filename and package version must match the Pi's renderer database. All supported releases specify librespot `0.8.0-1moode1`; each profile pins its moOde release commit. See the [profile audit](docs/profiles.md) and moOde's [librespot build recipe](https://github.com/moode-player/pkgbuild/blob/master/packages/librespot/build.sh). Custom upstream versions are outside the supported interface.

## Check compatibility over SSH (optional)

Copy `.env.example` to `.env` and set the four `RASPBERRY_*` values. Keep this file private. Normal builds do not use SSH or receive credentials.

```bash
docker run --rm --env-file .env -v moode-ssh:/cache \
  ghcr.io/algielen/moode-renderers-cross-compiler:v1 \
  inspect-pi --accept-new-host-key --pi-model 3b+ --moode-version 10.3.6
```

`--accept-new-host-key` trusts the first connection and stores its host key in the named volume. Later connections reject changed keys. Omit this option after the first connection. You can instead mount an existing OpenSSH known-hosts file and pass `--known-hosts /path/to/file`.

To check your compiled executable, also mount `dist` read-only and add `--binary /artifacts/librespot`:

```bash
docker run --rm --env-file .env -v moode-ssh:/cache -v "$PWD/dist:/artifacts:ro" \
  ghcr.io/algielen/moode-renderers-cross-compiler:v1 \
  inspect-pi --pi-model 3b+ --moode-version 10.3.6 --binary /artifacts/librespot
```

Inspection reads system information. Binary checking uploads to a temporary directory, runs `--version` and `--help`, and removes the upload. It never installs a package or starts playback. If `moode.local` cannot resolve inside the container, set `RASPBERRY_IP` to the Pi's LAN IPv4 address.

## Supported targets and validation

```bash
docker run --rm ghcr.io/algielen/moode-renderers-cross-compiler:v1 list-profiles
```

Profiles use generic ARM64 instructions and accept Pi `3b`, `3b+`, `3a+`, `4b`, `400`, `5`, `500`, `zero2w`, `cm3`, `cm3+`, `cm4`, and `cm5`, **running the specified 64-bit moOde image**. Model selection checks compatibility; it does not tune the binary for that CPU. ARM32 and releases outside the profile list are unsupported.

Hardware validation status is recorded in [docs/validation.md](docs/validation.md). CLI execution confirms loading and supported options; it does not establish Spotify discovery or successful audio playback.

## Build the compiler locally

```bash
git clone https://github.com/algielen/moode-renderers-cross-compiler.git
cd moode-renderers-cross-compiler
docker build -t moode-cross:local .
docker run --rm -v "$PWD/dist:/out" moode-cross:local \
  build --pi-model 3b+ --moode-version 10.3.6
```

On Windows run the same build with `wslc build -t moode-cross:local .`, then use the PowerShell mount syntax above. Run commands in PowerShell rather than Git Bash to avoid container-path rewriting.

## Development and releases

The build pins its Rust base image by digest, Rust 1.90.0, cargo-deb 3.8.0, a Debian package snapshot, and the librespot commit. Cargo uses its upstream lockfile. The manifest records the exact installed tool versions. Pinning inputs does not promise byte-identical binaries across hosts.

Run the CLI tests inside the compiler:

```bash
docker run --rm --entrypoint python3 moode-cross:local -m unittest discover -s /opt/tests -v
```

Pull requests and branch pushes build every supported release profile, check cache reuse, and install the default package inside a disposable ARM64 Trixie container. QEMU is used only for runtime tests; compilation uses the native AMD64 toolchain.

Push a tag such as `v1.0.0` to run the release workflow. Once checks pass, it publishes `ghcr.io/algielen/moode-renderers-cross-compiler:v1.0.0`, `:v1`, and `:latest`, and creates a GitHub release containing the renderer artifacts. The repository must permit GitHub Actions to publish packages and releases. After the first publication, set the GHCR package visibility to **Public** in its package settings. Exact release tags or image digests give stable references; `v1` and `latest` move with releases.

AirPlay, Qobuz, releases before 10.2.0, and custom source overrides are deferred. Add future renderers as separate recipes and compatibility profiles.
