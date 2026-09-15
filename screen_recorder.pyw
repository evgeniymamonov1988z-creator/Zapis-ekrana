'''Screen Recorder — запись экрана + микрофон.
Всё включено: ffmpeg.exe в bin/, библиотеки в lib/.
Интернет для запуска НЕ нужен.
Файлы сохраняются на Рабочий стол -> Mamonov/Mamonov video/

Логика:
  Запись -> Пауза -> Продолжить -> Пауза -> ... -> Сохранить
  Кнопка "Запись" переключает: старт / пауза / продолжить
  Кнопка "Сохранить" — финал: стоп, склейка, файл готов
'''

import os
import sys
import subprocess
import time
import shutil
import traceback
import tempfile

# --- Только одна копия программы (сокет) ---
import socket
try:
    _single_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _single_sock.bind(('127.0.0.1', 51998))
    _single_sock.listen(1)
except OSError:
    sys.exit(0)


# ============================================================
# КЛАСС UPDATER — встроен прямо в программу
# (отдельный файл updater.py больше не нужен)
# ============================================================

class Updater:
    """Обновление программы через Git-репозиторий."""

    def __init__(self, repo_url, branch="master", app_dir=None, ssl_verify=False):
        self.repo_url = repo_url
        self.branch = branch
        self.ssl_verify = ssl_verify
        self.app_dir = app_dir or os.path.dirname(os.path.abspath(
            sys.executable if getattr(sys, 'frozen', False) else __file__))

    def _git(self, *args):
        """Запуск git. Возвращает (returncode, stdout, stderr)."""
        cmd = ["git"]
        if not self.ssl_verify:
            cmd += ["-c", "http.sslVerify=false"]
        cmd += ["-c", "core.autocrlf=false"]
        cmd += ["-c", "credential.helper="]
        cmd += list(args)
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0  # SW_HIDE
            r = subprocess.run(cmd, cwd=self.app_dir, capture_output=True, text=True,
                               timeout=60, startupinfo=si,
                               creationflags=subprocess.CREATE_NO_WINDOW)
            return r.returncode, r.stdout.strip(), r.stderr.strip()
        except FileNotFoundError:
            return -1, "", "Git is not installed (git-scm.com)"
        except subprocess.TimeoutExpired:
            return -2, "", "Timeout — check internet"
        except Exception as e:
            return -3, "", str(e)

    def _is_repo(self):
        """Папка уже Git-репозиторий?"""
        return os.path.isdir(os.path.join(self.app_dir, ".git"))

    def connect(self):
        """Подключить папку к репозиторию. Возвращает (True/False, сообщение)."""
        rc, _, err = self._git("--version")
        if rc != 0:
            return False, err or "git is not installed"

        if self._is_repo():
            return True, "Already connected"

        rc, _, err = self._git("init")
        if rc != 0:
            return False, f"git init failed: {err}"

        rc, _, err = self._git("remote", "add", "origin", self.repo_url)
        if rc != 0:
            self._cleanup_git()
            return False, f"remote add failed: {err}"

        rc, _, err = self._git("fetch", "origin", self.branch)
        if rc != 0:
            self._cleanup_git()
            return False, f"fetch failed: {err}"

        self._git("checkout", "-b", self.branch)

        rc, _, err = self._git("reset", "--hard", f"origin/{self.branch}")
        if rc != 0:
            self._cleanup_git()
            return False, f"reset failed: {err}"

        return True, "Connected!"

    def update(self):
        """Обновить программу. Если не подключено — подключит автоматически.
        Возвращает (True/False, сообщение)."""
        rc, _, err = self._git("--version")
        if rc != 0:
            return False, err or "git is not installed"

        if not self._is_repo():
            ok, msg = self.connect()
            if not ok:
                return False, msg
            return True, "Connected and updated!"

        self._git("remote", "set-url", "origin", self.repo_url)

        # Сначала fetch — узнаем что нового в репо
        self._git("fetch", "origin", self.branch)

        # Простой pull с rebase (без checkout -- . — он откатывает файлы к старой версии)
        rc, out, err = self._git("pull", "--rebase", "origin", self.branch)
        if rc != 0:
            # Конфликт — жёсткий сброс до версии из репо
            self._git("reset", "--hard", f"origin/{self.branch}")
            rc2, out2, err2 = self._git("pull", "origin", self.branch)
            if rc2 != 0:
                return False, f"Update failed: {err}"

        if "Already up to date" in out or "Already up-to-date" in out:
            return True, "Already up to date"

        return True, "Updated!"

    def restart(self):
        """Перезапустить текущую программу."""
        exe = sys.executable
        script = os.path.abspath(sys.argv[0])
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0  # SW_HIDE
        subprocess.Popen([exe, script],
                         startupinfo=si,
                         creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW)
        try:
            import tkinter as tk
            if tk._default_root:
                tk._default_root.destroy()
        except Exception:
            os._exit(0)

    def _cleanup_git(self):
        """Удалить .git если что-то пошло не так."""
        git_dir = os.path.join(self.app_dir, ".git")
        shutil.rmtree(git_dir, ignore_errors=True)


# --- Папка программы ---
APP_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))

# --- Добавляем lib/ в путь для библиотек ---
LIB_DIR = os.path.join(APP_DIR, "lib")
if os.path.isdir(LIB_DIR):
    sys.path.insert(0, LIB_DIR)

# --- Ловим ошибки до создания окна ---
ERROR_LOG = os.path.join(APP_DIR, "error.log")


def _show_error(msg):
    """Показать ошибку любым способом: окно или файл."""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.title("Screen Recorder — Ошибка")
        root.geometry("600x350")
        root.configure(bg="#2b2b2b")
        tk.Label(root, text="Ошибка запуска:", font=("Segoe UI", 14, "bold"),
                 fg="#cc3333", bg="#2b2b2b").pack(pady=(15, 5))
        txt = tk.Text(root, font=("Consolas", 10), bg="#1a1a1a", fg="#ff6666",
                      wrap="word", height=12, width=65)
        txt.pack(padx=15, pady=5)
        txt.insert("1.0", msg)

        def _copy_error():
            try:
                root.clipboard_clear()
                root.clipboard_append(msg)
                btn_copy.config(text="Скопировано!")
                root.after(1500, lambda: btn_copy.config(text="📋 Копировать"))
            except Exception:
                pass

        txt.config(state="disabled")
        frm_btn = tk.Frame(root, bg="#2b2b2b")
        frm_btn.pack(pady=5)
        btn_copy = tk.Button(frm_btn, text="📋 Копировать", command=_copy_error,
                             bg="#3c3c3c", fg="#ffffff", relief="flat", width=14,
                             font=("Segoe UI", 10))
        btn_copy.pack(side="left", padx=5)
        tk.Button(frm_btn, text="OK", command=root.destroy,
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
    _show_error(f"Не удалось загрузить tkinter:\n{e}\n\nУстановите Python с python.org (не Microsoft Store)")
    sys.exit(1)


# ============================================================
# FFMPEG — ищем в bin/ рядом с программой, потом в PATH
# ============================================================
def find_ffmpeg():
    local = os.path.join(APP_DIR, "bin", "ffmpeg.exe")
    if os.path.isfile(local):
        return local
    in_path = shutil.which("ffmpeg")
    if in_path:
        return in_path
    return None


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

        debug_path = os.path.join(APP_DIR, "mic_debug_raw.txt")
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
        hex_path = os.path.join(APP_DIR, "mic_debug_hex.txt")
        try:
            with open(hex_path, "w", encoding="utf-8") as f:
                f.write(f"Raw bytes: {len(raw)}\n\n")
                for i in range(0, min(len(raw), 1000), 16):
                    chunk = raw[i:i+16]
                    hex_part = " ".join(f"{b:02x}" for b in chunk)
                    ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
                    f.write(f"{i:04x}  {hex_part:<48}  {ascii_part}\n")
                if b"@device_" in raw:
                    f.write(f"\n>>> @device_ НАЙДЕН в байтах! <<<\n")
                else:
                    f.write(f"\n>>> @device_ НЕ НАЙДЕН в байтах <<<\n")
                    if b"(audio)" in raw:
                        f.write(">>> (audio) НАЙДЕН в байтах <<<\n")
                    else:
                        f.write(">>> (audio) НЕ НАЙДЕН в байтах <<<\n")
        except Exception:
            pass

    # Парсим список
    all_mics = _parse_mics_from_raw(raw)

    # Лог для отладки — ВСЕ записи в одном with
    mic_debug_info = os.path.join(APP_DIR, "mic_result.txt")
    with open(mic_debug_info, "w", encoding="utf-8") as f:
        f.write(f"all_mics found: {len(all_mics)}\n")
        for i, m in enumerate(all_mics):
            f.write(f"  [{i}] display={m.get('display')!r}, alt={m.get('alt')!r}\n")

        if not all_mics:
            f.write("No mics found at all.\n")
        else:
            # Выбираем первый микрофон с альт. именем (ASCII, надёжно)
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
        self.root.title("Screen Recorder")
        self.root.resizable(False, False)
        self.root.configure(bg="#2b2b2b")
        self.root.attributes("-topmost", True)

        self.ffmpeg = find_ffmpeg()
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

        self.root.after(200, self._hide_from_capture)
        self._hover_check_id = None
        self._schedule_hover_check()

        # Лог
        self._log("MAMONOV Screen Recorder")
        self._log(f"ffmpeg: {self.ffmpeg or 'NOT FOUND'}")
        self._log(f"микрофон: {self.mic_display or 'не найден'}")

    # --- UI ---
    def _build_ui(self):
        pad = {"padx": 10, "pady": 4}

        self.frm_top = tk.Frame(self.root, bg="#2b2b2b")
        self.frm_top.pack(fill="x", pady=(6, 0))

        frm_btn = tk.Frame(self.frm_top, bg="#2b2b2b")
        frm_btn.pack(pady=(4, 6))

        self.btn_rec = tk.Button(frm_btn, text="\u25cf  Запись", font=("Segoe UI", 12, "bold"),
                                 width=12, command=self._on_rec_button,
                                 bg="#cc3333", fg="#ffffff", relief="flat",
                                 activebackground="#ee4444")
        self.btn_rec.pack(side="left", padx=6)

        self.btn_save = tk.Button(frm_btn, text="\u2b07  Сохранить", font=("Segoe UI", 12, "bold"),
                                  width=12, command=self._on_save_button,
                                  bg="#007acc", fg="#ffffff", relief="flat",
                                  activebackground="#0099ee")
        self.btn_save.pack(side="left", padx=6)

        frm_btn2 = tk.Frame(self.frm_top, bg="#2b2b2b")
        frm_btn2.pack(pady=(0, 4))

        self.btn_update = tk.Button(frm_btn2, text="\u21bb  Обновить", font=("Segoe UI", 11),
                                   width=26, command=self._run_update,
                                   bg="#555555", fg="#ffffff", relief="flat",
                                   activebackground="#777777")
        self.btn_update.pack()

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
        mic_label = "Звук" if self.mic_name else "Звук ✗"
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
        tk.Label(frm_video, text="Видео",
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
        self._btn_log = tk.Button(self.frm_detail, text="\U0001f4cb  Лог",
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
            self._btn_log.config(text="\U0001f4cb  Скопировано!")
            self.root.after(1500, lambda: self._btn_log.config(
                text="\U0001f4cb  Скрыть лог" if self._log_visible else "\U0001f4cb  Лог"))

    def _toggle_log(self):
        """Показать/скрыть лог."""
        if self._log_visible:
            self._log_frame.pack_forget()
            self._btn_log.config(text="\U0001f4cb  Лог")
            self._log_visible = False
        else:
            self._log_frame.pack(fill="both", expand=True)
            self._btn_log.config(text="\U0001f4cb  Скрыть лог")
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

    def _check_deps(self):
        if not self.ffmpeg:
            self.lbl_status.config(text="ffmpeg не найден", fg="#cc3333")
        elif self.mic_display:
            d = self.mic_display if len(self.mic_display) < 35 else self.mic_display[:32] + "..."
            tag = " [alt]" if self.mic_info and self.mic_info.get("alt") else ""
            fg = "#00cc66" if self.mic_tested else "#cc3333"
            self.lbl_status.config(text=f"Готово | Микрофон: {d}{tag}", fg=fg)
        else:
            self.lbl_status.config(text="Готово | Микрофон не найден", fg="#cc3333")

    # --- Клик по статусу = копировать ---

    def _copy_status(self, event=None):
        text = self.lbl_status.cget("text")
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            old_fg = self.lbl_status.cget("fg")
            self.lbl_status.config(text="Скопировано!", fg="#cccc00")
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
        if self.state == "idle":
            self.btn_rec.config(text="\u25cf  Запись", bg="#cc3333")
            self.btn_save.config(state="normal")
            self.cv_video.itemconfig(self.lamp_video, fill="#cc3333")
            self.cv_audio.itemconfig(self.lamp_audio, fill="#00cc66" if audio_ok else "#666666")
        elif self.state == "recording":
            self.btn_rec.config(text="\u25a0  Пауза", bg="#cc8800")
            self.btn_save.config(state="disabled")
            self.cv_video.itemconfig(self.lamp_video, fill="#00cc66")
            self.cv_audio.itemconfig(self.lamp_audio, fill="#00cc66" if audio_ok else "#cc3333")
        elif self.state == "paused":
            self.btn_rec.config(text="\u25b6  Продолжить", bg="#00cc66")
            self.btn_save.config(state="normal")
            self.cv_video.itemconfig(self.lamp_video, fill="#cc8800")
            self.cv_audio.itemconfig(self.lamp_audio, fill="#cc8800" if audio_ok else "#666666")

    def _hide_from_capture(self):
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.FindWindowW(None, "Screen Recorder")
            if hwnd:
                user32.SetWindowDisplayAffinity(hwnd, 0x11)
        except Exception:
            pass

    def _save_dir(self):
        base = os.path.join(os.path.expanduser("~"), "Desktop", "Mamonov", "Mamonov video")
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
        if self.state == "idle":
            self._start_recording()
        elif self.state == "recording":
            self._pause_recording()
        elif self.state == "paused":
            self._resume_recording()

    def _start_recording(self):
        if not self.ffmpeg:
            self.lbl_status.config(text="ffmpeg не найден", fg="#cc3333")
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
        self.lbl_status.config(text="Пауза", fg="#cc8800")

    def _resume_recording(self):
        self._spawn_segment()

    # ============================================================
    # КНОПКА «СОХРАНИТЬ»
    # ============================================================

    def _on_save_button(self):
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
            self.lbl_status.config(text=f"Сохранено: {os.path.basename(self.filepath)}", fg="#00cc66")
            h = self.accumulated // 3600
            m = (self.accumulated % 3600) // 60
            s = self.accumulated % 60
            self.lbl_timer.config(text=f"{h:02d}:{m:02d}:{s:02d}", fg="#00cc66")
            self._log(f"saved: {os.path.basename(self.filepath)}")
        else:
            self.lbl_status.config(text="Файл не найден! Сначала запиши.", fg="#cc3333")

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
            ffmpeg_log_path = os.path.join(APP_DIR, "ffmpeg_log.txt")
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
            self.lbl_status.config(text=f"Ошибка запуска: {e}", fg="#cc3333")
            return

        self.current_segment = seg_path
        self.seg_start = time.time()
        self.state = "recording"
        self._update_ui()
        self.lbl_status.config(text="Запись...", fg="#ff6666")
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
                err = "(лог пуст)"
            self._log(f"ffmpeg crashed: {err[-80:]}")
            self.state = "idle"
            self._update_ui()
            self.lbl_status.config(text=f"ffmpeg упал: {err[-80:]}", fg="#cc3333")

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

    def _run_update(self):
        self.lbl_status.config(text="Обновляю...", fg="#cccc00")
        self.root.update()
        try:
            upd = Updater(
                repo_url="https://oauth2:pv1_hXF132xz40gjb3875E5ag1m465A5iJ2794N052mF0g7sGZ6F773I0912wEZ1F675_1822378402@git.sourcecraft.dev/evgeniymamonov1988/screen-recorder.git",
                branch="master",
            )
            ok, msg = upd.update()
            if ok:
                self._log(f"update ok: {msg}")
                self.lbl_status.config(text=msg, fg="#00cc66")
                self.root.after(2000, lambda: (self._stop_ffmpeg(), upd.restart()))
            else:
                self._log(f"update fail: {msg}")
                self.lbl_status.config(text=msg, fg="#cc3333")
        except Exception as e:
            err = traceback.format_exc()
            self._log(f"update error: {err}")
            self.lbl_status.config(text=f"Ошибка обновления: {e}", fg="#cc3333")


# ============================================================
# ЗАПУСК
# ============================================================
def main():
    try:
        root = tk.Tk()
        root.geometry(f"{ScreenRecorderApp.WIN_W}x{ScreenRecorderApp.FULL_H}")
        app = ScreenRecorderApp(root)
        root.protocol("WM_DELETE_WINDOW", lambda: (app._on_save_button(), root.destroy()))
        root.mainloop()
    except Exception as e:
        err = traceback.format_exc()
        _show_error(f"Ошибка при запуске:\n\n{err}")


if __name__ == "__main__":
    main()
