@echo off
chcp 65001 >nul
set APP_DIR=%~dp0
cd /d %APP_DIR%

echo === Сборка MAMONOV Запись экрана (один .exe) ===
echo.

:: Удаляем старую сборку
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist "Запись экрана.spec" del "Запись экрана.spec"
if exist ScreenRecorder.spec del ScreenRecorder.spec

:: ffmpeg внутрь .exe (если лежит в bin\)
set EXTRA=
if exist bin\ffmpeg.exe (
    set EXTRA=--add-binary "bin\ffmpeg.exe;bin"
    echo [OK] ffmpeg.exe будет внутри .exe
) else (
    echo [!] ffmpeg.exe не найден в bin\ — будет искаться в PATH
)

:: Иконка для Проводника
set ICON=
if exist mamonov_icon.ico (
    set ICON=--icon=mamonov_icon.ico
    echo [OK] Иконка mamonov_icon.ico
) else (
    echo [!] Иконка mamonov_icon.ico не найдена — Проводник покажет стандартную
)

pyinstaller --noconfirm --onefile --windowed --name "Запись экрана" %ICON% --add-data "updater.pyw;." --add-data "mamonov_icon.ico;." %EXTRA% screen_recorder.pyw

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Сборка не удалась!
    pause
    goto :eof
)

:: Надеваем иконку через rcedit (после PyInstaller)
if exist mamonov_icon.ico (
    echo.
    echo === Надеваем иконку на ScreenRecorder.exe ===
    call set_icon.bat
) else (
    echo [!] Иконка не найдена — пропускаем
)

echo.
echo === Готово! ===
echo Файл: dist\Запись экрана.exe
echo.
pause
