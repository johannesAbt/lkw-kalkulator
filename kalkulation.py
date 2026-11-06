"""Rechenkern des Lkw-Kostenkalkulators.

Bewusst ohne jede Oberflächen-Abhängigkeit: Dieses Modul kann unverändert von
der Streamlit-App, einer Desktop-GUI (Qt, Flet, Tkinter) oder Tests genutzt
werden. Alle Beträge sind netto in Euro.
"""

from dataclasses import dataclass
from math import ceil

# Lenkzeitregeln nach VO (EG) 561/2006
LENKZEIT_TAG_REGEL_H = 9.0      # tägliche Lenkzeit
LENKZEIT_TAG_MAX_H = 10.0       # Verlängerung, höchstens 2x pro Woche
LENKZEIT_BLOCK_H = 4.5          # danach mind. 45 min Pause
PAUSE_H = 0.75


@dataclass(frozen=True)
class FahrzeugProfil:
    verbrauch_l_100km: float            # inkl. Kühlaggregat
    wartung_eur_km: float               # Verschleiß, Wartung, Reifen
    abschreibung_eur_tag: float         # kalkulatorische Abschreibung
    steuer_versicherung_eur_tag: float
    maut_eur_km: float                  # Mautsatz Deutschland (Toll Collect prüfen!)
    zuladung_t: float


FAHRZEUGE: dict[str, FahrzeugProfil] = {
    "12-Tonner (ca. 4 t Zuladung)": FahrzeugProfil(21.0, 0.10, 40.0, 14.0, 0.177, 4.0),
    "18-Tonner (ca. 9 t Zuladung)": FahrzeugProfil(26.0, 0.12, 71.0, 18.0, 0.238, 9.0),
}
STANDARD_FAHRZEUG = "18-Tonner (ca. 9 t Zuladung)"


@dataclass(frozen=True)
class Eingaben:
    km_tag: float
    maut_anteil: float              # 0.0 bis 1.0
    dieselpreis_eur_l: float
    fahrerkosten_tag: float
    fahrzeug: FahrzeugProfil
    durchschnitt_kmh: float = 62.0  # Mischverkehr inkl. Stadt/Landstraße
    arbeitstage_monat: int = 21
    zuschlag: float = 0.10          # Gewinn & Wagnis auf die Selbstkosten


@dataclass(frozen=True)
class Kostenblock:
    name: str
    betrag: float
    variabel: bool                  # True = km-abhängig, False = fix pro Tag


@dataclass(frozen=True)
class Lenkzeit:
    stunden: float
    pausen: int
    tourdauer_h: float              # Lenkzeit + vorgeschriebene Pausen
    status: str                     # "ok" | "verlaengert" | "unzulaessig"
    hinweis: str


@dataclass(frozen=True)
class Ergebnis:
    bloecke: list[Kostenblock]
    gesamt_tag: float
    pro_km: float
    maut_km: float
    variabel_tag: float
    fix_tag: float
    gesamt_monat: float
    angebot_tag: float
    angebot_km: float
    lenkzeit: Lenkzeit


def bewerte_lenkzeit(km: float, durchschnitt_kmh: float) -> Lenkzeit:
    if durchschnitt_kmh <= 0:
        raise ValueError("Durchschnittsgeschwindigkeit muss größer als 0 sein.")
    h = km / durchschnitt_kmh
    pausen = max(0, ceil(h / LENKZEIT_BLOCK_H) - 1)
    dauer = h + pausen * PAUSE_H

    if h <= LENKZEIT_TAG_REGEL_H:
        status, hinweis = "ok", "Innerhalb der regulären Tageslenkzeit von 9 Stunden."
    elif h <= LENKZEIT_TAG_MAX_H:
        status, hinweis = ("verlaengert",
                           "Nur mit verlängerter Lenkzeit (10 h) möglich, "
                           "das ist höchstens zweimal pro Woche erlaubt.")
    else:
        status, hinweis = ("unzulaessig",
                           "Überschreitet die maximale Tageslenkzeit von 10 Stunden. "
                           "Tour teilen oder Doppelbesatzung einplanen.")
    return Lenkzeit(h, pausen, dauer, status, hinweis)


def berechne(e: Eingaben) -> Ergebnis:
    if e.km_tag <= 0:
        raise ValueError("Die Tagesstrecke muss größer als 0 km sein.")
    if not 0.0 <= e.maut_anteil <= 1.0:
        raise ValueError("Der Mautanteil muss zwischen 0 und 1 liegen.")

    f = e.fahrzeug
    maut_km = e.km_tag * e.maut_anteil
    bloecke = [
        Kostenblock("Kraftstoff (Diesel + Kühlung)",
                    e.km_tag / 100.0 * f.verbrauch_l_100km * e.dieselpreis_eur_l, True),
        Kostenblock("Lkw-Maut (Deutschland)", maut_km * f.maut_eur_km, True),
        Kostenblock("Verschleiß, Wartung & Reifen", e.km_tag * f.wartung_eur_km, True),
        Kostenblock("Fahrer (Personalkosten)", e.fahrerkosten_tag, False),
        Kostenblock("Abschreibung", f.abschreibung_eur_tag, False),
        Kostenblock("Steuer & Versicherung", f.steuer_versicherung_eur_tag, False),
    ]
    variabel = sum(b.betrag for b in bloecke if b.variabel)
    fix = sum(b.betrag for b in bloecke if not b.variabel)
    gesamt = variabel + fix
    angebot = gesamt * (1.0 + e.zuschlag)

    return Ergebnis(
        bloecke=bloecke,
        gesamt_tag=gesamt,
        pro_km=gesamt / e.km_tag,
        maut_km=maut_km,
        variabel_tag=variabel,
        fix_tag=fix,
        gesamt_monat=gesamt * e.arbeitstage_monat,
        angebot_tag=angebot,
        angebot_km=angebot / e.km_tag,
        lenkzeit=bewerte_lenkzeit(e.km_tag, e.durchschnitt_kmh),
    )


def eur(betrag: float, nachkomma: int = 2) -> str:
    """Deutsches Zahlenformat: 1.234,56 €"""
    s = f"{betrag:,.{nachkomma}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".") + " €"
