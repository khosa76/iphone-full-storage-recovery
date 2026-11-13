@echo off
setlocal enabledelayedexpansion

echo ================================================================
echo  Calculate Custom Cryptex Override for Your Device
echo ================================================================
echo.

set /p IPSW_PATH="Drag and drop your IPSW firmware file here and press Enter: "
set "IPSW_PATH=%IPSW_PATH:"=%"

if not exist "%IPSW_PATH%" (
    echo [ERROR] IPSW file not found at: %IPSW_PATH%
    pause
    exit /b 1
)

python "%~dp0suggest_cryptex_size.py" "%IPSW_PATH%"
pause
