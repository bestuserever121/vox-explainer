#!/usr/bin/env python3
"""Dynamik auf einen Abschnitt legen - Zoom-Punch, Blitz, Farbversatz.

Fuer Stellen, an denen das Bild selbst arbeiten soll statt einer Karte, die
behauptet, dass etwas passiert. Die Laenge bleibt unangetastet: der Abschnitt
wird herausgetrennt, behandelt und wieder eingesetzt - kein Zeitraffer, sonst
laufen Untertitel und Ton auseinander.

    dynamik.py ein.mp4 aus.mp4 --von 11.2 --bis 13.6 --punch 0.0 1.1

Warum scale+crop und nicht zoompan: `scale` mit `eval=frame` wertet seine
Ausdruecke je Bild aus und ist ueberall gleich verfuegbar; zoompan bringt
eigene Zeitvariablen mit, die je nach Fassung fehlen.
"""
import argparse, subprocess, sys
from pathlib import Path


def lauf(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode:
        sys.exit(f"fehlgeschlagen: {' '.join(cmd[:6])} ...\n{p.stderr[-1200:]}")
    return p


def masse(weg):
    p = lauf(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
              "stream=width,height", "-show_entries", "format=duration",
              "-of", "default=nw=1:nk=1", str(weg)]).stdout.split()
    return int(p[0]), int(p[1]), float(p[2])


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ein"); ap.add_argument("aus")
    ap.add_argument("--von", type=float, required=True)
    ap.add_argument("--bis", type=float, required=True)
    ap.add_argument("--punch", type=float, nargs="*", default=[0.0],
                    help="Zeitpunkte der Zoom-Stoesse, gerechnet ab --von")
    ap.add_argument("--staerke", type=float, default=1.0)
    a = ap.parse_args()

    b, h, dauer = masse(a.ein)
    von, bis = max(0.0, a.von), min(dauer, a.bis)
    if bis <= von:
        sys.exit("leerer Abschnitt")

    # Der Zoom klingt nach jedem Stoss ab. Summe der Stoesse, nie unter 1.
    tiefe = 0.13 * a.staerke
    # gte(t,p) als Tor: ohne das ist max(0,t-p) vor dem Zeitpunkt 0, also
    # exp(0)=1 - der Stoss waere von Anfang an voll aktiv und wuerde zu seinem
    # eigenen Zeitpunkt gar nicht mehr zuschlagen.
    z = "1" + "".join(f"+{tiefe:.3f}*exp(-(t-{p:.3f})/0.21)*gte(t,{p:.3f})"
                      for p in a.punch)
    # Ein leichtes Wanken haelt das Bild lebendig, ohne dass es kippt.
    sx = f"6*sin(t*17)*exp(-t/1.3)"
    sy = f"4*sin(t*13+1)*exp(-t/1.3)"

    behandelt = (
        f"scale=w='ceil({b}*({z})/2)*2':h='ceil({h}*({z})/2)*2':eval=frame:flags=bicubic,"
        f"crop={b}:{h}:x='(in_w-{b})/2+{sx}':y='(in_h-{h})/2+{sy}',"
        # Blitz auf jedem Stoss, danach eine Spur mehr Farbe.
        # 0.26 riss das Bild ins Weisse - eq.brightness ist additiv, da ist
        # ein Zehntel schon deutlich sichtbar.
        f"eq=brightness='" + "+".join(
            f"0.085*exp(-(t-{p:.3f})/0.09)*gte(t,{p:.3f})" for p in a.punch)
        + f"':saturation=1.12:contrast=1.05:eval=frame,"
        # Farbversatz nur im Moment des ersten Stosses - laenger wirkt es kaputt.
        # edge=smear, sonst steht ein farbiger Balken am Bildrand.
        f"rgbashift=rh=-5:bh=5:edge=smear:"
        f"enable='between(t,{a.punch[0]:.2f},{a.punch[0]+0.15:.2f})'"
    )

    teile, fc = [], []
    fc.append(f"[0:v]split=3[q0][q1][q2]")
    n = 0
    if von > 0.01:
        fc.append(f"[q0]trim=0:{von:.4f},setpts=PTS-STARTPTS[p0]"); teile.append("[p0]"); n += 1
    fc.append(f"[q1]trim={von:.4f}:{bis:.4f},setpts=PTS-STARTPTS,{behandelt}[p1]")
    teile.append("[p1]"); n += 1
    if bis < dauer - 0.01:
        fc.append(f"[q2]trim={bis:.4f},setpts=PTS-STARTPTS[p2]"); teile.append("[p2]"); n += 1
    fc.append("".join(teile) + f"concat=n={n}:v=1:a=0[v]")

    print(f"  Dynamik auf {von:.2f}-{bis:.2f}s, {len(a.punch)} Stoss/Stoesse")
    lauf(["ffmpeg", "-v", "error", "-y", "-i", str(a.ein),
          "-filter_complex", ";".join(fc), "-map", "[v]", "-map", "0:a?",
          "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
          "-c:a", "copy", str(a.aus)])

    _, _, neu = masse(a.aus)
    if abs(neu - dauer) > 0.05:
        sys.exit(f"FEHLER: Laenge veraendert ({dauer:.2f}s -> {neu:.2f}s)")
    print(f"\nFertig: {a.aus}  ({neu:.2f}s, Laenge unveraendert)")


if __name__ == "__main__":
    main()
