# Validation

Target: Raspberry Pi 3B+, moOde 10.3.6 (r1036), Raspberry Pi OS Trixie ARM64.

Validated locally on 2026-10-20 using Windows PowerShell and `wslc` 3.0.3.0:

- Compiler image built from its pinned base and Debian snapshot.
- Clean librespot cross-build completed with four jobs; Cargo reported 1 minute 37 seconds.
- Cached build completed without recompiling crates; Cargo reported 0.17 seconds.
- Six CLI/profile/failure-handling tests passed, and a read-only output mount failed before compilation.
- AArch64 ELF, dynamic loader, Debian architecture/version, package assets, runtime dependencies, and artifact checksums inspected.
- Package installed in a disposable AMD64 Trixie container with ARM64 libraries. The installed binary's `--version` and `--help` ran through user-mode QEMU.
- SSH inspection confirmed the physical Pi's model, OS, release, and expected renderer package version.
- The standalone binary ran `--version` and `--help` on the physical Pi. All CLI options used by moOde were present; the temporary upload was removed.
- GitHub workflow passed `actionlint`.

The Pi provided libc 2.41, ALSA 1.2.14, and OpenSSL 3.5.4. The package declares `libasound2t64 (>= 1.0.29)`, `libc6 (>= 2.39)`, and `libssl3t64 (>= 3.0.0)`.

No package was installed on the physical Pi, no renderer settings were changed, and no Spotify discovery or audio playback test was performed. Other listed Pi models are compatible targets but have not been tested on hardware.

The release workflow additionally checks installation and informational CLI execution in a clean ARM64 Debian Trixie container. That particular test could not run locally because this `wslc` host lacks ARM binfmt emulation. Its runtime image built successfully; the full workflow still needs its first GitHub run. GHCR publishing and GitHub release creation are configured but have not been exercised.
