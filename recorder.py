#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAMONOV Запись экрана / MAMONOV Screen Recorder

Простая программа для записи экрана с минимальным потреблением ресурсов.
Две кнопки: Начать/Остановить запись и Сохранить.
Панель не попадает в видео (Windows 10 2004+).
"""

import tkinter as tk
import subprocess
import os
import sys
import ctypes
import tempfile
import shutil
import time
import re


# ============================================================
# Язык интерфейса
# ============================================================

def _is_russian_windows():
    """Определяет, русский ли интерфейс Windows."""
    try:
        lang = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        return (lang & 0xFF) == 0x19
    except Exception:
        return False


LANG = {}


def _load_lang():
    global LANG
    if _is_russian_windows():
        LANG = {
            'title':         'MAMONOV Запись экрана',
            'btn_start':     '▶  Начать запись',
            'btn_stop':      '⏹  Остановить',
            'btn_save':      '💾  Сохранить',
            'status_ready':  '',
            'status_rec':    '● Запись',
            'status_pause':  '⏸ Пауза',
            'status_saved':  '✓ Сохранено!',
            'status_err':    '✗ Ошибка',
            'no_mic':        'Микрофон не найден',
            'parent_folder': 'MAMONOV',
            'child_folder':  'MAMONOV Запись экрана',
            'file_prefix':   'Запись_',
            'err_ffmpeg':    'ffmpeg не найден! Установите ffmpeg и добавьте в PATH.',
            'err_rec':       'Ошибка записи',
        }
    else:
        LANG = {
            'title':         'MAMONOV Screen Recorder',
            'btn_start':     '▶  Start Recording',
            'btn_stop':      '⏹  Stop',
            'btn_save':      '💾  Save',
            'status_ready':  '',
            'status_rec':    '● Recording',
            'status_pause':  '⏸ Paused',
            'status_saved':  '✓ Saved!',
            'status_err':    '✗ Error',
            'no_mic':        'No microphone found',
            'parent_folder': 'MAMONOV',
            'child_folder':  'MAMONOV Screen Recorder',
            'file_prefix':   'Recording_',
            'err_ffmpeg':    'ffmpeg not found! Install ffmpeg and add to PATH.',
            'err_rec':       'Recording error',
        }


# ============================================================
# Утилиты
# ============================================================

CREATE_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def _find_ffmpeg():
    """Проверяет, доступен ли ffmpeg."""
    try:
        r = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True, text=True, timeout=5,
            creationflags=CREATE_NO_WINDOW
        )
        return r.returncode == 0
    except Exception:
        return False


def _detect_dshow_audio():
    """Возвращает список имён аудиоустройств DirectShow."""
    devices = []
    try:
        r = subprocess.run(
            ['ffmpeg', '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy'],
            capture_output=True, text=True, timeout=10,
            creationflags=CREATE_NO_WINDOW
        )
        output = r.stderr + r.stdout
        in_audio = False
        for line in output.splitlines():
            if '[dshow' in line:
                if 'DirectShow audio devices' in line:
                    in_audio = True
                elif 'DirectShow video' in line:
                    in_audio = False
                elif in_audio and '"' in line:
                    m = re.search(r'"([^"]+)"', line)
                    if m:
                        devices.append(m.group(1))
    except Exception:
        pass
    return devices


def _best_encoder():
    """Выбирает самый эффективный H.264 кодировщик."""
    order = ['h264_nvenc', 'h264_amf', 'h264_qsv', 'libx264']
    try:
        r = subprocess.run(
            ['ffmpeg', '-hide_banner', '-encoders'],
            capture_output=True, text=True, timeout=5,
            creationflags=CREATE_NO_WINDOW
        )
        body = r.stdout
        for enc in order:
            if enc in body:
                return enc
    except Exception:
        pass
    return 'libx264'


def _encoder_params(encoder):
    """Параметры ffmpeg для выбранного кодировщика."""
    if encoder == 'h264_nvenc':
        return ['-c:v', 'h264_nvenc', '-preset', 'p4',
                '-tune', 'ull', '-rc', 'vbr', '-cq', '23']
    elif encoder == 'h264_amf':
        return ['-c:v', 'h264_amf', '-quality', 'balanced',
                '-rc', 'vbr_peak', '-qp_i', '22', '-qp_p', '22']
    elif encoder == 'h264_qsv':
        return ['-c:v', 'h264_qsv', '-preset', 'medium',
                '-global_quality', '23']
    else:
        return ['-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23']


def _desktop_path():
    """Путь к рабочему столу текущего пользователя."""
    try:
        buf = ctypes.create_unicode_buffer(512)
        ctypes.windll.shell32.SHGetFolderPathW(0, 0x0010, 0, 0, buf)
        return buf.value
    except Exception:
        return os.path.join(os.path.expanduser('~'), 'Desktop')


def _fmt_time(seconds):
    """Форматирует секунды в HH:MM:SS или MM:SS."""
    s = int(seconds)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f'{h:02d}:{m:02d}:{s:02d}'
    return f'{m:02d}:{s:02d}'


# ============================================================
# Фирменная иконка папки (тёмный фон, синий круг, белая М)
# ============================================================

def _create_brand_icon(path):
    """Создаёт folder.ico в стиле бренда MAMONOV."""
    try:
        from PIL import Image, ImageDraw, ImageFont

        size = 256
        img = Image.new('RGBA', (size, size), (28, 28, 38, 255))
        draw = ImageDraw.Draw(img)

        # Синий круг
        margin = 28
        draw.ellipse(
            [margin, margin, size - margin, size - margin],
            fill=(25, 118, 210, 255)
        )

        # Белая «М»
        font = None
        for name in ('arialbd.ttf', 'arial.ttf', 'Arial Bold.ttf',
                     'C:/Windows/Fonts/arialbd.ttf',
                     'C:/Windows/Fonts/arial.ttf'):
            try:
                font = ImageFont.truetype(name, 148)
                break
            except Exception:
                continue
        if font is None:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), 'M', font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (size - tw) // 2
        y = (size - th) // 2 - bbox[1]
        draw.text((x, y), 'M', fill='white', font=font)

        sizes = [(16, 16), (32, 32), (48, 48), (128, 128), (256, 256)]
        img.save(path, format='ICO', sizes=sizes)
        return True
    except ImportError:
        return False


def _set_folder_icon(folder):
    """Устанавливает кастомную иконку на папку Windows."""
    icon_path = os.path.join(folder, 'folder.ico')
    if not os.path.exists(icon_path):
        if not _create_brand_icon(icon_path):
            return

    ini_path = os.path.join(folder, 'desktop.ini')
    with open(ini_path, 'w', encoding='utf-16') as f:
        f.write('[.ShellClassInfo]\n')
        f.write(f'IconResource={icon_path},0\n')

    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.SetFileAttributesW(ini_path, 0x02)   # HIDDEN
        kernel32.SetFileAttributesW(icon_path, 0x02)   # HIDDEN
        kernel32.SetFileAttributesW(folder, 0x04)     # SYSTEM
    except Exception:
        pass


# ============================================================
# Основной класс рекордера
# ============================================================

class ScreenRecorder:
    def __init__(self):
        _load_lang()

        # Состояние
        self._recording = False
        self._process = None
        self._segments = []
        self._seg_idx = 0
        self._temp_dir = tempfile.mkdtemp(prefix='mamonov_rec_')

        # Таймер записи
        self._total_time = 0.0
        self._seg_start = 0.0

        # Оборудование
        self._ffmpeg_ok = _find_ffmpeg()
        self._mic_name = None
        mics = _detect_dshow_audio()
        if mics:
            self._mic_name = mics[0]
        self._encoder = _best_encoder()

        # GUI
        self._root = tk.Tk()
        self._root.title(LANG['title'])
        self._root.attributes('-topmost', True)
        self._root.resizable(False, False)
        self._root.protocol('WM_DELETE_WINDOW', self._on_close)
        self._root.configure(bg='#1c1c2a')

        frm = tk.Frame(self._root, padx=12, pady=10, bg='#1c1c2a')
        frm.pack()

        btn_style = dict(
            font=('Segoe UI', 11, 'bold'),
            bg='#1976D2', fg='white',
            activebackground='#1565C0', activeforeground='white',
            relief='flat', cursor='hand2',
            width=26, height=2,
        )

        self._btn_rec = tk.Button(frm, text=LANG['btn_start'],
                                   command=self._toggle, **btn_style)
        self._btn_rec.pack(pady=(0, 6))

        self._btn_save = tk.Button(frm, text=LANG['btn_save'],
                                    command=self._save,
                                    state=tk.DISABLED, **btn_style)
        self._btn_save.pack(pady=(0, 6))

        self._lbl_status = tk.Label(
            frm, text=LANG['status_ready'],
            bg='#1c1c2a', fg='#aaaaaa',
            font=('Segoe UI', 10)
        )
        self._lbl_status.pack(fill='x')

        if self._mic_name is None:
            tk.Label(frm, text=LANG['no_mic'],
                     bg='#1c1c2a', fg='#666666',
                     font=('Segoe UI', 9)).pack()

        if not self._ffmpeg_ok:
            self._btn_rec.config(state=tk.DISABLED)
            self._lbl_status.config(text=LANG['err_ffmpeg'], fg='red')

        # Скрыть окно из захвата экрана (Windows 10 2004+)
        self._root.update_idletasks()
        try:
            hwnd = self._root.winfo_id()
            ctypes.windll.user32.SetWindowDisplayAffinity(
                hwnd, 0x11  # WDA_EXCLUDEFROMCAPTURE
            )
        except Exception:
            pass

    # ---- управление записью ----

    def _toggle(self):
        if self._recording:
            self._stop()
        else:
            self._start()

    def _start(self):
        self._seg_idx += 1
        seg_path = os.path.join(self._temp_dir, f'seg_{self._seg_idx:04d}.mp4')

        cmd = ['ffmpeg', '-hide_banner', '-y']

        # Видео: весь экран (gdigrab)
        cmd += ['-f', 'gdigrab', '-framerate', '30', '-i', 'desktop']

        # Аудио: микрофон (если есть)
        if self._mic_name:
            cmd += ['-f', 'dshow', '-i', f'audio={self._mic_name}']

        # Кодировщик видео
        cmd += _encoder_params(self._encoder)

        # Кодировщик аудио
        if self._mic_name:
            cmd += ['-c:a', 'aac', '-b:a', '128k']
        else:
            cmd += ['-an']

        cmd += ['-movflags', '+faststart', seg_path]

        try:
            self._process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW
            )
        except Exception:
            self._lbl_status.config(text=LANG['err_rec'], fg='red')
            return

        self._segments.append(seg_path)
        self._recording = True
        self._seg_start = time.time()

        self._btn_rec.config(text=LANG['btn_stop'], bg='#D32F2F',
                              activebackground='#C62828')
        self._btn_save.config(state=tk.DISABLED)
        self._tick_timer()

    def _stop(self):
        if self._process:
            try:
                self._process.stdin.write(b'q')
                self._process.stdin.flush()
                self._process.wait(timeout=5)
            except Exception:
                self._process.terminate()
                try:
                    self._process.wait(timeout=3)
                except Exception:
                    pass
            self._process = None

        # Накопить время
        if self._seg_start:
            self._total_time += time.time() - self._seg_start
            self._seg_start = 0

        self._recording = False
        elapsed = _fmt_time(self._total_time)
        self._btn_rec.config(text=LANG['btn_start'], bg='#1976D2',
                              activebackground='#1565C0')
        self._btn_save.config(state=tk.NORMAL)
        self._lbl_status.config(
            text=f'{LANG["status_pause"]}  {elapsed}', fg='#FFA000'
        )

    # ---- таймер записи ----

    def _tick_timer(self):
        if not self._recording:
            return
        cur = self._total_time + (time.time() - self._seg_start)
        elapsed = _fmt_time(cur)
        self._lbl_status.config(
            text=f'{LANG["status_rec"]}  {elapsed}', fg='#EF5350'
        )
        self._root.after(500, self._tick_timer)

    # ---- сохранение ----

    def _save(self):
        if self._recording:
            self._stop()

        if not self._segments:
            return

        # Целевая папка
        desktop = _desktop_path()
        parent = os.path.join(desktop, LANG['parent_folder'])
        target = os.path.join(parent, LANG['child_folder'])
        os.makedirs(target, exist_ok=True)
        _set_folder_icon(parent)
        _set_folder_icon(target)

        # Имя файла
        ts = time.strftime('%Y-%m-%d_%H-%M-%S')
        output = os.path.join(target, f'{LANG["file_prefix"]}{ts}.mp4')

        if len(self._segments) == 1:
            # Один сегмент — просто копируем
            shutil.copy2(self._segments[0], output)
        else:
            # Несколько сегментов — склеиваем через ffmpeg
            concat_path = os.path.join(self._temp_dir, 'concat.txt')
            with open(concat_path, 'w', encoding='utf-8') as f:
                for s in self._segments:
                    safe = s.replace('\\', '/').replace("'", "'\\\\''")
                    f.write(f"file '{safe}'\n")

            cmd = [
                'ffmpeg', '-hide_banner', '-y',
                '-f', 'concat', '-safe', '0', '-i', concat_path,
                '-c', 'copy', '-movflags', '+faststart', output
            ]
            try:
                subprocess.run(
                    cmd, creationflags=CREATE_NO_WINDOW, timeout=120
                )
            except Exception:
                shutil.copy2(self._segments[0], output)

        # Очистка
        self._cleanup()

        # Сброс состояния
        self._segments = []
        self._seg_idx = 0
        self._total_time = 0.0
        self._btn_save.config(state=tk.DISABLED)
        self._lbl_status.config(text=LANG['status_saved'], fg='#4CAF50')

    # ---- очистка временных файлов ----

    def _cleanup(self):
        for s in self._segments:
            try:
                os.remove(s)
            except Exception:
                pass
        try:
            shutil.rmtree(self._temp_dir, ignore_errors=True)
        except Exception:
            pass
        self._temp_dir = tempfile.mkdtemp(prefix='mamonov_rec_')

    # ---- закрытие программы ----

    def _on_close(self):
        if self._recording:
            self._stop()
        self._cleanup()
        self._root.destroy()

    # ---- запуск ----

    def run(self):
        self._root.mainloop()


# ============================================================
if __name__ == '__main__':
    app = ScreenRecorder()
    app.run()
