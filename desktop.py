"""Desktop-Version des Lkw-Kostenkalkulators (PySide6 / Qt).

Starten im Entwicklungsmodus:  .venv/bin/python desktop.py
Als Programm bauen:            ./build_mac.sh
"""

import json
import sys
from pathlib import Path

from PySide6.QtCore import QLocale, QRectF, QSettings, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QDoubleSpinBox, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QMainWindow, QPushButton, QScrollArea, QSizePolicy, QSlider,
    QVBoxLayout, QWidget,
)

from kalkulation import FAHRZEUGE, STANDARD_FAHRZEUG, Eingaben, FahrzeugProfil, berechne, eur

APP_NAME = "Lkw-Kalkulator"

# ------------------------------------------------------------------ Farben
THEMES = {
    "light": dict(
        bg="#f3f5f8", surface="#ffffff", input="#f7f9fb", border="#e1e6ed", track="#edf1f5",
        text="#18212c", muted="#697586", accent="#2f6db5", accent_soft="#a3bfe0",
        ok_bg="#e6f4eb", ok_fg="#1d6a39", warn_bg="#fff3dc", warn_fg="#875800",
        err_bg="#fde7e7", err_fg="#a32727",
    ),
    "dark": dict(
        bg="#12161b", surface="#1b2129", input="#222a33", border="#2c3541", track="#26303b",
        text="#e7ebf0", muted="#97a1ae", accent="#5d95d8", accent_soft="#3c5c84",
        ok_bg="#15301f", ok_fg="#82d49e", warn_bg="#382a0f", warn_fg="#f1c46c",
        err_bg="#3b1919", err_fg="#f29c9c",
    ),
}
THEME = dict(THEMES["light"])


def stylesheet(t: dict) -> str:
    return f"""
    QWidget {{ color: {t['text']}; font-size: 13px; }}
    #Main {{ background: {t['bg']}; }}
    #Sidebar, #SidebarInner {{ background: {t['surface']}; }}
    #Sidebar {{ border-right: 1px solid {t['border']}; }}
    QScrollArea {{ border: 0; background: transparent; }}
    #AppTitle {{ font-size: 17px; font-weight: 700; }}
    #H1 {{ font-size: 22px; font-weight: 700; }}
    #Section {{ color: {t['muted']}; font-size: 11px; font-weight: 700; }}
    #Muted, #KpiTitle, #KpiSub, #Head {{ color: {t['muted']}; }}
    #KpiTitle {{ font-size: 12px; }}
    #KpiSub, #Head, #RowArt {{ font-size: 11px; }}
    #RowArt {{ color: {t['muted']}; }}
    #KpiValue {{ font-size: 25px; font-weight: 650; }}
    #RowValue {{ font-weight: 600; }}
    #Card {{ background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 10px; }}
    #Divider {{ background: {t['border']}; max-height: 1px; min-height: 1px; }}

    QDoubleSpinBox {{
        background: {t['input']}; border: 1px solid {t['border']}; border-radius: 6px;
        padding: 5px 0; min-width: 104px; selection-background-color: {t['accent']};
    }}
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 0px; border: 0; }}
    QDoubleSpinBox:focus {{ border: 1px solid {t['accent']}; }}

    QPushButton#Seg {{
        background: {t['input']}; border: 1px solid {t['border']}; border-radius: 6px;
        padding: 8px 6px; font-weight: 600;
    }}
    QPushButton#Seg:checked {{ background: {t['accent']}; border-color: {t['accent']}; color: #ffffff; }}
    QPushButton#Link {{ background: transparent; border: 0; color: {t['accent']}; padding: 2px 0; text-align: left; }}
    QPushButton#Link:hover {{ text-decoration: underline; }}

    QSlider::groove:horizontal {{ height: 4px; background: {t['track']}; border-radius: 2px; }}
    QSlider::sub-page:horizontal {{ background: {t['accent']}; border-radius: 2px; }}
    QSlider::handle:horizontal {{
        background: {t['surface']}; border: 2px solid {t['accent']};
        width: 12px; height: 12px; margin: -6px 0; border-radius: 8px;
    }}

    #Banner {{ border-radius: 8px; }}
    #Banner[status="ok"] {{ background: {t['ok_bg']}; }}
    #Banner[status="verlaengert"] {{ background: {t['warn_bg']}; }}
    #Banner[status="unzulaessig"] {{ background: {t['err_bg']}; }}
    #Banner[status="ok"] QLabel {{ color: {t['ok_fg']}; }}
    #Banner[status="verlaengert"] QLabel {{ color: {t['warn_fg']}; }}
    #Banner[status="unzulaessig"] QLabel {{ color: {t['err_fg']}; }}
    #BannerTitle {{ font-weight: 700; }}

    QToolTip {{ background: {t['surface']}; color: {t['text']}; border: 1px solid {t['border']}; padding: 4px; }}
    """


def komma(x: float, nk: int = 1) -> str:
    return f"{x:.{nk}f}".replace(".", ",")


# ------------------------------------------------------------------ Bausteine
class Feld(QDoubleSpinBox):
    """Zahlenfeld mit Einheit; Mausrad nur bei Fokus (sonst verstellt Scrollen die Werte)."""

    def __init__(self, minimum, maximum, schritt, nachkomma, einheit, tooltip=""):
        super().__init__()
        self.setRange(minimum, maximum)
        self.setSingleStep(schritt)
        self.setDecimals(nachkomma)
        self.setSuffix(f" {einheit}")
        # Pfeiltasten bleiben technisch aktiv (Breite 0 per Stylesheet): Mit NoButtons schrumpft
        # das Textfeld in Qt 6.12 auf 1 px, sobald ein Stylesheet greift.
        self.lineEdit().setTextMargins(8, 0, 8, 0)
        self.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setToolTip(tooltip)

    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class Regler(QWidget):
    valueChanged = Signal(int)

    def __init__(self, minimum, maximum, schritt, einheit):
        super().__init__()
        self.einheit = einheit
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(minimum, maximum)
        self.slider.setSingleStep(schritt)
        self.slider.setPageStep(schritt)
        self.anzeige = QLabel()
        self.anzeige.setObjectName("RowValue")
        self.anzeige.setMinimumWidth(44)
        self.anzeige.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.slider, 1)
        lay.addWidget(self.anzeige)
        self.slider.valueChanged.connect(self._geaendert)
        self._geaendert(self.slider.value())

    def _geaendert(self, v):
        self.anzeige.setText(f"{v} {self.einheit}")
        self.valueChanged.emit(v)

    def value(self):
        return self.slider.value()

    def setValue(self, v):
        self.slider.setValue(int(v))


class Balken(QWidget):
    def __init__(self):
        super().__init__()
        self.anteil, self.variabel = 0.0, True
        self.setFixedHeight(10)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def setze(self, anteil, variabel):
        self.anteil, self.variabel = anteil, variabel
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        r = QRectF(self.rect())
        rad = r.height() / 2
        p.setBrush(QColor(THEME["track"]))
        p.drawRoundedRect(r, rad, rad)
        if self.anteil > 0:
            breite = max(r.height(), r.width() * self.anteil)
            p.setBrush(QColor(THEME["accent"] if self.variabel else THEME["accent_soft"]))
            p.drawRoundedRect(QRectF(0, 0, breite, r.height()), rad, rad)


class Punkt(QWidget):
    def __init__(self, farbschluessel):
        super().__init__()
        self.schluessel = farbschluessel
        self.setFixedSize(10, 10)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(THEME[self.schluessel]))
        p.drawEllipse(QRectF(self.rect()))


def karte():
    f = QFrame()
    f.setObjectName("Card")
    return f


def label(text="", name=None):
    lbl = QLabel(text)
    if name:
        lbl.setObjectName(name)
    return lbl


class Kpi(QFrame):
    def __init__(self, titel):
        super().__init__()
        self.setObjectName("Card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(4)
        self.titel = label(titel, "KpiTitle")
        self.wert = label("", "KpiValue")
        self.sub = label("", "KpiSub")
        for w in (self.titel, self.wert, self.sub):
            lay.addWidget(w)

    def setze(self, wert, sub="", titel=None):
        self.wert.setText(wert)
        self.sub.setText(sub)
        if titel:
            self.titel.setText(titel)


# ------------------------------------------------------------------ Hauptfenster
FAHRZEUG_FELDER = ("verbrauch", "wartung", "afa", "steuer", "maut")
ALLGEMEINE_FELDER = ("km", "maut_anteil", "diesel", "fahrer", "kmh", "tage", "zuschlag")


def standardwerte(klasse):
    p = FAHRZEUGE[klasse]
    return dict(verbrauch=p.verbrauch_l_100km, wartung=p.wartung_eur_km, afa=p.abschreibung_eur_tag,
                steuer=p.steuer_versicherung_eur_tag, maut=p.maut_eur_km)


class Fenster(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lkw Kosten-Kalkulator")
        self.setMinimumSize(1120, 720)
        self.klasse = STANDARD_FAHRZEUG
        self.klassen_werte = {k: standardwerte(k) for k in FAHRZEUGE}
        self._laedt = False

        root = QWidget()
        root.setObjectName("Main")
        lay = QHBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._baue_seitenleiste())
        lay.addWidget(self._baue_inhalt(), 1)
        self.setCentralWidget(root)

        self._lade_einstellungen()
        self.aktualisiere()

    # ---------------- Seitenleiste
    def _baue_seitenleiste(self):
        self.f = dict(
            km=Feld(1, 2000, 50, 0, "km"),
            diesel=Feld(0.5, 4.0, 0.05, 2, "€/l"),
            fahrer=Feld(0, 1000, 10, 2, "€"),
            kmh=Feld(20, 90, 1, 0, "km/h", "Realistischer Schnitt im Mischverkehr ohne Pausen."),
            tage=Feld(1, 31, 1, 0, "Tage"),
            verbrauch=Feld(5, 50, 0.5, 1, "l"),
            wartung=Feld(0.01, 1.0, 0.01, 2, "€/km"),
            afa=Feld(0, 500, 5, 2, "€"),
            steuer=Feld(0, 200, 1, 2, "€"),
            maut=Feld(0, 1, 0.001, 3, "€/km",
                      "Hängt von Gewichts-, Achs- und CO₂-Klasse ab.\nAktuelle Sätze bei Toll Collect prüfen."),
        )
        self.r = dict(maut_anteil=Regler(0, 100, 5, "%"), zuschlag=Regler(0, 40, 1, "%"))
        for k, v in dict(km=600, diesel=1.80, fahrer=210, kmh=62, tage=21).items():
            self.f[k].setValue(v)
        self.r["maut_anteil"].setValue(80)
        self.r["zuschlag"].setValue(10)

        inner = QWidget()
        inner.setObjectName("SidebarInner")
        v = QVBoxLayout(inner)
        v.setContentsMargins(22, 22, 22, 22)
        v.setSpacing(8)
        v.addWidget(label("🚚  Lkw-Kalkulator", "AppTitle"))
        v.addWidget(label("Kühl-Frischdienst · alle Werte netto", "Muted"))

        # Fahrzeugklasse als Segment-Schalter
        self._abschnitt(v, "FAHRZEUG")
        seg = QHBoxLayout()
        seg.setSpacing(6)
        self.seg_gruppe = QButtonGroup(self)
        self.seg_buttons = {}
        for klasse in FAHRZEUGE:
            b = QPushButton(klasse.split(" (")[0])
            b.setObjectName("Seg")
            b.setCheckable(True)
            b.setToolTip(klasse)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self.seg_gruppe.addButton(b)
            self.seg_buttons[klasse] = b
            seg.addWidget(b)
            b.clicked.connect(lambda _=False, k=klasse: self._wechsle_klasse(k))
        self.seg_buttons[self.klasse].setChecked(True)
        v.addLayout(seg)

        self._abschnitt(v, "TOUR")
        self._formular(v, [("Tagesstrecke", self.f["km"]), ("Mautpflichtig", self.r["maut_anteil"]),
                           ("Ø Geschwindigkeit", self.f["kmh"]), ("Arbeitstage / Monat", self.f["tage"])])

        self._abschnitt(v, "KOSTEN")
        self._formular(v, [("Dieselpreis", self.f["diesel"]), ("Fahrer pro Tag", self.f["fahrer"])])

        self._abschnitt(v, "FAHRZEUGWERTE")
        self._formular(v, [("Verbrauch / 100 km", self.f["verbrauch"]), ("Verschleiß & Reifen", self.f["wartung"]),
                           ("Abschreibung / Tag", self.f["afa"]), ("Steuer & Vers. / Tag", self.f["steuer"]),
                           ("Mautsatz", self.f["maut"])])
        reset = QPushButton("↺  Standardwerte dieser Klasse")
        reset.setObjectName("Link")
        reset.setCursor(Qt.CursorShape.PointingHandCursor)
        reset.clicked.connect(self._zuruecksetzen)
        v.addWidget(reset)

        self._abschnitt(v, "PREIS")
        self._formular(v, [("Gewinn & Wagnis", self.r["zuschlag"])])
        v.addStretch(1)

        for w in self.f.values():
            w.valueChanged.connect(self.aktualisiere)
        for w in self.r.values():
            w.valueChanged.connect(self.aktualisiere)

        scroll = QScrollArea()
        scroll.setObjectName("Sidebar")
        scroll.setWidget(inner)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFixedWidth(340)
        return scroll

    def _abschnitt(self, layout, titel):
        layout.addSpacing(12)
        layout.addWidget(label(titel, "Section"))

    def _formular(self, layout, zeilen):
        g = QGridLayout()
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(8)
        for i, (text, widget) in enumerate(zeilen):
            g.addWidget(label(text), i, 0)
            g.addWidget(widget, i, 1)
        g.setColumnMinimumWidth(0, 150)
        g.setColumnStretch(1, 1)
        layout.addLayout(g)

    # ---------------- Inhalt
    def _baue_inhalt(self):
        w = QWidget()
        w.setObjectName("Main")
        v = QVBoxLayout(w)
        v.setContentsMargins(28, 24, 28, 24)
        v.setSpacing(16)

        kopf = QVBoxLayout()
        kopf.setSpacing(2)
        self.titel = label("", "H1")
        self.untertitel = label("", "Muted")
        kopf.addWidget(self.titel)
        kopf.addWidget(self.untertitel)
        v.addLayout(kopf)

        kpis = QHBoxLayout()
        kpis.setSpacing(12)
        self.k_tag, self.k_km = Kpi("Selbstkosten pro Tag"), Kpi("Selbstkosten pro km")
        self.k_monat, self.k_angebot = Kpi("Monat"), Kpi("Angebotspreis")
        for k in (self.k_tag, self.k_km, self.k_monat, self.k_angebot):
            kpis.addWidget(k, 1)
        v.addLayout(kpis)

        self.banner = QFrame()
        self.banner.setObjectName("Banner")
        b = QVBoxLayout(self.banner)
        b.setContentsMargins(16, 12, 16, 12)
        b.setSpacing(2)
        self.banner_titel = label("", "BannerTitle")
        self.banner_text = label()
        self.banner_text.setWordWrap(True)
        b.addWidget(self.banner_titel)
        b.addWidget(self.banner_text)
        v.addWidget(self.banner)

        v.addWidget(self._baue_aufschluesselung())
        v.addStretch(1)
        return w

    def _baue_aufschluesselung(self):
        k = karte()
        v = QVBoxLayout(k)
        v.setContentsMargins(20, 18, 20, 18)
        v.setSpacing(14)

        kopf = QHBoxLayout()
        kopf.addWidget(label("Kostenaufschlüsselung", "AppTitle"))
        kopf.addStretch(1)
        for schluessel, text in (("accent", "variabel (km-abhängig)"), ("accent_soft", "fix (pro Tag)")):
            kopf.addWidget(Punkt(schluessel))
            kopf.addWidget(label(text, "Muted"))
            kopf.addSpacing(10)
        v.addLayout(kopf)

        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(18)
        self.grid.setVerticalSpacing(12)
        for spalte, (text, ausr) in enumerate((("KOSTENBLOCK", Qt.AlignmentFlag.AlignLeft), ("", None),
                                                ("€ / TAG", Qt.AlignmentFlag.AlignRight),
                                                ("€ / KM", Qt.AlignmentFlag.AlignRight),
                                                ("ANTEIL", Qt.AlignmentFlag.AlignRight))):
            kl = label(text, "Head")
            if ausr:
                kl.setAlignment(ausr)
            self.grid.addWidget(kl, 0, spalte)
        self.grid.setColumnStretch(1, 1)
        self.grid.setColumnMinimumWidth(0, 210)

        rechts = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        self.zeilen = []
        for _ in range(6):
            name_box = QWidget()
            nb = QVBoxLayout(name_box)
            nb.setContentsMargins(0, 0, 0, 0)
            nb.setSpacing(0)
            name, art = label(), label("", "RowArt")
            nb.addWidget(name)
            nb.addWidget(art)
            tag, km, anteil = label("", "RowValue"), label("", "Muted"), label("", "RowValue")
            for x in (tag, km, anteil):
                x.setAlignment(rechts)
                x.setMinimumWidth(70)
            self.zeilen.append(dict(box=name_box, name=name, art=art, balken=Balken(), tag=tag, km=km, anteil=anteil))
        v.addLayout(self.grid)

        trenner = QFrame()
        trenner.setObjectName("Divider")
        v.addWidget(trenner)
        self.fusszeile = label("", "Muted")
        v.addWidget(self.fusszeile)
        return k

    # ---------------- Logik
    def _wechsle_klasse(self, neue):
        if neue == self.klasse:
            return
        self.klassen_werte[self.klasse] = {k: self.f[k].value() for k in FAHRZEUG_FELDER}
        self.klasse = neue
        self._setze_fahrzeugfelder(self.klassen_werte[neue])

    def _zuruecksetzen(self):
        self.klassen_werte[self.klasse] = standardwerte(self.klasse)
        self._setze_fahrzeugfelder(self.klassen_werte[self.klasse])

    def _setze_fahrzeugfelder(self, werte):
        self._laedt = True
        for k in FAHRZEUG_FELDER:
            self.f[k].setValue(werte[k])
        self._laedt = False
        self.aktualisiere()

    def aktualisiere(self, *_):
        if self._laedt:
            return
        f, r = self.f, self.r
        basis = FAHRZEUGE[self.klasse]
        e = Eingaben(
            km_tag=f["km"].value(), maut_anteil=r["maut_anteil"].value() / 100,
            dieselpreis_eur_l=f["diesel"].value(), fahrerkosten_tag=f["fahrer"].value(),
            fahrzeug=FahrzeugProfil(f["verbrauch"].value(), f["wartung"].value(), f["afa"].value(),
                                    f["steuer"].value(), f["maut"].value(), basis.zuladung_t),
            durchschnitt_kmh=f["kmh"].value(), arbeitstage_monat=int(f["tage"].value()),
            zuschlag=r["zuschlag"].value() / 100,
        )
        erg = berechne(e)
        km = int(e.km_tag)

        self.titel.setText(self.klasse)
        self.untertitel.setText(f"{km} km pro Tag · davon {erg.maut_km:.0f} km mautpflichtig")
        self.k_tag.setze(eur(erg.gesamt_tag), f"variabel {eur(erg.variabel_tag, 0)} · fix {eur(erg.fix_tag, 0)}")
        self.k_km.setze(eur(erg.pro_km) + "/km", "Kostenuntergrenze je Kilometer")
        self.k_monat.setze(eur(erg.gesamt_monat, 0), f"bei {e.arbeitstage_monat} Arbeitstagen",
                           f"Monat")
        self.k_angebot.setze(eur(erg.angebot_tag), f"{eur(erg.angebot_km)}/km · +{r['zuschlag'].value()} % Zuschlag")

        lz = erg.lenkzeit
        titel = {"ok": "✓  Lenkzeit im Rahmen", "verlaengert": "⚠  Verlängerte Lenkzeit nötig",
                 "unzulaessig": "✕  Tour so nicht zulässig"}[lz.status]
        self.banner_titel.setText(f"{titel}  ·  ≈ {komma(lz.stunden)} h am Steuer")
        self.banner_text.setText(
            f"{lz.hinweis} {lz.pausen} × 45 min Pause, Tourdauer ≈ {komma(lz.tourdauer_h)} h "
            f"ohne Be- und Entladen (bei Ø {int(e.durchschnitt_kmh)} km/h).")
        self.banner.setProperty("status", lz.status)
        self.banner.style().unpolish(self.banner)
        self.banner.style().polish(self.banner)
        for kind in self.banner.findChildren(QLabel):
            kind.style().unpolish(kind)
            kind.style().polish(kind)

        groesster = max(b.betrag for b in erg.bloecke) or 1
        for i, (b, z) in enumerate(zip(sorted(erg.bloecke, key=lambda x: -x.betrag), self.zeilen), start=1):
            z["name"].setText(b.name)
            z["art"].setText("variabel · km-abhängig" if b.variabel else "fix · pro Tag")
            z["balken"].setze(b.betrag / groesster, b.variabel)
            z["tag"].setText(eur(b.betrag))
            z["km"].setText(eur(b.betrag / e.km_tag, 3))
            z["anteil"].setText(f"{komma(b.betrag / erg.gesamt_tag * 100)} %")
            for spalte, schluessel in enumerate(("box", "balken", "tag", "km", "anteil")):
                self.grid.addWidget(z[schluessel], i, spalte)
        self.fusszeile.setText(
            f"Summe {eur(erg.gesamt_tag)} pro Tag  ·  Mautsatz {komma(e.fahrzeug.maut_eur_km, 3)} €/km  ·  "
            f"Verbrauch {komma(e.fahrzeug.verbrauch_l_100km)} l/100 km bei {eur(e.dieselpreis_eur_l)}/l")

    # ---------------- Einstellungen merken
    def _lade_einstellungen(self):
        try:
            daten = json.loads(QSettings(APP_NAME, APP_NAME).value("zustand", "") or "{}")
        except (ValueError, TypeError):
            return
        self._laedt = True
        try:
            for k, werte in daten.get("klassen", {}).items():
                if k in self.klassen_werte:
                    self.klassen_werte[k].update({x: float(werte[x]) for x in FAHRZEUG_FELDER if x in werte})
            for k, wert in daten.get("allgemein", {}).items():
                (self.f.get(k) or self.r.get(k)).setValue(wert) if (k in self.f or k in self.r) else None
            if daten.get("klasse") in FAHRZEUGE:
                self.klasse = daten["klasse"]
                self.seg_buttons[self.klasse].setChecked(True)
        except (ValueError, TypeError, AttributeError):
            pass
        finally:
            self._laedt = False
        self._setze_fahrzeugfelder(self.klassen_werte[self.klasse])

    def closeEvent(self, event):
        self.klassen_werte[self.klasse] = {k: self.f[k].value() for k in FAHRZEUG_FELDER}
        allgemein = {k: (self.f[k] if k in self.f else self.r[k]).value() for k in ALLGEMEINE_FELDER}
        QSettings(APP_NAME, APP_NAME).setValue(
            "zustand", json.dumps(dict(klasse=self.klasse, klassen=self.klassen_werte, allgemein=allgemein)))
        super().closeEvent(event)

    # ---------------- Hell/Dunkel
    def wende_theme_an(self):
        dunkel = QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
        THEME.clear()
        THEME.update(THEMES["dark" if dunkel else "light"])
        QApplication.instance().setStyleSheet(stylesheet(THEME))
        for w in self.findChildren(QWidget):
            if isinstance(w, (Balken, Punkt)):
                w.update()


def ressource(name):
    basis = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return str(basis / name)


def main():
    QLocale.setDefault(QLocale(QLocale.Language.German, QLocale.Country.Germany))
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # einheitlich auf macOS und Windows; der macOS-Stil verkleinert gestylte Zahlenfelder
    app.setApplicationName(APP_NAME)
    icon = Path(ressource("assets/icon.png"))
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))
    fenster = Fenster()
    fenster.wende_theme_an()
    QGuiApplication.styleHints().colorSchemeChanged.connect(lambda _: fenster.wende_theme_an())
    fenster.resize(1240, 800)
    fenster.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
