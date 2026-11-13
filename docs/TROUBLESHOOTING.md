# Troubleshooting Guide: iOS Full-Storage Recovery

This guide covers all documented error codes, edge cases, and hardware/software checkpoints encountered during data-preserving recovery.

---

## Quick Reference Table

| Checkpoint | Error Code | Symptoms | Root Cause | Solution |
| :--- | :--- | :--- | :--- | :--- |
| **`downgrade_check`** | **Error 68** | `FAILURE:68 downgrade_check` | IPSW is older than the OS currently on the device | Download an IPSW $\ge$ the build on the phone |
| **`space_checks`** | **Error 1110** | `ENOSPC for upgrade install` | Over-declared cryptex size OR skipped AppDeletion | Use Two-Step Recipe (`--force-app-deletion`) |
| **`install_splat`** | **Error 100** | `Failed preallocation due to space` | APFS 84.35% ceiling on free space exceeded | Free space via Stage 2 AppDeletion (Step 1) |
| **`TSS / Personalize`** | **Yonkers Error** | `Unable to fetch Yonkers ticket` | Buggy TSS manifest parsing in older `libtatsu` | Build `libtatsu` from Git commit `cdbca26` or newer |
| **USB Init** | **Device Lost** | `Could not read data (-11). Aborting` | iTunes / 3uTools silently seized USB endpoint | Kill iTunes/3uTools in Task Manager before starting |
| **Recovery Init** | **Mode Mismatch** | `Device is in an invalid state` | Phone left in intermediate Restore mode (`PID_12AC`) | Force restart with buttons into Recovery (`PID_1281`) |

---

## Detailed Resolutions

### 1. Error 68: `downgrade_check`
```text
CHECKPOINT FAILURE:(FAILURE:68) RESTORED:[0x06A1] downgrade_check
```
- **Cause:** Apple strictly forbids downgrading the operating system during a data-preserving (`Customer Upgrade Install`) restore. If your device was running a beta version (e.g. iOS 18.2 Beta 2) or an unreleased build before it loop-crashed, you cannot install a public release (e.g. iOS 18.1).
- **Fix:** Identify the build version from your log or check the latest beta IPSW from [ipsw.dev](https://ipsw.dev). Download an IPSW version equal to or newer than the previous OS.

---

### 2. Error 1110: `space_checks (ENOSPC)`
```text
CHECKPOINT FAILURE:(FAILURE:1110) RESTORED:[0x06A3] space_checks ENOSPC for upgrade install
```
- **Scenario A (Standard Override on Locked Device):**
  If `suggest_cryptex_size.py` recommended an override of +150 MB (e.g. `6284`), Apple's `libpartition` compared container free space against the 150 MB shortfall and erroneously logged:
  `Sufficient space freed after initial cleanup. Skipping app deletion.`
  **Fix:** Switch to the **Two-Step Recipe**. Run Step 1 with `IDEVICERESTORE_CRYPTEX_SIZE_MIB=13660` to force AppDeletion, then run Step 2 with no override.
- **Scenario B (Override Too High during Step 2):**
  If you left `IDEVICERESTORE_CRYPTEX_SIZE_MIB` set while attempting the final restore, the restore aborted because the phone cannot have 13+ GB of free space.
  **Fix:** Clear the environment variable (`Remove-Item Env:\IDEVICERESTORE_CRYPTEX_SIZE_MIB` in PowerShell, or `unset IDEVICERESTORE_CRYPTEX_SIZE_MIB` in bash) before running Step 2.

---

### 3. Error 100: `install_splat (failed to install splat)`
```text
Transfer: Failed preallocation of 6341787648 bytes for /mnt9/cryptex1/current/os.dmg: Unknown error: -1.
Transfer: Failed preallocation due to space. No hope in this succeeding, bailing.
CHECKPOINT FAILURE:(FAILURE:100) (null):[0x06A6] install_splat
```
- **Cause:** The system cryptex image exceeds 84.35% of remaining container space.
- **Fix:** Your device needs ~1 GB more free space. Follow **Step 1** of the Two-Step Recipe to offload ~1–1.5 GB of third-party `.app` binaries. Once container free space exceeds **7,518 MB**, `install_splat` will pass smoothly.

---

### 4. Yonkers Ticket Bug (iPhone 14, 15, and 16)
```text
ERROR: Unable to fetch Yonkers ticket
```
- **Cause:** `libtatsu` version 1.0.5 and older has a bug where it fails to parse the new Yonkers TSS manifest keys on newer hardware.
- **Fix:** Compile `libtatsu` directly from Git master (`git clone https://github.com/libimobiledevice/libtatsu.git`). The pre-compiled Windows binaries in `bin/windows-x64/` already include the patched `libtatsu 1.1.0`.

---

### 5. USB Communication Dropping Mid-Restore
- **Cause:** Windows Apple Mobile Device Service background threads (or iTunes helper daemons) periodically query the device when it transitions between iBoot, Recovery, and Ramdisk states. If iTunes attempts to mount the device, the connection drops with error `-11` or pipe timeout.
- **Fix:**
  1. Open Windows Task Manager (`Ctrl+Shift+Esc`).
  2. Kill `iTunes.exe`, `3uTools.exe`, `AppleMobileDeviceProcess.exe`, and `AppleDevices.exe`.
  3. Ensure you are using an official or MFi-certified USB-A to Lightning / USB-C cable connected directly to a motherboard USB port (avoid USB hubs).

---

### 6. Device Stuck in Restore Mode (`PID_12AC`)
- **Cause:** If a restore attempt aborts or is interrupted, the device may stay booted into Apple's restore ramdisk (`PID_12AC`) rather than returning to Recovery Mode (`PID_1281`).
- **Fix:**
  Perform a hardware hard reset:
  1. Press and quickly release **Volume Up**.
  2. Press and quickly release **Volume Down**.
  3. Press and **hold the Side / Power button** until the screen turns completely off and the computer/cable icon reappears.

