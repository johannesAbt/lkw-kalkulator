# Lkw Kosten-Kalkulator

| Datei | Zweck |
|---|---|
| `kalkulation.py` | Rechenkern (ohne Oberfläche), von beiden Apps genutzt |
| `desktop.py` | Desktop-Programm (PySide6/Qt) |
| `app.py` | Browser-Version (Streamlit) |
| `test_kalkulation.py` | Tests der Referenzrechnung (766,04 €/Tag) |
| `build_mac.sh` | baut `Lkw-Kalkulator.app` und installiert sie nach `/Applications` |

```sh
.venv/bin/python desktop.py           # Desktop-App direkt starten
./build_mac.sh                        # nach Änderungen neu bauen + installieren
.venv/bin/python -m pytest -q         # Tests
.venv/bin/streamlit run app.py        # Browser-Version
```

Eingaben werden beim Schließen gespeichert und beim nächsten Start wiederhergestellt.
