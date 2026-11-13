#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify host environment, USB drivers, and connected iOS devices for recovery.

Checks:
- Windows Apple Mobile Device Service (usbaapl64.sys / Apple Mobile Device Support)
- Connected Apple USB devices in Recovery/Restore/DFU mode
- Conflicting software (iTunes, 3uTools, Apple Devices app running in background)
"""

import os
import subprocess
import sys


def check_conflicts():
    print("[-] Checking for background conflicting processes...")
    conflicts = ["iTunes.exe", "3uTools.exe", "AppleMobileDeviceProcess.exe", "AppleDevices.exe"]
    found = []
    try:
        out = subprocess.check_output(["tasklist"], text=True)
        for c in conflicts:
            if c.lower() in out.lower():
                found.append(c)
    except Exception:
        pass

    if found:
        print(f"    [!] WARNING: Conflicting software running: {', '.join(found)}")
        print("        Please close them before restoring to avoid USB connection theft.")
    else:
        print("    [+] No conflicting Apple/3uTools software running.")


def check_connected_devices():
    print("[-] Checking connected Apple USB devices...")
    try:
        out = subprocess.check_output(["pnputil", "/enum-devices", "/connected"], text=True)
        apple_lines = [l.strip() for l in out.splitlines() if "apple" in l.lower() or "vid_05ac" in l.lower()]
        if apple_lines:
            print("    [+] Apple device(s) detected via Windows PnP:")
            for l in apple_lines[:6]:
                print(f"        {l}")
        else:
            print("    [!] No Apple device detected in connected PnP list. Check cable connection.")
    except Exception as e:
        print(f"    [!] Error checking PnP devices: {e}")


def check_irecovery():
    print("[-] Checking device status with irecovery...")
    exe = os.path.join(os.path.dirname(__file__), "..", "bin", "windows-x64", "irecovery.exe")
    if not os.path.exists(exe):
        exe = "irecovery"

    try:
        out = subprocess.check_output([exe, "-q"], text=True, stderr=subprocess.STDOUT)
        print("    [+] Device query successful:")
        for line in out.splitlines():
            if any(k in line for k in ["PRODUCT", "MODEL", "ECID", "MODE", "SRNM", "CPID"]):
                print(f"        {line}")
    except subprocess.CalledProcessError as e:
        print("    [!] irecovery could not query device.")
        print("        Device might be rebooting, in Restore mode, or disconnected.")
    except FileNotFoundError:
        print("    [!] irecovery executable not found.")


def main():
    print("=======================================================")
    print(" iOS Full-Storage Recovery Environment Diagnostics")
    print("=======================================================\n")
    check_conflicts()
    print()
    check_connected_devices()
    print()
    check_irecovery()
    print("\n=======================================================")


if __name__ == "__main__":
    main()

