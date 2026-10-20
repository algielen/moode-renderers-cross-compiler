# Repository guide

## Purpose and boundaries

Build moOde's on-demand renderer packages on an AMD64 workstation for a Raspberry Pi running Trixie ARM64. The container must carry the toolchains; users should only need Docker or `wslc`. Keep documentation short and usable.

- Prefer PowerShell and `wslc` on this Windows machine. Docker is the equivalent interface on Linux and in CI. WSL alone is not a container engine.
- Compile with native AMD64 tools targeting AArch64. Use QEMU for runtime checks only. Preserve baseline ARM64 compatibility; do not use `-march=native` or host-specific Rust CPU tuning.
- Keep `.env`, credentials, build outputs, caches and IDE files out of commits and the Docker build context. Mount only the directories needed by a tool.
- Preserve unrelated user changes. Do not prune unrelated images, containers or volumes.
- Physical Pi checks are read-only unless the user explicitly requests installation: informational flags and temporary uploads only, with cleanup. Do not install packages, change settings or start/restart renderers for routine validation.

## Where things live

- `profiles/*.json`: release compatibility, aliases and pinned renderer sources.
- `compiler/cli.py`: profile selection, output publication, manifests and SSH inspection.
- `compiler/recipes.py`: Rust/native cross-builds, Debian packaging and ELF/dependency checks.
- `Dockerfile`: pinned compiler image, Debian snapshot, toolchains and target development libraries.
- `tests/`: profile/failure tests, full build matrix and disposable-container installation checks.
- `tests/select_profiles.py`: CI selection of profiles using the event's Git baseline.
- `docs/profiles.md`: release audit and source links. `docs/validation.md`: measured validation and its limits.
- `.github/workflows/build.yml`: CI matrix runner, default release artifacts and GHCR publishing.

## Creating a release profile

1. **Audit the actual moOde release.** Resolve its release tag to a full commit SHA. At that commit, inspect `var/local/www/db/moode-sqlite3.db.sql`, `www/inc/renderer.php`, `usr/local/bin/moodeutl` and `www/relnotes.txt`. Record the renderer's availability, package name/version, launch arguments and installation contract. Use the matching historical recipes in `moode-player/pkgbuild`; current `master` may describe a newer build.
2. **Copy the closest existing profile** to `profiles/<moode-version>.json`. Set `moode_version`, tag `aliases` and the canonical `moode_commit`. Keep aliases unique across profiles. Share a profile between original/fixed images only after checking all renderer contracts agree; otherwise update selection logic and tests to represent the difference.
3. **Verify the platform.** `distribution`, `architecture`, Rust `target` and `models` must describe the actual image. A different distribution/ABI or ARM32 target needs a compatible toolchain and libraries, not just changed JSON labels. New model names also need SSH model matching in `compiler/cli.py`.
4. **Populate `renderers` from the release database.** Use `librespot`, `airplay` and/or `qobuz` as keys. `spotify` is a CLI alias for `librespot`, not a separate profile entry. Omit renderers that the release does not support. Reset each renderer's `validated_models` to `[]`; validation of another moOde release does not transfer automatically.
5. **Pin every package.** Use the fields below, matching the release's complete Debian version, including its `moode` revision. Never substitute the latest upstream tag or infer a source tag solely from the package version.

| Package field | Requirement |
| --- | --- |
| `name`, `package_version` | Must produce the exact `<name>_<package_version>_arm64.deb` filename expected by moOde. The executable is installed/exported as `name`. |
| `source_url`, `source_tag`, `source_commit` | Upstream Git URL, matching release/build tag, and its full **commit** SHA. Dereference annotated tags; a tag-object SHA is not the commit. |
| `db_type` | Corresponding `cfg_plugin.type`: `spotify-connect`, `airplay`, `nqptp` or `qobuz-connect`. |
| `build_system` | Existing recipe: `cargo-deb` for librespot, `cargo` for headless Qobuz, `shairport` for shairport-sync, or `nqptp`. Add and test recipe code before introducing another value. |
| `cargo_package`, `workspace`, `features` | Required for Rust recipes. Workspace is relative to the checkout (`.` or, for old qbzd, `crates`). Features add to upstream defaults. Keep the upstream lockfile and `--locked`. |
| `rust_toolchain` | Optional override of the container default. Pin an exact version and install it in the Dockerfile before using it. |
| `build_env` | Optional compile-time identifiers required by that upstream build, such as `QBZD_BUILD_ID`. Do not confuse a binary build ID with the Debian version expected by moOde. |

To inspect a tag, use `git ls-remote --tags <source-url> 'refs/tags/<tag>' 'refs/tags/<tag>^{}'`. When the `^{}` result exists, pin that commit. The build still verifies the checkout against the recorded SHA.

AirPlay must list **both shairport-sync and nqptp**; nqptp's database row has component `system`. Qobuz changes repository/binary from `qbzd` to `pibuz` between existing profiles: preserve the release-specific name, workspace and build ID. Do not replace old qbzd with a current pibuz build.

6. **Update coverage and documentation.** Extend the explicit supported-version set and version/availability assertions in `tests/test_cli.py`. Add an immutable database/source link and version mapping to `docs/profiles.md`, and update README coverage. If the new release becomes the default, also update the workflow's build arguments, artifact names/paths and release archive name. Keep historical profiles unchanged unless correcting an audited error.
7. **Build and validate.** Follow the checks below. Add a model to `validated_models` only after informational binary checks on that model running the selected moOde release. Record exactly what was tested in `docs/validation.md`; CLI execution is not a discovery/audio playback test.

## Checks

Build the compiler and run CLI/profile tests:

```powershell
wslc build -t moode-cross:local .
wslc run --rm --entrypoint python3 moode-cross:local -m unittest discover -s /opt/tests -v
wslc run --rm moode-cross:local list-profiles
```

For a profile-only addition or correction, build the affected versions into a **new, empty** output directory. Use another directory name for a subsequent run; the builder deliberately refuses to overwrite successful artifacts.

```powershell
New-Item -ItemType Directory -Force dist/profile-check | Out-Null
wslc run --rm -v "${PWD}/dist/profile-check:/out" -v moode-build-cache:/cache `
  --entrypoint python3 moode-cross:local /opt/tests/build_profiles.py --versions-json '["10.3.6"]'
```

Replace the version array with the added/modified versions. Omit `--versions-json` for all profiles; use the full matrix after shared compiler/toolchain or build/runtime test changes. This checks manifests, checksums and binary agreement for identical recipes within the selected builds. Verify each changed recipe's ARM64 ELF/interpreter, Debian name/version, runtime dependencies and package assets. Exercise cache reuse when changing cache/build logic. Keep sources pristine and failed builds free of success artifacts, including failure of the second AirPlay component.

CI always runs lightweight CLI/profile tests. Pull requests compare with their merge base, branch pushes with the push event's previous commit, and release tags/manual runs with the preceding release tag. Only added/modified profiles compile, unless shared build/test/workflow files changed, no baseline exists, or the manual **Verify every profile** input is checked. Profile assertion edits in `tests/test_cli.py` alone do not force the full matrix. Releases additionally build the default download profile (currently 10.3.6); update this in `tests/select_profiles.py` when changing release artifact paths in the workflow.

The CI workflow builds `tests/Dockerfile.runtime` and runs every distinct package bundle in clean ARM64 Trixie with QEMU/binfmt support. Local `wslc` may lack ARM binfmt. Its alternative is a disposable compiler container running `tests/runtime.py --emulator qemu-aarch64` against the mounted artifacts; disable service startup there as in `tests/runtime.sh`. Do not install target libraries or emulation infrastructure on the workstation or Pi to run these checks.

After workflow changes, run `actionlint`, mounting only `.github/workflows` into its container. Documentation-only edits do not require rebuilding renderers. Check `git diff --check` and verify documentation paths/commands before finishing.

## Recording build timings

Use a stopwatch around the entire container command for elapsed time. Record renderer/version, CPU, runtime, job count, cache state and whether image downloads/builds are included. Cargo's `Finished ... in ...` reports a build phase, not the total container invocation. Do not present Cargo timings as end-to-end measurements or use copied artifact timestamps as a stopwatch. Keep README figures representative and label their scope; retain detailed observations in `docs/validation.md`.
