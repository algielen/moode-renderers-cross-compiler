# Licensing and release audit

Audited 2026-10-20. **Redistribution is permitted subject to upstream conditions; v0.1.1 is not cleared as a complete, compliant distribution.** The repository's original code and documentation use the [MIT license](../LICENSE). That grant does not relicense renderer binaries, dependencies, Debian packaging or the compiler image's third-party software.

## Pinned renderer sources

| Component | Source license | Evidence |
| --- | --- | --- |
| librespot 0.8.0 | MIT | [Pinned LICENSE](https://github.com/librespot-org/librespot/blob/d36f9f1907e8cc9d68a93f8ebc6b627b1bf7267d/LICENSE) |
| shairport-sync 5.5.2 | MIT-style license plus component notices | [Pinned LICENSES](https://github.com/mikebrady/shairport-sync/blob/7bad231c18368dbd26f298577f6210e36e4b0797/LICENSES); individual source files contain additional terms |
| nqptp 1.2.6 | GPL version 2 | [Pinned LICENSE](https://github.com/mikebrady/nqptp/blob/c17af00b40a454596ca43e1855c9aa13529ebc1f/LICENSE) |
| pibuz 2.5.1 | MIT | [Pinned LICENSE](https://github.com/PhilipVinc/pibuz/blob/465e21b2006718dc31999bda54fe5b60948acc9d/LICENSE) |
| Historical qbzd 2.0.2.moode49 | MIT | [Pinned LICENSE](https://github.com/PhilipVinc/qbz/blob/77562ac1a281b4347f4ecd6856e7b9ab9064b58b/LICENSE) |

The cached pinned sources for all four supported shairport versions contain `LICENSES` and `COPYING`. These top-level licenses are not a complete license declaration for linked executables. Inspect dependencies and their actual build options too, especially FFmpeg and cryptography libraries. Keeping independent tools together in a container does not make this repository's orchestration code GPL; each distributed component retains its obligations.

## Evidence from v0.1.1

The original [published release](https://github.com/algielen/moode-renderers-cross-compiler/releases/tag/v0.1.1) had four Debian packages and one binary bundle, with no corresponding-source or third-party-notice asset. The downloaded bundle's SHA-256 is `abc5c568b979201781eb6143f3efc3fff331f753535bed966442ca98022fe490`. Its manifests match the four pinned commits above. GitHub's automatically generated source archive contains this compiler repository, not the upstream renderers or their dependencies.

Package inspection of locally built matching recipes found:

- nqptp includes its GPL license, but the release does not supply its corresponding source and build/package scripts alongside the binary.
- pibuz includes its own MIT license; librespot includes an upstream copyright file. Neither packaging path collects the Rust dependency notices. The standalone binaries have no accompanying notices directory at all.
- shairport includes Debian's copyright file. That helps with its package, but standalone exports still need notices and the linked components require a build-specific review.

Scanning cached ARM64 release depfiles and the referenced crate manifests found 220 registry crates for librespot, 293 for pibuz and 352 for historical qbzd. These are conservative local-cache inventories, not an exact SBOM of the CI binaries: caches can contain earlier builds and the scan omits host build dependencies, nested bundled C code and Rust runtime internals. In particular, **Symphonia 0.5.5 is MPL-2.0** in all three; Qobuz builds also reference `mpris-server` 0.8.1 and `option-ext` 0.2.0 under MPL-2.0. Other notices include Apache-2.0, BSD, ISC, Unicode and bundled crypto terms. No conclusion about every dependency's compliance follows from its Cargo license field alone.

The GHCR image also redistributes Debian utilities/libraries, GCC, Rust toolchains and cargo-deb. The local matching compiler contains, for example, GCC 14.2.0-19cross1 and Git 2.47.3-0+deb13u1. Debian copyright files and Rust license files are retained, but there is no complete image source/notice delivery process. The pinned base digest and Debian Snapshot URL identify inputs; they do not by themselves discharge every source-delivery obligation.

## Required distribution work

### Verified remediation materials

Local remediation checks on 2026-10-20 reproduced all four original v0.1.1
executables byte for byte. Their source commits, Rust lockfile hashes/toolchain
versions where applicable, and Debian toolchain inventories agree. The original
tag's CLI and recipe hashes also match the published manifests. Repackaged Debian
packages carry the collected notices; the prepared standalone bundle includes
source/notice companions. Executable bytes are unchanged; package/archive checksums
change when adding materials.

The inspected published compiler digest is
`sha256:55fe51c1dd9769f186a76336f9880d5f776c67d4a7b8f4658278084e55252336`.
Its 524 installed Debian binary package records match the source inventory. The
supplement includes 350 Debian source package/version inputs, both Rust source
distributions, and locked cargo-deb/rustup sources and vendor closures. All 36,163
material hashes passed verification. Rustup source matches the installed binary's
commit; cargo-deb's source matches the registry checksum. The split source archive's
internal source manifest matches SHA-256
`9da8f614b417f04d4870cf84a2f1a9239a62d799e4bd4ae2900b5ca482385bdb`.

Prepared supplement assets and provenance records are under ignored
`dist/licensing-v0.1.1-supplements/`; repackaged binaries, bundle and draft release
notes are under `dist/licensing-v0.1.1-release/`. These materials have **not been
published**: the GitHub release endpoint returned 404 at the publication check.
Collection and reproducibility evidence do not substitute for reviewing actual
license terms, selected alternatives and bundled code. The public distribution is
not declared cleared.

### Follow-up review and release scope

The follow-up collector retains inline notices (including Shairport's `alac.c`
and `tinysvcmdns.c` headers) in full. Cargo manifests now record actual compiler
artifacts, features and host/target roles. Dependency metadata uses the build's
features and collection fails if a built package is absent. The complete vendor
closure is still supplied, including unused workspace/platform packages.

`tests/review_licenses.py ARTIFACTS --output REPORT.json` proposes offered Cargo
license alternatives for built packages only; it preserves AND obligations and
leaves unknown terms unresolved. It is not a native-code or legal clearance.
The current report covers 280 librespot, 430 qbzd and 363 pibuz build packages.
Two qbzd workspace crates (`qbz-cache`, `qbz-library`) omit Cargo license metadata;
their manifests name blitzkriegfc, matching the pinned repository's root MIT grant.
That source evidence needs to accompany review rather than silently inventing
metadata. Unused Slint workspace dependencies do not establish that the headless
binary incorporates Slint.

AirPlay publication remains on hold. All four pinned Shairport versions contain
the same `nqptp-shm-structures.h` GPLv2-only notice. The header contains ABI
constants/structures, so its effect on the combined work needs clarification;
this audit does not assume those declarations are copyrightable. The actual
FFmpeg libraries report GPLv2-or-later and Shairport links OpenSSL 3 (Apache-2.0).
Apache's [compatibility guidance](https://www.apache.org/licenses/GPL-compatibility)
does not support Apache-2.0/GPLv2 combinations. Changing FFmpeg alone would not
resolve the header question. A maintainer question is retained locally under
ignored `dist/airplay-license-question.md` and has **not been sent**.

The owner selected **v0.1.2 for moOde 10.2.0 with Spotify downloads only**, then
subsequent releases can advance through 10.2.1 and later profiles. Qobuz is absent
before 10.3.4. AirPlay publication
is deferred, its question stays local and unsent, and the compiler remains locally
built. The workflow allowlist follows the selected profile and excludes AirPlay;
the first release therefore contains librespot only.
Historical qbzd is not a download in this release. The deleted v0.1.1 stays deleted.
Future scope does not erase source/notice obligations for previously distributed
artifacts. Compiler-image publication still requires a fresh notice/source delivery
bundle; the existing source bundle is about 2.3 GB compressed.

For the reviewed librespot and pibuz recipes, every actual Cargo build package has a recognized
offered license selection. The native interfaces/bundles inspected are ALSA and
OpenSSL for librespot, and ALSA, AWS-LC and bundled SQLite for pibuz. AWS-LC's full
composite ISC/Apache/MIT/BSD grant and nested notices are retained, not reduced to
the Rust wrapper's license. SQLite's public-domain source header and wrapper MIT
license are retained. Dynamically linked system libraries are package dependencies,
not copied into these downloads. The source and notice archives retain original
Rust/runtime and nested native-code notices. MPL source instructions are included
inside packages and alongside binaries. This scoped review does not clear AirPlay,
historical qbzd or the compiler image for publication. Pibuz is reviewed but is
not part of the first 10.2.0 release.

### Remediation implemented in the working tree

New builds collect a source archive and notice archive per package. The source archive
contains the pristine pinned renderer, the complete locked Cargo vendor closure where
applicable, Rust library sources/notices, dependency metadata and our build/package
scripts. Shairport's exact Debian packaging archive is exported alongside it. Debian
packages retain existing notices and gain `/usr/share/doc/<name>/redistribution`, with
source acquisition instructions. Standalone bundles contain the same companion archives.
Manifests record archive checksums; `tests/check_redistribution.py` verifies them before
the workflow prepares a draft release. The Cargo inventory deliberately includes
unused platforms and host tools; it is not an exact linked-code SBOM.

The workflow now creates drafts and does not publish compiler images. These safeguards
do **not** publish the prepared v0.1.1 supplements or establish clearance. Before making
a draft public, review license choices, bundled native code and source completeness for
the actual linked executable, including system static/runtime code. Filename-based
notice collection now also retains complete text files containing inline copyright,
SPDX or license markers; this remains an inventory, not clearance. Compiler image
source delivery remains a separate prerequisite to restoring GHCR publication.

The image-source collector can run inside the exact compiler image being audited:

```powershell
New-Item -ItemType Directory -Force dist/image-sources | Out-Null
wslc run --rm -v "${PWD}/dist/image-sources:/out" --entrypoint python3 `
  moode-cross:local /opt/compiler/image_sources.py
```

It collects installed Debian source versions, including `Built-Using` and
`Static-Built-Using`, checks downloaded source files against Snapshot content hashes
and `.dsc` SHA-256s, and retains Rust source distributions, Rust toolchain notices,
and the locked cargo-deb/rustup source closures. `SOURCE-MANIFEST.json` is the completion
marker. Interrupted Debian downloads can be revalidated with `--resume`. Record the
exact inspected OCI digest separately; a source manifest alone does not bind materials
to a published image. Retain the source package filenames when archiving/uploading
these materials and provide them with equivalent access alongside the image.

To repair v0.1.1, preserve the original downloaded binaries and manifests, match their
source commits, lockfile hashes, compiler versions and build options, then prepare
source/notice supplements against that evidence. Compare dependency inventories with
the original build before claiming correspondence; a new build alone cannot attest to
an old binary. Upload reviewed supplements alongside the existing downloads and update
the release notes with source acquisition instructions. Any replacement package must
be identified as rebuilt, with new checksums. Existing GHCR tags require their own
matching image inventories, source delivery and notices before clearance.

1. For each release, collect exact source, license texts, copyright/NOTICE files and dependency inventories from the actual builds. Include vendored code and selected license alternatives. Preserve notices inside Debian packages and alongside standalone binaries.
2. Supply nqptp's complete corresponding source and our build/package scripts with equivalent access from the release. Do not substitute a link to an upstream homepage or GitHub's compiler-only source archive. GPLv2 section 3 governs binary/source delivery; see the [FSF distribution FAQ](https://www.gnu.org/licenses/gpl-faq.html#DistributeWithSourceOnInternet).
3. Make the exact MPL-covered dependency sources available and tell binary recipients where to obtain them, including modifications if any. A larger MIT application can contain MPL files, but those files retain MPL obligations: [MPL 2.0 sections 3.2–3.4](https://www.mozilla.org/en-US/MPL/2.0/).
4. Audit the whole compiler image separately: inventory Debian source package versions and Rust/cargo-deb dependencies, retain notices, and provide the required corresponding sources using a license-compliant mechanism. Base-image availability alone is not a complete redistribution review. Debian explains its redistribution policy in [About Copyrights and Software Licenses](https://www.debian.org/releases/stable/arm64/ch01s08.en.html).
5. Verify generated source/notice assets before publishing another binary/image release, then repair v0.1.1's distribution materials. Do not describe it as license-cleared until those items are resolved.

This audit identifies copyright-license requirements; it does not establish trademark permission, codec patent clearance, service-provider approval or compliance with Spotify/Qobuz account terms. No proprietary Spotify, Apple or Qobuz SDK was identified in the inspected top-level source manifests, but a full vendored-dependency review remains outstanding. This is an engineering audit, not a legal opinion.
