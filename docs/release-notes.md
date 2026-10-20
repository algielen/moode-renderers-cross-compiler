Renderer downloads for **moOde 10.3.6, Trixie ARM64**:

- Spotify Connect: librespot 0.8.0-1moode1.
- Qobuz Connect: pibuz 2.5.1-1moode1.

Download the `.deb` for the renderer you need. The combined archive also includes
standalone executables, build manifests, logs and per-renderer checksums.

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

Validation includes all 27 profile/renderer builds, source/checksum checks, and
installation plus informational CLI checks for every distinct bundle in ARM64
Trixie. These checks do not establish audio playback or discovery behavior.
