
import sys
from typing import Optional, Dict

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QAction
from PySide6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QDialog, QDialogButtonBox, QLineEdit, QTextEdit, QScrollArea, QCheckBox, QFrame,
    QInputDialog, QMessageBox, QToolBar, QGridLayout, QComboBox
)

import dbold


class NewListDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Новая заметка / список")
        self.setMinimumWidth(420)

        name_lbl = QLabel("Название")
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Например: Покупки")

        type_lbl = QLabel("Тип")
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Список (чекбоксы)", "Заметка (текст)"])

        color_lbl = QLabel("Цвет карточки")
        self.color_combo = QComboBox()
        self.color_combo.addItems(["#ffffff", "#fff7cc", "#e7f5ff", "#ffe7f0", "#e8ffe7"])

        items_lbl = QLabel("Пункты (по одному в строке) / Текст заметки")
        self.items_edit = QTextEdit()
        self.items_edit.setPlaceholderText("Молоко\nХлеб\nЯйца")

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addWidget(name_lbl); lay.addWidget(self.title_edit)
        lay.addWidget(type_lbl); lay.addWidget(self.type_combo)
        lay.addWidget(color_lbl); lay.addWidget(self.color_combo)
        lay.addWidget(items_lbl); lay.addWidget(self.items_edit)
        lay.addWidget(btns)

    def get_data(self):
        title = self.title_edit.text().strip()
        color = self.color_combo.currentText()
        is_checklist = self.type_combo.currentIndex() == 0
        raw = [s for s in self.items_edit.toPlainText().splitlines()]
        items = [s.strip() for s in raw if s.strip()] if is_checklist else (raw and [raw[0]] or [])
        return title, items, color, is_checklist

    def accept(self):
        title, items, color, is_checklist = self.get_data()
        if not title:
            QMessageBox.warning(self, "Пустое название", "Введите название.")
            return
        super().accept()


class RoundCard(QFrame):
    def __init__(self, parent=None, color="#ffffff"):
        super().__init__(parent)
        self.setObjectName("card")
        self.setProperty("class", "card")
        self.setStyleSheet(f"QFrame#card {{ background: {color}; }}" )


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Checklist Notes — Xiaomi Notes style")
        self.resize(1100, 700)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        top = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по названию и пунктам...")
        self.search_edit.textChanged.connect(self._reload_grid)

        self.new_btn = QPushButton("＋ Новая")
        self.new_btn.clicked.connect(self._create_new)

        self.show_archived = QPushButton("Архив")
        self.show_archived.setCheckable(True)
        self.show_archived.toggled.connect(self._reload_grid)

        top.addWidget(self.search_edit)
        top.addWidget(self.show_archived)
        top.addWidget(self.new_btn)

        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(12); self.grid.setVerticalSpacing(12)
        self.scroll.setWidget(self.grid_host)

        self.detail_title = QLabel("Выберите заметку")
        f2 = QFont(); f2.setPointSize(13); f2.setBold(True); self.detail_title.setFont(f2)

        self.detail_toolbar = QToolBar()
        self.add_item_action = QAction("Добавить пункт", self); self.add_item_action.triggered.connect(self._add_item)
        self.reset_action = QAction("Сбросить отмеченные", self); self.reset_action.triggered.connect(self._reset_checked)
        self.pin_action = QAction("Закрепить/Открепить", self); self.pin_action.triggered.connect(self._toggle_pin_current)
        self.archive_action = QAction("В архив/из архива", self); self.archive_action.triggered.connect(self._toggle_archive_current)
        for a in (self.add_item_action, self.reset_action, self.pin_action, self.archive_action):
            self.detail_toolbar.addAction(a)

        self.items_container = QWidget()
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(6, 6, 6, 6); self.items_layout.setSpacing(8); self.items_layout.addStretch()
        self.detail_scroll = QScrollArea(); self.detail_scroll.setWidgetResizable(True); self.detail_scroll.setWidget(self.items_container)

        panes = QHBoxLayout()
        left = QVBoxLayout(); left.addLayout(top); left.addWidget(self.scroll, 1)

        right_card = QFrame(); right_card.setObjectName("card")
        right_card.setStyleSheet("QFrame#card{background:#fff;border:1px solid #e5e7eb;border-radius:16px;}")
        right = QVBoxLayout(right_card); right.setContentsMargins(16,16,16,16)
        right.addWidget(self.detail_title); right.addWidget(self.detail_toolbar); right.addWidget(self.detail_scroll, 1)

        panes.addLayout(left, 2); panes.addWidget(right_card, 3)
        root.addLayout(panes, 1)

        self.active_list_id: Optional[int] = None
        self.checkbox_map: Dict[int, QCheckBox] = {}

        self._apply_styles()
        self._reload_grid()

    def _apply_done_style(self, checkbox: QCheckBox, checked: bool) -> None:
        f = checkbox.font(); f.setStrikeOut(checked); checkbox.setFont(f)
        checkbox.setStyleSheet("QCheckBox#todo { color: %s; }" % ("#6b7280" if checked else "#1f2937"))

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget { background: qlineargradient(x1:0,y1:0, x2:0, y2:1, stop:0 #f6f8fb, stop:1 #eaeef5);
                      font-family: 'Segoe UI', 'Roboto', sans-serif; font-size: 12.5pt; color: #1f2937; }
            QFrame#card { background:#ffffff; border:1px solid #e5e7eb; border-radius:16px; }
            QLineEdit { border: 1px solid #e5e7eb; border-radius: 12px; padding: 8px 10px; background:#f9fafb; }
            QPushButton { background: qlineargradient(x1:0,y1:0, x2:0, y2:1, stop:0 #4f46e5, stop:1 #4338ca);
                          border:0; color:#fff; padding:8px 12px; border-radius:12px; font-weight:600; }
            QToolBar { background:#f8fafc; border:1px solid #e5e7eb; border-radius:12px; padding:6px; }
            QToolBar QToolButton { padding:8px 12px; border-radius:10px; background:#ffffff; border:1px solid #e5e7eb; margin-right:8px; }

            /* --- ЧЕКБОКСЫ: фиксированный индикатор + видимая разница checked/unchecked --- */
            QCheckBox#todo::indicator {
                width: 22px; height: 22px;
                margin-right: 10px;
                border-radius: 6px;
                border: 1px solid #cbd5e1;
                background: #ffffff;
            }
            QCheckBox#todo::indicator:checked {
                background: qlineargradient(x1:0,y1:0, x2:0, y2:1, stop:0 #4f46e5, stop:1 #4338ca);
                border: 1px solid #4f46e5;
            }
            QCheckBox#todo::indicator:unchecked {
                background: #ffffff;
            }
            QCheckBox#todo { padding: 8px 10px; background:#fff; border:1px solid #e5e7eb; border-radius:12px; }
        """)

    def _reload_grid(self):
        # Здесь у вас код обновления карточек (оставлен без изменений)
        pass

    # Остальные методы (_open_note, _add_item, _reset_checked, и т.д.) — без изменений
    # Важно: убедитесь, что при создании чекбокса вы вызываете:
    # cb.setObjectName("todo")
    # и подключаете stateChanged к обработчику, который вызывает db.set_item_checked и _apply_done_style()


def main():
    app = QApplication(sys.argv)
    # Принудительно единый стиль, чтобы индикатор чекбокса корректно отрисовывался
    try:
        from PySide6.QtWidgets import QStyleFactory
        app.setStyle(QStyleFactory.create("Fusion"))
    except Exception:
        pass

    db.get_conn()
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
