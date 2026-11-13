# iPhone Full-Storage Recovery Toolchain (Zero Data Loss)

> An end-to-end, rookie-friendly master guide and toolchain to recover any iPhone stuck in Recovery Mode or a boot loop due to 100% full storage (`Error 100 install_splat` or `Error 1110 space_checks`) **without losing a single photo, message, chat, or document**.

---

## The Golden Rules Before You Begin

> [!CAUTION]
> 1. **NEVER USE `-e` or `--erase`:** Every command in this guide performs a **Customer Upgrade Install**. Using `-e` or clicking "Restore" in iTunes will permanently wipe your device.
> 2. **DO NOT BLINDLY COPY NUMBERS:** The override number (e.g. `13660`) is calculated specifically from your phone's free space. [Phase 3](#phase-3-calculate-your-phones-custom-override) shows you how to get your exact number with 1 click.
> 3. **DO NOT UNPLUG DURING POST-RESTORE:** The white screen reading "Attempting data recovery" takes **20 to 50 minutes**. Do not disconnect the cable or force-restart the phone.

---

## Why Standard Recovery Fails & How This Fix Works

When an iPhone hits 100% full storage (0 GB free) and reboots:
1. **The 84% APFS Allocation Ceiling (Error 100):** During restore, `restored` writes the system cryptex image (`os.dmg`, ~6.3 GB). APFS rejects any single file allocation exceeding ~**84.35% of remaining container free space**. If free space is less than ~7,518 MB, it aborts with `Error 100 (failed to install splat)`.
2. **The Passcode Encryption Lock:** On devices with a passcode, storage is encrypted (Class C/B keys). In Recovery Mode, cache deletion scripts fail with `Operation not permitted`. Initial cleanup only frees ~12 KB.
3. **Apple's libpartition Comparison Bug (Error 1110):** `restored` has a second-stage cleanup called `AppDeletion` that offloads third-party `.app` binaries from `/private/var/containers/Bundle/Application/` (keeping user data and databases 100% intact). However, Apple's code mistakenly compares total free space against the shortfall. When the shortfall is small, it erroneously logs `"Sufficient space freed after initial cleanup. Skipping app deletion."` and aborts with `Error 1110`.

### The Two-Step Solution:
```mermaid
flowchart LR
    A["Stuck (0GB Free)"] --> B["Step 1: Forced Override"]
    B --> C["AppDeletion (+1.5 GB)"]
    C --> D["Step 2: Normal Restore"]
    D --> E["APFS Preallocation OK"]
    E --> F["100% Data Intact"]
```

| Step | Setting / Command | Action & Mechanism | Result on Device |
| :--- | :--- | :--- | :--- |
| **Step 1** | `IDEVICERESTORE_CRYPTEX_SIZE_MIB=<YOUR_NUMBER>` | Bypasses comparison bug; triggers Stage 2 `AppDeletion` | Offloads ~1.5 GB `.app` bundles; reboots to Recovery |
| **Step 2** | Override unset (Normal restore) | Flashes OS root & preallocates cryptex image | Passes APFS ceiling (78% < 84%); **Restore Finished** |

---

## Step-by-Step Recovery Walkthrough (Rookie Guide)

### Phase 1: Setup & Download Signed Firmware

1. **Driver Setup (Windows):**
   - Install **iTunes** directly from [Apple's website](https://www.apple.com/itunes/) (use the standalone `.exe` installer, **NOT** the Microsoft Store version).
   - Completely close iTunes, Apple Devices, and 3uTools before starting so they do not interrupt USB communication.
2. **Identify Your iPhone Model & ECID:**
   - Plug your iPhone into your computer via USB while in Recovery Mode (screen shows a computer and cable).
   - In PowerShell or Command Prompt, run:
     ```powershell
     .\bin\windows-x64\irecovery.exe -q
     ```
   - Note the **`PRODUCT`** (e.g. `iPhone12,5`), **`MODEL`** (e.g. `d431ap`), and **`ECID`** (e.g. `0x001971611442802e`).
3. **Download Signed IPSW:**
   - Go to **[IPSW.me](https://ipsw.me)** (or **[ipsw.dev](https://ipsw.dev)** for beta builds).
   - Select your exact model matching the `PRODUCT` identifier.
   - Download firmware with a **green checkmark (Signed)**.
   > [!IMPORTANT]
   > The IPSW version must be **equal to or newer** than the iOS version already on the phone. Downgrades fail with `Error 68 (downgrade_check)`.

---

### Phase 2: Run Baseline Diagnostic (Generate Your Log)

The diagnostic run determines whether your phone is blocked by Error 100 and creates your device log (`restore_<ECID>_<time>.log`):

```powershell
.\bin\windows-x64\idevicerestore.exe -y -P "C:\path\to\your_firmware.ipsw"
```
*(On macOS/Linux: `idevicerestore -y -P "/path/to/firmware.ipsw"`)*

- **What happens:** The restore will write the root filesystem and fail at `install_splat` with `Failed preallocation due to space (Error 100)`.
- **What this gives you:** A log file named `restore_<ECID>_<timestamp>.log` is saved in your directory. Proceed to Phase 3.

---

### Phase 3: Calculate YOUR Phone's Custom Override Number

Do not guess or copy numbers from other users! Calculate the exact number for your phone:

#### Method A: 1-Click Batch Tool (Windows)
Double-click **`tools\calculate_my_override.bat`**, drag and drop your downloaded `.ipsw` file into the window, and hit Enter.

#### Method B: Python Command
```bash
python tools/suggest_cryptex_size.py "C:\path\to\your_firmware.ipsw"
```

#### What the Tool Outputs:
```text
=================================================================
 iOS Firmware: iPhone12,5 - iOS 27.3 (24C5037i)
 Real System Cryptex Size: 6048 MiB
=================================================================
[+] Analyzing restore log: restore_001971611442802e_1794587292.log
    - Space Needed:     13073 MB
    - Free Space:       6507 MB

>>> STEP 1: FORCE APP DELETION (Free ~1.2 GB of App Binaries) <<<
In Windows PowerShell, run:
    $env:IDEVICERESTORE_CRYPTEX_SIZE_MIB = "13859"
    .\bin\windows-x64\idevicerestore.exe -y -P "C:\path\to\your_firmware.ipsw"

>>> STEP 2: COMPLETE RESTORE (With Override Cleared) <<<
    Remove-Item Env:\IDEVICERESTORE_CRYPTEX_SIZE_MIB
    .\bin\windows-x64\idevicerestore.exe -y -P "C:\path\to\your_firmware.ipsw"
```

#### The Math Behind Your Custom Number:
To trigger `AppDeletion` and delete $T$ megabytes of app binaries:
$$\text{CryptexOverride} = (2 \times \text{ContainerFreeSpace}) + \text{TargetDelete} - \text{Offset}$$
Our tool automatically calculates this formula using your exact free space!

---

### Phase 4: Step 1 — Force Stage 2 AppDeletion

Run the command printed by the tool in Phase 3 with your custom override:

```powershell
# Set your custom number calculated in Phase 3
$env:IDEVICERESTORE_CRYPTEX_SIZE_MIB = "YOUR_CALCULATED_NUMBER"

# Launch Step 1
.\bin\windows-x64\idevicerestore.exe -y -P "C:\path\to\your_firmware.ipsw"
```

#### What Happens During Step 1:
1. `libpartition` starts space checks and identifies that required space exceeds container free space.
2. It executes `AppDeletion`:
   ```text
   We need a additional 899497984 bytes for the restore from App deletion
   Attempting to run AppDeletion to free 899497984 bytes
   AppDeletion was able to free up sufficient space for asr retry attempt
   ```
3. **1 to 2 GB of third-party `.app` bundles are deleted** from `/private/var/containers/Bundle/Application/`.
4. The run exits with **Error 1110 (`space_checks`)**. **THIS IS EXPECTED AND NORMAL!**
5. The device cleanly unmounts the Data volume, runs the APFS container reaper, and **automatically reboots back to Recovery Mode**.

---

### Phase 5: Step 2 — Full Data-Preserving Restore

Once your iPhone screen shows the Recovery Mode logo again (computer + cable):

1. **Clear the override variable:**
   ```powershell
   Remove-Item Env:\IDEVICERESTORE_CRYPTEX_SIZE_MIB
   ```
   *(On macOS/Linux bash: `unset IDEVICERESTORE_CRYPTEX_SIZE_MIB`)*

2. **Execute the clean restore:**
   ```powershell
   .\bin\windows-x64\idevicerestore.exe -y -P "C:\path\to\your_firmware.ipsw"
   ```

#### Milestones to Watch in Terminal:
- `Checkpoint completed id: 0x6A3 (space_checks) result=0` (Passes with zero errors!).
- Root filesystem restores (8.9 GB written via ASR).
- Baseband, Rose, Savage, and SEP firmwares flash.
- `install_splat`: Preallocation of `os.dmg` **succeeds** because free space is now $> 8\text{ GB}$ (78% < 84% ceiling).
- `Sealing System Volume (77)`.
- Final status:
  ```text
  Got status message
  Status: Restore Finished
  DONE
  progress: 7 1.000000
  ```

---

### Phase 6: Post-Restore Sequence (On Your iPhone)

> [!WARNING]
> Do NOT disconnect the USB cable or hard-reset the phone during this phase.

1. **Reboot:** The iPhone reboots and shows the Apple logo with a progress bar.
2. **"Swipe up to recover":** A white screen appears prompting **"Swipe up to recover"**. Swipe up and enter your **regular passcode**.
3. **"Attempting data recovery":** The screen displays a white background with a progress bar reading **"Attempting data recovery"**.
   - **Duration:** This takes between **20 and 50 minutes** as iOS updates database indexes and schema files.
   - The bar may pause near 80–90% or run a second progress pass. This is completely normal.
4. **Lock Screen Arrival:** The phone boots directly into your familiar **Lock Screen** with your personalized wallpaper, notifications, and apps intact (NOT the factory "Hello" screen).
5. **Apps:** Some third-party apps may have a small cloud icon next to their names. Their application code was offloaded, but their documents, login sessions, and chat histories are 100% intact. Tap them on Wi-Fi to re-download.

---

## 1-Click Interactive Batch Files (Windows)

For Windows users who prefer not to type commands:

1. **`tools\calculate_my_override.bat`**: Drag & drop your IPSW to get your custom override.
2. **`scripts\run_step1_app_deletion.bat`**: Drag & drop IPSW, enter your override number, and let it run Step 1.
3. **`scripts\run_step2_full_restore.bat`**: Drag & drop IPSW once rebooted to finish the restore.

---

## Verified Success Numbers (iPhone 11 Pro Max, 64 GB)

| Checkpoint / Metric | Before Fix | After Stage 2 AppDeletion (Step 1) | Final Clean Restore (Step 2) |
| :--- | :--- | :--- | :--- |
| **Data Volume Usage** | 45,593 MB | 43,987 MB (**-1,526 MB apps offloaded**) | 43,987 MB |
| **Container Free Space** | 6,507 MB | **8,114 MB** (+1,607 MB free space) | **Sufficient (> 8.1 GB)** |
| **Cryptex Preallocation** | 97.5% of free space | — | **78.16% of free space (< 84% ceiling)** |
| **Restore Status** | Failed (Error 100) | AppDeletion Succeeded | **Status: Restore Finished (100%)** |
| **User Data & Photos** | Preserved | Preserved | **100% Intact & Verified** |

---

## Additional Documentation

- [Technical Deep Dive (APFS Ceiling & libpartition Disassembly)](docs/TECHNICAL_DEEP_DIVE.md)
- [Troubleshooting Manual (Error 68, 100, 1110, Yonkers Ticket, USB Drops)](docs/TROUBLESHOOTING.md)
- [Building from Source (macOS, Linux, Windows MSYS2)](scripts/)
- [Sample Failure & Success Logs](examples/logs/)

---

## Credits & References

- Initial Cryptex patch and APFS ceiling research by [3SENN/iphone-stuck-in-recovery-full-storage](https://github.com/3SENN/iphone-stuck-in-recovery-full-storage).
- Upstream restore suite by [libimobiledevice](https://github.com/libimobiledevice/idevicerestore).
- Stage 2 `AppDeletion` comparison bug discovery & two-step recipe by **khosa76**.
