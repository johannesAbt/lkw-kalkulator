"""Zeichnet das App-Icon (1024×1024 PNG) mit Qt – ohne externe Grafiken."""

import sys

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QLinearGradient, QPainter, QPen

ziel = sys.argv[1] if len(sys.argv) > 1 else "assets/icon.png"
app = QGuiApplication(sys.argv)
img = QImage(1024, 1024, QImage.Format.Format_ARGB32)
img.fill(Qt.GlobalColor.transparent)
p = QPainter(img)
p.setRenderHint(QPainter.RenderHint.Antialiasing)

# Hintergrund (macOS-Raster: 824 px Fläche, 100 px Rand)
grad = QLinearGradient(0, 100, 0, 924)
grad.setColorAt(0, QColor("#3b80cf"))
grad.setColorAt(1, QColor("#1d4c8c"))
p.setPen(Qt.PenStyle.NoPen)
p.setBrush(grad)
p.drawRoundedRect(QRectF(100, 100, 824, 824), 185, 185)

weiss = QColor("#ffffff")
p.setBrush(weiss)
p.drawRoundedRect(QRectF(190, 340, 430, 310), 28, 28)          # Kühlkoffer
p.drawRoundedRect(QRectF(636, 430, 200, 220), 34, 34)          # Fahrerhaus
p.drawRect(QRectF(636, 560, 200, 90))
p.setBrush(QColor("#2a63aa"))
p.drawRoundedRect(QRectF(672, 462, 128, 82), 16, 16)           # Fenster

for x in (300, 520, 750):                                       # Räder
    p.setBrush(QColor("#163b6d"))
    p.drawEllipse(QPointF(x, 670), 62, 62)
    p.setBrush(weiss)
    p.drawEllipse(QPointF(x, 670), 24, 24)

p.setPen(QPen(QColor("#2f6db5"), 1))                            # Schneeflocke
f = QFont()
f.setPixelSize(190)
f.setBold(True)
p.setFont(f)
p.drawText(QRectF(190, 340, 430, 310), Qt.AlignmentFlag.AlignCenter, "❄")
p.end()
img.save(ziel)
print("Icon gespeichert:", ziel)
