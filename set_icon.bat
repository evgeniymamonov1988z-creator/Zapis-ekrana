@echo off
setlocal
set APP_DIR=%~dp0

echo === Applying MAMONOV icon to ScreenRecorder.exe ===
echo.

rem rcedit - small tool that embeds an icon into an .exe (downloaded once into bin\)
set RCEDIT=%APP_DIR%bin\rcedit-x64.exe

if not exist "%RCEDIT%" (
    echo [i] rcedit not found, downloading into bin\
    if not exist "%APP_DIR%bin" mkdir "%APP_DIR%bin"
    powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://github.com/electron/rcedit/releases/download/v2.0.0/rcedit-x64.exe' -OutFile '%RCEDIT%'"
    if errorlevel 1 (
        echo [ERROR] Failed to download rcedit
        goto :eof
    )
    echo [OK] rcedit downloaded
)

set EXE=%APP_DIR%dist\ScreenRecorder.exe
set ICO=%APP_DIR%mamonov_icon.ico

if not exist "%EXE%" (
    echo [ERROR] %EXE% not found. Run build.bat first.
    goto :eof
)
if not exist "%ICO%" (
    echo [ERROR] %ICO% not found.
    goto :eof
)

"%RCEDIT%" "%EXE%" --set-icon "%ICO%"
if errorlevel 1 (
    echo [ERROR] rcedit failed to set icon
    goto :eof
)

echo [OK] Icon applied
