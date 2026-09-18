@echo off
chcp 65001 >nul
set APP_DIR=%~dp0

echo === Надеваем иконку MAMONOV на ScreenRecorder.exe ===
echo.

:: rcedit — маленькая утилита для встраивания иконок в .exe
:: Скачивается один раз в bin\
set RCEDIT=%APP_DIR%bin\rcedit-x64.exe

if not exist "%RCEDIT%" (
    echo [!] rcedit не найден, скачиваем в bin\
    if not exist "%APP_DIR%bin" mkdir "%APP_DIR%bin"
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/electron/rcedit/releases/download/v2.0.0/rcedit-x64.exe' -OutFile '%RCEDIT%'"
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось скачать rcedit
        echo Скачайте вручную: https://github.com/electron/rcedit/releases
        pause
        goto :eof
    )
    echo [OK] rcedit скачан
)

set EXE=%APP_DIR%dist\ScreenRecorder.exe
set ICO=%APP_DIR%mamonov_icon.ico

if not exist "%EXE%" (
    echo [ОШИБКА] %EXE% не найден
    echo Сначала запустите build.bat
    pause
    goto :eof
)

if not exist "%ICO%" (
    echo [ОШИБКА] %ICO% не найден
    pause
    goto :eof
)

echo [OK] Надеваем иконку на ScreenRecorder.exe...
"%RCEDIT%" "%EXE%" --set-icon "%ICO%"

if errorlevel 1 (
    echo [ОШИБКА] rcedit не смог надеть иконку
    pause
    goto :eof
)

echo.
echo === Готово! Иконка MAMONOV на ScreenRecorder.exe ===
echo.
pause
