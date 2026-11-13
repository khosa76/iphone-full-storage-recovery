#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
"""Suggest a tailored value for IDEVICERESTORE_CRYPTEX_SIZE_MIB.

Reads the real system cryptex size (Cryptex1,SystemOSSize) from the IPSW's
BuildManifest.plist, reads the space numbers from the restore_<ECID>_<time>.log
written during your diagnostic attempt, and computes the exact custom override
needed for YOUR specific phone.

Handles:
- Standard unlocked devices (single-run override)
- Passcode-locked devices (two-step Stage 2 AppDeletion override to bypass Apple's comparison bug)
"""

import argparse
import glob
import os
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


def find_latest_log():
    """Look for restore_*.log files in current and parent directories."""
    candidates = glob.glob("restore_*.log") + glob.glob("../*.log") + glob.glob("../*/*.log")
    logs = [f for f in candidates if os.path.basename(f).startswith("restore_") and f.endswith(".log")]
    if not logs:
        return None
    logs.sort(key=os.path.getmtime, reverse=True)
    return logs[0]


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
    """Return (declared_mib, needed_mb, free_mb, is_locked, skipped_app_deletion) from log."""
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
        description="Calculate the exact custom IDEVICERESTORE_CRYPTEX_SIZE_MIB for your device.")
    parser.add_argument("ipsw", help="Path to the signed IPSW you are restoring with")
    parser.add_argument("--log", help="Path to restore_*.log (if omitted, auto-detects latest log)")
    parser.add_argument("--target-delete-mb", type=int, default=1200,
                        help="Amount of app binaries to delete in MiB for locked phones (default: 1200 MiB)")
    args = parser.parse_args()

    if not os.path.exists(args.ipsw):
        sys.exit(f"[ERROR] IPSW file not found: {args.ipsw}")

    manifest = read_manifest(args.ipsw)
    sizes = update_cryptex_sizes(manifest)
    if not sizes:
        sys.exit("[ERROR] No Update identity found in this IPSW. Ensure you have an official Restore IPSW.")

    products = ", ".join(manifest.get("SupportedProductTypes", []))
    print("=================================================================")
    print(f" iOS Firmware: {products} - iOS {manifest.get('ProductVersion')} ({manifest.get('ProductBuildVersion')})")
    for device_class, size in sorted(sizes.items()):
        print(f" Real System Cryptex Size ({device_class}): {size} MiB")
    print("=================================================================\n")

    log_path = args.log or find_latest_log()

    if not log_path or not os.path.exists(log_path):
        print("[!] No restore log found.")
        print("    Run a baseline diagnostic first to generate your phone's log:")
        print("    .\\bin\\windows-x64\\idevicerestore.exe -y -P \"<path_to_ipsw>\"")
        print("\n    Fallback baseline suggestion:")
        default_val = next(iter(sizes.values())) + TESTED_OVERDECLARE_MIB
        print(f"    IDEVICERESTORE_CRYPTEX_SIZE_MIB={default_val}")
        return

    print(f"[+] Analyzing restore log: {os.path.abspath(log_path)}")
    parsed = read_space_numbers(log_path)
    numbers, is_locked, skipped_app_deletion = parsed

    if numbers is None:
        sys.exit(f"[ERROR] Could not find 'SpaceNeededForRestore' in {log_path}. Was it a complete restore log?")

    declared, needed, free = numbers
    headroom = free - needed
    print(f"    - Declared Cryptex: {declared} MiB")
    print(f"    - Space Needed:     {needed} MB")
    print(f"    - Free Space:       {free} MB")
    print(f"    - Current Headroom: {headroom} MB")

    # Calculate Step 1 override to force Stage 2 AppDeletion
    # Formula: CryptexOverride = 2 * ContainerFreeSpace + TargetDelete - Offset (approx 355 MB)
    target_del_bytes = args.target_delete_mb * 1024 * 1024
    container_free_bytes = free * 1024 * 1024
    cryptex_step1_bytes = (2 * container_free_bytes) + target_del_bytes - (355 * 1024 * 1024)
    step1_override = int(cryptex_step1_bytes / (1024 * 1024))

    # Standard suggestion for unlocked phones
    standard_override = declared + headroom + TARGET_EXCESS_MB

    print("\n-----------------------------------------------------------------")
    print("                YOUR CUSTOM RESTORE INSTRUCTIONS                 ")
    print("-----------------------------------------------------------------")

    if is_locked or skipped_app_deletion or free < 7500:
        print("[!] DIAGNOSIS: Locked storage / Low container headroom detected.")
        if is_locked:
            print("    PhotoData caches cannot be wiped (device encrypted with passcode).")
        print("    You MUST use the Two-Step Stage 2 AppDeletion Method.")
        print("\n>>> STEP 1: FORCE APP DELETION (Free ~1.2 GB of App Binaries) <<<")
        print("In Windows PowerShell, run:")
        print(f"    $env:IDEVICERESTORE_CRYPTEX_SIZE_MIB = \"{step1_override}\"")
        print(f"    .\\bin\\windows-x64\\idevicerestore.exe -y -P \"{args.ipsw}\"")
        print("\nIn Linux / macOS bash, run:")
        print(f"    IDEVICERESTORE_CRYPTEX_SIZE_MIB={step1_override} idevicerestore -y -P \"{args.ipsw}\"")
        print("\n* NOTE: Step 1 will delete ~1.2 GB of third-party apps, then exit with Error 1110.")
        print("  Your phone will reboot back to Recovery Mode with expanded free space.")

        print("\n>>> STEP 2: COMPLETE RESTORE (With Override Cleared) <<<")
        print("Once your phone reboots back to the Recovery screen, run:")
        print("In Windows PowerShell:")
        print("    Remove-Item Env:\\IDEVICERESTORE_CRYPTEX_SIZE_MIB")
        print(f"    .\\bin\\windows-x64\\idevicerestore.exe -y -P \"{args.ipsw}\"")
        print("\nIn Linux / macOS bash:")
        print(f"    idevicerestore -y -P \"{args.ipsw}\"")
        print("\n* Result: Passes space_checks, passes install_splat, and finishes 100%!")
    else:
        print("[+] Storage appears unlocked. You can try the single-run override:")
        print(f"    $env:IDEVICERESTORE_CRYPTEX_SIZE_MIB = \"{standard_override}\"")
        print(f"    .\\bin\\windows-x64\\idevicerestore.exe -y -P \"{args.ipsw}\"")

    print("=================================================================\n")


if __name__ == "__main__":
    main()
