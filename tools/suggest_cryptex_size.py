#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
"""Suggest a value for IDEVICERESTORE_CRYPTEX_SIZE_MIB.

Reads the real system cryptex size (Cryptex1,SystemOSSize) from the IPSW's
BuildManifest.plist. Optionally reads the space numbers from the
restore_<ECID>_<time>.log that idevicerestore wrote during a failed attempt
with the same IPSW, and computes a value tuned to your device.

Enhanced with --force-app-deletion to handle the Apple libpartition comparison bug
on locked devices where photo caches cannot be deleted.

Usage:
    python3 tools/suggest_cryptex_size.py <firmware.ipsw>
    python3 tools/suggest_cryptex_size.py <firmware.ipsw> --log restore_<ECID>_<time>.log
    python3 tools/suggest_cryptex_size.py <firmware.ipsw> --log restore_<ECID>_<time>.log --force-app-deletion 1000
"""

import argparse
import plistlib
import re
import sys
import zipfile

TESTED_OVERDECLARE_MIB = 748
TARGET_EXCESS_MB = 150

SIZE_LINE = re.compile(r"Size of Cryptex1,SystemOS is (\d+) MB")
SPACE_LINE = re.compile(r"SpaceNeededForRestore: (\d+) MB\s*ContainerFreeSpace: (\d+) MB")
LOCKED_PHOTO_LINE = re.compile(r"Could not reset metadata on /mnt2/mobile/Media/PhotoData.*Operation not permitted")
APP_DELETION_SKIP_LINE = re.compile(r"Sufficient space freed after initial cleanup\. Skipping app deletion\.")


def read_manifest(ipsw_path):
    """Return the BuildManifest.plist of an IPSW as a dict."""
    with zipfile.ZipFile(ipsw_path) as ipsw:
        return plistlib.loads(ipsw.read("BuildManifest.plist"))


def update_cryptex_sizes(manifest):
    """Return {device_class: Cryptex1,SystemOSSize in MiB} for the Update identities."""
    sizes = {}
    for identity in manifest.get("BuildIdentities", []):
        info = identity.get("Info", {})
        size = info.get("Cryptex1,SystemOSSize")
        if info.get("RestoreBehavior") == "Update" and size is not None:
            sizes[info.get("DeviceClass", "unknown")] = size
    return sizes


def read_space_numbers(log_path):
    """Return (declared_mib, needed_mb, free_mb, is_locked, skipped_app_deletion) from the restore log."""
    with open(log_path, encoding="utf-8", errors="replace") as f:
        text = f.read()

    declared = None
    result = None
    for match in re.finditer(f"{SIZE_LINE.pattern}|{SPACE_LINE.pattern}", text):
        if match.group(1) is not None:
            declared = int(match.group(1))
        elif declared is not None:
            result = (declared, int(match.group(2)), int(match.group(3)))

    is_locked = bool(LOCKED_PHOTO_LINE.search(text))
    skipped_app_deletion = bool(APP_DELETION_SKIP_LINE.search(text))
    return result, is_locked, skipped_app_deletion


def main():
    parser = argparse.ArgumentParser(
        description="Suggest a value for IDEVICERESTORE_CRYPTEX_SIZE_MIB.")
    parser.add_argument("ipsw", help="the signed IPSW you will restore with")
    parser.add_argument("--log", help="restore_*.log from a failed idevicerestore attempt with the same IPSW")
    parser.add_argument("--force-app-deletion", type=int, metavar="MIB",
                        help="Target MiB to offload via Stage 2 AppDeletion (recommended: 1000-1500 for locked devices)")
    args = parser.parse_args()

    manifest = read_manifest(args.ipsw)
    sizes = update_cryptex_sizes(manifest)
    if not sizes:
        sys.exit("No Update identity with Cryptex1,SystemOSSize in this IPSW. This fix does not apply to it.")

    products = ", ".join(manifest.get("SupportedProductTypes", []))
    print(f"IPSW: {products}, iOS {manifest.get('ProductVersion')} ({manifest.get('ProductBuildVersion')})")
    for device_class, size in sorted(sizes.items()):
        print(f"Real Cryptex1,SystemOSSize ({device_class}): {size} MiB")

    if args.log:
        numbers, is_locked, skipped_app_deletion = read_space_numbers(args.log)
        if numbers is None:
            sys.exit(f"No 'SpaceNeededForRestore' line found in {args.log}.")
        declared, needed, free = numbers
        headroom = free - needed
        print(f"From the log: declared {declared} MiB, needed {needed} MB, free {free} MB "
              f"({headroom} MB headroom)")

        if is_locked or skipped_app_deletion:
            print("\n[!] NOTICE: Passcode lock or skipped app deletion detected in log:")
            if is_locked:
                print("    - PhotoData caches returned 'Operation not permitted' (device storage encrypted/locked).")
            if skipped_app_deletion:
                print("    - Apple's libpartition comparison bug skipped Stage 2 AppDeletion.")

        if args.force_app_deletion:
            target_del_mb = args.force_app_deletion
            target_del_bytes = target_del_mb * 1024 * 1024
            container_free_bytes = free * 1024 * 1024
            cryptex_override_bytes = (2 * container_free_bytes) + target_del_bytes - (355 * 1024 * 1024)
            override_val = int(cryptex_override_bytes / (1024 * 1024))
            print(f"\n=== TWO-STEP RECIPE FOR LOCKED DEVICES ===")
            print(f"Step 1: Run with override to force Stage 2 AppDeletion ({target_del_mb} MiB offloaded):")
            print(f"    IDEVICERESTORE_CRYPTEX_SIZE_MIB={override_val}")
            print("    (This run will delete app bundles, then end after space_checks with Error 1110).")
            print("\nStep 2: Run with NO OVERRIDE (real cryptex size) once device reboots to Recovery:")
            print("    idevicerestore -y -P -i <ECID> <firmware.ipsw>")
            print("    (Will pass space_checks, pass install_splat preallocation, and finish 100%).")
            return
        else:
            value = declared + headroom + TARGET_EXCESS_MB
    else:
        if len(sizes) > 1:
            sys.exit("This IPSW covers several device classes. Pass --log to pick the right one.")
        value = next(iter(sizes.values())) + TESTED_OVERDECLARE_MIB
        print(f"No log given: using +{TESTED_OVERDECLARE_MIB} MiB, standard baseline suggestion.")

    print()
    print(f"IDEVICERESTORE_CRYPTEX_SIZE_MIB={value}")


if __name__ == "__main__":
    main()
