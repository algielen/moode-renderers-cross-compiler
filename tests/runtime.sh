#!/bin/sh
# Runs in a disposable, clean ARM64 Debian container; never on the user's Pi.
set -eu
test "$(dpkg --print-architecture)" = arm64
rm /etc/apt/sources.list.d/debian.sources
printf 'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian/20261010T000000Z trixie main\n' > /etc/apt/sources.list
apt-get update
apt-get install -y --no-install-recommends /artifacts/librespot_0.8.0-1moode1_arm64.deb ca-certificates
test "$(dpkg-query -W -f='${Version}' librespot)" = 0.8.0-1moode1
librespot --version
librespot --help > /tmp/librespot-help
for option in --backend --device --onevent --enable-volume-normalisation --normalisation-knee --zeroconf-port; do
    grep -q -- "$option" /tmp/librespot-help
done
ldd /usr/bin/librespot > /tmp/librespot-libraries
cat /tmp/librespot-libraries
if grep -q 'not found' /tmp/librespot-libraries; then exit 1; fi
