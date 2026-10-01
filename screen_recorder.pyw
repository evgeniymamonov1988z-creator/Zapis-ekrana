'''Screen Recorder — запись экрана + микрофон.
Всё включено: ffmpeg.exe в bin/, библиотеки в lib/.
Интернет для запуска НЕ нужен.
Файлы сохраняются на Рабочий стол -> Mamonov/Mamonov video/

Логика:
  Запись -> Пауза -> Продолжить -> Пауза -> ... -> Сохранить
  Кнопка "Запись" переключает: старт / пауза / продолжить
  Кнопка "Сохранить" — финал: стоп, склейка, файл готов

Язык: русский / английский (по языку системы)
'''

import os
import sys
import re
import subprocess
import time
import shutil
import traceback
import tempfile
import locale
import datetime
# DemoBlock встроен прямо в этот файл (см. ниже)

# --- Определяем язык интерфейса ---
def _detect_lang():
    """Определить язык системы: 'ru' или 'en'."""
    try:
        lang = locale.getdefaultlocale()[0]
        if lang and lang.lower().startswith('ru'):
            return 'ru'
    except Exception:
        pass
    try:
        import ctypes
        windll = ctypes.windll.kernel32
        lang_id = windll.GetUserDefaultUILanguage()
        # Russian: 0x0419, Ukrainian: 0x0422, Belarusian: 0x0423
        if lang_id in (0x0419, 0x0422, 0x0423):
            return 'ru'
    except Exception:
        pass
    return 'en'

LANG = _detect_lang()

# --- Словарь строк ---
T = {
    'ru': {
        'title': 'Запись экрана',
        'btn_rec': '\u25cf  Запись',
        'btn_pause': '\u25a0  Пауза',
        'btn_resume': '\u25b6  Продолжить',
        'btn_save': '\u2b07  Сохранить',
        'btn_log': '\U0001f4cb  Лог',
        'btn_hide_log': '\U0001f4cb  Скрыть лог',
        'btn_copied': '\U0001f4cb  Скопировано!',
        'status_ready_mic': 'Готово | Микрофон: {}{}',
        'status_ready_no_mic': 'Готово | Микрофон не найден',
        'status_no_ffmpeg': 'ffmpeg не найден',
        'status_recording': 'Запись...',
        'status_paused': 'Пауза',
        'status_saved': 'Сохранено: {}',
        'status_no_file': 'Файл не найден! Сначала запиши.',
        'status_copy': 'Скопировано!',
        'status_start_error': 'Ошибка запуска: {}',
        'status_ffmpeg_crash': 'ffmpeg упал: {}',
        'label_audio': 'Звук',
        'label_audio_off': 'Звук \u2717',
        'label_video': 'Видео',
        'log_mic': 'микрофон: {}',
        'log_mic_not_found': 'микрофон не найден',
        # Окно ошибки
        'error_title': 'Запись экрана — Ошибка',
        'error_label': 'Ошибка запуска:',
        'error_copy': '\U0001f4cb Копировать',
        'error_copied': 'Скопировано!',
        'error_ok': 'OK',
        'error_main': 'Ошибка при запуска:\n\n{}',
        'error_tkinter': 'Не удалось загрузить tkinter:\n{}\n\nУстановите Python с python.org (не Microsoft Store)',
        'error_copy_btn': '\U0001f4cb Копировать',
        # Демо
        'demo_title': 'Запись экрана — ДЕМО',
        'demo_days_3': 'ДЕМО — 3 дня',
        'demo_days_2': 'ДЕМО — 2 дня',
        'demo_days_1': 'ДЕМО — 1 день',
        'demo_expired': 'Демо кончилось',
        'demo_buy': 'Разблокировать за 299 ₽',
        'demo_buy_link': 'https://evgeniymamonov.com/buy.html',
        'copy_label': '№ копии: {}',
        # Первый запуск — скачивание ffmpeg
        'dl_title': 'Первый запуск — установка',
        'dl_wait': 'Идёт первичная настройка, подождите…',
        'dl_ffmpeg': 'Скачиваю ffmpeg (~90 МБ)…',
        'dl_extract': 'Распаковываю ffmpeg…',
        'dl_done': 'Готово!',
        'dl_error': 'Не удалось скачать ffmpeg (проверьте интернет)',
    },
    'en': {
        'title': 'Screen Recorder',
        'btn_rec': '\u25cf  Record',
        'btn_pause': '\u25a0  Pause',
        'btn_resume': '\u25b6  Resume',
        'btn_save': '\u2b07  Save',
        'btn_log': '\U0001f4cb  Log',
        'btn_hide_log': '\U0001f4cb  Hide log',
        'btn_copied': '\U0001f4cb  Copied!',
        'status_ready_mic': 'Ready | Mic: {}{}',
        'status_ready_no_mic': 'Ready | Mic not found',
        'status_no_ffmpeg': 'ffmpeg not found',
        'status_recording': 'Recording...',
        'status_paused': 'Paused',
        'status_saved': 'Saved: {}',
        'status_no_file': 'File not found! Record first.',
        'status_copy': 'Copied!',
        'status_start_error': 'Start error: {}',
        'status_ffmpeg_crash': 'ffmpeg crashed: {}',
        'label_audio': 'Audio',
        'label_audio_off': 'Audio \u2717',
        'label_video': 'Video',
        'log_mic': 'mic: {}',
        'log_mic_not_found': 'mic not found',
        'error_title': 'Screen Recorder — Error',
        'error_label': 'Startup error:',
        'error_copy': '\U0001f4cb Copy',
        'error_copied': 'Copied!',
        'error_ok': 'OK',
        'error_main': 'Startup error:\n\n{}',
        'error_tkinter': 'Failed to load tkinter:\n{}\n\nInstall Python from python.org (not Microsoft Store)',
        'error_copy_btn': '\U0001f4cb Copy',
        # Demo
        'demo_title': 'Screen Recorder — DEMO',
        'demo_days_3': 'DEMO — 3 days',
        'demo_days_2': 'DEMO — 2 days',
        'demo_days_1': 'DEMO — 1 day',
        'demo_expired': 'Demo expired',
        'demo_buy': 'Unlock for $9.99',
        'demo_buy_link': 'https://evgeniymamonov.com/en/buy.html',
        'copy_label': 'Copy #: {}',
        # First run — ffmpeg download
        'dl_title': 'First run — setup',
        'dl_wait': 'First-time setup, please wait…',
        'dl_ffmpeg': 'Downloading ffmpeg (~90 MB)…',
        'dl_extract': 'Extracting ffmpeg…',
        'dl_done': 'Done!',
        'dl_error': 'Failed to download ffmpeg (check your internet)',
    },
}

def t(key, *args):
    """Получить строку на текущем языке с подстановкой аргументов."""
    s = T.get(LANG, T['en']).get(key, T['en'].get(key, key))
    if args:
        try:
            s = s.format(*args)
        except Exception:
            pass
    return s


# --- Только одна копия программы ---
import ctypes

# --- Скрытая папка данных (логи и служебные файлы) — НЕ на рабочем столе ---
_DATA_BASE = os.environ.get('LOCALAPPDATA') or os.environ.get('APPDATA') or os.path.expanduser('~')
DATA_DIR = os.path.join(_DATA_BASE, 'MAMONOV')
try:
    os.makedirs(DATA_DIR, exist_ok=True)
except Exception:
    DATA_DIR = os.path.dirname(os.path.abspath(
        sys.executable if getattr(sys, 'frozen', False) else __file__))

# --- Только одна копия программы (надёжно, через именованный mutex) ---
# Старый способ (PID-файл) давал ложные срабатывания: Windows переиспользует
# номера процессов, поэтому программа могла решить, что копия уже запущена,
# и молча закрыться. У mutex такого недостатка нет.
_ALREADY_RUNNING = False
try:
    _mutex = ctypes.windll.kernel32.CreateMutexW(
        None, False, "MAMONOV_ScreenRecorder_SingleInstance")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        _ALREADY_RUNNING = True
except Exception:
    _mutex = None

if _ALREADY_RUNNING:
    _hwnd = ctypes.windll.user32.FindWindowW(None, t('title'))
    if _hwnd:
        ctypes.windll.user32.ShowWindow(_hwnd, 9)  # SW_RESTORE
        ctypes.windll.user32.SetForegroundWindow(_hwnd)
    sys.exit(0)


# --- Папка программы ---
APP_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))

# --- Добавляем lib/ в путь для библиотек ---
LIB_DIR = os.path.join(APP_DIR, "lib")
if os.path.isdir(LIB_DIR):
    sys.path.insert(0, LIB_DIR)

# --- Ловим ошибки до создания окна ---
ERROR_LOG = os.path.join(DATA_DIR, "error.log")


def _show_error(msg):
    """Показать ошибку любым способом: окно или файл."""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.title(t('error_title'))
        root.geometry("600x350")
        root.configure(bg="#2b2b2b")
        tk.Label(root, text=t('error_label'), font=("Segoe UI", 14, "bold"),
                 fg="#cc3333", bg="#2b2b2b").pack(pady=(15, 5))
        txt = tk.Text(root, font=("Consolas", 10), bg="#1a1a1a", fg="#ff6666",
                      wrap="word", height=12, width=65)
        txt.pack(padx=15, pady=5)
        txt.insert("1.0", msg)

        def _copy_error():
            try:
                root.clipboard_clear()
                root.clipboard_append(msg)
                btn_copy.config(text=t('error_copied'))
                root.after(1500, lambda: btn_copy.config(text=t('error_copy')))
            except Exception:
                pass

        txt.config(state="disabled")
        frm_btn = tk.Frame(root, bg="#2b2b2b")
        frm_btn.pack(pady=5)
        btn_copy = tk.Button(frm_btn, text=t('error_copy'), command=_copy_error,
                             bg="#3c3c3c", fg="#ffffff", relief="flat", width=14,
                             font=("Segoe UI", 10))
        btn_copy.pack(side="left", padx=5)
        tk.Button(frm_btn, text=t('error_ok'), command=root.destroy,
                  bg="#3c3c3c", fg="#ffffff", relief="flat", width=10,
                  font=("Segoe UI", 10)).pack(side="left", padx=5)
        root.mainloop()
    except Exception:
        pass
    with open(ERROR_LOG, "w", encoding="utf-8") as f:
        f.write(msg + "\n")


try:
    import tkinter as tk
    from tkinter import scrolledtext
except ImportError as e:
    _show_error(t('error_tkinter', e))
    sys.exit(1)


# ============================================================
# ДЕМО-БЛОК v2.2 — встроен прямо в .exe
# Общая буквенно-цифровая схема:
#   буквы = вид программы (AE = Screen Recorder),
#   цифры = номер копии.
# Полный номер копии (например AE7) сервер вписывает при
# скачивании маркером MAMONOV_ID: в конец .exe.
# ============================================================

PRODUCT_CODE = "AE"            # буквенный код Screen Recorder в общей схеме
_ID_MARKER = b'MAMONOV_ID:'
_COPY_NUMBER = "AE1"           # запасной номер для запуска из исходников
_DEMO_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'MAMONOV')
_SITE = "https://evgeniymamonov.com"
_SERVER_URL = _SITE + "/api/ping.php"
_COPY_RE = re.compile(r'^[A-Z]{2}\d+$')

# Одна сборка для всех: номер копии вшивается при скачивании с сайта,
# полную версию открывает оплата (на сайте — Prodamus, в магазине —
# Digiseller сам вписывает оплаченный номер). Отдельной «магазинной»
# версии больше нет.


def _machine_id():
    """Устойчивый «отпечаток» этого компьютера (16 hex-символов).

    На Windows — MachineGuid из реестра (самый стабильный ид системы) +
    имя компьютера. Запасной вариант — MAC-адрес. Без личных данных.
    Та же схема, что и у «Кадрика» — одна копия = один компьютер.
    """
    import hashlib
    import platform
    parts = []
    if os.name == 'nt':
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r'SOFTWARE\Microsoft\Cryptography', 0,
                winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
            try:
                guid, _ = winreg.QueryValueEx(key, 'MachineGuid')
            finally:
                winreg.CloseKey(key)
            if guid:
                parts.append(str(guid))
        except Exception:
            pass
    try:
        node = platform.node()
        if node:
            parts.append(node)
    except Exception:
        pass
    if not parts:
        try:
            import uuid
            parts.append(str(uuid.getnode()))
        except Exception:
            pass
    raw = '|'.join(p for p in parts if p) or 'unknown'
    return hashlib.sha256(raw.encode('utf-8', 'ignore')).hexdigest()[:16].upper()


def _read_copy_number():
    """«Свежий» номер копии из самого файла.
    Номер больше НЕ пишется в имя файла, поэтому:
    1) Основной способ — метка MAMONOV_ID: в конце .exe (вписывает сайт).
    2) Запасной — номер в имени файла (старые скачанные копии).
    3) Запуск из исходников — _COPY_NUMBER.
    Постоянный номер компьютера и восстановление с сервера — в DemoBlock."""
    try:
        exe_path = sys.executable
        if not exe_path or exe_path.endswith(('python.exe', 'pythonw.exe', 'python3.exe', 'python3w.exe')):
            return _COPY_NUMBER

        # 1) Метка в хвосте .exe — основной способ.
        try:
            with open(exe_path, 'rb') as f:
                f.seek(-256, 2)
                tail = f.read(256)
            idx = tail.find(_ID_MARKER)
            if idx != -1:
                start = idx + len(_ID_MARKER)
                raw = tail[start:start + 16].decode('ascii', errors='ignore')
                m = re.match(r'[A-Za-z]{2}\d{1,6}', raw)
                if m:
                    return m.group(0).upper()
        except Exception:
            pass

        # 2) Номер в имени файла — запасной (старые копии с номером в имени).
        stem = os.path.splitext(os.path.basename(exe_path))[0]
        m = re.search(r'([A-Za-z]{2}\d{1,6})$', stem)
        if m:
            return m.group(1).upper()

        return _COPY_NUMBER
    except Exception:
        return _COPY_NUMBER


COPY_NUMBER = _read_copy_number()


class DemoBlock:
    """Демо-блок в общей буквенно-цифровой схеме.

    code       — буквенный код вида программы (AE = Screen Recorder)
    copy       — полный номер копии (AE7); читается из .exe
    demo_days  — сколько дней длится демо
    t          — функция перевода
    """

    def __init__(self, code=PRODUCT_CODE, copy=None, demo_days=3, t=None):
        self.code = code
        self.demo_days = demo_days
        self._t = t
        self._bar_frame = None

        self._demo_file = os.path.join(_DEMO_DIR, f'.demo_date_{self.code}')
        self._license_file = os.path.join(_DEMO_DIR, f'.demo_licensed_{self.code}')
        self._copy_file = os.path.join(_DEMO_DIR, f'.copy_{self.code}')
        # Файл со статусом — в папке Mamonov video\bin рядом с рабочими файлами.
        self._status_file = os.path.join(_bin_dir(), f'status_{self.code}.txt')

        # Постоянный номер копии на этот компьютер (с восстановлением
        # по отпечатку, если локальный файл с номером потерялся).
        self.copy = copy or self._resolve_copy()

        self.status, self.days_left = self._check()
        self.expired = (self.status == 'expired')
        self.licensed = (self.status == 'licensed')

        # Записать понятный файл со статусом на компьютер.
        self._write_status()

        self.ping()

    # ---- Постоянный номер копии на компьютер ----

    def _load_saved_copy(self):
        """Сохранённый постоянный номер этого компьютера (или '')."""
        try:
            with open(self._copy_file, 'r', encoding='utf-8') as f:
                val = (f.read().strip() or '').upper()
            return val if _COPY_RE.match(val) else ''
        except Exception:
            return ''

    def _save_copy(self, val):
        """Закрепить номер за компьютером (скрытый файл)."""
        try:
            os.makedirs(_DEMO_DIR, exist_ok=True)
            with open(self._copy_file, 'w', encoding='utf-8') as f:
                f.write(val)
            if os.name == 'nt':
                try:
                    ctypes.windll.kernel32.SetFileAttributesW(self._copy_file, 2)
                except Exception:
                    pass
        except Exception:
            pass

    def _recover_copy(self):
        """Спросить сервер, какой номер закреплён за этим компьютером.
        Возвращает (copy, reached): copy — номер или '', reached — дошли ли
        до сервера."""
        try:
            import urllib.request
            import urllib.parse
            import json
            params = urllib.parse.urlencode({'machine': _machine_id()})
            url = f'{_SITE}/api/recover.php?{params}'
            req = urllib.request.Request(url, method='GET')
            req.add_header('User-Agent', 'MAMONOV-DemoBlock/2.2')
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read().decode('utf-8', 'ignore') or '{}')
            copy = (data.get('copy', '') or '').upper()
            return (copy if _COPY_RE.match(copy) else ''), True
        except Exception:
            return '', False

    def _resolve_copy(self):
        """Постоянный номер копии для этого компьютера.

        Порядок: сохранённый локально → восстановленный с сервера по отпечатку
        → «свежий» из файла. Новый номер закрепляем только на действительно
        новом компьютере (когда сервер ответил, что номера ещё нет).
        """
        saved = self._load_saved_copy()
        if _COPY_RE.match(saved):
            return saved
        rec, reached = self._recover_copy()
        if _COPY_RE.match(rec or ''):
            self._save_copy(rec)
            return rec
        fresh = (COPY_NUMBER or '').upper()
        if _COPY_RE.match(fresh):
            # Закрепляем, только если сервер точно ответил (правда новый
            # компьютер). Без связи — вернём номер на сеанс, но не закрепляем:
            # как появится интернет, восстановим настоящий номер.
            if reached:
                self._save_copy(fresh)
            return fresh
        return _COPY_NUMBER

    def _check(self):
        # 1) Сначала смотрим сохранённый на компьютере статус (работает
        # без интернета). Если копия уже отмечена оплаченной —
        # остаёмся полной версией.
        if self._read_status() == 'licensed':
            return ('licensed', 0)

        if os.path.isfile(self._license_file):
            try:
                with open(self._license_file, 'r') as f:
                    data = f.read().strip()
                if data == 'ok':
                    return ('licensed', 0)
            except Exception:
                pass

        try:
            os.makedirs(_DEMO_DIR, exist_ok=True)
            if os.path.isfile(self._demo_file):
                with open(self._demo_file, 'r') as f:
                    first_run = f.read().strip()
                first_date = datetime.datetime.strptime(first_run, '%Y-%m-%d').date()
            else:
                today = datetime.date.today()
                with open(self._demo_file, 'w') as f:
                    f.write(today.strftime('%Y-%m-%d'))
                first_date = today

            days_passed = (datetime.date.today() - first_date).days
            days_left = self.demo_days - days_passed

            if days_left <= 0:
                return ('expired', 0)
            return ('ok', days_left)
        except Exception:
            return ('ok', self.demo_days)

    def mark_licensed(self):
        try:
            os.makedirs(_DEMO_DIR, exist_ok=True)
            with open(self._license_file, 'w') as f:
                f.write('ok')
            self.status = 'licensed'
            self.licensed = True
            self.expired = False
            self._write_status()
        except Exception:
            pass

    def _read_status(self):
        """Прочитать сохранённый статус с компьютера.
        Возвращает 'licensed' / 'demo' / 'expired' или '' (файла нет)."""
        try:
            import json
            with open(self._status_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return str(data.get('status', '') or '')
        except Exception:
            return ''

    def _write_status(self):
        """Сохранить статус копии в понятный файл на компьютере.
        Программа читает его при запуске (без интернета), а сервер
        периодически уточняет его, когда есть связь."""
        try:
            import json
            os.makedirs(os.path.dirname(self._status_file), exist_ok=True)
            if self.status == 'licensed':
                code, text = 'licensed', 'Оплачено (полная версия)'
            elif self.status == 'expired':
                code, text = 'expired', 'Демо кончилось — не оплачено'
            else:
                code, text = 'demo', f'Демо, осталось дней: {self.days_left}'
            data = {
                'product': self.code,
                'copy': self.copy,
                'status': code,
                'status_text': text,
                'days_left': self.days_left,
                'updated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            with open(self._status_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def ping(self):
        try:
            import urllib.request
            import urllib.parse
            params = urllib.parse.urlencode({
                'product': self.code,
                'instance': self.copy,
                'machine': _machine_id(),
                'status': 'demo' if self.status == 'ok' else self.status,
                'days': self.days_left,
            })
            url = f'{_SERVER_URL}?{params}'
            req = urllib.request.Request(url, method='GET')
            req.add_header('User-Agent', 'MAMONOV-DemoBlock/2.2')
            urllib.request.urlopen(req, timeout=3)
        except Exception:
            pass

    def check_server_license(self, callback=None):
        try:
            import urllib.request
            import urllib.parse
            import json
            params = urllib.parse.urlencode({
                'product': self.code,
                'instance': self.copy,
                'machine': _machine_id(),
            })
            url = f'{_SITE}/api/check.php?{params}'
            req = urllib.request.Request(url, method='GET')
            req.add_header('User-Agent', 'MAMONOV-DemoBlock/2.2')
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read().decode('utf-8'))
            # Сервер может прислать закреплённый/оплаченный номер копии —
            # принимаем его и делаем своим («переименование» копии).
            srv_copy = (data.get('copy', '') or '').upper()
            if _COPY_RE.match(srv_copy) and srv_copy != self.copy:
                self.copy = srv_copy
                self._save_copy(srv_copy)
                self._write_status()
            if data.get('licensed'):
                self.mark_licensed()
                if callback:
                    callback()
        except Exception:
            pass

    def bar_text(self):
        t = self._t or (lambda k, *a: k)
        if self.licensed:
            return ''
        if self.days_left >= 3:
            return t('demo_days_3')
        elif self.days_left == 2:
            return t('demo_days_2')
        elif self.days_left == 1:
            return t('demo_days_1')
        else:
            return t('demo_expired')

    def buy_url(self):
        t = self._t or (lambda k, *a: k)
        base = t('demo_buy_link')
        return f'{base}?product={self.code}&instance={self.copy}'

    def open_buy_link(self, event=None):
        import webbrowser
        webbrowser.open(self.buy_url())

    def build_bar(self, parent, t=None):
        if t:
            self._t = t
        if self.licensed:
            return (None, None)

        frm = tk.Frame(parent, bg="#2b2b2b")
        frm.pack(fill="x", padx=10, pady=(5, 0))
        self._bar_frame = frm

        lbl_demo = tk.Label(frm, text=self.bar_text(),
                            font=("Segoe UI", 9, "bold"),
                            fg="#DAA520", bg="#2b2b2b")
        lbl_demo.pack(side="left")

        lbl_buy = None
        if self.expired:
            t_fn = self._t or (lambda k, *a: k)
            lbl_buy = tk.Label(frm, text=t_fn('demo_buy'),
                               font=("Segoe UI", 9, "bold"),
                               fg="#0099ee", bg="#2b2b2b", cursor="hand2")
            lbl_buy.pack(side="left", padx=(10, 0))
            lbl_buy.bind("<Button-1>", self.open_buy_link)

        return (lbl_demo, lbl_buy)

    def lock_buttons(self, *buttons):
        if self.expired:
            for btn in buttons:
                btn.config(state="disabled")
            return True
        else:
            for btn in buttons:
                btn.config(state="normal")
            return False


# ============================================================
# FFMPEG — ищем рядом (bin/), в кэше пользователя, потом в PATH.
# Если нигде нет — ensure_ffmpeg() скачает его из интернета.
# ============================================================

# Готовый статический билд (один ffmpeg.exe без внешних DLL)
_FFMPEG_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-win64-gpl.zip"


def _video_base():
    """Папка с записями: Рабочий стол / Mamonov / Mamonov video."""
    return os.path.join(os.path.expanduser("~"), "Desktop", "Mamonov", "Mamonov video")


def _bin_dir():
    """Папка с рабочими файлами (ffmpeg и т.п.):
    Mamonov / Mamonov video / bin."""
    return os.path.join(_video_base(), "bin")


def _ffmpeg_cache_path():
    """Путь к скачанному ffmpeg в рабочей папке программы."""
    return os.path.join(_bin_dir(), 'ffmpeg.exe')


def _ffmpeg_legacy_cache_path():
    """Старое место (%LOCALAPPDATA%\\MAMONOV\\bin) — чтобы уже
    скачанный раньше ffmpeg не качать заново."""
    base = os.environ.get('LOCALAPPDATA') or os.environ.get('APPDATA') or os.path.expanduser('~')
    return os.path.join(base, 'MAMONOV', 'bin', 'ffmpeg.exe')


def find_ffmpeg():
    # 1) рядом с программой
    local = os.path.join(APP_DIR, "bin", "ffmpeg.exe")
    if os.path.isfile(local):
        return local
    # 2) скачанный ранее в рабочую папку Mamonov video\\bin
    cached = _ffmpeg_cache_path()
    if os.path.isfile(cached):
        return cached
    # 2б) старое место кэша (старые установки) — переносим в новое
    legacy = _ffmpeg_legacy_cache_path()
    if os.path.isfile(legacy):
        try:
            os.makedirs(_bin_dir(), exist_ok=True)
            shutil.copy2(legacy, cached)
            if os.path.isfile(cached):
                return cached
        except Exception:
            pass
        return legacy
    # 3) в PATH
    in_path = shutil.which("ffmpeg")
    if in_path:
        return in_path
    return None


def ensure_ffmpeg(root):
    """Вернуть путь к ffmpeg. Если его нигде нет — скачать из
    интернета (единый .exe в рабочую папку
    Mamonov\\Mamonov video\\bin) с окном прогресса.
    При ошибке вернуть None."""
    found = find_ffmpeg()
    if found:
        return found

    import urllib.request
    import zipfile
    import tempfile

    dest = _ffmpeg_cache_path()
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
    except Exception:
        return None

    # Маленькое окно прогресса
    win = None
    lbl = None
    try:
        import tkinter as tk
        win = tk.Toplevel(root)
        win.title(t('dl_title'))
        win.configure(bg="#2b2b2b")
        win.attributes("-topmost", True)
        win.resizable(False, False)
        tk.Label(win, text=t('dl_wait'), bg="#2b2b2b", fg="#ffffff",
                 font=("Segoe UI", 10)).pack(padx=20, pady=(16, 4))
        lbl = tk.Label(win, text=t('dl_ffmpeg'), bg="#2b2b2b", fg="#4a9eff",
                       font=("Segoe UI", 9))
        lbl.pack(padx=20, pady=(0, 16))
        win.update_idletasks()
        w, h = 380, 100
        x = (win.winfo_screenwidth() - w) // 2
        y = (win.winfo_screenheight() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")
        win.update()
    except Exception:
        win = None
        lbl = None

    def _set(text):
        try:
            if lbl is not None:
                lbl.config(text=text)
            if win is not None:
                win.update()
        except Exception:
            pass

    tmp_zip = os.path.join(tempfile.gettempdir(), "mamonov_ffmpeg.zip")
    ok = False
    try:
        req = urllib.request.Request(_FFMPEG_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get('Content-Length', 0))
            downloaded = 0
            with open(tmp_zip, 'wb') as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = int(downloaded * 100 / total)
                        _set(t('dl_ffmpeg') + f"  {pct}%")
                    else:
                        mb = downloaded / (1024 * 1024)
                        _set(t('dl_ffmpeg') + f"  {mb:.0f} MB")

        _set(t('dl_extract'))
        with zipfile.ZipFile(tmp_zip, 'r') as zf:
            target = None
            for n in zf.namelist():
                nl = n.lower().replace('\\', '/')
                if nl.endswith('bin/ffmpeg.exe'):
                    target = n
                    break
            if target is None:
                for n in zf.namelist():
                    if n.lower().endswith('ffmpeg.exe'):
                        target = n
                        break
            if target is not None:
                with zf.open(target) as src, open(dest, 'wb') as out:
                    shutil.copyfileobj(src, out)
                ok = os.path.isfile(dest)
    except Exception:
        ok = False
    finally:
        try:
            if os.path.isfile(tmp_zip):
                os.remove(tmp_zip)
        except Exception:
            pass

    _set(t('dl_done') if ok else t('dl_error'))
    try:
        if win is not None:
            win.destroy()
    except Exception:
        pass

    return dest if ok else None


# ============================================================
# МИКРОФОН — поиск через ffmpeg -list_devices
# ============================================================
def _list_mics_raw(ffmpeg_path):
    """Получить сырой вывод ffmpeg -list_devices через bat-файл."""
    if not ffmpeg_path:
        return None

    raw = b""

    try:
        tmp_dir = tempfile.mkdtemp(prefix="mic_detect_")
        raw_path = os.path.join(tmp_dir, "devices_raw.txt")
        bat_path = os.path.join(tmp_dir, "find_mic.bat")

        bat_line = f'"{ffmpeg_path}" -list_devices true -f dshow -i dummy 2>"{raw_path}"'
        with open(bat_path, "wb") as f:
            f.write(bat_line.encode("ascii") + b"\r\n")

        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0

        proc = subprocess.Popen(
            ["cmd", "/c", bat_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
            startupinfo=si
        )
        proc.wait(timeout=15)

        if os.path.isfile(raw_path):
            with open(raw_path, "rb") as f:
                raw = f.read()

        debug_path = os.path.join(DATA_DIR, "mic_debug_raw.txt")
        try:
            with open(debug_path, "wb") as f:
                f.write(raw)
        except Exception:
            pass

        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass
    except Exception:
        pass

    return raw if raw else None


def _parse_mics_from_raw(raw):
    """Распарсить сырой вывод ffmpeg -list_devices.
    Возвращаем список словарей: [{"display": str, "alt": str|None}, ...]
    """
    mics = []
    if not raw:
        return mics

    # Способ 1: ищем @device_ с wave_
    pos = 0
    seen_alts = set()
    while True:
        dev_pos = raw.find(b"@device_", pos)
        if dev_pos < 0:
            break
        end = dev_pos
        while end < len(raw) and end - dev_pos < 250 and raw[end:end+1] not in (b'"', b'\n', b'\r'):
            end += 1
        alt = raw[dev_pos:end].decode("ascii", errors="replace")

        if "wave_" in alt and alt not in seen_alts:
            seen_alts.add(alt)
            search_back = raw[max(0, dev_pos - 400):dev_pos]
            display = None
            for enc in ("utf-8", "cp1251", "cp866", "latin-1"):
                try:
                    decoded = search_back.decode(enc)
                    parts = decoded.split('"')
                    for i in range(len(parts) - 2, -1, -1):
                        if len(parts) > i + 1 and parts[i + 1].strip() and "Alternative" not in parts[i + 1]:
                            display = parts[i + 1].strip()
                            break
                    if display:
                        break
                except Exception:
                    continue
            mics.append({"display": display or "Mic", "alt": alt})

        pos = end

    # Способ 2: ищем (audio)
    if not mics:
        pos = 0
        seen_displays = set()
        while True:
            audio_pos = raw.find(b"(audio)", pos)
            if audio_pos < 0:
                break
            after_audio = audio_pos + len(b"(audio)")

            next_audio = raw.find(b"(audio)", after_audio)
            search_limit = next_audio if next_audio >= 0 else len(raw)
            alt_name = None
            device_pos = raw.find(b"@device_", after_audio, search_limit)
            if device_pos >= 0:
                end = device_pos
                while end < len(raw) and end - device_pos < 250 and raw[end:end+1] not in (b'"', b'\n', b'\r'):
                    end += 1
                alt_name = raw[device_pos:end].decode("ascii", errors="replace")

            line_start = raw.rfind(b'\n', 0, audio_pos)
            line_start = line_start + 1 if line_start >= 0 else 0
            line_bytes = raw[line_start:audio_pos + len(b"(audio)")]

            display_name = None
            for enc in ("utf-8", "cp866", "cp1251", "latin-1"):
                try:
                    decoded = line_bytes.decode(enc)
                    parts = decoded.split('"')
                    if len(parts) >= 2 and parts[1].strip():
                        display_name = parts[1].strip()
                        break
                except Exception:
                    continue

            key = display_name or ""
            if key not in seen_displays:
                seen_displays.add(key)
                mics.append({"display": display_name or "Mic", "alt": alt_name})

            pos = after_audio

    return mics


def pick_mic(ffmpeg_path):
    """Найти микрофон автоматически."""
    if not ffmpeg_path:
        return None

    raw = _list_mics_raw(ffmpeg_path)

    # Сохраняем hex-дамп для отладки
    if raw:
        hex_path = os.path.join(DATA_DIR, "mic_debug_hex.txt")
        try:
            with open(hex_path, "w", encoding="utf-8") as f:
                f.write(f"Raw bytes: {len(raw)}\n\n")
                for i in range(0, min(len(raw), 1000), 16):
                    chunk = raw[i:i+16]
                    hex_part = " ".join(f"{b:02x}" for b in chunk)
                    ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
                    f.write(f"{i:04x}  {hex_part:<48}  {ascii_part}\n")
                if b"@device_" in raw:
                    f.write(f"\n>>> @device_ found in bytes! <<<\n")
                else:
                    f.write(f"\n>>> @device_ NOT found in bytes <<<\n")
                    if b"(audio)" in raw:
                        f.write(">>> (audio) found in bytes <<<\n")
                    else:
                        f.write(">>> (audio) NOT found in bytes <<<\n")
        except Exception:
            pass

    # Парсим список
    all_mics = _parse_mics_from_raw(raw)

    # Лог для отладки
    mic_debug_info = os.path.join(DATA_DIR, "mic_result.txt")
    with open(mic_debug_info, "w", encoding="utf-8") as f:
        f.write(f"all_mics found: {len(all_mics)}\n")
        for i, m in enumerate(all_mics):
            f.write(f"  [{i}] display={m.get('display')!r}, alt={m.get('alt')!r}\n")

        if not all_mics:
            f.write("No mics found at all.\n")
        else:
            with_alt = [m for m in all_mics if m.get("alt") and "wave_" in m["alt"]]
            if with_alt:
                m = with_alt[0]
                f.write(f"Selected (alt name): display={m.get('display')!r}, alt={m.get('alt')!r}\n")
            else:
                f.write("No alt name found. Using first mic (will use bat for encoding).\n")
                m = all_mics[0]
                f.write(f"Selected: display={m.get('display')!r}, alt={m.get('alt')!r}\n")

    if not all_mics:
        return None

    # Выбираем результат
    with_alt = [m for m in all_mics if m.get("alt") and "wave_" in m["alt"]]
    if with_alt:
        m = with_alt[0]
        m["tested"] = True
        return m

    m = all_mics[0]
    m["tested"] = False
    return m


# ============================================================
# ГЛАВНОЕ ОКНО
# ============================================================
class ScreenRecorderApp:
    COMPACT_H = 100
    FULL_H = 350
    WIN_W = 290

    def __init__(self, root):
        self.root = root
        self.root.title(t('title'))
        self.root.resizable(False, False)
        self.root.configure(bg="#2b2b2b")
        self.root.attributes("-topmost", True)

        # Демо-блок
        self.demo = DemoBlock(code="AE", demo_days=3, t=t)
        if self.demo.expired:
            self.root.title(t('demo_title'))

        self.ffmpeg = ensure_ffmpeg(self.root)
        self.process = None
        self.timer_id = None

        # Микрофон
        self.mic_info = pick_mic(self.ffmpeg)
        self.mic_name = None
        self.mic_display = None
        self.mic_needs_bat = False
        self.mic_tested = False
        if self.mic_info:
            self.mic_display = self.mic_info.get("display")
            self.mic_tested = self.mic_info.get("tested", False)
            if self.mic_info.get("alt"):
                self.mic_name = self.mic_info["alt"]
                self.mic_needs_bat = False
            elif self.mic_info.get("display"):
                self.mic_name = self.mic_info["display"]
                self.mic_needs_bat = True

        self.state = "idle"
        self.filepath = None
        self.segments = []
        self.segment_num = 0
        self.accumulated = 0
        self.seg_start = None
        self.current_segment = None
        self._temp_dir = None

        self.compact = False
        self._build_ui()
        self._check_deps()
        self._update_ui()

        # Спросить сервер, оплачена ли эта копия (и закрепить её за
        # компьютером при первом запуске). Делаем в фоне, чтобы не
        # тормозить открытие окна.
        self.root.after(1200, self._start_license_check)

        self.root.after(200, self._hide_from_capture)
        self._hover_check_id = None
        self._schedule_hover_check()

        # Лог
        self._log("MAMONOV Screen Recorder")
        self._log(f"ffmpeg: {self.ffmpeg or 'NOT FOUND'}")
        self._log(t('log_mic', self.mic_display) if self.mic_display else t('log_mic_not_found'))

    # --- UI ---
    def _build_ui(self):
        pad = {"padx": 10, "pady": 4}

        self.frm_top = tk.Frame(self.root, bg="#2b2b2b")
        self.frm_top.pack(fill="x", pady=(6, 0))

        frm_btn = tk.Frame(self.frm_top, bg="#2b2b2b")
        frm_btn.pack(pady=(4, 6))

        self.btn_rec = tk.Button(frm_btn, text=t('btn_rec'), font=("Segoe UI", 12, "bold"),
                                 width=12, command=self._on_rec_button,
                                 bg="#cc3333", fg="#ffffff", relief="flat",
                                 activebackground="#ee4444")
        self.btn_rec.pack(side="left", padx=6)

        self.btn_save = tk.Button(frm_btn, text=t('btn_save'), font=("Segoe UI", 12, "bold"),
                                  width=12, command=self._on_save_button,
                                  bg="#007acc", fg="#ffffff", relief="flat",
                                  activebackground="#0099ee")
        self.btn_save.pack(side="left", padx=6)

        # Демо-строка (золотая)
        # Демо-строка (через DemoBlock)
        self.demo.build_bar(self.frm_top, t)

        self.frm_detail = tk.Frame(self.root, bg="#2b2b2b")
        self.frm_detail.pack(fill="x")

        self.lbl_status = tk.Label(self.frm_detail, text="", font=("Segoe UI", 9),
                                   fg="#aaaaaa", bg="#2b2b2b", cursor="hand2")
        self.lbl_status.pack(**pad)
        self.lbl_status.bind("<Button-1>", self._copy_status)
        self._status_copy_timer = None

        frm_ind = tk.Frame(self.frm_detail, bg="#2b2b2b")
        frm_ind.pack(pady=(4, 2))

        frm_audio = tk.Frame(frm_ind, bg="#2b2b2b")
        frm_audio.pack(side="left", padx=16)
        self.cv_audio = tk.Canvas(frm_audio, width=18, height=18,
                                  bg="#2b2b2b", highlightthickness=0)
        self.cv_audio.pack()
        self.lamp_audio = self.cv_audio.create_oval(2, 2, 16, 16, fill="#cc3333")
        mic_label = t('label_audio') if self.mic_name else t('label_audio_off')
        self.lbl_audio = tk.Label(frm_audio, text=mic_label,
                                 font=("Segoe UI", 8), fg="#999999" if self.mic_name else "#666666",
                                 bg="#2b2b2b")
        self.lbl_audio.pack()

        frm_video = tk.Frame(frm_ind, bg="#2b2b2b")
        frm_video.pack(side="left", padx=16)
        self.cv_video = tk.Canvas(frm_video, width=18, height=18,
                                  bg="#2b2b2b", highlightthickness=0)
        self.cv_video.pack()
        self.lamp_video = self.cv_video.create_oval(2, 2, 16, 16, fill="#cc3333")
        tk.Label(frm_video, text=t('label_video'),
                 font=("Segoe UI", 8), fg="#999999", bg="#2b2b2b").pack()

        self.lbl_timer = tk.Label(self.frm_detail, text="00:00:00",
                                  font=("Consolas", 24, "bold"),
                                  fg="#00cc66", bg="#2b2b2b")
        self.lbl_timer.pack(pady=10)

        # Кнопка лога
        btn_log_style = dict(
            font=("Segoe UI", 9),
            bg="#333348", fg="#aaaaaa",
            activebackground="#444458", activeforeground="#cccccc",
            relief="flat", cursor="hand2",
        )
        self._log_visible = False
        self._btn_log = tk.Button(self.frm_detail, text=t('btn_log'),
                                   command=self._toggle_log, **btn_log_style)
        self._btn_log.pack(pady=(4, 0))

        # Лог (скрыт по умолчанию)
        self._log_frame = tk.Frame(self.root, bg="#2b2b2b")
        self._log_text = scrolledtext.ScrolledText(
            self._log_frame,
            width=50, height=10,
            bg="#0d0d1a", fg="#cccccc",
            font=("Consolas", 9),
            relief="flat",
            state=tk.DISABLED,
            wrap=tk.WORD,
            cursor="hand2",
        )
        self._log_text.pack(padx=8, pady=(0, 8))
        self._log_text.bind("<Button-1>", self._copy_log)

    # --- Лог ---

    def _log(self, msg):
        """Добавляет строку в лог."""
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] {msg}\n"

        def _insert():
            self._log_text.config(state=tk.NORMAL)
            self._log_text.insert(tk.END, line)
            self._log_text.see(tk.END)
            self._log_text.config(state=tk.DISABLED)

        if self.root.winfo_exists():
            self.root.after(0, _insert)

    def _copy_log(self, event=None):
        """Копирует весь лог в буфер обмена."""
        text = self._log_text.get("1.0", tk.END).strip()
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self._btn_log.config(text=t('btn_copied'))
            self.root.after(1500, lambda: self._btn_log.config(
                text=t('btn_hide_log') if self._log_visible else t('btn_log')))

    def _toggle_log(self):
        """Показать/скрыть лог."""
        if self._log_visible:
            self._log_frame.pack_forget()
            self._btn_log.config(text=t('btn_log'))
            self._log_visible = False
        else:
            self._log_frame.pack(fill="both", expand=True)
            self._btn_log.config(text=t('btn_hide_log'))
            self._log_visible = True

    # --- Сворачивание/разворачивание ---

    def _schedule_hover_check(self):
        self._hover_check_id = self.root.after(300, self._do_hover_check)

    def _do_hover_check(self):
        try:
            x = self.root.winfo_pointerx()
            y = self.root.winfo_pointery()
            rx = self.root.winfo_rootx()
            ry = self.root.winfo_rooty()
            rw = self.root.winfo_width()
            rh = self.root.winfo_height()
            inside = (rx <= x <= rx + rw and ry <= y <= ry + rh)
        except Exception:
            inside = False

        if inside and self.compact:
            self.compact = False
            self.frm_detail.pack(fill="x", after=self.frm_top)
            self.root.geometry(f"{self.WIN_W}x{self.FULL_H}")
            self.root.update_idletasks()
        elif not inside and not self.compact:
            self.compact = True
            self.frm_detail.pack_forget()
            self.root.geometry(f"{self.WIN_W}x{self.COMPACT_H}")
            self.root.update_idletasks()

        self._schedule_hover_check()

    # --- Проверка зависимостей ---

    # --- Ссылка «Получить за отзыв» ---

    def _check_deps(self):
        if self.demo.expired:
            self.lbl_status.config(text=t('demo_expired'), fg="#cc3333")
        elif not self.ffmpeg:
            self.lbl_status.config(text=t('status_no_ffmpeg'), fg="#cc3333")
        elif self.mic_display:
            d = self.mic_display if len(self.mic_display) < 35 else self.mic_display[:32] + "..."
            tag = " [alt]" if self.mic_info and self.mic_info.get("alt") else ""
            fg = "#00cc66" if self.mic_tested else "#cc3333"
            self.lbl_status.config(text=t('status_ready_mic', d, tag), fg=fg)
        else:
            self.lbl_status.config(text=t('status_ready_no_mic'), fg="#cc3333")

    # --- Клик по статусу = копировать ---

    def _copy_status(self, event=None):
        text = self.lbl_status.cget("text")
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            old_fg = self.lbl_status.cget("fg")
            self.lbl_status.config(text=t('status_copy'), fg="#cccc00")
            if self._status_copy_timer:
                self.root.after_cancel(self._status_copy_timer)
            self._saved_status = (text, old_fg)
            self._status_copy_timer = self.root.after(1000, self._restore_status)

    def _restore_status(self):
        if hasattr(self, '_saved_status') and self._saved_status:
            txt, fg = self._saved_status
            self.lbl_status.config(text=txt, fg=fg)
            self._saved_status = None
        self._status_copy_timer = None

    # --- Обновить UI ---

    def _update_ui(self):
        audio_ok = self.mic_name is not None
        if self.demo.expired:
            self.btn_rec.config(state="disabled")
            self.btn_save.config(state="disabled")
            return
        if self.state == "idle":
            self.btn_rec.config(state="normal", text=t('btn_rec'), bg="#cc3333")
            self.btn_save.config(state="normal")
            self.cv_video.itemconfig(self.lamp_video, fill="#cc3333")
            self.cv_audio.itemconfig(self.lamp_audio, fill="#00cc66" if audio_ok else "#666666")
        elif self.state == "recording":
            self.btn_rec.config(state="normal", text=t('btn_pause'), bg="#cc8800")
            self.btn_save.config(state="disabled")
            self.cv_video.itemconfig(self.lamp_video, fill="#00cc66")
            self.cv_audio.itemconfig(self.lamp_audio, fill="#00cc66" if audio_ok else "#cc3333")
        elif self.state == "paused":
            self.btn_rec.config(state="normal", text=t('btn_resume'), bg="#00cc66")
            self.btn_save.config(state="normal")
            self.cv_video.itemconfig(self.lamp_video, fill="#cc8800")
            self.cv_audio.itemconfig(self.lamp_audio, fill="#cc8800" if audio_ok else "#666666")

    def _start_license_check(self):
        # Фоновый запрос к серверу: оплачена ли копия.
        # При первом запуске этот же запрос закрепляет копию за
        # компьютером на сервере (check.php -> machine_bind).
        import threading

        def _worker():
            try:
                self.demo.check_server_license(
                    callback=lambda: self.root.after(0, self._on_license_confirmed))
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

        # Периодически сверяться с сервером (раз в 30 минут),
        # пока программа открыта и есть интернет.
        try:
            if self.root.winfo_exists():
                self.root.after(30 * 60 * 1000, self._start_license_check)
        except Exception:
            pass

    def _on_license_confirmed(self):
        # Сервер подтвердил оплату — снимаем демо на лету:
        # убираем демо-строку и включаем кнопки.
        try:
            if not self.root.winfo_exists():
                return
        except Exception:
            return
        try:
            bar = getattr(self.demo, '_bar_frame', None)
            if bar is not None:
                bar.destroy()
                self.demo._bar_frame = None
        except Exception:
            pass
        try:
            self.root.title(t('title'))
        except Exception:
            pass
        try:
            self._update_ui()
        except Exception:
            pass

    def _hide_from_capture(self):
        # Прячем окно программы от записи экрана — ВСЕГДА, как в проверенной
        # рабочей сборке. Никаких исключений/файлов-переключателей здесь нет:
        # панель видна на мониторе, но не попадает в видео.
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            self.root.update_idletasks()

            # Чтобы на 64-битной Windows дескрипторы окон не обрезались.
            user32.FindWindowW.restype = wintypes.HWND
            user32.GetAncestor.restype = wintypes.HWND
            user32.SetWindowDisplayAffinity.argtypes = [
                wintypes.HWND, wintypes.DWORD]
            user32.SetWindowDisplayAffinity.restype = wintypes.BOOL

            # 17 (0x11) = WDA_EXCLUDEFROMCAPTURE — именно это значение
            # стоит в проверенной рабочей сборке и реально убирает окно
            # из записи. Проблема была не в значении, а в том, что прежний
            # способ (GetAncestor) находил не то окно. Здесь помечаем
            # окно сразу несколькими способами — работает на любом
            # языке («Screen Recorder» / «Запись экрана») и в демо, и в полной.
            WDA = 0x11
            my_pid = kernel32.GetCurrentProcessId()

            def _apply(h):
                if h:
                    try:
                        user32.SetWindowDisplayAffinity(h, WDA)
                    except Exception:
                        pass

            # 1) По заголовку: текущий + оба языка, обычный и «ДЕМО».
            titles = {
                self.root.title(),
                'Screen Recorder', 'Запись экрана',
                'Screen Recorder — DEMO', 'Запись экрана — ДЕМО',
            }
            for ttl in titles:
                if ttl:
                    try:
                        _apply(user32.FindWindowW(None, ttl))
                    except Exception:
                        pass

            # 2) Самый надёжный способ: помечаем все видимые окна
            #    верхнего уровня, принадлежащие нашему процессу
            #    (не зависит от заголовка и языка).
            try:
                WNDENUMPROC = ctypes.WINFUNCTYPE(
                    wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

                def _cb(hwnd, lparam):
                    try:
                        if user32.IsWindowVisible(hwnd):
                            pid = wintypes.DWORD(0)
                            user32.GetWindowThreadProcessId(
                                hwnd, ctypes.byref(pid))
                            if pid.value == my_pid:
                                _apply(hwnd)
                    except Exception:
                        pass
                    return True

                user32.EnumWindows(WNDENUMPROC(_cb), 0)
            except Exception:
                pass

            # 3) Само окно Tk напрямую (на всякий случай).
            try:
                _apply(user32.GetAncestor(self.root.winfo_id(), 2))  # GA_ROOT
            except Exception:
                pass
        except Exception:
            pass

    def _save_dir(self):
        base = _video_base()
        os.makedirs(base, exist_ok=True)
        return base

    def _get_temp_dir(self):
        if not self._temp_dir:
            self._temp_dir = tempfile.mkdtemp(prefix="screenrec_")
        return self._temp_dir

    def _cleanup_temp_dir(self):
        if self._temp_dir and os.path.isdir(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir, ignore_errors=True)
            except Exception:
                pass
            self._temp_dir = None

    def _concat_segments(self):
        if len(self.segments) <= 1:
            if self.segments:
                src = self.segments[0]
                if src != self.filepath:
                    if os.path.isfile(self.filepath):
                        os.remove(self.filepath)
                    os.rename(src, self.filepath)
            return

        list_path = self.filepath + ".list.txt"
        with open(list_path, "w", encoding="utf-8") as f:
            for seg in self.segments:
                safe = seg.replace("\\", "/")
                f.write(f"file '{safe}'\n")

        tmp_out = self.filepath + ".tmp.mp4"
        cmd = [
            self.ffmpeg, "-y",
            "-f", "concat", "-safe", "0", "-i", list_path,
            "-c", "copy",
            tmp_out
        ]
        self._log(f"concat: {len(self.segments)} segments")
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         timeout=120, startupinfo=si)
            if os.path.isfile(tmp_out) and os.path.getsize(tmp_out) > 0:
                if os.path.isfile(self.filepath):
                    os.remove(self.filepath)
                os.rename(tmp_out, self.filepath)
            else:
                if os.path.isfile(tmp_out):
                    os.remove(tmp_out)
        except Exception as e:
            self._log(f"concat error: {e}")

        try:
            os.remove(list_path)
        except Exception:
            pass
        for seg in self.segments[1:]:
            try:
                os.remove(seg)
            except Exception:
                pass

    # ============================================================
    # КНОПКА «ЗАПИСЬ»
    # ============================================================

    def _on_rec_button(self):
        if self.demo.expired:
            return
        if self.state == "idle":
            self._start_recording()
        elif self.state == "recording":
            self._pause_recording()
        elif self.state == "paused":
            self._resume_recording()

    def _start_recording(self):
        if not self.ffmpeg:
            self.lbl_status.config(text=t('status_no_ffmpeg'), fg="#cc3333")
            return

        ts = time.strftime("%Y-%m-%d_%H-%M-%S")
        self.filepath = os.path.join(self._save_dir(), f"recording_{ts}.mp4")
        self.segments = []
        self.segment_num = 0
        self.accumulated = 0
        self.seg_start = None
        self._temp_dir = None

        self._spawn_segment()

    def _pause_recording(self):
        self._stop_ffmpeg()

        if self.current_segment and os.path.isfile(self.current_segment):
            self.segments.append(self.current_segment)
        self.current_segment = None

        if self.seg_start:
            self.accumulated += int(time.time() - self.seg_start)
            self.seg_start = None

        self.state = "paused"
        self._update_ui()

        h = self.accumulated // 3600
        m = (self.accumulated % 3600) // 60
        s = self.accumulated % 60
        self.lbl_timer.config(text=f"{h:02d}:{m:02d}:{s:02d}", fg="#cc8800")
        self.lbl_status.config(text=t('status_paused'), fg="#cc8800")

    def _resume_recording(self):
        self._spawn_segment()

    # ============================================================
    # КНОПКА «СОХРАНИТЬ»
    # ============================================================

    def _on_save_button(self):
        if self.demo.expired:
            return
        if self.state == "recording":
            self._stop_ffmpeg()
            if self.current_segment and os.path.isfile(self.current_segment):
                self.segments.append(self.current_segment)
            self.current_segment = None
            if self.seg_start:
                self.accumulated += int(time.time() - self.seg_start)
                self.seg_start = None

        if self.filepath and self.segments:
            self._concat_segments()

        if self.filepath and os.path.isfile(self.filepath) and os.path.getsize(self.filepath) > 0:
            self.lbl_status.config(text=t('status_saved', os.path.basename(self.filepath)), fg="#00cc66")
            h = self.accumulated // 3600
            m = (self.accumulated % 3600) // 60
            s = self.accumulated % 60
            self.lbl_timer.config(text=f"{h:02d}:{m:02d}:{s:02d}", fg="#00cc66")
            self._log(f"saved: {os.path.basename(self.filepath)}")
        else:
            self.lbl_status.config(text=t('status_no_file'), fg="#cc3333")

        self.filepath = None
        self.segments = []
        self.segment_num = 0
        self.accumulated = 0
        self.seg_start = None
        self.current_segment = None
        self._cleanup_temp_dir()
        self.state = "idle"
        self._update_ui()
        self.lbl_timer.config(text="00:00:00", fg="#00cc66")

    # ============================================================
    # Запуск / остановка ffmpeg
    # ============================================================

    def _spawn_segment(self):
        """Запустить ffmpeg для нового сегмента."""
        # Гарантируем, что окно скрыто от записи именно в момент
        # старта записи (заголовок к этому моменту уже окончательный).
        try:
            self._hide_from_capture()
        except Exception:
            pass
        self.segment_num += 1
        tmp = self._get_temp_dir()
        seg_path = os.path.join(tmp, f"seg_{self.segment_num}.mp4")

        if self.mic_name and not self.mic_needs_bat:
            cmd_list = [
                self.ffmpeg, "-y",
                "-f", "gdigrab", "-framerate", "30", "-i", "desktop",
                "-f", "dshow", "-i", f"audio={self.mic_name}",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                "-pix_fmt", "yuv420p",
                seg_path
            ]
        elif self.mic_name and self.mic_needs_bat:
            bat_line = (
                f'"{self.ffmpeg}" -y'
                f' -f gdigrab -framerate 30 -i desktop'
                f' -f dshow -i "audio={self.mic_name}"'
                f' -c:v libx264 -preset ultrafast -crf 23'
                f' -c:a aac -b:a 128k'
                f' -pix_fmt yuv420p'
                f' "{seg_path}"'
            )
            cmd_list = None
        else:
            cmd_list = [
                self.ffmpeg, "-y",
                "-f", "gdigrab", "-framerate", "30", "-i", "desktop",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-an",
                "-pix_fmt", "yuv420p",
                seg_path
            ]

        self._log(f"cmd: {' '.join(cmd_list) if cmd_list else 'bat: ' + bat_line}")

        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0

            if self.mic_name and self.mic_needs_bat and bat_line:
                bat_path = os.path.join(tmp, f"rec_seg_{self.segment_num}.bat")
                try:
                    import ctypes
                    oem_cp = ctypes.windll.kernel32.GetOEMCP()
                    bat_enc = f"cp{oem_cp}"
                except Exception:
                    bat_enc = "cp866"
                with open(bat_path, "wb") as f:
                    f.write(bat_line.encode(bat_enc) + b"\r\n")
                run_cmd = ["cmd", "/c", bat_path]
            elif cmd_list is not None:
                run_cmd = cmd_list
            else:
                return

            # Лог ffmpeg — в файл
            ffmpeg_log_path = os.path.join(DATA_DIR, "ffmpeg_log.txt")
            ffmpeg_log_f = open(ffmpeg_log_path, "wb")
            self.process = subprocess.Popen(
                run_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=ffmpeg_log_f,
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
                startupinfo=si
            )
            self._ffmpeg_log_f = ffmpeg_log_f
            self._ffmpeg_log_path = ffmpeg_log_path
            self.root.after(1000, self._check_ffmpeg_started)
        except Exception as e:
            self._log(f"ERROR start: {e}")
            self.lbl_status.config(text=t('status_start_error', e), fg="#cc3333")
            return

        self.current_segment = seg_path
        self.seg_start = time.time()
        self.state = "recording"
        self._update_ui()
        self.lbl_status.config(text=t('status_recording'), fg="#ff6666")
        self._tick_timer()

    def _check_ffmpeg_started(self):
        """Проверяем, не упал ли ffmpeg через секунду после запуска."""
        if self.process and self.process.poll() is not None:
            if hasattr(self, '_ffmpeg_log_f') and self._ffmpeg_log_f:
                try:
                    self._ffmpeg_log_f.close()
                except Exception:
                    pass
                self._ffmpeg_log_f = None
            err = ""
            try:
                with open(self._ffmpeg_log_path, "rb") as f:
                    raw = f.read()
                err = raw.decode("utf-8", errors="replace").strip()[-300:]
            except Exception:
                err = "(empty log)"
            self._log(f"ffmpeg crashed: {err[-80:]}")
            self.state = "idle"
            self._update_ui()
            self.lbl_status.config(text=t('status_ffmpeg_crash', err[-80:]), fg="#cc3333")

    def _stop_ffmpeg(self):
        """Остановить процесс ffmpeg."""
        if self.process and self.process.poll() is None:
            if self.mic_needs_bat:
                self.process.kill()
                try:
                    self.process.communicate(timeout=3)
                except Exception:
                    pass
            else:
                try:
                    self.process.communicate(input=b"q", timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    try:
                        self.process.communicate(timeout=3)
                    except Exception:
                        pass
            self.process = None

        # Прочитать лог ffmpeg после остановки
        if hasattr(self, '_ffmpeg_log_f') and self._ffmpeg_log_f:
            try:
                self._ffmpeg_log_f.close()
            except Exception:
                pass
            self._ffmpeg_log_f = None

        if hasattr(self, '_ffmpeg_log_path') and os.path.isfile(self._ffmpeg_log_path):
            try:
                with open(self._ffmpeg_log_path, "rb") as f:
                    raw = f.read()
                err_text = raw.decode("utf-8", errors="replace").strip()
                lines = [l for l in err_text.splitlines() if l.strip()]
                if lines:
                    self._log("--- ffmpeg output (last lines) ---")
                    for l in lines[-10:]:
                        self._log(l)
                    self._log("--- end ---")
            except Exception:
                pass

    # --- Таймер ---

    def _tick_timer(self):
        if self.state != "recording":
            return
        now = int(time.time() - self.seg_start) + self.accumulated
        h = now // 3600
        m = (now % 3600) // 60
        s = now % 60
        self.lbl_timer.config(text=f"{h:02d}:{m:02d}:{s:02d}", fg="#ff6666")
        self.timer_id = self.root.after(1000, self._tick_timer)

    # --- Обновление ---




# ============================================================
# ЗАПУСК
# ============================================================
def main():
    try:
        root = tk.Tk()
        root.geometry(f"{ScreenRecorderApp.WIN_W}x{ScreenRecorderApp.FULL_H}")
        app = ScreenRecorderApp(root)
        def _quit():
            # При закрытии окна — сохранить запись, остановить ffmpeg
            # и гарантированно завершить процесс, чтобы программа
            # не висела в фоне и могла снова запуститься.
            try:
                app._on_save_button()
            except Exception:
                pass
            try:
                app._stop_ffmpeg()
            except Exception:
                pass
            try:
                root.destroy()
            except Exception:
                pass
            os._exit(0)

        root.protocol("WM_DELETE_WINDOW", _quit)
        root.mainloop()
        os._exit(0)
    except Exception as e:
        err = traceback.format_exc()
        _show_error(t('error_main', err))


if __name__ == "__main__":
    main()