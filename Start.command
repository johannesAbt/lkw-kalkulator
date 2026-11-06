#!/bin/zsh
# Doppelklick startet den Lkw-Kostenkalkulator im Browser (Beenden: Fenster schließen)
cd "$(dirname "$0")"
exec .venv/bin/streamlit run app.py
