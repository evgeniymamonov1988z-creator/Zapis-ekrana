@echo off
setlocal
set APP_DIR=%~dp0
cd /d "%APP_DIR%"

echo === Building MAMONOV Screen Recorder (single .exe) ===
echo.

rem --- clean old build ---
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist ScreenRecorder.spec del ScreenRecorder.spec

rem --- ffmpeg inside .exe (only if present in bin\) ---
set EXTRA=
if exist bin\ffmpeg.exe (
    set EXTRA=--add-binary "bin\ffmpeg.exe;bin"
    echo [OK] ffmpeg.exe will be embedded
) else (
    echo [i] ffmpeg.exe not in bin\ - app downloads it on first run
)

rem --- icon for Explorer ---
set ICON=
if exist mamonov_icon.ico (
    set ICON=--icon=mamonov_icon.ico
    echo [OK] icon mamonov_icon.ico
) else (
    echo [i] icon not found - default icon
)

pyinstaller --noconfirm --onefile --windowed --name ScreenRecorder %ICON% --add-data "updater.pyw;." --add-data "mamonov_icon.ico;." %EXTRA% screen_recorder.pyw

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    pause
    goto :eof
)

rem --- put icon onto the exe via rcedit ---
if exist mamonov_icon.ico (
    echo.
    echo === Applying icon ===
    call set_icon.bat
)

rem --- rename result to Russian name (built from Unicode codes, no Cyrillic in this file) ---
echo.
echo === Renaming result to Russian name ===
powershell -NoProfile -Command "$c=[char[]](0x0417,0x0430,0x043F,0x0438,0x0441,0x044C,0x20,0x044D,0x043A,0x0440,0x0430,0x043D,0x0430); $n=(-join $c)+'.exe'; if (Test-Path 'dist\ScreenRecorder.exe'){ Rename-Item -LiteralPath 'dist\ScreenRecorder.exe' -NewName $n -Force; Write-Host ('[OK] dist\'+$n) }"

echo.
echo === Done! ===
echo The ready file is in the dist folder.
echo.
pause
