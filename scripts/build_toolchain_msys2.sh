#!/bin/bash
set -e

# Automated Build Script for Windows (MSYS2 UCRT64)
# Builds libimobiledevice suite with Yonkers ticket fix and Cryptex size override patch

echo "=== Installing MSYS2 UCRT64 Dependencies ==="
pacman -S --needed --noconfirm base-devel mingw-w64-ucrt-x86_64-toolchain git \
  mingw-w64-ucrt-x86_64-autotools mingw-w64-ucrt-x86_64-pkgconf \
  mingw-w64-ucrt-x86_64-libzip mingw-w64-ucrt-x86_64-curl \
  mingw-w64-ucrt-x86_64-openssl mingw-w64-ucrt-x86_64-zlib

BUILD_DIR="$HOME/build_idevicerestore"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

echo "=== 1. Building libplist ==="
[ -d libplist ] || git clone https://github.com/libimobiledevice/libplist.git
cd libplist && git pull
./autogen.sh --prefix=/ucrt64 --without-cython
make -j4 && make install && cd ..

echo "=== 2. Building libimobiledevice-glue ==="
[ -d libimobiledevice-glue ] || git clone https://github.com/libimobiledevice/libimobiledevice-glue.git
cd libimobiledevice-glue && git pull
./autogen.sh --prefix=/ucrt64
make -j4 && make install && cd ..

echo "=== 3. Building libusbmuxd ==="
[ -d libusbmuxd ] || git clone https://github.com/libimobiledevice/libusbmuxd.git
cd libusbmuxd && git pull
./autogen.sh --prefix=/ucrt64
make -j4 && make install && cd ..

echo "=== 4. Building libtatsu (Latest Git for iOS 18 / Yonkers support) ==="
[ -d libtatsu ] || git clone https://github.com/libimobiledevice/libtatsu.git
cd libtatsu && git pull
./autogen.sh --prefix=/ucrt64
make -j4 && make install && cd ..

echo "=== 5. Building libirecovery ==="
[ -d libirecovery ] || git clone https://github.com/libimobiledevice/libirecovery.git
cd libirecovery && git pull
./autogen.sh --prefix=/ucrt64
make -j4 && make install && cd ..

echo "=== 6. Building libimobiledevice ==="
[ -d libimobiledevice ] || git clone https://github.com/libimobiledevice/libimobiledevice.git
cd libimobiledevice && git pull
./autogen.sh --prefix=/ucrt64 --without-cython
make -j4 && make install && cd ..

echo "=== 7. Building Patched idevicerestore ==="
[ -d idevicerestore ] || git clone https://github.com/libimobiledevice/idevicerestore.git
cd idevicerestore
git checkout 60192e9
# Apply patch if not already applied
git apply --check ../../patches/0001-restore-Allow-overriding-the-declared-Cryptex1-SystemOSSize.patch 2>/dev/null && \
  git apply ../../patches/0001-restore-Allow-overriding-the-declared-Cryptex1-SystemOSSize.patch || echo "Patch already applied or skipped"

./autogen.sh --prefix=/ucrt64
make -j4 && make install && cd ..

echo "=== Verifying idevicerestore installation ==="
strings /ucrt64/bin/idevicerestore.exe | grep -i "IDEVICERESTORE_CRYPTEX_SIZE_MIB"
echo "=== BUILD COMPLETE! idevicerestore is ready in /ucrt64/bin/idevicerestore.exe ==="

