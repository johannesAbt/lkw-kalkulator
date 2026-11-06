import altair as alt
import pandas as pd
import streamlit as st

from kalkulation import FAHRZEUGE, STANDARD_FAHRZEUG, Eingaben, FahrzeugProfil, berechne, eur

st.set_page_config(page_title="Lkw Kosten-Kalkulator", page_icon="🚚", layout="wide")
st.title("🚚 Lkw Kosten-Kalkulator (Kühl-Frischdienst)")

# ---------------------------------------------------------------- Eingaben
sb = st.sidebar
sb.header("🔧 Kalkulations-Parameter")
klasse = sb.selectbox("Fahrzeugklasse", list(FAHRZEUGE), index=list(FAHRZEUGE).index(STANDARD_FAHRZEUG))
p = FAHRZEUGE[klasse]

km = sb.number_input("Tägliche Fahrstrecke (km)", 1, 2000, 600, 50)
maut_prozent = sb.slider("Mautpflichtiger Anteil (%)", 0, 100, 80, 5)
diesel = sb.number_input("Dieselpreis (€/l netto)", 0.50, 4.00, 1.80, 0.05)
fahrer = sb.number_input("Fahrerkosten (€/Tag)", 0.0, 1000.0, 210.0, 10.0)

# Schlüssel pro Fahrzeugklasse: Beim Wechsel der Klasse greifen deren Standardwerte,
# eigene Anpassungen bleiben pro Klasse erhalten.
with sb.expander("⚙️ Fahrzeugwerte"):
    verbrauch = st.number_input("Verbrauch l/100 km (inkl. Kühlung)", 5.0, 50.0, p.verbrauch_l_100km, 0.5, key=f"v_{klasse}")
    wartung = st.number_input("Verschleiß/Reifen (€/km)", 0.01, 1.00, p.wartung_eur_km, 0.01, key=f"w_{klasse}")
    afa = st.number_input("Abschreibung (€/Tag)", 0.0, 500.0, p.abschreibung_eur_tag, 5.0, key=f"a_{klasse}")
    steuer = st.number_input("Steuer & Versicherung (€/Tag)", 0.0, 200.0, p.steuer_versicherung_eur_tag, 1.0, key=f"s_{klasse}")
    maut_satz = st.number_input("Mautsatz (€/km)", 0.0, 1.0, p.maut_eur_km, 0.001, format="%.3f", key=f"m_{klasse}",
                                help="Abhängig von Gewichts-, Achs- und CO₂-Klasse. Aktuelle Sätze bei Toll Collect prüfen.")

with sb.expander("🧭 Tour & Preis"):
    kmh = st.number_input("Ø Geschwindigkeit (km/h)", 20, 90, 62, 1,
                          help="Realistischer Schnitt im Mischverkehr inkl. Stadt und Landstraße, ohne Pausen.")
    tage = st.number_input("Arbeitstage pro Monat", 1, 31, 21, 1)
    zuschlag = st.slider("Zuschlag Gewinn & Wagnis (%)", 0, 40, 10, 1)

e = Eingaben(
    km_tag=km, maut_anteil=maut_prozent / 100, dieselpreis_eur_l=diesel, fahrerkosten_tag=fahrer,
    fahrzeug=FahrzeugProfil(verbrauch, wartung, afa, steuer, maut_satz, p.zuladung_t),
    durchschnitt_kmh=kmh, arbeitstage_monat=tage, zuschlag=zuschlag / 100,
)
r = berechne(e)

# ---------------------------------------------------------------- Kennzahlen
c1, c2, c3, c4 = st.columns(4)
c1.metric("Selbstkosten pro Tag", eur(r.gesamt_tag))
c2.metric("Selbstkosten pro km", eur(r.pro_km) + "/km")
c3.metric(f"Monat ({tage} Tage)", eur(r.gesamt_monat, 0))
c4.metric(f"Angebotspreis (+{zuschlag} %)", eur(r.angebot_tag), f"{eur(r.angebot_km)}/km", delta_color="off")

lz = r.lenkzeit
text = (f"**Lenkzeit ≈ {str(round(lz.stunden, 1)).replace(".", ",")} h** bei Ø {kmh} km/h · {lz.pausen} × 45 min Pause · "
        f"Tourdauer ≈ {str(round(lz.tourdauer_h, 1)).replace(".", ",")} h ohne Be- und Entladen. {lz.hinweis}")
{"ok": st.success, "verlaengert": st.warning, "unzulaessig": st.error}[lz.status](text)

st.divider()

# ---------------------------------------------------------------- Aufschlüsselung
df = pd.DataFrame({
    "Kostenblock": [b.name for b in r.bloecke],
    "Art": ["variabel (km)" if b.variabel else "fix (Tag)" for b in r.bloecke],
    "€/Tag": [b.betrag for b in r.bloecke],
    "€/km": [b.betrag / km for b in r.bloecke],
})
df["Anteil"] = df["€/Tag"] / r.gesamt_tag * 100

links, rechts = st.columns(2)
with links:
    st.subheader("📋 Kostenaufschlüsselung (netto)")
    st.dataframe(
        df, hide_index=True, width="stretch",
        column_config={
            "€/Tag": st.column_config.NumberColumn(format="%.2f €"),
            "€/km": st.column_config.NumberColumn(format="%.3f €"),
            "Anteil": st.column_config.ProgressColumn(format="%.1f %%", min_value=0, max_value=100),
        },
    )
    st.caption(f"Variabel: {eur(r.variabel_tag)} · Fix: {eur(r.fix_tag)} · "
               f"Mautstrecke: {r.maut_km:.0f} von {km} km")

with rechts:
    st.subheader("📊 Kostenverteilung")
    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=3)
        .encode(
            x=alt.X("€/Tag:Q", title="€ pro Tag"),
            y=alt.Y("Kostenblock:N", sort="-x", title=None),
            color=alt.Color("Art:N", scale=alt.Scale(range=["#2f6db5", "#9db9dc"]),
                            legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["Kostenblock", alt.Tooltip("€/Tag:Q", format=".2f"), alt.Tooltip("Anteil:Q", format=".1f")],
        )
        .properties(height=280)
    )
    st.altair_chart(chart, width="stretch")
