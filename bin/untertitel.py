#!/usr/bin/env python3
"""Untertitel aus den Wortzeiten einbrennen.

Bewusst ueber ASS und ffmpeg statt ueber einen Browser: das laeuft ueberall,
braucht keine Renderstrecke und ist um Groessenordnungen schneller.

    untertitel.py schnitt.mp4 --worte worte.json --aus mit-untertiteln.mp4

Wurde vorher geschnitten, muessen die Wortzeiten durch den Schnitt gerechnet
werden - sonst laufen die Untertitel um die herausgeschnittene Zeit vor. Liegt
neben dem Video eine `.schnitt.json`, passiert das von selbst.
"""
import argparse, json, subprocess, sys
from pathlib import Path

# Zu den Stilen in vorlage/szene.js passende Schriftfarben.
STILE = {
    "papier":    {"farbe": "&H00FFFFFF", "rand": "&H00000000", "randbreite": 4},
    "dunkel":    {"farbe": "&H00FFFFFF", "rand": "&H00000000", "randbreite": 4},
    "blaupause": {"farbe": "&H00FFF3EA", "rand": "&H00521F0B", "randbreite": 4},
    "riso":      {"farbe": "&H00FFFFFF", "rand": "&H001B1B1B", "randbreite": 5},
}


def lauf(cmd):
    p = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if p.returncode:
        sys.exit(f"fehlgeschlagen: {' '.join(str(c) for c in cmd[:6])} ...\n{p.stderr[-1200:]}")
    return p


def masse(weg):
    r = lauf(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
              "stream=width,height", "-of", "csv=p=0", weg]).stdout.strip()
    b, h = r.split(",")[:2]
    return int(b), int(h)


def durch_den_schnitt(worte, abschnitte):
    """Wortzeiten auf die geschnittene Fassung umrechnen."""
    neu, versatz = [], 0.0
    for ab in abschnitte:
        von, bis = ab["von"], ab["bis"]
        for w in worte:
            # Nur Woerter, die ganz in diesem Abschnitt liegen. Ein Wort, das
            # ueber eine Schnittkante ragt, wurde ohnehin angeschnitten.
            if w["von"] >= von - 1e-6 and w["bis"] <= bis + 1e-6:
                neu.append({"wort": w["wort"],
                            "von": w["von"] - von + versatz,
                            "bis": w["bis"] - von + versatz})
        versatz += bis - von
    return neu


def zeit(t):
    t = max(0.0, t)
    st = int(t // 3600); mi = int((t % 3600) // 60); se = t % 60
    return f"{st}:{mi:02d}:{se:05.2f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--worte", required=True)
    ap.add_argument("--aus", required=True)
    ap.add_argument("--gruppe", type=int, default=3,
                    help="Woerter je Einblendung: einzelne flackern, ganze Saetze liest niemand")
    ap.add_argument("--stil", default="papier")
    ap.add_argument("--schrift", default="Adwaita Sans")
    a = ap.parse_args()

    video = Path(a.video)
    worte = json.loads(Path(a.worte).read_text(encoding="utf-8"))
    liste = video.with_suffix(".schnitt.json")
    if liste.exists():
        vorher = len(worte)
        worte = durch_den_schnitt(worte, json.loads(liste.read_text(encoding="utf-8"))["abschnitte"])
        print(f"  Wortzeiten durch den Schnitt gerechnet ({vorher} -> {len(worte)})")

    b, h = masse(video)
    st = STILE.get(a.stil, STILE["papier"])
    groesse = max(28, round(h * 0.048))
    rand_unten = round(h * 0.14)          # innerhalb der Bedienleisten der Apps

    zeilen = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {b}", f"PlayResY: {h}",
        "WrapStyle: 2", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        # SecondaryColour gehoert dazu. Fehlt sie in der Format-Zeile, ordnet
        # libass jedes weitere Feld falsch zu - und der Text bleibt unsichtbar,
        # ohne dass irgendwo ein Fehler auftaucht.
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour,"
        " OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut,"
        " ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow,"
        " Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: vox,{a.schrift},{groesse},{st['farbe']},{st['farbe']},{st['rand']},"
        f"&H64000000,-1,0,0,0,100,100,0,0,1,{st['randbreite']},2,2,60,60,{rand_unten},1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    n = 0
    for i in range(0, len(worte), a.gruppe):
        gruppe = worte[i:i + a.gruppe]
        text = " ".join(w["wort"] for w in gruppe).replace("\n", " ")
        von, bis = gruppe[0]["von"], gruppe[-1]["bis"]
        if bis - von < 0.25:
            bis = von + 0.25
        zeilen.append(f"Dialogue: 0,{zeit(von)},{zeit(bis)},vox,,0,0,0,,{text}")
        n += 1

    ass = video.with_suffix(".ass")
    ass.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    print(f"  {n} Einblendungen, Schrift {groesse}px, {rand_unten}px vom unteren Rand")

    # subtitles= braucht einen Pfad ohne Doppelpunkt-Sonderbedeutung.
    pfad = str(ass).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    lauf(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf", f"subtitles='{pfad}'",
          "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
          "-c:a", "copy", a.aus])
    print(f"\n  {a.aus}")


if __name__ == "__main__":
    main()
