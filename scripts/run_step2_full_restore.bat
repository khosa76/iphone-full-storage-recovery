@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo  iPhone Full-Storage Recovery - Step 2: Full Data-Preserving Restore
echo ========================================================
echo.
echo Make sure your iPhone is back on the Recovery Mode screen
echo (screen showing computer and cable).
echo.

set /p IPSW_PATH="Drag and drop your IPSW file here and press Enter: "
set "IPSW_PATH=%IPSW_PATH:"=%"

if not exist "%IPSW_PATH%" (
    echo [ERROR] IPSW file not found at: %IPSW_PATH%
    pause
    exit /b 1
)

echo [+] Ensuring IDEVICERESTORE_CRYPTEX_SIZE_MIB is cleared...
set IDEVICERESTORE_CRYPTEX_SIZE_MIB=

echo [+] Launching idevicerestore (Data-Preserving Upgrade Install)...
"%~dp0..\bin\windows-x64\idevicerestore.exe" -y -P "%IPSW_PATH%"

echo.
echo ========================================================
echo Restore command finished.
echo If output shows 'Status: Restore Finished', your iPhone
echo will reboot to 'Swipe up to recover' -> Passcode ->
echo 'Attempting data recovery' (takes 20-50 minutes).
echo.
echo DO NOT UNPLUG YOUR IPHONE UNTIL YOU SEE YOUR LOCK SCREEN!
echo ========================================================
pause

