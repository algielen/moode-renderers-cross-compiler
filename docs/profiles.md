# Release profiles

moOde introduced the renderer build/install framework in commit [0085122](https://github.com/moode-player/moode/commit/00851220cdc05d12953e204d5d6a06e3d431b068), **19 April 2026**. It added the AirPlay/Spotify Install buttons and worker jobs; the UI explicitly described building and installing librespot.

The first public release with this feature was **10.2.0**. Its [original release, r1020](https://github.com/moode-player/moode/releases/tag/r1020), was published **8 May 2026** (release notes/image dated 6 May). The [corrected r1020fix image](https://github.com/moode-player/moode/releases/tag/r1020fix) followed on **13 May 2026**. Both announce on-demand Shairport-sync 5 and Librespot 8 installation for new images. The preceding 10.1.2 release predates this framework.

## Audited builds

Audit date: 20 October 2026. Each link below points to the immutable renderer database used to create that release's profile. The dates are from each tag's release notes, not GitHub publication timestamps.

| moOde version | Accepted tag aliases | Release-note date | AirPlay | Qobuz | Renderer database |
| --- | --- | --- | --- | --- | --- |
| 10.2.0 | `r1020`, `r1020fix` | 2026-05-06 / 2026-05-13 | 5.0.4 | Not available | [original](https://github.com/moode-player/moode/blob/d922c0204c6e1b9d255d3d3a100000ce10e73d98/var/local/www/db/moode-sqlite3.db.sql), [corrected](https://github.com/moode-player/moode/blob/c54b407865a673874f0b21f8316c7b6daaef087f/var/local/www/db/moode-sqlite3.db.sql) |
| 10.2.1 | `r1021` | 2026-05-23 | 5.0.4 | Not available | [database](https://github.com/moode-player/moode/blob/db4bab57fe20eff6361714f1fb9be941ae901cf5/var/local/www/db/moode-sqlite3.db.sql) |
| 10.2.2 | `r1022` | 2026-05-31 | 5.0.4 | Not available | [database](https://github.com/moode-player/moode/blob/45feca68c9cb00d95c3813975b565a6ec1697e34/var/local/www/db/moode-sqlite3.db.sql) |
| 10.2.3 | `r1023` | 2026-06-15 | 5.0.4 | Not available | [database](https://github.com/moode-player/moode/blob/e9ab76a5b916290ea27ccab165cff74ca31638bd/var/local/www/db/moode-sqlite3.db.sql) |
| 10.2.4 | `r1024` | 2026-06-21 | 5.0.4 | Not available | [database](https://github.com/moode-player/moode/blob/5bfa424b7bdd52322201803b89d3704d3142fdbd/var/local/www/db/moode-sqlite3.db.sql) |
| 10.3.0 | `r1030` | 2026-07-14 | 5.0.4 | Not available | [database](https://github.com/moode-player/moode/blob/cedf27b59abe5508502047a05281a0279e4302f2/var/local/www/db/moode-sqlite3.db.sql) |
| 10.3.1 | `r1031` | 2026-07-22 | 5.0.4 | Not available | [database](https://github.com/moode-player/moode/blob/9faf08ff27fe90c6afc389c92a8ff1ce788c734c/var/local/www/db/moode-sqlite3.db.sql) |
| 10.3.2 | `r1032` | 2026-08-03 | 5.2.1 | Not available | [database](https://github.com/moode-player/moode/blob/3699fd9485065b6bcda6e2c6b96af6231a5ac81a/var/local/www/db/moode-sqlite3.db.sql) |
| 10.3.3 | `r1033` | 2026-08-27 | 5.2.1 | Not available | [database](https://github.com/moode-player/moode/blob/e3a43932781bda201b5c6d399ff59f4589c52fdd/var/local/www/db/moode-sqlite3.db.sql) |
| 10.3.4 | `r1034` | 2026-09-08 | 5.5.1 | qbzd 2.0.2 | [database](https://github.com/moode-player/moode/blob/bc96bb8abcefa03698f90b4820584c2c5ee94ec7/var/local/www/db/moode-sqlite3.db.sql) |
| 10.3.5 | `r1035` | 2026-09-30 | 5.5.2 | pibuz 2.5.1 | [database](https://github.com/moode-player/moode/blob/fa077a32b3adb6483588467bdee7928237d50107/var/local/www/db/moode-sqlite3.db.sql) |
| 10.3.6 | `r1036` | 2026-10-10 | 5.5.2 | pibuz 2.5.1 | [database](https://github.com/moode-player/moode/blob/1226c6a66204dd58380846ef26e7763a94ed86d1/var/local/www/db/moode-sqlite3.db.sql) |

All 12 versions (13 tags) select librespot **0.8.0-1moode1**, Trixie ARM64. AirPlay versions above refer to shairport-sync; all require **nqptp 1.2.6-1moode1**. The AirPlay/Qobuz package versions append `-1moode1` to the versions in the table. The audit checked each tag's renderer database, invocation, installer and guide. Both 10.2.0 images use the same renderer contract, so `r1020fix` resolves to the canonical 10.2.0 profile, whose `moode_commit` records the original tag.

Qobuz is absent before 10.3.4. That release expects `qbzd_2.0.2-1moode1_arm64.deb`; its pinned source is upstream's `qbzd-v2.0.2.moode49`, matching the initial moOde build recipe and its `QBZD_BUILD_ID`. From 10.3.5, the installer expects `pibuz_2.5.1-1moode1_arm64.deb`. These are separate source repositories/builds; the compiler does not substitute one for the other.

AirPlay builds both shairport-sync and nqptp. Shairport-sync uses the pinned upstream source with Debian packaging and moOde's feature selection (AirPlay 2, ALSA, metadata, OpenSSL, Avahi, SOXR, D-Bus/MPRIS and MQTT; no libdaemon, JACK, PulseAudio, PipeWire or convolution). NQPTP supplies the timing daemon and its systemd unit. Qobuz packages contain the headless binary and documentation, without installing a second daemon service alongside moOde's own process management.

Each release groups its supported renderers under `renderers`; each renderer lists its required `packages`. Manifest schema 2 records the selected renderer and per-package source/build/dependency details. Profiles sharing a recipe export the same binary. CI builds every available release/renderer combination and tests each distinct runtime bundle. Release downloads provide all three renderers for 10.3.6; historical versions can be built with their profiles.

Hardware and cross-build validation are recorded separately in [validation.md](validation.md). No earlier moOde image has been installed on the test Pi, and no renderer package is automatically installed there.
