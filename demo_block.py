"""
ШАБЛОН ДЕМО-БЛОКА v2.1
Подключается к любой программе на Python (tkinter).

КАК РАБОТАЕТ:
— Сервер при скачивании встраивает UUID прямо в файл программы
— Программа читает свой UUID из себя самой
— При запуске тихо звонит на сервер: кто запустился, какой статус
— При активации отправляет product_id + UUID на сервер
— Сервер решает: разблокировать или нет

КАК ИСПОЛЬЗОВАТЬ:
1. Скопируй demo_block.py в папку программы
2. Добавь строки в словарь переводов T (см. ниже)
3. В __init__ программы: self.demo = DemoBlock(product_id=3, demo_days=3, t=t)
4. В _build_ui(): self.demo.build_bar(parent_frame, t)
5. В _update_ui(): self.demo.lock_buttons(btn_rec, btn_save, ...)
6. В обработчиках кнопок: if self.demo.expired: return

НА СЕРВЕРЕ (при скачивании):
— Скрипт скачивания заменяет _INSTANCE_UUID = "PLACEHOLDER"
  на _INSTANCE_UUID = "реальный-uuid"
— Каждый скачанный экземпляр получает свой уникальный номер

СТАТИСТИКА (на сервере):
— ping() при запуске считает уникальные установки
— Дашборд покажет: скачано, пользуется, демо истекло, получили за отзыв

ПЛОЩАДКИ:
— product_id=1 → Market Watch Bulk Loader
— product_id=2 → MWBL Free
— product_id=3 → Screen Recorder
— product_id=4 → MWBL Studio
"""

import os
import datetime

# ============================================================
# УНИКАЛЬНЫЙ НОМЕР ЭКЗЕМПЛЯРА
# Сервер при скачивании заменяет PLACEHOLDER на реальный UUID
# ============================================================

_INSTANCE_UUID = "PLACEHOLDER"

# ============================================================
# ПУТИ — общая папка, но файлы у каждого продукта свои
# ============================================================

_DEMO_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'MAMONOV')

# URL сервера статистики и лицензий (сделаем позже)
_SERVER_URL = "https://evgeniymamonov.com/api/ping"

# ============================================================
# СТРОКИ ДЛЯ СЛОВАРЯ ПЕРЕВОДОВ T — добавь в свой словарь
# ============================================================

# RU = {
#     'demo_days_3': 'ДЕМО — 3 дня',
#     'demo_days_2': 'ДЕМО — 2 дня',
#     'demo_days_1': 'ДЕМО — 1 день',
#     'demo_expired': 'Демо кончилось',
#     'demo_buy': 'Получить за отзыв',
#     'demo_buy_link': 'https://evgeniymamonov.com/buy.html',
# }
#
# EN = {
#     'demo_days_3': 'DEMO — 3 days',
#     'demo_days_2': 'DEMO — 2 days',
#     'demo_days_1': 'DEMO — 1 day',
#     'demo_expired': 'Demo expired',
#     'demo_buy': 'Get for a review',
#     'demo_buy_link': 'https://evgeniymamonov.com/buy.html',
# }


# ============================================================
# КЛАСС DEMOBLOCK
# ============================================================

class DemoBlock:
    """Универсальный демо-блок для любой программы.

    Параметры:
        product_id  — номер продукта (1=MWBL, 2=MWBL Free, 3=Screen Recorder, ...)
        demo_days   — сколько дней длится демо (3 или 7)
        t           — функция перевода (если нет, будет EN)
    """

    def __init__(self, product_id, demo_days=3, t=None):
        self.product_id = product_id
        self.demo_days = demo_days
        self._t = t  # функция перевода

        # Файлы у каждого продукта свои (не конфликтуют)
        self._demo_file = os.path.join(_DEMO_DIR, f'.demo_date_{product_id}')
        self._license_file = os.path.join(_DEMO_DIR, f'.demo_licensed_{product_id}')

        # Уникальный номер экземпляра
        if _INSTANCE_UUID != "PLACEHOLDER":
            # Сервер вписал при скачивании
            self.instance_uuid = _INSTANCE_UUID
        else:
            # Разработка — генерируем и сохраняем в APPDATA
            self.instance_uuid = self._generate_fallback_uuid()

        # Проверяем демо-статус
        self.status, self.days_left = self._check()
        self.expired = (self.status == 'expired')
        self.licensed = (self.status == 'licensed')

        # Тихий звонок на сервер — считаем уникальные запуски
        # Серверную часть делаем позже, сейчас клиент готов
        self.ping()

    # ----------------------------------------------------------
    # UUID: запасной вариант для разработки
    # ----------------------------------------------------------

    def _generate_fallback_uuid(self):
        """Если сервер не вписал UUID (разработка),
        генерируем и сохраняем в APPDATA."""
        fallback_file = os.path.join(_DEMO_DIR, f'.dev_uuid_{self.product_id}')
        try:
            os.makedirs(_DEMO_DIR, exist_ok=True)
            if os.path.isfile(fallback_file):
                with open(fallback_file, 'r') as f:
                    uid = f.read().strip()
                if uid:
                    return uid
            import uuid
            uid = str(uuid.uuid4())
            with open(fallback_file, 'w') as f:
                f.write(uid)
            return uid
        except Exception:
            import uuid
            return str(uuid.uuid4())

    # ----------------------------------------------------------
    # Проверка демо
    # ----------------------------------------------------------

    def _check(self):
        """Проверить демо-статус. Возвращает:
            ('licensed', 0)   — сервер разрешил, полная версия
            ('ok', days_left) — демо действует
            ('expired', 0)    — демо кончилось
        """
        # Сервер уже разрешил?
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

            # Есть файл с датой?
            if os.path.isfile(self._demo_file):
                with open(self._demo_file, 'r') as f:
                    first_run = f.read().strip()
                first_date = datetime.datetime.strptime(first_run, '%Y-%m-%d').date()
            else:
                # Первый запуск — записываем дату
                today = datetime.date.today()
                with open(self._demo_file, 'w') as f:
                    f.write(today.strftime('%Y-%m-%d'))
                first_date = today

            # Сколько дней прошло
            days_passed = (datetime.date.today() - first_date).days
            days_left = self.demo_days - days_passed

            if days_left <= 0:
                return ('expired', 0)
            return ('ok', days_left)

        except Exception:
            # Ошибка чтения — даём работать
            return ('ok', self.demo_days)

    # ----------------------------------------------------------
    # Сервер подтвердил — записываем
    # ----------------------------------------------------------

    def mark_licensed(self):
        """Сервер подтвердил — записываем локально.
        Вызови после успешного ответа сервера."""
        try:
            os.makedirs(_DEMO_DIR, exist_ok=True)
            with open(self._license_file, 'w') as f:
                f.write('ok')
            self.status = 'licensed'
            self.licensed = True
            self.expired = False
        except Exception:
            pass

    # ----------------------------------------------------------
    # Звонок на сервер — статистика запусков
    # ----------------------------------------------------------

    def ping(self):
        """Тихий звонок на сервер при запуске.
        Отправляет product_id, instance_uuid, статус демо.
        Сервер считает уникальные установки и живых пользователей.
        Если сервер недоступен — ничего не ломается, программа работает дальше.

        СЕРВЕРНУЮ ЧАСТЬ (/api/ping) ДЕЛАЕМ ПОЗЖЕ.
        """
        try:
            import urllib.request
            import urllib.parse
            params = urllib.parse.urlencode({
                'product': self.product_id,
                'instance': self.instance_uuid,
                'status': self.status,
                'days': self.days_left,
            })
            url = f'{_SERVER_URL}?{params}'
            req = urllib.request.Request(url, method='GET')
            req.add_header('User-Agent', 'MAMONOV-DemoBlock/2.1')
            # Таймаут 3 секунды — не тормозим запуск
            urllib.request.urlopen(req, timeout=3)
        except Exception:
            pass  # Сервер недоступен — не проблема

    # ----------------------------------------------------------
    # Проверка лицензии на сервере
    # ----------------------------------------------------------

    def check_server_license(self, callback=None):
        """Спросить сервер: этот экземпляр оплачен/разблокирован?
        Если да — вызвать mark_licensed() и callback.

        callback — функция, которую вызвать после успешной активации,
        например обновить UI.

        СЕРВЕРНУЮ ЧАСТЬ (/api/check) ДЕЛАЕМ ПОЗЖЕ.
        """
        try:
            import urllib.request
            import urllib.parse
            import json
            params = urllib.parse.urlencode({
                'product': self.product_id,
                'instance': self.instance_uuid,
            })
            url = f'https://evgeniymamonov.com/api/check?{params}'
            req = urllib.request.Request(url, method='GET')
            req.add_header('User-Agent', 'MAMONOV-DemoBlock/2.1')
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read().decode('utf-8'))
            if data.get('licensed'):
                self.mark_licensed()
                if callback:
                    callback()
        except Exception:
            pass  # Сервер недоступен — работаем по локальному статусу

    # ----------------------------------------------------------
    # Текст для золотой строки
    # ----------------------------------------------------------

    def bar_text(self):
        """Текст для золотой демо-строки."""
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

    # ----------------------------------------------------------
    # Ссылка на страницу покупки/отзыва
    # ----------------------------------------------------------

    def buy_url(self):
        """Ссылка на buy.html с product_id и instance_uuid."""
        t = self._t or (lambda k, *a: k)
        base = t('demo_buy_link')
        return f'{base}?product={self.product_id}&instance={self.instance_uuid}'

    # ----------------------------------------------------------
    # Открыть ссылку в браузере
    # ----------------------------------------------------------

    def open_buy_link(self, event=None):
        """Открыть страницу покупки/отзыва в браузере."""
        import webbrowser
        webbrowser.open(self.buy_url())

    # ----------------------------------------------------------
    # UI: золотая строка + ссылка (для tkinter)
    # ----------------------------------------------------------

    def build_bar(self, parent, t=None):
        """Создать золотую демо-строку в интерфейсе.

        parent — фрейм-родитель (tk.Frame)
        t — функция перевода

        Возвращает (lbl_demo, lbl_buy) — метки, или (None, None) если licensed.
        """
        import tkinter as tk
        if t:
            self._t = t

        if self.licensed:
            return (None, None)

        frm = tk.Frame(parent, bg="#2b2b2b")
        frm.pack(fill="x", padx=10, pady=(5, 0))

        # Золотая строка
        lbl_demo = tk.Label(frm, text=self.bar_text(),
                            font=("Segoe UI", 9, "bold"),
                            fg="#DAA520", bg="#2b2b2b")
        lbl_demo.pack(side="left")

        lbl_buy = None
        if self.expired:
            # Ссылка «Получить за отзыв»
            t_fn = self._t or (lambda k, *a: k)
            lbl_buy = tk.Label(frm, text=t_fn('demo_buy'),
                               font=("Segoe UI", 9, "bold"),
                               fg="#0099ee", bg="#2b2b2b", cursor="hand2")
            lbl_buy.pack(side="left", padx=(10, 0))
            lbl_buy.bind("<Button-1>", self.open_buy_link)

        return (lbl_demo, lbl_buy)

    # ----------------------------------------------------------
    # UI: блокировка кнопок
    # ----------------------------------------------------------

    def lock_buttons(self, *buttons):
        """Заблокировать кнопки, если демо кончилось.
        Передай список кнопок: demo.lock_buttons(btn_rec, btn_save)"""
        if self.expired:
            for btn in buttons:
                btn.config(state="disabled")
            return True
        else:
            for btn in buttons:
                btn.config(state="normal")
            return False
