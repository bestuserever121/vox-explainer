#!/usr/bin/env python3
"""Foto in ein schwarzweisses Rasterbild verwandeln - Zeitungsdruck-Optik.

Der Look aus Vox-artigen Erklaervideos: entsaettigt, hart im Kontrast, in ein
Punktraster zerlegt, dazu ein leichter Farbversatz wie bei schlecht
uebereinanderliegenden Druckplatten.

    rasterbild.py ein.jpg aus.png --punkt 6 --winkel 20

Das Raster wird schraeg gelegt (klassisch 45 Grad, hier flacher), sonst bilden
die Punkte sichtbare waagerechte Reihen und es sieht nach Bildschirm aus
statt nach Druck.
"""
import argparse, math
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageOps, ImageFilter


def raster(bild: Image.Image, punkt: int, winkel: float, ueber: int = 3):
    """Punktraster: je dunkler die Stelle, desto groesser der Punkt."""
    g = bild.convert("L")
    b, h = g.size
    # Ueberabtasten und am Ende verkleinern - sonst sind die Punkte treppig.
    gross = Image.new("L", (b * ueber, h * ueber), 255)
    zeichen = ImageDraw.Draw(gross)
    rad = math.radians(winkel)
    # Diagonale als Reichweite, damit das gedrehte Gitter das Bild ganz deckt.
    reich = int(math.hypot(b, h) / punkt) + 2
    for iy in range(-reich, reich):
        for ix in range(-reich, reich):
            # Gitterpunkt im gedrehten System, zurueck ins Bild gerechnet
            x = (ix * punkt) * math.cos(rad) - (iy * punkt) * math.sin(rad) + b / 2
            y = (ix * punkt) * math.sin(rad) + (iy * punkt) * math.cos(rad) + h / 2
            if not (0 <= x < b and 0 <= y < h):
                continue
            wert = g.getpixel((int(x), int(y)))
            # Flaeche des Punktes proportional zur Schwaerze
            r = (punkt / 2.0) * math.sqrt((255 - wert) / 255.0) * 1.28
            if r < 0.35:
                continue
            cx, cy = x * ueber, y * ueber
            rr = r * ueber
            zeichen.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=0)
    return gross.resize((b, h), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ein"); ap.add_argument("aus")
    ap.add_argument("--punkt", type=int, default=5, help="Rasterweite in Pixeln")
    ap.add_argument("--winkel", type=float, default=20.0)
    ap.add_argument("--kontrast", type=float, default=1.15)
    ap.add_argument("--beschnitt", type=float, default=1.0)
    ap.add_argument("--aufhellen", type=float, default=0.18)
    ap.add_argument("--breite", type=int, default=900)
    ap.add_argument("--versatz", type=int, default=2, help="Farbversatz in Pixeln")
    a = ap.parse_args()

    im = Image.open(a.ein)
    hat_alpha = im.mode in ("RGBA", "LA") or "transparency" in im.info
    im = im.convert("RGBA")
    if im.width != a.breite:
        im = im.resize((a.breite, round(im.height * a.breite / im.width)), Image.LANCZOS)
    alpha = im.getchannel("A")
    # Auf Weiss legen, sonst rastert der schwarze Grund der leeren Flaeche mit.
    auf_weiss = Image.new("RGB", im.size, (255, 255, 255))
    auf_weiss.paste(im, mask=alpha)

    g = ImageOps.grayscale(auf_weiss)
    g = ImageOps.autocontrast(g, cutoff=a.beschnitt)
    g = ImageEnhance.Contrast(g).enhance(a.kontrast)
    if a.aufhellen:
        # Die Vorlage ist hell. Ohne das Anheben werden dunkle Trikots zu
        # geschlossenen schwarzen Flaechen und das Gesicht verschwindet.
        g = g.point(lambda v: min(255, int(v + (255 - v) * a.aufhellen)))
    g = g.filter(ImageFilter.GaussianBlur(0.5))
    punkte = raster(g, a.punkt, a.winkel)

    # Farbversatz: die Druckplatten liegen leicht daneben.
    v = a.versatz
    leer = Image.new("L", punkte.size, 255)
    rot   = Image.merge("RGB", (punkte, leer, leer))
    gruen = Image.merge("RGB", (leer, punkte, leer))
    blau  = Image.merge("RGB", (leer, leer, punkte))
    # Die drei Platten uebereinander: je Kanal das Dunkelste gewinnt, damit
    # sich die Punkte wie Druckfarbe aufeinanderlegen statt sich aufzuhellen.
    stapel = np.full((punkte.size[1], punkte.size[0], 3), 255, dtype=np.uint8)
    for lage, (dx, dy) in ((rot, (-v, 0)), (gruen, (0, v // 2)), (blau, (v, 0))):
        versetzt = Image.new("RGB", punkte.size, (255, 255, 255))
        versetzt.paste(lage, (dx, dy))
        stapel = np.minimum(stapel, np.array(versetzt))
    aus = Image.fromarray(stapel)

    if hat_alpha:
        # Die Maske eine Spur schrumpfen, sonst bleibt ein heller Saum stehen.
        rand = alpha.filter(ImageFilter.MinFilter(3))
        aus = aus.convert("RGBA")
        aus.putalpha(rand)
    aus.save(a.aus)
    print(f"{a.aus}  {aus.size[0]}x{aus.size[1]}  Raster {a.punkt}px @ {a.winkel:g} Grad")


if __name__ == "__main__":
    main()
