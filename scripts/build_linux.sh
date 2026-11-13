#!/bin/bash
set -e

echo "=== Building iPhone Full-Storage Recovery Toolchain on Linux (Debian/Ubuntu) ==="

sudo apt update
sudo apt install -y build-essential checkinstall git autoconf automake libtool pkg-config \
    libplist-dev libimobiledevice-glue-dev libusbmuxd-dev libssl-dev libzip-dev libcurl4-openssl-dev zlib1g-dev

BUILD_DIR="$HOME/build_idevicerestore_linux"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

echo "[-] Building libtatsu..."
[ -d libtatsu ] || git clone https://github.com/libimobiledevice/libtatsu.git
cd libtatsu && git pull
./autogen.sh --prefix=/usr/local
make -j$(nproc) && sudo make install && sudo ldconfig && cd ..

echo "[-] Building libirecovery..."
[ -d libirecovery ] || git clone https://github.com/libimobiledevice/libirecovery.git
cd libirecovery && git pull
./autogen.sh --prefix=/usr/local
make -j$(nproc) && sudo make install && sudo ldconfig && cd ..

echo "[-] Building libimobiledevice..."
[ -d libimobiledevice ] || git clone https://github.com/libimobiledevice/libimobiledevice.git
cd libimobiledevice && git pull
./autogen.sh --prefix=/usr/local --without-cython
make -j$(nproc) && sudo make install && sudo ldconfig && cd ..

echo "[-] Building patched idevicerestore..."
[ -d idevicerestore ] || git clone https://github.com/libimobiledevice/idevicerestore.git
cd idevicerestore
git checkout 60192e9
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
git apply "$SCRIPT_DIR/../patches/0001-restore-Allow-overriding-the-declared-Cryptex1-SystemOSSize.patch" 2>/dev/null || true
./autogen.sh --prefix=/usr/local PKG_CONFIG_PATH="/usr/local/lib/pkgconfig"
make -j$(nproc) && sudo make install && sudo ldconfig && cd ..

echo "=== Build Complete! idevicerestore is installed in /usr/local/bin/idevicerestore ==="
