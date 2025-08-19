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
    p.setPen(QPen(QColor("#ffffff"), max(6, int(size*0.08)), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)); p.setBrush(Qt.NoBrush)
    p.drawPath(path); p.end(); return pm

if __name__ == "__main__":
    app = QApplication([])
    pm = make_app_icon(256)
    pm.save("app.ico", "ICO")
    print("Saved app.ico")
