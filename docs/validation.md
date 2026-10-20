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

No package was installed on the physical Pi, no renderer settings were changed, and no Spotify discovery or audio playback test was performed. Other listed Pi models are compatible targets but have not been tested on hardware.

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

## CI-only validation

The release workflow additionally checks installation and informational CLI execution in a clean ARM64 Debian Trixie container. That particular test could not run locally because this `wslc` host lacks ARM binfmt emulation. Its runtime image built successfully; the full workflow still needs its first GitHub run. GHCR publishing and GitHub release creation are configured but have not been exercised.
