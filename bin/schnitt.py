#!/usr/bin/env python3
"""Rohschnitt: Fuellwoerter und totes Band aus einer Aufnahme entfernen.

Fuer Material, das schon existiert - Talking Head, Podcast, Kameraaufnahme.
Der Schnitt orientiert sich an zwei Quellen, nicht an einer:

  * das Transkript sagt, WO gesprochen wird,
  * die Pegelmessung sagt, wo Stille ist.

Beides zusammen, weil jede allein irrt: Transkriptluecken sind bei vielen
Modellen null (die Abschnitte stossen aneinander), und eine Pegelmessung haelt
leise Sprache fuer Stille.

    schnitt.py roh.mp4 --worte worte.json --aus schnitt.mp4
"""
import argparse, json, math, subprocess, sys
from pathlib import Path

FUELLER = {
    # "also" und "genau" stehen bewusst NICHT drin: am Satzanfang tragen sie,
    # und ihr Wegfall zerreisst den Satzbau.
    "äh", "ähm", "ähh", "hm", "hmm", "halt", "quasi", "sozusagen", "irgendwie",
    "uh", "uhm", "um", "erm", "like", "you know",
}
STILLE_MAX = 0.60     # laenger als das darf keine Pause stehen bleiben
STILLE_REST = 0.18    # so viel Atem bleibt uebrig
RAND = 0.045          # Sicherheitsabstand um jedes Wort


def lauf(cmd, **kw):
    p = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)
    if p.returncode:
        sys.exit(f"fehlgeschlagen: {' '.join(str(c) for c in cmd[:6])} ...\n{p.stderr[-1200:]}")
    return p


def dauer_von(weg) -> float:
    return float(lauf(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                       "-of", "csv=p=0", weg]).stdout.strip())


def bildrate(weg) -> float:
    r = lauf(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
              "stream=r_frame_rate", "-of", "csv=p=0", weg]).stdout.strip()
    if "/" in r:
        a, b = r.split("/")
        return float(a) / float(b) if float(b) else 30.0
    return float(r or 30.0)


def stilleschwelle(weg) -> float:
    """Die Schwelle aus der Aufnahme rechnen, nicht raten.

    Eine feste Schwelle ist eine Wette auf den Pegel. Bei einer leisen
    Handyaufnahme lag die lauteste Stelle bei -36 dB - eine feste Schwelle von
    -33 dB haette die komplette Aufnahme als Stille gewertet.
    """
    try:
        import numpy as np
    except ImportError:
        return -33.0
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(weg), "-ac", "1",
                          "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
    x = np.frombuffer(pcm, dtype="<f4")
    if x.size < 16000:
        return -33.0
    n = x.size // 1600
    rms = np.sqrt((x[:n * 1600].reshape(n, 1600) ** 2).mean(axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-9)
    ruhe, sprache = float(np.percentile(db, 10)), float(np.percentile(db, 85))
    return max(-70.0, min(-28.0, ruhe + 0.45 * (sprache - ruhe)))


def stillen_finden(weg, schwelle_db, mindest=0.35):
    p = subprocess.run(["ffmpeg", "-v", "info", "-i", str(weg), "-af",
                        f"silencedetect=noise={schwelle_db}dB:d={mindest}",
                        "-f", "null", "-"], capture_output=True, text=True)
    stillen, start = [], None
    for zeile in p.stderr.splitlines():
        if "silence_start:" in zeile:
            start = float(zeile.split("silence_start:")[1].split()[0])
        elif "silence_end:" in zeile and start is not None:
            stillen.append((start, float(zeile.split("silence_end:")[1].split()[0])))
            start = None
    return stillen


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("quelle")
    ap.add_argument("--worte", help="worte.json aus transkript.py")
    ap.add_argument("--aus", required=True)
    ap.add_argument("--behalte-fueller", action="store_true")
    ap.add_argument("--pause-max", type=float, default=STILLE_MAX)
    a = ap.parse_args()

    quelle = Path(a.quelle)
    gesamt, fps = dauer_von(quelle), bildrate(quelle)
    worte = json.loads(Path(a.worte).read_text(encoding="utf-8")) if a.worte else []
    for w in worte:
        w["_fueller"] = w["wort"].strip(" ,.!?").lower() in FUELLER

    schwelle = stilleschwelle(quelle)
    stillen = stillen_finden(quelle, schwelle)
    print(f"  Stilleschwelle {schwelle:.0f} dB, {len(stillen)} Stillen gefunden")

    weg = []
    if not a.behalte_fueller:
        for w in worte:
            if w["_fueller"]:
                weg.append((w["von"] - RAND, w["bis"] + RAND))
    for von, bis in stillen:
        if bis - von > a.pause_max:
            ueber = (bis - von) - STILLE_REST
            mitte = (von + bis) / 2.0
            weg.append((mitte - ueber / 2.0, mitte + ueber / 2.0))

    # Die wichtigste Sperre: was ein Wort beruehrt, wird nie entfernt. Die
    # Pegelmessung kann sich irren, das Transkript weiss, wo gesprochen wurde.
    gesprochen = [(w["von"], w["bis"]) for w in worte if not w["_fueller"]]
    def beruehrt(v, b):
        return any(not (b <= wv + 0.02 or v >= wb - 0.02) for wv, wb in gesprochen)
    vorher = len(weg)
    weg = [(v, b) for v, b in weg if not beruehrt(v, b)]
    if vorher != len(weg):
        print(f"  {vorher - len(weg)} Schnitte verworfen, weil sie Woerter beruehrt haetten")

    # Abschnitte bilden und aufs Bildraster runden
    weg.sort()
    zusammen, absch, zeiger = [], [], 0.0
    for v, b in weg:
        if zusammen and v <= zusammen[-1][1]:
            zusammen[-1] = (zusammen[-1][0], max(zusammen[-1][1], b))
        else:
            zusammen.append((v, b))
    for v, b in zusammen:
        if v - zeiger > 0.12:
            absch.append((zeiger, v))
        zeiger = max(zeiger, b)
    if gesamt - zeiger > 0.12:
        absch.append((zeiger, gesamt))
    absch = [(round(v * fps) / fps, round(b * fps) / fps) for v, b in absch] or [(0.0, gesamt)]
    neu = sum(b - v for v, b in absch)
    print(f"  {len(absch)} Abschnitte, {neu:.2f}s statt {gesamt:.2f}s "
          f"({(neu/gesamt-1)*100:+.0f}%)")

    # Bild und Ton in einem Durchgang. Die Uebergaenge sind kurze Kreuzblenden
    # mit gleicher Leistung - Ausblenden auf Null tauscht Knackser gegen Loecher.
    ein, vteile, ateile = [], [], []
    for i, (v, b) in enumerate(absch):
        ein += ["-ss", f"{v:.4f}", "-to", f"{b:.4f}", "-i", str(quelle)]
        vteile.append(f"[{i}:v]setpts=PTS-STARTPTS,fps={fps}[v{i}]")
        ateile.append(f"[{i}:a]asetpts=PTS-STARTPTS[a{i}]")
    n = len(absch)
    fc = vteile + ateile
    fc.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vout]")
    if n == 1:
        fc.append("[a0]anull[aout]")
    else:
        letzte = "a0"
        for i in range(1, n):
            fc.append(f"[{letzte}][a{i}]acrossfade=d=0.020:c1=tri:c2=tri[ax{i}]")
            letzte = f"ax{i}"
        fc.append(f"[{letzte}]anull[aout]")
    lauf(["ffmpeg", "-v", "error", "-y", *ein, "-filter_complex", ";".join(fc),
          "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-crf", "18",
          "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k",
          a.aus])

    # Die Schnittliste daneben legen - danach laesst sich alles nachvollziehen.
    Path(a.aus).with_suffix(".schnitt.json").write_text(
        json.dumps({"quelle": str(quelle), "fps": fps, "schwelle_db": round(schwelle, 1),
                    "abschnitte": [{"von": v, "bis": b} for v, b in absch]},
                   indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\n  {a.aus}  ({dauer_von(a.aus):.2f}s)")


if __name__ == "__main__":
    main()
