# Validation

Target: Raspberry Pi 3B+, moOde 10.3.6 (r1036), Raspberry Pi OS Trixie ARM64.

Validated locally on 2026-10-20 using Windows PowerShell and `wslc` 3.0.3.0:

- Compiler image built from its pinned base and Debian snapshot.
- Clean librespot cross-build completed with four jobs; Cargo reported 1 minute 37 seconds.
- Cached build completed without recompiling crates; Cargo reported 0.17 seconds.
- Thirteen CLI/profile/failure-handling tests passed. These include unavailable-renderer rejection and discarding the first AirPlay package if its second component fails. A read-only output mount failed before compilation.
- All 27 release/renderer combinations cross-built using `wslc`: 12 Spotify, 12 AirPlay, and 3 Qobuz. Each manifest and checksum set passed, and equivalent recipes exported identical binaries. Every release/tag alias, including `r1020fix`, resolved to its intended profile.
- AArch64 ELF, dynamic loader, Debian architecture/version, package assets, runtime dependencies, and artifact checksums inspected.
- All seven distinct renderer bundles installed in a disposable AMD64 Trixie container with ARM64 libraries. This covers librespot 0.8.0, shairport-sync 5.0.4 / 5.2.1 / 5.5.1 / 5.5.2 paired with nqptp 1.2.6, qbzd 2.0.2.moode49, and pibuz 2.5.1. Informational version/help flags and dynamic-library loading passed through user-mode QEMU. Service startup was disabled inside the test container.
- SSH inspection confirmed the physical Pi's model, OS, release, and expected renderer package version.
- The latest standalone librespot, shairport-sync, nqptp, and pibuz binaries ran informational version/help flags on the physical Pi. The expected CLI options were present; temporary uploads were removed. Earlier AirPlay versions and qbzd were tested under QEMU only.
- GitHub workflow passed `actionlint`.

The Pi provided libc 2.41, ALSA 1.2.14, and OpenSSL 3.5.4. Runtime dependencies are derived per package and recorded in each schema-2 manifest. Librespot requires ALSA/libc/OpenSSL; pibuz requires ALSA/libc/libgcc. AirPlay additionally links its selected Avahi, FFmpeg, crypto, metadata and messaging libraries; older qbzd also links JACK.

With the user's authorization on 2026-10-20, the physical Pi was upgraded using the cross-built AirPlay packages and `sudo moodeutl --installpkg airplay`: shairport-sync 4.3.7-1moode1 to 5.5.2-1moode1, and nqptp 1.2.4-1moode1 to 1.2.6-1moode1. Artifact checksums passed before upload. The database and shairport configuration were backed up on the Pi before installation. moOde's installer reset AirPlay configuration to its defaults. Both packages reported `install ok installed`, `dpkg --audit` was empty, and informational version checks passed again after a confirmed reboot. AirPlay was initially left disabled after installation, matching its pre-install state.

AirPlay installation and startup validation **passed**. After the user enabled AirPlay, shairport-sync and nqptp ran successfully; TCP 7000 and UDP 319/320 were listening, and Avahi advertised both `_airplay._tcp` and `_raop._tcp` as Moode AirPlay. No startup errors appeared in the service journals, and `/var/log/moode_shairport-sync.log` was empty. moOde launches shairport-sync directly, so its inactive systemd unit does not indicate a failure. The user subsequently stopped the service. Sender connection, audio decoding, synchronization and playback remain untested because no Apple sender was available.

No Spotify or Qobuz package was installed on the physical Pi. Other listed Pi models are compatible targets but have not been tested on hardware.

## Build-time observations

Host: AMD Ryzen 7 5800X3D, 8 cores / 16 logical processors; Windows PowerShell with `wslc` 3.0.3.0. The recorded renderer builds used four jobs and an already-built compiler image.

| Build | Recorded time | Scope / cache state |
| --- | --- | --- |
| librespot 0.8.0 | 1 min 37 sec | Initial Cargo release build, with no compiled renderer artifacts cached |
| pibuz 2.5.1 | 2 min 38 sec | Cargo release build using Rust 1.94; source/dependency downloads were warmed by the earlier Rust 1.90 attempt |
| qbzd 2.0.2.moode49 | 4 min 08 sec | Initial Cargo release build using Rust 1.94; shared dependency downloads were already partly cached |
| librespot 0.8.0, cached | 0.17 sec | Cargo phase only; no crates recompiled |
| AirPlay 5.5.2 + nqptp 1.2.6 | 26.85 sec | Stopwatch around the entire successful `wslc run`, fresh named cache volume, including checkout/downloads, compilation, packaging and export |

The AirPlay wall-clock measurement was taken on 2026-10-20 with `--renderer airplay --moode-version 10.3.6 --pi-model 3b+ --jobs 4`. Its exit code was zero, and the temporary cache volume was removed afterward. Raw timing/log artifacts are under ignored `dist/timings/`. The Cargo timings come from the corresponding completed build logs. Do not interpret them as whole-command measurements, include compiler-image setup in them, or compare these examples as a controlled benchmark across renderers.

## Licensing remediation validation (2026-10-20)

The local compiler image with source/notice export passed 29 unit tests, all 27
profile/renderer builds, archive/manifest checksum checks and binary agreement for
equivalent recipes. Exported sources for all eight distinct component versions were
checked; all three Cargo applications resolved their exported lockfiles/vendor trees
offline with an empty Cargo home and networking disabled. Every distinct renderer
bundle installed and passed informational version/help and dynamic-library checks in
a disposable compiler container using `qemu-aarch64`, with service startup disabled.
No physical Pi changes were made for this work. Workflow `actionlint` passed.

All four original v0.1.1 executables matched the rebuilt executables byte for byte.
The original published compiler image's Debian inventory matched the collected source
inputs, all 36,163 material hashes verified, and the original tag's build-script hashes
matched the published manifests. The updated image collector's cargo-deb and pinned
rustup source export paths also passed locked offline metadata resolution.
These checks establish correspondence and integrity, not blanket license clearance.
Ignored logs/materials are under `dist/licensing-*`; see [licensing.md](licensing.md)
for delivery status and outstanding review.

## Follow-up licensing validation

The follow-up notice/artifact collection passed all 27 profile/renderer builds,
manifest/archive checksum checks and equivalent-recipe binary comparisons in
`dist/licensing-review-matrix-02`. All eight distinct component source exports
passed checks, including locked offline Cargo resolution with an empty Cargo home.
All seven distinct bundles installed and passed informational help/version and
library checks with `qemu-aarch64` in a disposable compiler container; service
startup was disabled. These are not playback or discovery checks.

The final tooling image passed 42 unit tests as UID/GID 65534 without networking.
This includes inline-notice retention, compiler component notices, offered-license
expression handling and actual-build inventory checks. The three Cargo reports
are review proposals; unresolved qbzd metadata and the AirPlay header question are
recorded in [licensing.md](licensing.md). No release, image or maintainer message
was published, and no physical Pi was changed. The updated compiler-image notice
export has unit coverage but has not yet been collected into a new delivery bundle.

## CI performance changes

Run `39497717932` reached the former 60-minute limit after 26 of 27 builds; the
last source/notice export was interrupted. The matrix ran 46m21s. Warm librespot
compilation took 0.21–0.25s per profile, but each whole warm build took 111–113s;
the twelve matrix invocations consumed about 22m24s. Runtime/source checks had not
started. These observations distinguish compilation from repeated export work.

A single-thread gzip benchmark used the same 1,031,188,480-byte librespot source
tar payload on Ryzen 7 5800X3D, WSL2, Python 3.13.5/zlib 1.3.1. Level 6 took
11.245s and produced 111,673,756 bytes; level 9 took 30.227s and produced
108,887,186 bytes. Decompressed SHA-256s matched. This measures compression only,
excluding startup, initial decompression and verification; it is not a build timing.

Companion archives now use level 6, and logs time copying, vendoring, metadata,
notice discovery, compression and Debian repacking separately. CI splits selected
profiles into renderer jobs with separate caches. Aggregate verification checks
exact planned coverage and equivalent-recipe binary hashes, then binds release
files to approved hashes. Empty Qobuz selections are omitted; documentation-only
plans skip builds. Normal full verification retains the entire matrix and all
runtime/source checks. The explicit profile-only smoke option validates only its
selected profile and labels the resulting unpublished draft accordingly.
Unit checks cover missing/duplicate reports, recipe/hash mismatches and extra or
modified release files. CI end-to-end savings remain to be measured.

Before the initial 10.2.0 workflow trial, 59 unit tests passed without root or
networking and workflow `actionlint` passed. Local renderer-shard builds passed for
10.3.6 and 10.2.0; their aggregate/hash-binding paths were exercised, including a
Spotify-only 10.2.0 release directory. The initial profile's three component source
exports passed checks and locked Cargo resolution offline. The 10.3.6 bundles also
passed QEMU installation/informational checks. This does not replace a complete
post-change compatibility-matrix run; the requested GitHub trial is profile-only.

The [10.2.0 trial](https://github.com/algielen/moode-renderers-cross-compiler/actions/runs/39510276390)
passed all jobs: 60 unit tests, separate Spotify/AirPlay builds, clean ARM64 runtime
checks, offline sources, aggregate coverage and release file binding. Only Spotify
downloads were published in v0.1.2. Downloaded release assets also matched the
approval, source pin and regenerated license report before publication. This
single-profile run is not a full-matrix performance or compatibility measurement.

## Original CI validation

The [v0.1.1 verification job](https://github.com/algielen/moode-renderers-cross-compiler/actions/runs/39461501856) passed on 2026-10-20: CLI/failure tests, cache reuse, all 27 profile/renderer builds, and installation plus informational CLI execution of every distinct bundle in clean ARM64 Debian Trixie. QEMU/binfmt was used for these runtime checks. That particular runtime test could not run locally because this `wslc` host lacks ARM binfmt emulation. The minimal runtime image explicitly points apt at its bootstrapped CA bundle for verified HTTPS access to Debian Snapshot.
