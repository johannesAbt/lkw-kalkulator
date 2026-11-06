import pytest

from kalkulation import FAHRZEUGE, STANDARD_FAHRZEUG, Eingaben, berechne, bewerte_lenkzeit, eur


def referenz(**aenderungen):
    werte = dict(km_tag=600, maut_anteil=0.8, dieselpreis_eur_l=1.80,
                 fahrerkosten_tag=210, fahrzeug=FAHRZEUGE[STANDARD_FAHRZEUG])
    werte.update(aenderungen)
    return Eingaben(**werte)


def test_referenzrechnung_18_tonner():
    r = berechne(referenz())
    betraege = {b.name: b.betrag for b in r.bloecke}
    assert betraege["Kraftstoff (Diesel + Kühlung)"] == pytest.approx(280.80)
    assert betraege["Lkw-Maut (Deutschland)"] == pytest.approx(114.24)
    assert betraege["Verschleiß, Wartung & Reifen"] == pytest.approx(72.00)
    assert r.gesamt_tag == pytest.approx(766.04)
    assert r.pro_km == pytest.approx(1.2767, abs=1e-4)
    assert r.variabel_tag + r.fix_tag == pytest.approx(r.gesamt_tag)


def test_angebot_und_monat():
    r = berechne(referenz(zuschlag=0.10, arbeitstage_monat=21))
    assert r.angebot_tag == pytest.approx(766.04 * 1.10)
    assert r.gesamt_monat == pytest.approx(766.04 * 21)


@pytest.mark.parametrize("km, status", [(500, "ok"), (600, "verlaengert"), (700, "unzulaessig")])
def test_lenkzeit_status(km, status):
    assert bewerte_lenkzeit(km, 62).status == status


def test_pausen():
    assert bewerte_lenkzeit(279, 62).pausen == 0   # 4,5 h
    assert bewerte_lenkzeit(600, 62).pausen == 2   # 9,7 h


def test_ungueltige_eingaben():
    with pytest.raises(ValueError):
        berechne(referenz(km_tag=0))
    with pytest.raises(ValueError):
        berechne(referenz(maut_anteil=1.5))


def test_eur_format():
    assert eur(1234.5) == "1.234,50 €"
