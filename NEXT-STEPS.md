# Next session

## Current state

- [v0.1.2](https://github.com/algielen/moode-renderers-cross-compiler/releases/tag/v0.1.2) is public: **Spotify for moOde 10.2.0**, with verified sources, notices and checksums.
- [Successful workflow](https://github.com/algielen/moode-renderers-cross-compiler/actions/runs/39510276390): 60 tests, renderer builds, ARM64 runtime checks, offline sources and aggregate release checks. This covered **10.2.0 only**, not all profiles.
- CI now splits work by renderer, uses gzip level 6 and logs redistribution phase timings.
- AirPlay publication stays deferred. Its unsent question is local: `dist/airplay-license-question.md`. Compiler images remain locally built.

## Next steps

1. Release-selection changes are committed and pushed. Only new, cleared recipes may produce release artifacts; normal compatibility validation stays separate.
2. **Do not release 10.2.1 separately:** librespot is identical through 10.3.6 and reuses v0.1.2.
3. [v0.1.3](https://github.com/algielen/moode-renderers-cross-compiler/releases/tag/v0.1.3) publishes approved pibuz for **10.3.5–10.3.6**. Its six assets passed checksum, CI approval, source pin and regenerated license-report checks. The publication receipt prevents duplicate builds. AirPlay and historical qbzd remain blocked.
4. No currently supported profile needs another cleared package release. For a new recipe, review its complete dependencies and build inputs before enabling it; never infer clearance from a changed source, feature set or toolchain.
5. The focused [release run](https://github.com/algielen/moode-renderers-cross-compiler/actions/runs/40344220862) and full [compatibility run](https://github.com/algielen/moode-renderers-cross-compiler/actions/runs/40329433504) passed. Keep the documented historical renderer TLS limitation visible in release notes.

## Keep in mind

- Never move a published tag. Use a new version for each profile release.
- Preserve the unrelated `.idea/moode-renderers-cross-compiler.iml` modification.
- Full-matrix validation passed; end-to-end performance comparison remains outstanding.
- Performance analysis: `dist/build-performance-review.md`; compression measurements: `dist/benchmark-gzip.log`.
- Do not restore v0.1.1, publish AirPlay/compiler images, send the maintainer question or install anything on the Pi without further instructions.
