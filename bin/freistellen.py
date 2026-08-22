#!/usr/bin/env python3
"""Motiv vom Hintergrund freistellen (optional, braucht `rembg`).

Ohne Freisteller stehen die Fotos als Rechtecke im Bild - das bricht die
Collagen-Optik sofort. Deshalb lieber eine Fehlermeldung als ein Rechteck.

    freistellen.py ein.jpg aus.png

Einrichten (einmalig, laeuft lokal, keine Anmeldung noetig):
    python3 -m venv .venv && .venv/bin/pip install "rembg[cpu]" pillow
"""
import argparse, sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ein"); ap.add_argument("aus")
    ap.add_argument("--modell", default="u2net")
    ap.add_argument("--eng", action="store_true",
                    help="auf die Silhouette beschneiden (empfohlen)")
    a = ap.parse_args()
    try:
        from rembg import remove, new_session
        from PIL import Image
    except ImportError:
        sys.exit("rembg fehlt. Einrichten:\n"
                 "  python3 -m venv .venv && .venv/bin/pip install \"rembg[cpu]\" pillow\n"
                 "und dann .venv/bin/python fuer dieses Skript nutzen.")

    im = Image.open(a.ein).convert("RGB")
    raus = remove(im, session=new_session(a.modell), post_process_mask=True)
    alpha = raus.getchannel("A")
    anteil = sum(alpha.histogram()[200:]) / (alpha.size[0] * alpha.size[1])
    if anteil < 0.02:
        sys.exit(f"Freistellung misslungen: nur {anteil*100:.1f}% behalten. "
                 f"Anderes Bild nehmen oder --modell wechseln.")
    if a.eng:
        # Ohne Beschnitt hat jedes Bild anders viel leeren Rand, und die
        # Hoehenangaben im Layout stimmen nicht mehr zueinander.
        kasten = alpha.getbbox()
        if kasten:
            raus = raus.crop(kasten)
    raus.save(a.aus)
    print(f"{a.aus}  {raus.size[0]}x{raus.size[1]}  behalten {anteil*100:.1f}%")


if __name__ == "__main__":
    main()
