import sys
from typing import Dict, Set

from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QFont, QAction, QPixmap, QIcon, QColor, QBrush, QPainter, QLinearGradient, QPainterPath
from PySide6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QDialog, QDialogButtonBox, QLineEdit, QTextEdit, QScrollArea, QCheckBox, QFrame,
    QInputDialog, QMessageBox, QToolBar, QComboBox, QTreeWidget, QTreeWidgetItem, QStyleFactory
)

import db


# ---------- Вспомогательное: иконка приложения ----------
def make_app_icon(size: int = 256) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)

    p = QPainter(pm)
    # В некоторых версиях нет HighQualityAntialiasing — используем набор флагов ниже.
    try:
        p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform, True)
    except Exception:
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)

    # фон с градиентом
    grad = QLinearGradient(0, 0, 0, size)
    grad.setColorAt(0.0, QColor("#22c55e"))
    grad.setColorAt(1.0, QColor("#16a34a"))
    p.setBrush(grad)
    p.setPen(Qt.NoPen)
    radius = int(size * 0.22)
    p.drawRoundedRect(0, 0, size, size, radius, radius)

    # галочка
    path = QPainterPath()
    path.moveTo(size * 0.26, size * 0.55)
    path.lineTo(size * 0.45, size * 0.74)
    path.lineTo(size * 0.78, size * 0.36)

    from PySide6.QtGui import QPen
    pen = QPen(QColor("#ffffff"), max(6, int(size * 0.08)), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawPath(path)

    p.end()
    return QIcon(pm)



# ---- подтверждение удаления (кнопки: «Нет» слева, «Да» справа) ----
def confirm_delete(parent, title: str, text: str) -> bool:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(QMessageBox.Warning)
    btn_no = box.addButton("Нет", QMessageBox.NoRole)
    btn_yes = box.addButton("Да", QMessageBox.YesRole)
    box.setDefaultButton(btn_yes)
    box.exec()
    return box.clickedButton() is btn_yes


# ---------- Диалог создания списка ----------
class NewListDialog(QDialog):
    COLORS = ["#ffffff", "#fff7cc", "#e7f5ff", "#ffe7f0", "#e8ffe7", "#fde68a", "#bfdbfe", "#fecaca", "#bbf7d0"]

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
        self._populate_color_combo()

        items_lbl = QLabel("Пункты / Текст заметки")
        self.items_edit = QTextEdit()
        self.items_edit.setPlaceholderText("Для списка — один пункт в строке.\nДля текстовой заметки — просто текст.")

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addWidget(name_lbl); lay.addWidget(self.title_edit)
        lay.addWidget(type_lbl); lay.addWidget(self.type_combo)
        lay.addWidget(color_lbl); lay.addWidget(self.color_combo)
        lay.addWidget(items_lbl); lay.addWidget(self.items_edit)
        lay.addWidget(btns)

        self._apply_dialog_styles()

    def _populate_color_combo(self):
        for hexc in self.COLORS:
            pm = QPixmap(18, 18); pm.fill(QColor(hexc))
            self.color_combo.addItem(QIcon(pm), "", hexc)
        self.color_combo.setCurrentIndex(0)

    def _apply_dialog_styles(self):
        self.setStyleSheet("""
            QDialog { background:#ffffff; color:#111827; }
            QLabel { color:#111827; }
            QLineEdit, QTextEdit, QComboBox {
                background:#ffffff; color:#111827;
                border:1px solid #e5e7eb; border-radius:10px; padding:8px 10px;
            }
            QComboBox QAbstractItemView { background:#ffffff; color:#111827; selection-background-color:#eef2ff; }
            QDialogButtonBox QPushButton {
                background: qlineargradient(x1:0,y1:0, x2:0, y2:1, stop:0 #4f46e5, stop:1 #4338ca);
                border:0; color:#fff; padding:8px 12px; border-radius:10px; font-weight:600;
            }
        """)

    def get_data(self):
        title = self.title_edit.text().strip()
        color = self.color_combo.currentData() or "#ffffff"
        is_checklist = self.type_combo.currentIndex() == 0
        raw_text = self.items_edit.toPlainText().strip()
        raw_lines = [s for s in raw_text.splitlines()]
        items = [s.strip() for s in raw_lines if s.strip()] if is_checklist else []
        return title, items, color, is_checklist, raw_text

    def accept(self):
        title, items, color, is_checklist, _raw = self.get_data()
        if not title:
            QMessageBox.warning(self, "Пустое название", "Введите название.")
            return
        if is_checklist and not items:
            QMessageBox.warning(self, "Пустой список", "Добавьте хотя бы один пункт, либо выберите тип «Заметка (текст)».")
            return
        super().accept()


# ---------- Строка пункта списка (ListWindow) ----------
class ItemRow(QFrame):
    toggled_for_action = Signal(int, bool)  # (item_id, selected_for_action)

    def __init__(self, item: dict, on_done_toggle, parent=None):
        super().__init__(parent)
        self.setObjectName("itemRow")
        self.item_id = item["id"]
        self._selected = False
        self._on_done_toggle = on_done_toggle

        lay = QHBoxLayout(self); lay.setContentsMargins(10, 8, 10, 8); lay.setSpacing(10)
        self.done_cb = QCheckBox(item["text"]); self.done_cb.setObjectName("todo")
        self.done_cb.setChecked(bool(item["checked"]))
        self.done_cb.stateChanged.connect(self._on_done_state_changed)
        lay.addWidget(self.done_cb, 1)

        self._apply_done_style(self.done_cb.isChecked())
        if self.done_cb.isChecked():
            self._selected = True
        self._apply_selected_style()

    def mousePressEvent(self, e):
        self._selected = not self._selected
        self._apply_selected_style()
        self.toggled_for_action.emit(self.item_id, self._selected)
        super().mousePressEvent(e)

    def _on_done_state_changed(self, state: int):
        done = (state == Qt.Checked)
        self._on_done_toggle(self.item_id, done)
        self._apply_done_style(done)
        self._selected = done
        self._apply_selected_style()
        self.toggled_for_action.emit(self.item_id, self._selected)

    def _apply_done_style(self, checked: bool):
        f = self.done_cb.font(); f.setStrikeOut(checked); self.done_cb.setFont(f)
        self.done_cb.setStyleSheet("QCheckBox#todo { color: %s; }" % ("#6b7280" if checked else "#1f2937"))

    def _apply_selected_style(self):
        self.setProperty("selected", True if self._selected else False)
        self.style().unpolish(self); self.style().polish(self)

    def set_selected(self, on: bool):
        self._selected = on; self._apply_selected_style()

    def is_selected(self) -> bool:
        return self._selected

    def set_done(self, checked: bool):
        self.done_cb.blockSignals(True); self.done_cb.setChecked(checked); self.done_cb.blockSignals(False)
        self._apply_done_style(checked)


# ---------- Окно со списком задач / текстовой заметкой ----------
class ListWindow(QWidget):
    def __init__(self, list_id: int, home: QWidget):
        super().__init__()
        self.setWindowTitle("Список задач")
        self.resize(450, 640)

        self.list_id = list_id
        self.home = home
        self._exit_on_close = True
        self.selected_items: Set[int] = set()
        self.rows: Dict[int, ItemRow] = {}
        self.text_view: QTextEdit | None = None  # для текстовых заметок

        root = QVBoxLayout(self); root.setContentsMargins(14, 14, 14, 14); root.setSpacing(10)

        toolbar = QToolBar()
        self.back_action = QAction("⬅ Назад", self); self.back_action.triggered.connect(self._go_back)
        self.delete_action = QAction("🗑 Удалить выбранные", self); self.delete_action.triggered.connect(self._delete_selected)
        self.clear_checks_action = QAction("✔ Снять галочки", self); self.clear_checks_action.triggered.connect(self._uncheck_done)
        toolbar.addAction(self.back_action); toolbar.addSeparator(); toolbar.addAction(self.delete_action); toolbar.addAction(self.clear_checks_action)

        self.title_lbl = QLabel(""); f = QFont(); f.setPointSize(13); f.setBold(True); self.title_lbl.setFont(f)

        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.items_host = QWidget()
        self.items_layout = QVBoxLayout(self.items_host); self.items_layout.setContentsMargins(6,6,6,6); self.items_layout.setSpacing(8); self.items_layout.addStretch()
        self.scroll.setWidget(self.items_host)

        self.add_btn = QPushButton("＋ Добавить пункт"); self.add_btn.clicked.connect(self._add_item)

        root.addWidget(toolbar); root.addWidget(self.title_lbl); root.addWidget(self.scroll, 1); root.addWidget(self.add_btn)

        self._apply_styles()
        self._load_data()

    def closeEvent(self, event):
        if self._exit_on_close: QApplication.quit()
        else: event.accept()

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget { background: qlineargradient(x1:0,y1:0, x2:0, y2:1, stop:0 #f6f8fb, stop:1 #eaeef5);
                      font-family: 'Segoe UI','Roboto',sans-serif; font-size:12.5pt; color:#1f2937; }
            QToolBar { background:#f8fafc; border:1px solid #e5e7eb; border-radius:12px; padding:6px; }
            QToolBar QToolButton { padding:8px 12px; border-radius:10px; background:#ffffff; border:1px solid #e5e7eb; margin-right:8px; }
            QPushButton { background: qlineargradient(x1:0,y1:0, x2:0, y2:1, stop:0 #4f46e5, stop:1 #4338ca);
                          border:0; color:#fff; padding:10px 14px; border-radius:14px; font-weight:600; }
            QFrame#itemRow { background:#ffffff; border:1px solid #e5e7eb; border-radius:12px; }
            QFrame#itemRow[selected="true"] { background:#22c55e; border:1px solid #16a34a; color:white; }
            QFrame#itemRow[selected="true"] QCheckBox { color: white; }
            QCheckBox#todo::indicator { width: 22px; height: 22px; margin-right: 10px; border-radius: 6px; border: 1px solid #94a3b8; background: #ffffff; }
            QCheckBox#todo::indicator:checked { background: #22c55e; border: 1px solid #16a34a; }
            QCheckBox#todo::indicator:unchecked { background: #ffffff; }
            QTextEdit#noteViewer { background:#ffffff; border:1px solid #e5e7eb; border-radius:12px; padding:12px; }
        """)

    def _selected_ids(self) -> Set[int]:
        if self.selected_items:
            return set(self.selected_items)
        return {iid for iid, row in self.rows.items() if row.done_cb.isChecked()}

    def _load_data(self):
        lists = db.get_lists(include_archived=True, include_deleted=False)
        current = next((l for l in lists if l["id"] == self.list_id), None)
        kind = (current or {}).get("kind", "checklist")
        self.title_lbl.setText(current["title"] if current else "Список")

        # очистка виджетов
        while self.items_layout.count() > 1:
            it = self.items_layout.takeAt(0); w = it.widget()
            if w: w.deleteLater()
        self.rows.clear(); self.selected_items.clear()

        # Режим «текст»
        if kind == "text":
            self.delete_action.setVisible(False)
            self.clear_checks_action.setVisible(False)
            self.add_btn.setVisible(False)

            self.text_view = QTextEdit()
            self.text_view.setObjectName("noteViewer")
            self.text_view.setReadOnly(True)
            self.text_view.setPlainText(current.get("note_text") or "")
            self.items_layout.insertWidget(self.items_layout.count() - 1, self.text_view)
            return

        # Режим «чеклист»
        self.delete_action.setVisible(True)
        self.clear_checks_action.setVisible(True)
        self.add_btn.setVisible(True)
        self.text_view = None

        items = db.get_items(self.list_id)
        if not items:
            hint = QLabel("Пока нет пунктов. Нажмите «Добавить пункт»."); hint.setStyleSheet("color:#6b7280;")
            self.items_layout.insertWidget(0, hint); return

        def on_done_toggle(item_id: int, done: bool):
            db.set_item_checked(item_id, done)

        for it in items:
            row = ItemRow(it, on_done_toggle)
            row.toggled_for_action.connect(self._on_row_toggle)
            self.items_layout.insertWidget(self.items_layout.count() - 1, row)
            self.rows[it["id"]] = row
            if row.is_selected(): self.selected_items.add(it["id"])

    def _on_row_toggle(self, item_id: int, selected: bool):
        if selected: self.selected_items.add(item_id)
        else: self.selected_items.discard(item_id)

    def _uncheck_done(self):
        changed = False
        for item_id, row in self.rows.items():
            if row.done_cb.isChecked():
                db.set_item_checked(item_id, False)
                row.set_done(False)
                changed = True
            if row.is_selected():
                row.set_selected(False)
        self.selected_items.clear()
        if changed: self._load_data()

    def _delete_selected(self):
        ids = self._selected_ids()
        if not ids:
            QMessageBox.information(self, "Нет выбора", "Отметьте строки (позеленеют) или поставьте галочки.")
            return
        if not confirm_delete(self, "Удалить", f"Удалить выбранные ({len(ids)}) пункты?"):
            return
        conn = db.get_conn()
        qmarks = ",".join(["?"] * len(ids))
        conn.execute(f"DELETE FROM items WHERE id IN ({qmarks})", list(ids))
        conn.commit()
        self._load_data()

    def _add_item(self):
        text, ok = QInputDialog.getText(self, "Новый пункт", "Текст пункта:")
        if not ok or not text.strip(): return
        db.add_item(self.list_id, text.strip())
        self._load_data()

    def _go_back(self):
        self._exit_on_close = False
        self.home.show()
        self.close()


# ---------- Стартовое окно ----------
class HomeWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Checklist Notes")
        self.setWindowIcon(make_app_icon())
        self.resize(450, 640)

        self.selected_lists: Set[int] = set()

        root = QVBoxLayout(self); root.setContentsMargins(14, 14, 14, 14); root.setSpacing(10)

        toolbar = QToolBar()
        self.search_action = QAction("🔍", self); self.search_action.triggered.connect(self._toggle_search)
        self.pin_action = QAction("📌", self); self.pin_action.triggered.connect(self._pin_selected)
        self.delete_action = QAction("🗑️", self); self.delete_action.triggered.connect(self._delete_selected)
        self.new_action = QAction("＋", self); self.new_action.triggered.connect(self._new_list)
        toolbar.addAction(self.search_action); toolbar.addAction(self.pin_action); toolbar.addAction(self.delete_action); toolbar.addSeparator(); toolbar.addAction(self.new_action)

        self.search_edit = QLineEdit(); self.search_edit.setPlaceholderText("Поиск по названию, пунктам и тексту...")
        self.search_edit.textChanged.connect(self._reload_table); self.search_edit.setVisible(False)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["", "Список"])
        self.tree.setColumnWidth(0, 36)
        self.tree.setRootIsDecorated(False)
        self.tree.itemChanged.connect(self._on_item_changed)
        self.tree.itemClicked.connect(self._on_item_clicked)

        root.addWidget(toolbar); root.addWidget(self.search_edit); root.addWidget(self.tree, 1)

        self._apply_styles()
        self._reload_table()

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget { background: qlineargradient(x1:0,y1:0, x2:0, y2:1, stop:0 #f6f8fb, stop:1 #eaeef5);
                      font-family: 'Segoe UI','Roboto',sans-serif; font-size:12.5pt; color:#1f2937; }
            QToolBar { background:#f8fafc; border:1px solid #e5e7eb; border-radius:12px; padding:6px; }
            QToolBar QToolButton { padding:8px 12px; border-radius:10px; background:#ffffff; border:1px solid #e5e7eb; margin-right:8px; }
            QTreeWidget { background:#ffffff; border:1px solid #e5e7eb; border-radius:12px; }
            QLineEdit { border: 1px solid #e5e7eb; border-radius: 12px; padding: 8px 10px; background:#f9fafb; }
            QTreeView::indicator { width: 18px; height: 18px; border-radius: 4px; border: 1px solid #94a3b8; background: #ffffff; }
            QTreeView::indicator:checked { background: #4f46e5; border: 1px solid #4338ca; }
            QTreeView::indicator:unchecked { background: #ffffff; }
        """)

    def _toggle_search(self):
        self.search_edit.setVisible(not self.search_edit.isVisible())
        if self.search_edit.isVisible(): self.search_edit.setFocus()

    def _new_list(self):
        dlg = NewListDialog(self)
        if dlg.exec():
            title, items, color, is_checklist, raw_text = dlg.get_data()
            kind = "checklist" if is_checklist else "text"
            list_id = db.create_list(title, items, color=color, pinned=False, kind=kind, note_text=(None if is_checklist else raw_text))
            self._reload_table()
            # сразу открыть только что созданную заметку
            self._open_list(list_id)

    def _reload_table(self):
        self.tree.blockSignals(True); self.tree.clear()
        q = self.search_edit.text().strip() or None
        lists = db.get_lists(include_archived=False, include_deleted=False, query=q)
        for row in lists:
            item = QTreeWidgetItem()
            item.setData(0, Qt.UserRole, row["id"])
            item.setCheckState(0, Qt.Unchecked)
            # Показываем тип
            marker = "📝 " if row.get("kind") == "text" else ""
            item.setText(1, f"{marker}{row['title']}")
            self._apply_item_color(item, row.get("color") or "#ffffff")
            self.tree.addTopLevelItem(item)
        self.tree.blockSignals(False); self.selected_lists.clear()

    def _apply_item_color(self, item: QTreeWidgetItem, hexc: str):
        col = QColor(hexc); item.setBackground(1, QBrush(col))
        r, g, b = col.red(), col.green(), col.blue()
        luma = 0.2126*r + 0.7152*g + 0.0722*b
        text_col = QColor("#111827") if luma > 160 else QColor("#ffffff")
        item.setForeground(1, QBrush(text_col))

    def _on_item_changed(self, item: QTreeWidgetItem, col: int):
        if col != 0: return
        list_id = item.data(0, Qt.UserRole)
        if item.checkState(0) == Qt.Checked: self.selected_lists.add(list_id)
        else: self.selected_lists.discard(list_id)

    def _on_item_clicked(self, item: QTreeWidgetItem, col: int):
        if col == 1:
            list_id = item.data(0, Qt.UserRole)
            self._open_list(list_id)

    def _open_list(self, list_id: int):
        self.list_win = ListWindow(list_id, home=self)
        self.list_win.setWindowIcon(make_app_icon())
        self.list_win.show()
        self.hide()

    def _pin_selected(self):
        if not self.selected_lists:
            QMessageBox.information(self, "Нет выбора", "Отметьте списки чекбоксами слева."); return
        for lid in list(self.selected_lists): db.set_pinned(lid, True)
        self._reload_table()

    def _delete_selected(self):
        if not self.selected_lists:
            QMessageBox.information(self, "Нет выбора", "Отметьте списки чекбоксами слева."); return
        if not confirm_delete(self, "Удалить", f"Удалить выбранные ({len(self.selected_lists)}) списки?"): return
        for lid in list(self.selected_lists): db.soft_delete(lid)
        self._reload_table()


def main():
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    app.setWindowIcon(make_app_icon())
    db.get_conn()
    w = HomeWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
