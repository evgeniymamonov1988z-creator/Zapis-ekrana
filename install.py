#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Установщик MAMONOV Запись экрана
Автоматически скачивает ffmpeg и устанавливает Pillow.
"""

import subprocess
import sys
import os
import urllib.request
import zipfile
import shutil
import ctypes
import time


CREATE_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def _is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def _run_cmd(cmd, **kw):
    return subprocess.run(
        cmd, creationflags=CREATE_NO_WINDOW,
        capture_output=True, text=True, timeout=300, **kw
    )


def _progress(label, current, total):
    pct = int(current * 100 / total) if total > 0 else 0
    bar_len = 30
    filled = int(bar_len * pct / 100)
    bar = '█' * filled + '░' * (bar_len - filled)
    print(f'\r  {label}  [{bar}] {pct}%', end='', flush=True)


def _download_with_progress(url, dest):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        total = int(resp.headers.get('Content-Length', 0))
        with open(dest, 'wb') as f:
            downloaded = 0
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                _progress('Скачивание', downloaded, total)
    print()  # новая строка после прогресс-бара


def _add_to_path_win(path):
    """Добавляет путь в PATH текущего пользователя (Windows)."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Environment', 0, winreg.KEY_SET_VALUE
        )
        existing, _ = winreg.QueryValueEx(key, 'Path')
        if path not in existing:
            new_path = existing.rstrip(';') + ';' + path
            winreg.SetValueEx(key, 'Path', 0, winreg.REG_EXPAND_SZ, new_path)
        winreg.CloseKey(key)
        # Уведомить систему об изменении
        ctypes.windll.user32.SendMessageW(0xFFFF, 0x001A, 0, 'Environment')
        return True
    except Exception as e:
        print(f'  Не удалось добавить в PATH: {e}')
        return False


# ============================================================
# Установка ffmpeg
# ============================================================

def install_ffmpeg():
    print('=' * 50)
    print('  Установка ffmpeg')
    print('=' * 50)

    # Проверяем, есть ли уже
    r = _run_cmd(['ffmpeg', '-version'])
    if r.returncode == 0:
        print('  ✓ ffmpeg уже установлен')
        return True

    # Папка установки
    prog_dir = os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files'), 'MAMONOV')
    ffmpeg_dir = os.path.join(prog_dir, 'ffmpeg')
    ffmpeg_bin = os.path.join(ffmpeg_dir, 'bin')

    # Скачать
    url = 'https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-win64-gpl.zip'
    temp_zip = os.path.join(os.environ.get('TEMP', 'C:\\Temp'), 'ffmpeg_download.zip')
    temp_extract = os.path.join(os.environ.get('TEMP', 'C:\\Temp'), 'ffmpeg_extract')

    print('  Скачиваю ffmpeg (≈90 МБ, GitHub CDN)...')
    try:
        _download_with_progress(url, temp_zip)
    except Exception as e:
        print(f'  ✗ Ошибка скачивания: {e}')
        print('  Скачайте вручную с https://www.gyan.dev/ffmpeg/builds/')
        return False

    # Извлечь ТОЛЬКО bin/ffmpeg.exe (не весь архив)
    print('  Извлекаю ffmpeg.exe...')
    os.makedirs(temp_extract, exist_ok=True)
    extracted_exe = None
    try:
        with zipfile.ZipFile(temp_zip, 'r') as zf:
            for info in zf.infolist():
                name_lower = info.filename.lower().replace('\\', '/')
                if name_lower.endswith('ffmpeg.exe') and 'bin/' in name_lower:
                    with zf.open(info) as src, open(os.path.join(temp_extract, 'ffmpeg.exe'), 'wb') as dst:
                        while True:
                            chunk = src.read(65536)
                            if not chunk:
                                break
                            dst.write(chunk)
                    extracted_exe = os.path.join(temp_extract, 'ffmpeg.exe')
                    break
            # Fallback: любой ffmpeg.exe в архиве
            if not extracted_exe:
                for info in zf.infolist():
                    if info.filename.lower().endswith('ffmpeg.exe'):
                        with zf.open(info) as src, open(os.path.join(temp_extract, 'ffmpeg.exe'), 'wb') as dst:
                            while True:
                                chunk = src.read(65536)
                                if not chunk:
                                    break
                                dst.write(chunk)
                        extracted_exe = os.path.join(temp_extract, 'ffmpeg.exe')
                        break
    except Exception as e:
        print(f'  ✗ Ошибка распаковки: {e}')
        return False

    if not extracted_exe or not os.path.isfile(extracted_exe):
        print('  ✗ ffmpeg.exe не найден в архиве')
        return False

    # Переместить в Program Files/MAMONOV/ffmpeg/bin/
    os.makedirs(ffmpeg_bin, exist_ok=True)
    dest = os.path.join(ffmpeg_bin, 'ffmpeg.exe')
    shutil.copy2(extracted_exe, dest)
    print(f'  ✓ ffmpeg.exe установлен: {dest}')

    # Добавить в PATH
    if _add_to_path_win(ffmpeg_bin):
        print(f'  ✓ Добавлено в PATH: {ffmpeg_bin}')
    else:
        print(f'  ⚠ Добавьте в PATH вручную: {ffmpeg_bin}')

    # Очистка
    try:
        os.remove(temp_zip)
        shutil.rmtree(temp_extract, ignore_errors=True)
    except Exception:
        pass

    return True


# ============================================================
# Установка Pillow
# ============================================================

def install_pillow():
    print()
    print('=' * 50)
    print('  Установка Pillow')
    print('=' * 50)

    try:
        from PIL import Image
        print('  ✓ Pillow уже установлен')
        return True
    except ImportError:
        pass

    print('  Устанавливаю Pillow через pip...')
    try:
        r = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', 'Pillow', '--quiet'],
            creationflags=CREATE_NO_WINDOW, timeout=120
        )
        if r.returncode == 0:
            print('  ✓ Pillow установлен')
            return True
        else:
            print('  ✗ Ошибка установки Pillow')
            return False
    except Exception as e:
        print(f'  ✗ Ошибка: {e}')
        return False


# ============================================================
# Ярлык на рабочем столе
# ============================================================

def create_shortcut():
    print()
    print('=' * 50)
    print('  Создание ярлыка')
    print('=' * 50)

    try:
        import winshell
        has_winshell = True
    except ImportError:
        has_winshell = False

    # Путь к pythonw.exe (без чёрного окна)
    pythonw_path = sys.executable.replace('python.exe', 'pythonw.exe')
    if not os.path.isfile(pythonw_path):
        pythonw_path = sys.executable  # fallback

    desktop = os.path.join(os.path.expanduser('~'), 'Desktop')

    # Попробуем через winshell
    if has_winshell:
        try:
            import winshell
            shortcut = winshell.shortcut(
                os.path.join(desktop, 'MAMONOV Запись экрана.lnk')
            )
            shortcut.path = pythonw_path
            shortcut.arguments = f'"{os.path.abspath("screen_recorder.pyw")}"'
            shortcut.working_dir = os.path.abspath('.')
            shortcut.description = 'MAMONOV Запись экрана'
            shortcut.write()
            print('  ✓ Ярлык создан')
            return True
        except Exception:
            pass

    # Через PowerShell
    try:
        ps_script = f'''
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut("{os.path.join(desktop, 'MAMONOV Запись экрана.lnk')}")
$sc.TargetPath = "{pythonw_path}"
$sc.Arguments = ""{os.path.abspath('screen_recorder.pyw')}""
$sc.WorkingDirectory = "{os.path.abspath('.')}"
$sc.Description = "MAMONOV Запись экрана"
$sc.Save()
'''
        subprocess.run(
            ['powershell', '-Command', ps_script],
            creationflags=CREATE_NO_WINDOW, timeout=15
        )
        print('  ✓ Ярлык создан')
        return True
    except Exception as e:
        print(f'  ✗ Не удалось создать ярлык: {e}')
        print(f'  Запустите вручную: pythonw screen_recorder.pyw')
        return False


# ============================================================
# Главная функция
# ============================================================

def main():
    print()
    print('╔══════════════════════════════════════════╗')
    print('║   MAMONOV Запись экрана — Установщик    ║')
    print('╚══════════════════════════════════════════╝')
    print()

    # Проверка ОС
    if sys.platform != 'win32':
        print('Установщик предназначен для Windows.')
        sys.exit(1)

    ok = True

    # 1. ffmpeg
    if not install_ffmpeg():
        ok = False

    # 2. Pillow
    if not install_pillow():
        ok = False

    # 3. Ярлык
    create_shortcut()

    # Итог
    print()
    print('=' * 50)
    if ok:
        print('  ✓ Всё установлено! Запустите программу:')
        print('    pythonw screen_recorder.pyw')
        print('  Или через ярлык на рабочем столе.')
    else:
        print('  ⚠ Часть компонентов не установлена.')
        print('  См. ошибки выше.')
    print('=' * 50)
    print()


if __name__ == '__main__':
    main()
