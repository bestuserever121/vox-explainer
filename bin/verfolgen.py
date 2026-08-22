#!/usr/bin/env python3
"""Einen Bildausschnitt durch das Video verfolgen - fuer Masken und Marker.

Ohne Verfolgung klebt eine Maske an einer festen Stelle und der Kopf laeuft
darunter weg. Gearbeitet wird mit normierter Kreuzkorrelation: ein Muster wird
im naechsten Bild in einem Suchfenster wiedergefunden. Nur numpy, keine
Fremdbibliothek.

    verfolgen.py roh.mp4 --von 15.5 --bis 21.0 --start 675,400 --muster 190 \\
                 --aus spur.json

Ergebnis: [{ "t": 15.50, "x": 675, "y": 400, "guete": 0.94 }, ...]

Die Guete sagt, wie sicher der Treffer war. Faellt sie unter --mindestguete,
haelt die Spur die letzte Lage und markiert `gehalten` - besser ein
stehendes Ziel als ein springendes.
"""
import argparse, json, subprocess, sys
from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


def bilder_lesen(weg, von, bis, fps, breite, hoehe):
    roh = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(weg), "-ss", f"{von:.3f}", "-to", f"{bis:.3f}",
         "-vf", f"fps={fps},scale={breite}:{hoehe},format=gray",
         "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
    n = len(roh) // (breite * hoehe)
    if n == 0:
        sys.exit("keine Bilder gelesen - Zeitbereich pruefen")
    return np.frombuffer(roh, dtype=np.uint8)[:n * breite * hoehe] \
             .reshape(n, hoehe, breite).astype(np.float32)


def bestes_treffen(bild, muster, mx, my, suche):
    """Bestes Vorkommen des Musters um (mx,my) herum finden."""
    th, tw = muster.shape
    H, W = bild.shape
    x0 = int(np.clip(mx - tw // 2 - suche, 0, W - tw))
    y0 = int(np.clip(my - th // 2 - suche, 0, H - th))
    x1 = int(np.clip(mx - tw // 2 + suche, 0, W - tw))
    y1 = int(np.clip(my - th // 2 + suche, 0, H - th))
    feld = bild[y0:y1 + th, x0:x1 + tw]
    if feld.shape[0] < th or feld.shape[1] < tw:
        return mx, my, 0.0
    sicht = sliding_window_view(feld, (th, tw))
    v = sicht.reshape(-1, th * tw)
    v = v - v.mean(axis=1, keepdims=True)
    norm = np.sqrt((v * v).sum(axis=1)) + 1e-6
    m = muster.ravel() - muster.mean()
    mn = np.sqrt((m * m).sum()) + 1e-6
    punkte = (v @ m) / (norm * mn)
    i = int(np.argmax(punkte))
    dy, dx = divmod(i, sicht.shape[1])
    return x0 + dx + tw // 2, y0 + dy + th // 2, float(punkte[i])


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--von", type=float, required=True)
    ap.add_argument("--bis", type=float, required=True)
    ap.add_argument("--start", required=True, help="x,y im Vollbild")
    ap.add_argument("--muster", type=int, default=190, help="Kantenlaenge im Vollbild")
    ap.add_argument("--suche", type=int, default=70, help="Suchfenster im Vollbild")
    ap.add_argument("--fps", type=float, default=25.0)
    ap.add_argument("--teiler", type=int, default=2, help="Rechnen auf halber Groesse")
    ap.add_argument("--mindestguete", type=float, default=0.55)
    ap.add_argument("--aus", required=True)
    a = ap.parse_args()

    masse = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=width,height", "-of", "csv=p=0",
                            a.video], capture_output=True, text=True).stdout.strip()
    VB, VH = (int(v) for v in masse.split(",")[:2])
    B, H = VB // a.teiler, VH // a.teiler
    bilder = bilder_lesen(a.video, a.von, a.bis, a.fps, B, H)

    sx, sy = (int(v) for v in a.start.split(","))
    mx, my = sx // a.teiler, sy // a.teiler
    k = max(16, a.muster // a.teiler // 2 * 2)
    suche = max(8, a.suche // a.teiler)

    def ausschnitt(bild, cx, cy):
        x0 = int(np.clip(cx - k // 2, 0, B - k)); y0 = int(np.clip(cy - k // 2, 0, H - k))
        return bild[y0:y0 + k, x0:x0 + k].copy()

    muster = ausschnitt(bilder[0], mx, my)
    spur, gehalten = [], 0
    for i, bild in enumerate(bilder):
        if i == 0:
            g = 1.0
        else:
            nx, ny, g = bestes_treffen(bild, muster, mx, my, suche)
            if g >= a.mindestguete:
                mx, my = nx, ny
                # Das Muster langsam nachfuehren: das Gesicht dreht sich, ein
                # starres Muster verliert es. Zu schnell nachfuehren driftet.
                neu = ausschnitt(bild, mx, my)
                muster = 0.85 * muster + 0.15 * neu
            else:
                gehalten += 1
        spur.append({"t": round(a.von + i / a.fps, 4),
                     "x": int(mx * a.teiler), "y": int(my * a.teiler),
                     "guete": round(g, 3)})
    Path(a.aus).write_text(json.dumps(spur, indent=1), encoding="utf-8")
    guten = [s["guete"] for s in spur[1:]]
    print(f"  {len(spur)} Lagen, Guete im Mittel {np.mean(guten):.2f} "
          f"(min {np.min(guten):.2f}), {gehalten}x gehalten")
    print(f"  {a.aus}")


if __name__ == "__main__":
    main()
