#!/bin/bash
set -e

echo "=== Building iPhone Full-Storage Recovery Toolchain on macOS ==="

if ! command -v brew &>/dev/null; then
    echo "[!] Homebrew is required. Install it from https://brew.sh/"
    exit 1
fi

echo "[-] Installing Homebrew dependencies..."
brew install automake autoconf libtool pkg-config libzip openssl curl libplist libimobiledevice-glue libusbmuxd

BUILD_DIR="$HOME/build_idevicerestore_macos"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

echo "[-] Building libtatsu (latest git)..."
[ -d libtatsu ] || git clone https://github.com/libimobiledevice/libtatsu.git
cd libtatsu && git pull
./autogen.sh --prefix=/usr/local PKG_CONFIG_PATH="/usr/local/lib/pkgconfig:$(brew --prefix openssl)/lib/pkgconfig"
make -j$(sysctl -n hw.ncpu) && sudo make install && cd ..

echo "[-] Building libirecovery (latest git)..."
[ -d libirecovery ] || git clone https://github.com/libimobiledevice/libirecovery.git
cd libirecovery && git pull
./autogen.sh --prefix=/usr/local PKG_CONFIG_PATH="/usr/local/lib/pkgconfig:$(brew --prefix openssl)/lib/pkgconfig"
make -j$(sysctl -n hw.ncpu) && sudo make install && cd ..

echo "[-] Building libimobiledevice (latest git)..."
[ -d libimobiledevice ] || git clone https://github.com/libimobiledevice/libimobiledevice.git
cd libimobiledevice && git pull
./autogen.sh --prefix=/usr/local --without-cython PKG_CONFIG_PATH="/usr/local/lib/pkgconfig:$(brew --prefix openssl)/lib/pkgconfig"
make -j$(sysctl -n hw.ncpu) && sudo make install && cd ..

echo "[-] Building patched idevicerestore..."
[ -d idevicerestore ] || git clone https://github.com/libimobiledevice/idevicerestore.git
cd idevicerestore
git checkout 60192e9
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
git apply "$SCRIPT_DIR/../patches/0001-restore-Allow-overriding-the-declared-Cryptex1-SystemOSSize.patch" 2>/dev/null || true
./autogen.sh --prefix=/usr/local PKG_CONFIG_PATH="/usr/local/lib/pkgconfig:$(brew --prefix openssl)/lib/pkgconfig:$(brew --prefix libzip)/lib/pkgconfig:$(brew --prefix curl)/lib/pkgconfig"
make -j$(sysctl -n hw.ncpu) && sudo make install && cd ..

echo "=== Build Complete! Verified idevicerestore is installed in /usr/local/bin/idevicerestore ==="
