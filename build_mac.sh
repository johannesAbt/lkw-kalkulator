#!/bin/zsh
# Baut "Lkw-Kalkulator.app" (macOS) nach dist/ und kopiert sie nach /Applications.
set -euo pipefail
cd "$(dirname "$0")"
PY=.venv/bin/python

mkdir -p assets build/icon.iconset
$PY make_icon.py assets/icon.png
for s in 16 32 128 256 512; do
  sips -z $s $s assets/icon.png --out build/icon.iconset/icon_${s}x${s}.png >/dev/null
  sips -z $((s*2)) $((s*2)) assets/icon.png --out build/icon.iconset/icon_${s}x${s}@2x.png >/dev/null
done
iconutil -c icns build/icon.iconset -o assets/icon.icns

.venv/bin/pyinstaller --noconfirm --clean --windowed \
  --name "Lkw-Kalkulator" \
  --icon assets/icon.icns \
  --add-data "assets/icon.png:assets" \
  --osx-bundle-identifier de.lkwkalkulator.app \
  --exclude-module streamlit --exclude-module pandas --exclude-module altair \
  --exclude-module pytest --exclude-module tkinter \
  desktop.py

rm -rf "/Applications/Lkw-Kalkulator.app"
cp -R "dist/Lkw-Kalkulator.app" /Applications/
echo "Fertig: /Applications/Lkw-Kalkulator.app"
