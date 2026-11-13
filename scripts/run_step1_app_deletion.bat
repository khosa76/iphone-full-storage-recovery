@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo  iPhone Full-Storage Recovery - Step 1: Force App Deletion
echo ========================================================
echo.
echo This step forces libpartition to offload 1-2 GB of third-party
echo app bundles from your device without touching user data or photos.
echo.
echo NOTE: This run is EXPECTED to exit with Error 1110 after freeing space.
echo The device will automatically reboot into Recovery Mode for Step 2.
echo.

set /p IPSW_PATH="Drag and drop your IPSW file here and press Enter: "
set "IPSW_PATH=%IPSW_PATH:"=%"

if not exist "%IPSW_PATH%" (
    echo [ERROR] IPSW file not found at: %IPSW_PATH%
    pause
    exit /b 1
)

set /p OVERRIDE_MIB="Enter Cryptex override (Press Enter for default 13660): "
if "%OVERRIDE_MIB%"=="" set OVERRIDE_MIB=13660

echo.
echo [+] Setting IDEVICERESTORE_CRYPTEX_SIZE_MIB=%OVERRIDE_MIB%
set IDEVICERESTORE_CRYPTEX_SIZE_MIB=%OVERRIDE_MIB%

echo [+] Launching idevicerestore...
"%~dp0..\bin\windows-x64\idevicerestore.exe" -y -P "%IPSW_PATH%"

echo.
echo ========================================================
echo Step 1 complete. Check the logs above for:
echo 'AppDeletion was able to free up sufficient space'
echo.
echo Wait until your iPhone reboots back to the Recovery screen,
echo then run 'run_step2_full_restore.bat'.
echo ========================================================
pause
