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

The [published release](https://github.com/algielen/moode-renderers-cross-compiler/releases/tag/v0.1.1) has four Debian packages and one binary bundle, with no corresponding-source or third-party-notice asset. The downloaded bundle's SHA-256 is `abc5c568b979201781eb6143f3efc3fff331f753535bed966442ca98022fe490`. Its manifests match the four pinned commits above. GitHub's automatically generated source archive contains this compiler repository, not the upstream renderers or their dependencies.

Package inspection of locally built matching recipes found:

- nqptp includes its GPL license, but the release does not supply its corresponding source and build/package scripts alongside the binary.
- pibuz includes its own MIT license; librespot includes an upstream copyright file. Neither packaging path collects the Rust dependency notices. The standalone binaries have no accompanying notices directory at all.
- shairport includes Debian's copyright file. That helps with its package, but standalone exports still need notices and the linked components require a build-specific review.

Scanning cached ARM64 release depfiles and the referenced crate manifests found 220 registry crates for librespot, 293 for pibuz and 352 for historical qbzd. These are conservative local-cache inventories, not an exact SBOM of the CI binaries: caches can contain earlier builds and the scan omits host build dependencies, nested bundled C code and Rust runtime internals. In particular, **Symphonia 0.5.5 is MPL-2.0** in all three; Qobuz builds also reference `mpris-server` 0.8.1 and `option-ext` 0.2.0 under MPL-2.0. Other notices include Apache-2.0, BSD, ISC, Unicode and bundled crypto terms. No conclusion about every dependency's compliance follows from its Cargo license field alone.

The GHCR image also redistributes Debian utilities/libraries, GCC, Rust toolchains and cargo-deb. The local matching compiler contains, for example, GCC 14.2.0-19cross1 and Git 2.47.3-0+deb13u1. Debian copyright files and Rust license files are retained, but there is no complete image source/notice delivery process. The pinned base digest and Debian Snapshot URL identify inputs; they do not by themselves discharge every source-delivery obligation.

## Required distribution work

1. For each release, collect exact source, license texts, copyright/NOTICE files and dependency inventories from the actual builds. Include vendored code and selected license alternatives. Preserve notices inside Debian packages and alongside standalone binaries.
2. Supply nqptp's complete corresponding source and our build/package scripts with equivalent access from the release. Do not substitute a link to an upstream homepage or GitHub's compiler-only source archive. GPLv2 section 3 governs binary/source delivery; see the [FSF distribution FAQ](https://www.gnu.org/licenses/gpl-faq.html#DistributeWithSourceOnInternet).
3. Make the exact MPL-covered dependency sources available and tell binary recipients where to obtain them, including modifications if any. A larger MIT application can contain MPL files, but those files retain MPL obligations: [MPL 2.0 sections 3.2–3.4](https://www.mozilla.org/en-US/MPL/2.0/).
4. Audit the whole compiler image separately: inventory Debian source package versions and Rust/cargo-deb dependencies, retain notices, and provide the required corresponding sources using a license-compliant mechanism. Base-image availability alone is not a complete redistribution review. Debian explains its redistribution policy in [About Copyrights and Software Licenses](https://www.debian.org/releases/stable/arm64/ch01s08.en.html).
5. Verify generated source/notice assets before publishing another binary/image release, then repair v0.1.1's distribution materials. Do not describe it as license-cleared until those items are resolved.

This audit identifies copyright-license requirements; it does not establish trademark permission, codec patent clearance, service-provider approval or compliance with Spotify/Qobuz account terms. No proprietary Spotify, Apple or Qobuz SDK was identified in the inspected top-level source manifests, but a full vendored-dependency review remains outstanding. This is an engineering audit, not a legal opinion.
