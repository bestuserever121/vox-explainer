#!/usr/bin/env bash
# Prueft, was vorhanden ist - und sagt bei Fehlendem, wie es dazukommt.
set -u
gruen() { printf '  \033[32mok\033[0m    %-22s %s\n' "$1" "$2"; }
rot()   { printf '  \033[31mfehlt\033[0m %-22s %s\n' "$1" "$2"; }

echo
echo "vox - Voraussetzungen"
echo

for c in ffmpeg ffprobe node python3; do
  p=$(command -v "$c" 2>/dev/null) && gruen "$c" "$p" || rot "$c" "ueber die Paketverwaltung installieren"
done

python3 - <<'PY' 2>/dev/null && printf '  \033[32mok\033[0m    %-22s %s\n' "python PIL + numpy" "vorhanden" \
  || printf '  \033[31mfehlt\033[0m %-22s %s\n' "python PIL + numpy" "pip install pillow numpy"
import PIL, numpy
PY

HF="${HYPERFRAMES:-$HOME/projects/hyperframes/packages/cli/bin/hyperframes.mjs}"
if [ -f "$HF" ]; then gruen "hyperframes" "$HF"
else rot "hyperframes" "git clone https://github.com/heygen-com/hyperframes && pnpm install && pnpm build"; fi

# GSAP wird bewusst nicht mitgeliefert - fremde Lizenz. Beim ersten Lauf holen.
G="${GSAP:-$(dirname "$0")/vorlage/gsap.min.js}"
if [ -f "$G" ]; then
  gruen "gsap.min.js" "$G"
elif [ "${1:-}" = "--holen" ]; then
  echo "  hole gsap.min.js ..."
  if curl -fsSL "https://cdn.jsdelivr.net/npm/gsap@3/dist/gsap.min.js" -o "$G"; then
    gruen "gsap.min.js" "$G (geladen)"
  else rot "gsap.min.js" "Download fehlgeschlagen - von https://gsap.com holen"; fi
else
  rot "gsap.min.js" "./voraussetzungen.sh --holen  (oder von https://gsap.com)"
fi

if [ -x "$(dirname "$0")/.venv/bin/python" ] && \
   "$(dirname "$0")/.venv/bin/python" -c "import rembg" 2>/dev/null; then
  gruen "rembg (Freisteller)" ".venv"
else
  printf '  \033[33mopt\033[0m   %-22s %s\n' "rembg (Freisteller)" \
    'python3 -m venv .venv && .venv/bin/pip install "rembg[cpu]" pillow'
fi

if command -v whisper-cli >/dev/null 2>&1; then gruen "whisper-cli" "$(command -v whisper-cli)"
else printf '  \033[33mopt\033[0m   %-22s %s\n' "whisper-cli" "https://github.com/ggml-org/whisper.cpp"; fi
echo
