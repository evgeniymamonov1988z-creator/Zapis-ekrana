# -*- coding: utf-8 -*-
"""
Экранник — ключ активации (Ekrannik-Unlock).

Запускается после оплаты. Делает две вещи:
  1) удаляет файл demo.flag рядом с Ekrannik.exe → программа считает себя полной;
  2) стирает сохранённую дату первого запуска демо (реестр + %APPDATA%\\MAMONOV).
Затем удаляет сам себя, чтобы не оставался в загрузках.

Ничего не устанавливает, не трогает записи и настройки пользователя.
"""

import os
import sys
import subprocess

CODE = 'AE'
APP_EXE = 'Ekrannik.exe'


def appdata_dir():
    base = os.environ.get('APPDATA') or os.path.expanduser('~')
    return os.path.join(base, 'MAMONOV')


def find_app_dirs():
    """Найти папки, где лежит Ekrannik.exe."""
    found = []
    candidates = []
    appdata = os.environ.get('APPDATA')
    localappdata = os.environ.get('LOCALAPPDATA')
    if localappdata:
        candidates.append(os.path.join(localappdata, 'Programs', 'Ekrannik'))
    for env in ('ProgramFiles', 'ProgramFiles(x86)', 'ProgramW6432'):
        p = os.environ.get(env)
        if p:
            candidates.append(os.path.join(p, 'Ekrannik'))
    candidates.append(os.path.dirname(os.path.abspath(sys.argv[0])))
    for c in candidates:
        try:
            if c and os.path.isfile(os.path.join(c, APP_EXE)) and c not in found:
                found.append(c)
        except Exception:
            pass
    return found


def remove_flag(folder):
    flag = os.path.join(folder, 'demo.flag')
    try:
        if os.path.isfile(flag):
            try:
                import ctypes
                ctypes.windll.kernel32.SetFileAttributesW(flag, 128)  # обычный
            except Exception:
                pass
            os.remove(flag)
            return True
    except Exception as e:
        return ('err', str(e))
    return False


def clear_demo_date():
    """Стереть дату первого запуска: файл + реестр."""
    done = []
    f = os.path.join(appdata_dir(), '.demo_date_' + CODE)
    try:
        if os.path.isfile(f):
            try:
                import ctypes
                ctypes.windll.kernel32.SetFileAttributesW(f, 128)
            except Exception:
                pass
            os.remove(f)
            done.append('file')
    except Exception:
        pass
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\MAMONOV', 0,
                            winreg.KEY_SET_VALUE) as key:
            try:
                winreg.DeleteValue(key, 'first_' + CODE)
                done.append('reg')
            except FileNotFoundError:
                pass
    except Exception:
        pass
    return done


def self_delete():
    """Удалить сам файл после выхода (через отдельный cmd)."""
    try:
        exe = os.path.abspath(sys.argv[0])
        if getattr(sys, 'frozen', False):
            subprocess.Popen(['cmd', '/c', 'ping', '127.0.0.1', '-n', '2', '>nul',
                              '&', 'del', '/f', '/q', exe],
                             creationflags=0x08000000)
    except Exception:
        pass


def main():
    dirs = find_app_dirs()
    if not dirs:
        try:
            import tkinter as tk
            from tkinter import messagebox
            r = tk.Tk(); r.withdraw()
            messagebox.showerror('Экранник — активация',
                                 'Не удалось найти Ekrannik.exe.\n'
                                 'Сначала установите программу, затем запустите этот ключ.')
            r.destroy()
        except Exception:
            print('Ekrannik.exe не найден')
        return

    for d in dirs:
        remove_flag(d)
    cleared = clear_demo_date()

    try:
        import tkinter as tk
        from tkinter import messagebox
        r = tk.Tk(); r.withdraw()
        messagebox.showinfo('Экранник — активация',
                            'Готово! Теперь у вас полная версия.\n\n'
                            'Откройте Экранник — ограничений по дням нет.')
        r.destroy()
    except Exception:
        print('Готово: полная версия.')
    self_delete()


if __name__ == '__main__':
    main()
