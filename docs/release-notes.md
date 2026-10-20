Renderer downloads for **moOde @MOODE_PROFILE@, Trixie ARM64**:

@PACKAGES@

Download the `.deb` for the renderer you need. The combined archive also includes
standalone executables, build manifests, logs and per-renderer checksums.

These baseline ARM64 packages use the same executable across Pi models supported
by the moOde @MOODE_PROFILE@ profile. The manifest records the reference model `3b+` used by
CI; it does not select CPU tuning or restrict the download to that model. Physical
validation status remains model-specific.

**Sources and licenses:** retain the matching `*_sources.tar.gz` and
`*_notices.tar.gz` companions when redistributing. The combined archive includes
them too. Sources contain the pinned upstream code, locked Rust dependencies,
Rust library sources and build/package scripts. Original third-party licenses
and notices are preserved; this repository's MIT license does not replace them.
MPL-covered dependency files remain under MPL-2.0, with their exact sources in
the companion archive's `vendor/` directory. `license-selections.json` records
offered Cargo license alternatives used in the review, not a complete linked-code
SBOM. Verify downloads against `SHA256SUMS`.

AirPlay downloads are deferred pending a separate licensing clarification. No
compiler image is published with this release; build it locally from the tagged
source. The deleted v0.1.1 release is not restored.

Validation includes the selected profile/renderer builds, source/checksum checks,
and installation plus informational CLI checks in ARM64 Trixie. These checks do
not establish audio playback or discovery behavior. The workflow run records the
exact selection; a profile-only smoke test is not full compatibility validation.
