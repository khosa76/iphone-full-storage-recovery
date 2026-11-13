# Technical Deep Dive: APFS Preallocation Ceilings & Apple libpartition Logic

This document provides a technical and reverse-engineered explanation of why iOS devices with full storage fail during updates, and why our two-step Stage 2 AppDeletion method successfully recovers them without data loss.

---

## 1. APFS Container Architecture & Preallocation

### Container Space Sharing
APFS groups volumes into a single shared Container (`/dev/disk0s1`, synthesized as `/dev/disk3` during restore).
In an iOS restore environment:
- **`disk3s1`**: System (APFS snapshot / Root OS)
- **`disk3s2`**: Data (`/mnt2`, User files, databases, photos, and apps)
- **`disk3s3`**: xART (`/mnt7`, SEP hardware storage)
- **`disk3s4`**: Update (`/mnt4`)
- **`disk3s5`**: Hardware (`/mnt6`)
- **`disk3s7`**: Preboot (`/mnt9`, Cryptexes and boot firmware)

All volumes share the container's free space pool.

### The 84.35% Preallocation Limit
During `install_splat` (checkpoint `0x06A6`), `restored` installs the system cryptex image:
`Cryptex1,SystemOS` $\to$ `/mnt9/cryptex1/current/os.dmg` (typically 5,800 to 6,342 MB).

To prevent filesystem fragmentation and ensure atomic writes, `restored` issues:
```c
fcntl(fd, F_PREALLOCATE, &(fstore_t){
    .fst_flags = F_ALLOCATEALL | F_ALLOCATECONTIG,
    .fst_posmode = F_PEOFPOSMODE,
    .fst_offset = 0,
    .fst_length = cryptex_file_size,
    .fst_bytesalloc = 0
});
```
APFS enforces an internal allocation threshold: **a single reservation cannot exceed ~84.35% of remaining container free space**.

| Container Free Space | Maximum Allowed Preallocation (84.35%) | Real `os.dmg` Size (iPhone 11 Pro Max) | Result |
| :--- | :--- | :--- | :--- |
| **6,507 MB** | 5,488 MB | 6,342 MB (97.5% of free space) | **REJECTED (`Unknown error: -1`)** |
| **6,587 MB** | 5,556 MB | 6,342 MB (96.3% of free space) | **REJECTED (`Unknown error: -1`)** |
| **8,114 MB** | **6,844 MB** | 6,342 MB (**78.16% of free space**) | **ACCEPTED (Success!)** |

To pass `install_splat`, container free space must be $\ge \frac{6,341,787,648}{0.8435} \approx \mathbf{7,518\text{ MB}}$.

---

## 2. Stage 1 Cleanup & The Passcode Encryption Lock

Before restoring the OS, `restored` runs `space_checks` (checkpoint `0x06A3`). If space appears tight, it calls `libpartition`'s low-space cleanup routine.

### Why Photo Cache Purging Fails
The cleanup routine attempts to purge thumbnail databases and photo caches from `/mnt2/mobile/Media/PhotoData` and `Syndication.photoslibrary`.

However, on any device protected by a passcode, the flash storage uses hardware-backed Data Protection (Class C and Class B keys):
- In locked Recovery Mode, the user's passcode has not been entered.
- The hardware cryptographic keys remain locked inside the Secure Enclave (SEP).
- Therefore, the filesystem denies modification to user directories:
```text
libpartition: Could not reset metadata on /mnt2/mobile/Media/PhotoData/Thumbnails/: Operation not permitted
libpartition: Deleting contents of /mnt2/mobile/Library/Photos/Libraries/Syndication.photoslibrary/ failed (result: 1)
```
Consequently, Stage 1 cleanup frees **only ~12 KB** (temporary crash logs).

---

## 3. The Apple libpartition Comparison Bug

When Stage 1 cleanup does not free enough space, `libpartition` is designed to trigger Stage 2 cleanup: **`AppDeletion`**.
`AppDeletion` offloads third-party `.app` application bundles from `/private/var/containers/Bundle/Application/`, preserving all app databases, documents, and user preferences.

### The Buggy Comparison Logic
In Apple's `restored_update` binary, the check to decide whether to run `AppDeletion` contains a critical flaw:

```c
// Decompiled representation of Apple's libpartition logic:
uint64_t container_free_after_initial_cleanup = get_container_free_space();
uint64_t shortfall = space_needed_for_restore - container_free_after_initial_cleanup;

// BUG: Apple compares the entire container free space against the shortfall!
if (container_free_after_initial_cleanup >= shortfall) {
    ramrod_log("Sufficient space freed after initial cleanup. Skipping app deletion. "
               "SpaceNeededForRestore: %llu ContainerFreeSpace: %llu ContainerFreeSpaceAfterInitialCleanup: %llu\n",
               shortfall, container_free_before, container_free_after_initial_cleanup);
    // Skips AppDeletion and exits cleanup!
} else {
    uint64_t bytes_to_delete = shortfall - container_free_after_initial_cleanup;
    ramrod_log("We need a additional %llu bytes for the restore from App deletion\n", bytes_to_delete);
    run_app_deletion(bytes_to_delete);
}
```

### Why Standard Suggested Overrides Fail (Error 1110)
Standard calculation tools pick an override that puts `space_needed` ~150 MB over free space:
- `shortfall`: ~150 MB (156,971,008 bytes).
- `container_free_after_initial_cleanup`: ~6,823 MB (6,823,956,480 bytes).

Because **6,823 MB $\ge$ 150 MB**, the `if` statement evaluates to `true`!
The code logs:
```text
Sufficient space freed after initial cleanup. Skipping app deletion. SpaceNeededForRestore: 156971008 ContainerFreeSpace: 6823948288 ContainerFreeSpaceAfterInitialCleanup: 6823956480
```
It skips `AppDeletion`, performs no further cleanup, and then tests whether free space satisfies `SpaceNeededForRestore`. Since the 150 MB deficit remains, it terminates with:
```text
CHECKPOINT FAILURE:(FAILURE:1110) RESTORED:[0x06A3] space_checks ENOSPC for upgrade install
```

---

## 4. The Mathematical Derivation of the Override

To force `libpartition` into Stage 2 `AppDeletion`, we must satisfy:
$$\text{shortfall} > \text{ContainerFreeSpace}$$

Given:
$$\text{shortfall} = \text{SpaceNeededForRestore} - \text{ContainerFreeSpace}$$

Substituting into the inequality:
$$\text{SpaceNeededForRestore} - \text{ContainerFreeSpace} > \text{ContainerFreeSpace}$$
$$\mathbf{\text{SpaceNeededForRestore} > 2 \times \text{ContainerFreeSpace}}$$

### Calculating Bytes Deleted by AppDeletion
When the inequality holds, `libpartition` requests:
$$\text{bytes\_to\_delete} = \text{shortfall} - \text{ContainerFreeSpace} = \text{SpaceNeededForRestore} - 2 \times \text{ContainerFreeSpace}$$

To delete a target amount of app binaries (e.g. $T = 1,000\text{ MiB}$):
$$\text{SpaceNeededForRestore} = 2 \times \text{ContainerFreeSpace} + T$$

### Converting to `IDEVICERESTORE_CRYPTEX_SIZE_MIB`
`restored` calculates `SpaceNeededForRestore` from `Cryptex1,SystemOSSize`:
$$\text{SpaceNeededForRestore} = \text{CryptexSize} + \text{BaseRestoreSpace} - \text{SystemVolumeSize} - \text{PrebootVolumeSize}$$

On iPhone 11/12/13/14 series, the offset $(\text{BaseRestoreSpace} - \text{SystemVolumeSize} - \text{PrebootVolumeSize})$ is approximately $+355\text{ to }+372\text{ MB}$.

Therefore:
$$\mathbf{\text{CryptexOverrideBytes} = (2 \times \text{ContainerFreeSpaceBytes}) + \text{TargetDeleteBytes} - \text{OffsetBytes}}$$

Plugging in our iPhone 11 Pro Max numbers:
- $\text{ContainerFreeSpace} \approx 6,824\text{ MB}$
- $T = 1,000\text{ MB}$
- $\text{Offset} \approx 372\text{ MB}$
$$\text{CryptexOverride} = (2 \times 6,824) + 1,000 - 372 = \mathbf{14,276\text{ MB}} \approx \mathbf{13,660\text{ MiB}}$$

Declaring `13,660 MiB` asked `AppDeletion` to free 899 MB, and it freed **1,526 MB** of apps, expanding container free space to **8,114 MB** and clearing the APFS preallocation ceiling.
