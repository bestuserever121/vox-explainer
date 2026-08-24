#!/usr/bin/env python3
"""Untertitel aus den Wortzeiten einbrennen.

Bewusst ueber ASS und ffmpeg statt ueber einen Browser: das laeuft ueberall,
braucht keine Renderstrecke und ist um Groessenordnungen schneller.

    untertitel.py schnitt.mp4 --worte worte.json --aus mit-untertiteln.mp4

Wurde vorher geschnitten, muessen die Wortzeiten durch den Schnitt gerechnet
werden - sonst laufen die Untertitel um die herausgeschnittene Zeit vor. Liegt
neben dem Video eine `.schnitt.json`, passiert das von selbst.
"""
import argparse, difflib, html, json, pathlib, re, subprocess, sys
import pathlib
from pathlib import Path

# Zu den Stilen in vorlage/szene.js passende Schriftfarben.
STILE = {
    "papier":    {"farbe": "&H00FFFFFF", "rand": "&H00000000", "randbreite": 4},
    "dunkel":    {"farbe": "&H00FFFFFF", "rand": "&H00000000", "randbreite": 4},
    "blaupause": {"farbe": "&H00FFF3EA", "rand": "&H00521F0B", "randbreite": 4},
    "riso":      {"farbe": "&H00FFFFFF", "rand": "&H001B1B1B", "randbreite": 5},
    "nomobo":    {"farbe": "&H00FFFFFF", "rand": "&H000E0907", "randbreite": 5},
}


sys.path.insert(0, str(Path(__file__).resolve().parent))
import umbruch


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


SATZENDE = (".", "!", "?", ":")


def karten_bauen(worte, max_woerter, max_zeichen, mindest_s):
    """Woerter zu Einblendungen gruppieren.

    Feste Dreiergruppen schneiden mitten durch Saetze - "ist niemand. Jede"
    liest sich wie ein Fehler, weil es einer ist. Deshalb drei Regeln:

      1. Ein Satzende beendet immer eine Karte.
      2. Innerhalb des Satzes wird bevorzugt am Komma getrennt.
      3. Zu kurze Karten werden mit der naechsten verschmolzen - unter etwa
         einer Sekunde flackert es nur.
    """
    karten, aktuell = [], []

    def schliessen():
        if aktuell:
            karten.append(aktuell.copy()); aktuell.clear()

    for w in worte:
        aktuell.append(w)
        text = " ".join(x["wort"] for x in aktuell)
        wort = w["wort"].rstrip("\"'\u00bb\u201c")
        if wort.endswith(SATZENDE):
            schliessen(); continue
        if len(aktuell) >= max_woerter or len(text) >= max_zeichen:
            # Lieber am letzten Komma trennen als mitten in der Wendung.
            komma = max((i for i, x in enumerate(aktuell[:-1])
                         if x["wort"].endswith(",")), default=None)
            if komma is not None and komma >= 1:
                rest = aktuell[komma + 1:]
                del aktuell[komma + 1:]
                schliessen()
                aktuell.extend(rest)
            else:
                schliessen()
    schliessen()

    # Zu kurze Karten verschmelzen
    raus = []
    for k in karten:
        dauer = k[-1]["bis"] - k[0]["von"]
        if raus and dauer < mindest_s:
            vorher = raus[-1]
            zusammen = " ".join(x["wort"] for x in vorher + k)
            if len(zusammen) <= max_zeichen * 1.6:
                vorher.extend(k); continue
        raus.append(k)
    return raus


def aus_dem_text(worte, textweg):
    """Die Schreibweise aus dem Sprechertext uebernehmen, die Zeiten aus der
    Erkennung.

    Die Erkennung hoert, was gesprochen wurde, und schreibt es nach eigenem
    Ermessen: "Und zu Hause." statt "Hause?", "37." statt "37,0",
    "Fuenffachen" statt "Fuenffache". Der geschriebene Text ist die Wahrheit -
    die Erkennung taugt nur fuer das Timing.
    """
    roh = pathlib.Path(textweg).read_text(encoding="utf-8")
    soll = [w for w in re.split(r"\s+", roh.strip()) if w]
    ist = [w["wort"] for w in worte]
    norm = lambda x: re.sub(r"[^\wäöüß]", "", x.lower())
    ab = difflib.SequenceMatcher(a=[norm(x) for x in ist], b=[norm(x) for x in soll])
    neu, offen = [], 0
    for tag, i1, i2, j1, j2 in ab.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                neu.append({**worte[i1 + k], "wort": soll[j1 + k]})
        elif tag == "replace":
            # Gleich viele Woerter: eins zu eins. Sonst den Textteil auf die
            # vorhandenen Zeiten verteilen.
            paare = min(i2 - i1, j2 - j1)
            for k in range(paare):
                neu.append({**worte[i1 + k], "wort": soll[j1 + k]})
            for k in range(paare, j2 - j1):
                if neu:
                    neu[-1]["wort"] += " " + soll[j1 + k]
            offen += abs((i2 - i1) - (j2 - j1))
        elif tag == "insert":
            for k in range(j1, j2):
                if neu:
                    neu[-1]["wort"] += " " + soll[k]
            offen += j2 - j1
        # "delete": die Erkennung hat etwas gehoert, das nicht im Text steht -
        # weglassen, sonst steht Erfundenes im Bild.
    print(f"  Text uebernommen: {len(neu)} Woerter"
          + (f", {offen} Stellen angepasst" if offen else ", deckungsgleich"))
    return neu


def ersetzen_laden(weg):
    """Schreibweisen richtigstellen.

    Die Erkennung schreibt "7,7" und "14.20", im Bild steht "7,70" und
    "14:20". Zwei Schreibweisen derselben Zahl im selben Video sind ein
    Fehler, den jeder sieht.
    """
    if not weg:
        return {}
    return json.loads(Path(weg).read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--worte", required=True)
    ap.add_argument("--aus", required=True)
    ap.add_argument("--gruppe", type=int, default=4,
                    help="Richtwert fuer Woerter je Einblendung; Satz- und Kommagrenzen gehen vor")
    ap.add_argument("--zeichen", type=int, default=0,
                    help="Zeichen je Zeile. Netflix nennt 42 fuer die kleine "
                         "Schrift am Bildrand; der Reel-Brenner setzt gross "
                         "und mittig. 0 = aus Bildbreite und Schriftgrad "
                         "ausrechnen.")
    ap.add_argument("--lesetempo", type=float, default=umbruch.ZEICHEN_JE_SEKUNDE,
                    help="Zeichen je Sekunde (Netflix: 17 fuer Erwachsene)")
    ap.add_argument("--mindest", type=float, default=umbruch.MIN_STANDZEIT,
                    help="Mindeststandzeit in Sekunden (Netflix: 5/6)")
    ap.add_argument("--text", help="Sprechertext - liefert die Schreibweise, "
                                   "die Erkennung nur die Zeiten")
    ap.add_argument("--ersetzen", help="JSON mit Schreibweisen, z.B. {\"7,7\": \"7,70\"}")
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
    # 0.048 sah gut aus, liess aber nur 20 Zeichen je Zeile zu - und damit
    # war die Netflix-Regel (Umbruch entlang grammatischer Einheiten) bei
    # vielen deutschen Saetzen gar nicht erfuellbar. Etwas kleiner, dafuer
    # richtig gebrochen.
    # An der Breite messen, nicht an der Hoehe. Beim Splitscreen ist das Bild
    # nur noch 1240 statt 1920 hoch - die Schrift wuerde mitschrumpfen,
    # obwohl das Bild genauso breit bleibt.
    groesse = max(28, round(b * 0.072))
    rand_unten = round(h * 0.115)          # innerhalb der Bedienleisten der Apps

    zeilen = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {b}", f"PlayResY: {h}",
        # WrapStyle 0 = umbrechen. Mit 2 laufen lange Zeilen einfach aus dem
        # Bild heraus - links und rechts abgeschnitten, ohne Warnung.
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        # SecondaryColour gehoert dazu. Fehlt sie in der Format-Zeile, ordnet
        # libass jedes weitere Feld falsch zu - und der Text bleibt unsichtbar,
        # ohne dass irgendwo ein Fehler auftaucht.
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour,"
        " OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut,"
        " ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow,"
        " Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: vox,{a.schrift},{groesse},{st['farbe']},{st['farbe']},{st['rand']},"
        f"&H64000000,-1,0,0,0,100,100,0,0,1,{st['randbreite']},2,2,44,44,{rand_unten},1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    if a.text:
        worte = aus_dem_text(worte, a.text)
    tausch = ersetzen_laden(a.ersetzen)
    if tausch:
        for w in worte:
            w["wort"] = tausch.get(w["wort"], w["wort"])

    # Umbruch und Standzeiten nach dem Netflix Timed Text Style Guide.
    # karten_bauen() kannte nur Satzende und Komma - das erklaert Zeilen wie
    # "5,2 / ct bekommen", die die Zahl von ihrer Einheit reissen.
    # Der Grenzwert muss zur tatsaechlich gerenderten Breite passen. Ist er
    # zu gross, bricht libass ein zweites Mal um - und dann steht da wieder
    # "5,2 / ct bekommen", obwohl der Umbruch oben alles richtig gemacht hat.
    # Poppins Bold laeuft mit rund 0,52 em je Zeichen.
    breite = a.zeichen or max(12, int((b - 120) / (groesse * 0.52)))
    karten = umbruch.karten(worte, breite=breite, zps=a.lesetempo,
                            min_s=a.mindest, max_s=umbruch.MAX_STANDZEIT)
    n = 0
    for k in karten:
        text = "\\N".join(z.replace("\n", " ") for z in k["zeilen"])
        zeilen.append(f"Dialogue: 0,{zeit(k['von'])},{zeit(k['bis'])},vox,,0,0,0,,{text}")
        n += 1

    ass = video.with_suffix(".ass")
    ass.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    print(f"  {breite} Zeichen je Zeile · {n} Einblendungen, Schrift {groesse}px, {rand_unten}px vom unteren Rand")

    # subtitles= braucht einen Pfad ohne Doppelpunkt-Sonderbedeutung.
    pfad = str(ass).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    lauf(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf", f"subtitles='{pfad}'",
          "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
          "-c:a", "copy", a.aus])
    print(f"\n  {a.aus}")


if __name__ == "__main__":
    main()
