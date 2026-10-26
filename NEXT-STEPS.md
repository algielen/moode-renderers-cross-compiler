# Next session

## Current state

- [v0.1.2](https://github.com/algielen/moode-renderers-cross-compiler/releases/tag/v0.1.2) is public: **Spotify for moOde 10.2.0**, with verified sources, notices and checksums.
- [Successful workflow](https://github.com/algielen/moode-renderers-cross-compiler/actions/runs/39510276390): 60 tests, renderer builds, ARM64 runtime checks, offline sources and aggregate release checks. This covered **10.2.0 only**, not all profiles.
- CI now splits work by renderer, uses gzip level 6 and logs redistribution phase timings.
- AirPlay publication stays deferred. Its unsent question is local: `dist/airplay-license-question.md`. Compiler images remain locally built.

## Next steps

1. Review the local release-selection changes before committing/pushing. Only new, cleared recipes may produce release artifacts; normal compatibility validation stays separate.
2. **Do not release 10.2.1 separately:** librespot is identical through 10.3.6 and reuses v0.1.2.
3. Resolve owner confirmation for the reviewed pibuz recipe in `compiler/release-policy.json`. If enabled, its next candidate is **10.3.5**, also matching 10.3.6. AirPlay and historical qbzd remain blocked.
4. When a new candidate exists, create a new tag and run `build.yml` with `profile=10.3.5`, `profile_only=true`, `full=false`. Require every selected-package check to pass and review exact assets before publishing.
5. After publication, record the exact recipe/release receipt in the policy to prevent duplicate future builds. Never infer clearance for a changed source, feature set or toolchain.

## Keep in mind

- Never move a published tag. Use a new version for each profile release.
- Preserve the unrelated `.idea/moode-renderers-cross-compiler.iml` modification.
- Full-matrix validation and end-to-end performance comparison after the CI changes remain outstanding. Run with `full=true`, `profile_only=false` when ready.
- Performance analysis: `dist/build-performance-review.md`; compression measurements: `dist/benchmark-gzip.log`.
- Do not restore v0.1.1, publish AirPlay/compiler images, send the maintainer question or install anything on the Pi without further instructions.
