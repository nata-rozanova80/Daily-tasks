# Daily-tasks
Ежедневный список дел
# Checklist Notes (Xiaomi-style) — PySide6 + SQLite

Мини-приложение заметок в стиле Xiaomi Notes: цветные карточки, чеклисты с галочками, текстовые заметки, быстрые групповые действия и удобный поиск.

## ✨ Возможности

* **Два типа заметок**:

  * *Список (чекбоксы)* — отмечайте выполненные пункты, массово снимайте галочки, удаляйте выбранные.
  * *Текстовая заметка* — отображается в отдельном окне без чекбоксов.
* **Поиск** по **названию**, **пунктам чеклиста** и **тексту** заметок (без учета регистра, работает с кириллицей).
* **Главное окно**: список всех заметок с чекбоксами для групповых действий (**закрепить, удалить**), поиск, создание новой.
* **Открытие списка** в новом окне (старое скрывается): «Назад», «Удалить выбранные», «Снять галочки».
  Выделение строк — **ярко-зелёным**, клик по тексту пункта ставит/снимает галочку и включает выделение.
* **Цветовые карточки**: у каждой заметки свой цвет (квадратик-образец в диалоге создания). На главном экране строка заметки окрашивается в выбранный цвет.
* **Локальная база** SQLite с автосозданием/миграциями и индексами для быстрого поиска.
* **Иконка приложения**: зелёный градиент с галочкой (рисуется программно и для EXE можно сгенерировать `app.ico`).

---

## 🧱 Стек

* Python 3.9+ (рекомендуется 3.10/3.11)
* [PySide6](https://doc.qt.io/qtforpython/)
* SQLite (встроен)
* PyInstaller — упаковка под Windows

---

## 📦 Установка и запуск (из исходников)

```bash
# Клонировать
git clone https://github.com/<your>/<repo>.git
cd <repo>

# Виртуальное окружение
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

pip install --upgrade pip
pip install PySide6
```

Запуск:

```bash
python main.py
```

---

## 🗃 Где хранится база

* **Windows**: `%USERPROFILE%\AppData\Roaming\ChecklistNotes\app.db`
* **Linux**: `~/.local/share/ChecklistNotes/app.db`

Файл создается автоматически при первом запуске. Миграции выполняются «на лету».

---

## 🧭 Быстрый тур по интерфейсу

* **Главное окно**:

  * Поле поиска (скрывается/показывается по кнопке «🔍»)
  * Список заметок: слева чекбокс (для групповых действий), справа название на цветном фоне
  * Кнопки: «📌» (закрепить выбранные), «🗑️» (удалить выбранные), «＋» (новая)

* **Окно списка**:

  * «⬅ Назад», «🗑 Удалить выбранные», «✔ Снять галочки»
  * Пункты списка как чекбоксы; клик по тексту = отметить + выделить строку зелёным
  * «＋ Добавить пункт» внизу

---

## 🔍 Поиск

Поиск на главном экране ищет одновременно:

* `lists.title` — название заметки,
* `items.text` — текст пунктов чеклиста,
* `lists.note_text` — содержимое текстовых заметок.

Работает без учета регистра (кириллица/латиница). Для скорости создаются индексы.

---

## 🎨 Иконка приложения

Иконка окна генерируется программно. Для EXE-файла Windows нужен **файл** `.ico`.
Скрипт для быстрого создания `app.ico`:

```python
# make_icon.py
from PySide6.QtGui import QPixmap, QPainter, QLinearGradient, QColor, QPainterPath, QPen
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

def make_app_icon(size=256) -> QPixmap:
    pm = QPixmap(size, size); pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform, True)
    grad = QLinearGradient(0, 0, 0, size)
    grad.setColorAt(0.0, QColor("#22c55e")); grad.setColorAt(1.0, QColor("#16a34a"))
    p.setBrush(grad); p.setPen(Qt.NoPen)
    r = int(size*0.22); p.drawRoundedRect(0, 0, size, size, r, r)
    path = QPainterPath(); path.moveTo(size*0.26, size*0.55); path.lineTo(size*0.45, size*0.74); path.lineTo(size*0.78, size*0.36)
    p.setPen(QPen(QColor("#fff"), max(6, int(size*0.08)), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)); p.setBrush(Qt.NoBrush)
    p.drawPath(path); p.end(); return pm

if __name__ == "__main__":
    app = QApplication([])
    pm = make_app_icon(256)
    pm.save("app.ico", "ICO")
    print("Saved app.ico")
```

Запуск:

```bash
python make_icon.py
```

---

## 🛠 Сборка Windows EXE и ярлык на рабочем столе

Установить PyInstaller:

```powershell
pip install pyinstaller
```

Сборка **без пробелов** в имени (так проще в PowerShell):

```powershell
pyinstaller --noconfirm --clean `
  --windowed --onefile `
  --name "ChecklistNotes" `
  --icon ".\app.ico" `
  .\main.py
```

EXE появится в `.\dist\ChecklistNotes.exe`. Проверить:

```powershell
& ".\dist\ChecklistNotes.exe"
```

Создать ярлык на рабочем столе:

```powershell
$exe = (Resolve-Path ".\dist\ChecklistNotes.exe").Path
$ico = (Resolve-Path ".\app.ico").Path
$desktop = [Environment]::GetFolderPath('Desktop')
$lnk = Join-Path $desktop 'Checklist Notes.lnk'
if (Test-Path $lnk) { Remove-Item $lnk -Force }
$wsh = New-Object -ComObject WScript.Shell
$s = $wsh.CreateShortcut($lnk)
$s.TargetPath = $exe
$s.WorkingDirectory = (Split-Path $exe)
$s.IconLocation = $ico
$s.Description = 'Checklist Notes'
$s.Save()
```

> Если ярлык не запускает приложение — проверьте, что **Target** указывает на реальный `ChecklistNotes.exe`, а **Рабочая папка** — на папку `dist`.
> Если иконка «серая», переименуйте `app.ico` → `app2.ico` и пересоздайте ярлык (сброс кэша иконок).

---

## 🗂 Структура проекта

```
.
├─ main.py            # UI и логика приложения (PySide6)
├─ db.py              # Работа с SQLite: таблицы, миграции, поиск
├─ app.ico            # (опционально) иконка для EXE/ярлыка
├─ make_icon.py       # (опционально) генератор app.ico
└─ README.md
```

---

## ⚙️ Конфигурация

* Цвета карточек настраиваются при создании заметки (в палитре квадратиков).
* Путь к базе задаётся автоматически по ОС (см. «Где хранится база»).
  Можно изменить, поправив `_DB_PATH` в `db.py`.

---

## 🧩 Известные мелочи / советы

* Если используете другое оформление Qt и «галочки» у чекбоксов выглядят нечитабельными — в коде принудительно применяется стиль **Fusion** для единообразного рендера.
* Для очень больших баз имеет смысл вынести SQLite в отдельную папку и/или включить VACUUM/анализ (в текущей версии не требуется).

---

## 🗺 Дальнейшие идеи (пул-реквесты приветствуются)

* Редактирование текстовых заметок (кнопка «Изменить/Сохранить»).
* Подсветка совпадений при поиске.
* Внутренний поиск по пунктам в открытом списке.
* Экспорт/импорт базы и/или синхронизация.

---

## 📜 Лицензия

MIT (можете заменить на свою при публикации).

---

## 🙌 Автор / связь

Если есть вопросы/идеи/баг-репорты — создавайте Issue в репозитории. PR с улучшениями приветствуются!
