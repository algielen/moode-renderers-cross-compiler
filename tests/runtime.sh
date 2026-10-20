#!/bin/sh
# Runs in a disposable, clean ARM64 Debian container; never on the user's Pi.
set -eu
test "$(dpkg --print-architecture)" = arm64
rm /etc/apt/sources.list.d/debian.sources
printf 'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian/20261010T000000Z trixie main\n' > /etc/apt/sources.list
# The minimal image lacks the OpenSSL trust-store symlinks normally installed
# by ca-certificates. Point apt at the bootstrapped bundle explicitly.
printf 'Acquire::https::CaInfo "/etc/ssl/certs/ca-certificates.crt";\n' > /etc/apt/apt.conf.d/80-runtime-ca
apt-get update --error-on=any
# Packages must not start audio services inside this test container.
printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d
chmod +x /usr/sbin/policy-rc.d
apt-get install -y --no-install-recommends python3 ca-certificates
python3 /runtime.py
