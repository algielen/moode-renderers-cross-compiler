# Host tools run on AMD64; only the renderer is compiled for ARM64.
FROM rust:1.90.0-slim-trixie@sha256:7fa728f3678acf5980d5db70960cf8491aff9411976789086676bdf0c19db39e

LABEL org.opencontainers.image.source="https://github.com/algielen/moode-renderers-cross-compiler" \
      org.opencontainers.image.description="Cross-compile moOde renderers for Raspberry Pi"

ENV DEBIAN_SNAPSHOT=20261010T000000Z \
    CARGO_DEB_VERSION=3.8.0 \
    CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=aarch64-linux-gnu-gcc \
    CC_aarch64_unknown_linux_gnu=aarch64-linux-gnu-gcc \
    AR_aarch64_unknown_linux_gnu=aarch64-linux-gnu-ar \
    PKG_CONFIG_ALLOW_CROSS=1 \
    PKG_CONFIG_LIBDIR=/usr/lib/aarch64-linux-gnu/pkgconfig:/usr/share/pkgconfig \
    RUST_MIN_STACK=16777216 \
    RUSTFLAGS="-Ccodegen-units=1 -Ctarget-cpu=generic" \
    CARGO_TARGET_DIR=/cache/target \
    RUSTUP_TOOLCHAIN=1.90.0 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN test "$(dpkg --print-architecture)" = amd64 \
    && dpkg --add-architecture arm64 \
    && rm /etc/apt/sources.list.d/debian.sources \
    && printf 'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian/%s trixie main\n' "$DEBIAN_SNAPSHOT" > /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates git gcc-aarch64-linux-gnu binutils-aarch64-linux-gnu \
       libc6-dev-arm64-cross libasound2-dev:arm64 libssl-dev:arm64 \
       pkg-config dpkg-dev python3 python3-paramiko file xz-utils \
    && rm -rf /var/lib/apt/lists/* \
    && rustup target add aarch64-unknown-linux-gnu \
    && cargo install cargo-deb --version "$CARGO_DEB_VERSION" --locked \
    && rm -rf /usr/local/cargo/registry /usr/local/cargo/git

# AirPlay uses autotools/Debian packaging; the older Qobuz daemon also links JACK.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       autoconf automake libtool debhelper dh-autoreconf devscripts \
       g++-aarch64-linux-gnu cmake clang libclang-dev xmltoman xxd \
       libavahi-client-dev:arm64 libavcodec-dev:arm64 libavformat-dev:arm64 \
       libavutil-dev:arm64 libswresample-dev:arm64 libconfig-dev:arm64 \
       libpopt-dev:arm64 libsoxr-dev:arm64 libplist-dev:arm64 libplist-utils \
       libsodium-dev:arm64 libmosquitto-dev:arm64 libgcrypt20-dev:arm64 uuid-dev:arm64 \
       libglib2.0-dev:arm64 libglib2.0-dev-bin:amd64 \
       libjack-jackd2-dev:arm64 libdbus-1-dev:arm64 \
    && rm -rf /var/lib/apt/lists/*

# Qobuz uses Arc::new_zeroed_slice, stabilized after the librespot toolchain.
RUN rustup set auto-self-update disable \
    && rustup toolchain install 1.94.0 --profile minimal --target aarch64-unknown-linux-gnu

COPY compiler /opt/compiler
COPY LICENSE /opt/compiler/LICENSE
COPY docs/licensing.md /opt/compiler/THIRD-PARTY.md
COPY profiles /opt/profiles
COPY tests /opt/tests
RUN mkdir -p /cache /out \
    && dpkg-query -W -f='${binary:Package}\t${Version}\n' > /opt/compiler/toolchain-packages.tsv

WORKDIR /work
ENTRYPOINT ["python3", "/opt/compiler/cli.py"]
CMD ["--help"]
