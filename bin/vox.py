#!/usr/bin/env python3
"""vox - Erklaervideos im Papier-Collagen-Stil aus einer Spec-Datei.

    vox.py neu    mein-video/       Projekt mit Beispiel anlegen

  Szene aus einer Spec bauen:
    vox.py bilder mein-video/       Fotos freistellen und rastern
    vox.py szene  mein-video/       Szene rendern (ohne Ton)

  Vorhandenes Material schneiden:
    vox.py schnitt mein-video/      Fuellwoerter und totes Band entfernen
    vox.py untertitel mein-video/   Untertitel einbrennen

  Beides:
    vox.py ton    mein-video/       Ton polieren, Bett drunter, normalisieren
    vox.py bauen  mein-video/       alles nacheinander

Gerendert wird mit HyperFrames (github.com/heygen-com/hyperframes). Pfad wird
gesucht oder ueber die Umgebungsvariable HYPERFRAMES gesetzt.
"""
import argparse, json, math, os, shutil, subprocess, sys, tempfile
from pathlib import Path

HIER = Path(__file__).resolve().parent
VORLAGE = HIER.parent / "vorlage"
BEISPIEL = HIER.parent / "beispiel"


def lauf(cmd, **kw):
    p = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)
    if p.returncode:
        sys.exit(f"fehlgeschlagen: {' '.join(str(c) for c in cmd[:6])} ...\n{p.stderr[-1500:]}")
    return p


def spec_lesen(projekt: Path):
    weg = projekt / "spec.json"
    if not weg.exists():
        sys.exit(f"{weg} fehlt. Anlegen mit:  vox.py neu {projekt}")
    return json.loads(weg.read_text(encoding="utf-8"))


# Ein Fehler im Szenen-Skript bricht die Szene ab, aber nicht den Rendervorgang:
# HyperFrames kodiert brav weiter und liefert ein Video vollen Umfangs, in dem
# nur die Haelfte des Aufbaus steht. Genau so ist ein Reel entstanden, bei dem
# ein einziges falsches Ankerwort alles nach der Uhr verschluckt hat - ohne
# eine Zeile Fehlermeldung. Deshalb malt die Wache den Fehler ins Bild.
WACHE = """<script>
window.addEventListener("error", function (e) {
  var d = document.createElement("div");
  d.setAttribute("style", "position:fixed;inset:0;z-index:999999;background:#B00020;"
    + "color:#fff;font:700 34px/1.4 ui-monospace,monospace;padding:70px;"
    + "white-space:pre-wrap;word-break:break-word");
  d.textContent = "SZENE ABGEBROCHEN\\n\\n" + e.message + "\\n\\n"
    + (e.filename || "") + ":" + (e.lineno || "");
  (document.body || document.documentElement).appendChild(d);
});
</script>
"""

def hyperframes_finden():
    for p in (os.environ.get("HYPERFRAMES"),
              Path.home() / "projects/hyperframes/packages/cli/bin/hyperframes.mjs",
              Path.home() / "hyperframes/packages/cli/bin/hyperframes.mjs"):
        if p and Path(p).exists():
            return Path(p)
    return None


# ---------------------------------------------------------------- Bilder ----
# Muss zu STILE in vorlage/szene.js passen: welche Stile stehen auf dunklem
# Grund und brauchen deshalb umgekehrte Rasterfotos.
DUNKLE_STILE = {"dunkel", "blaupause"}


def bilder(projekt: Path, spec):
    """Fotos freistellen und ins Punktraster legen."""
    roh = projekt / "bilder"
    if not roh.is_dir():
        print("  kein Ordner bilder/ - uebersprungen"); return
    arbeit = projekt / "arbeit"; arbeit.mkdir(exist_ok=True)
    gewuenscht = {b["datei"] for f in spec.get("felder", [])
                  for b in (f.get("bilder") or []) if b.get("datei")}
    if not gewuenscht:
        # Eine frei geschriebene Szene sagt nicht in der Spec, welche Bilder sie
        # braucht - dann wird alles aufbereitet, was in bilder/ liegt.
        gewuenscht = {q.stem + ".png" for q in sorted(roh.iterdir())
                      if q.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")}
    python = os.environ.get("VOX_PYTHON", sys.executable)
    for name in sorted(gewuenscht):
        ziel = arbeit / name
        quelle = next((q for q in roh.glob(Path(name).stem + ".*")), None)
        if quelle is None:
            print(f"  {name}: keine Quelle in bilder/ - uebersprungen"); continue
        with tempfile.TemporaryDirectory() as tmp:
            frei = Path(tmp) / "frei.png"
            p = subprocess.run([python, HIER / "freistellen.py", quelle, frei, "--eng"],
                               capture_output=True, text=True)
            eingang = frei if p.returncode == 0 else quelle
            if p.returncode:
                print(f"  {name}: ohne Freisteller ({p.stderr.strip().splitlines()[0][:60]})")
            befehl = [sys.executable, HIER / "rasterbild.py", eingang, ziel,
                      "--breite", str(spec.get("rasterbreite", 640))]
            if spec.get("fotos_negativ", spec.get("stil") in DUNKLE_STILE):
                befehl.append("--negativ")
            lauf(befehl)
        print(f"  {name} fertig")


# ----------------------------------------------------------------- Szene ----
def szene(projekt: Path, spec):
    """Szene bauen und mit HyperFrames rendern."""
    hf = hyperframes_finden()
    if not hf:
        sys.exit("HyperFrames nicht gefunden.\n"
                 "  git clone https://github.com/heygen-com/hyperframes ~/projects/hyperframes\n"
                 "  cd ~/projects/hyperframes && pnpm install && pnpm build\n"
                 "Oder den Pfad zur hyperframes.mjs in HYPERFRAMES setzen.")
    gsap = gsap_da()
    if not gsap:
        sys.exit("gsap.min.js nicht gefunden. Datei nach vorlage/gsap.min.js legen "
                 "oder den Pfad in GSAP setzen.")

    arbeit = projekt / "arbeit"; arbeit.mkdir(exist_ok=True)
    # HyperFrames sucht index.html - und der Lint liest den Quelltext dieser
    # einen Datei. Steht die Zeitleiste in einer externen .js, findet er sie
    # nicht. Also wird alles hineingeschrieben.
    huelle = (VORLAGE / "szene.html").read_text(encoding="utf-8")
    laufzeit = (VORLAGE / "vox.js").read_text(encoding="utf-8")
    # data-duration und die Masse liest HyperFrames aus dem statischen HTML,
    # bevor irgendein Skript laeuft. Sie zur Laufzeit zu setzen kommt zu spaet.
    b, h = spec.get("masse", [1920, 1080])
    huelle = (huelle
              .replace('data-duration="10.000"', f'data-duration="{spec.get("dauer", 30):.3f}"')
              .replace('data-width="1920"', f'data-width="{b}"')
              .replace('data-height="1080"', f'data-height="{h}"'))
    # Eine eigene Szene im Projekt schlaegt die mitgelieferte Rasteranordnung.
    # Genau dafuer ist die Trennung da: raster.js ist EIN Weg, nicht DER Weg.
    # Geprueft aufgeloeste Fakten, falls vorhanden. Sie stehen VOR der Szene,
    # damit sie beim Aufbau schon da sind.
    faktenweg = projekt / "fakten.js"
    fakten = faktenweg.read_text(encoding="utf-8") if faktenweg.exists() else ""
    if fakten:
        print("  Fakten: aus fakten.js (geprueft aufgeloest)")
    eigen = projekt / "szene.js"
    if eigen.exists():
        anordnung = eigen.read_text(encoding="utf-8")
        print("  Anordnung: szene.js aus dem Projekt")
    else:
        anordnung = (VORLAGE / "raster.js").read_text(encoding="utf-8")
        print("  Anordnung: Raster (vorlage/raster.js)")
    spec_js = "window.SPEC = " + json.dumps(spec, ensure_ascii=False, indent=1) + ";"
    # Wortzeiten mitgeben, damit die Szene nach Woertern fragen kann statt
    # nach Sekunden. Ohne das ist jede neue Sprachspur Handarbeit.
    wweg = projekt / "worte.json"
    if wweg.exists():
        spec_js += ("\nwindow.WORTE = "
                    + wweg.read_text(encoding="utf-8").strip().rstrip(";") + ";")
        print("  Wortzeiten: worte.json")
    bweg = projekt / "bezug.json"
    if bweg.exists():
        # Welche Fakten diese Szene meint - damit eine Vorlage allgemein
        # bleiben kann statt Schluessel fest einzubauen.
        spec_js += "\nwindow.BEZUG = " + bweg.read_text(encoding="utf-8").strip() + ";"
    huelle = huelle.replace(
        '<script src="spec.js"></script>\n<script src="vox.js"></script>\n'
        '<script src="szene.js"></script>',
        WACHE
        + f"<script>\n{spec_js}\n</script>\n<script>\n{laufzeit}\n</script>\n"
        + (f"<script>\n{fakten}\n</script>\n" if fakten else "")
        + f"<script>\n{anordnung}\n</script>")
    shutil.copy(gsap, arbeit / "gsap.min.js")
    # Bilddateien aus dem Projekt mitnehmen. Ohne das laeuft ein
    # url('foto.jpg') in der Szene ins Leere - der Renderer meldet nichts,
    # das Bild ist einfach nicht da.
    for q in projekt.iterdir():
        if q.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".svg"):
            shutil.copy(q, arbeit / q.name)
    (arbeit / "index.html").write_text(huelle, encoding="utf-8")
    shutil.copy(gsap, arbeit / "gsap.min.js")
    # Bilddateien aus dem Projekt mitnehmen. Ohne das laeuft ein
    # url('foto.jpg') in der Szene ins Leere - der Renderer meldet nichts,
    # das Bild ist einfach nicht da.
    for q in projekt.iterdir():
        if q.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".svg"):
            shutil.copy(q, arbeit / q.name)
    (arbeit / "hyperframes.json").write_text('{"paths":{"assets":"."}}', encoding="utf-8")

    aus = projekt / "aus"; aus.mkdir(exist_ok=True)
    lauf(["node", hf, "lint", arbeit])
    if spec.get("ueberlagerung"):
        # ProRes 4444: WebM verliert den Alphakanal stillschweigend, und ohne
        # Alpha deckt die Ebene das Material vollstaendig zu.
        ziel = aus / "ebene.mov"
        lauf(["node", hf, "render", arbeit, "-o", ziel, "--format", "mov"])
        pf = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                             "-show_entries", "stream=pix_fmt", "-of", "csv=p=0", str(ziel)],
                            capture_output=True, text=True).stdout.strip()
        if not pf.startswith(("yuva", "rgba", "bgra", "argb", "gbrap")):
            sys.exit(f"FEHLER: Ebene ohne Alpha (pix_fmt={pf}) - sie wuerde alles zudecken.")
        print(f"  {ziel}  (Alpha: {pf})")
    else:
        ziel = aus / "szene.mp4"
        lauf(["node", hf, "render", arbeit, "-o", ziel, "--format", "mp4", "--quality", "high"])
        print(f"  {ziel}")
    return ziel


def gsap_da():
    for p in (os.environ.get("GSAP"), VORLAGE / "gsap.min.js",
              Path.home() / "projects/schnittraum/workflows/gsap.min.js"):
        if p and Path(p).exists():
            return Path(p)
    return None


# -------------------------------------------------------------- Material ----
def worte_holen(projekt: Path, spec, quelle: Path) -> Path | None:
    """Wortzeiten besorgen - aus einer vorhandenen Datei oder per whisper."""
    ziel = projekt / "arbeit" / "worte.json"
    ziel.parent.mkdir(exist_ok=True)
    if ziel.exists():
        return ziel
    eigene = projekt / "worte.json"
    if eigene.exists():
        shutil.copy(eigene, ziel); return ziel
    tr = (spec.get("video") or {}).get("transkript") or {}
    modell = tr.get("modell") or os.environ.get("WHISPER_MODELL")
    if not modell or not Path(modell).exists():
        print("  ohne Transkript (kein Modell) - es wird nur nach Pegel geschnitten")
        return None
    befehl = [sys.executable, HIER / "transkript.py", quelle,
              "--modell", modell, "--sprache", tr.get("sprache", "auto")]
    if tr.get("whisper"):
        befehl += ["--whisper", tr["whisper"]]
    p = subprocess.run([str(c) for c in befehl], capture_output=True, text=True)
    if p.returncode:
        print(f"  Transkript fehlgeschlagen: {p.stderr.strip().splitlines()[-1][:70]}")
        return None
    ziel.write_text(p.stdout, encoding="utf-8")
    return ziel


def schnitt(projekt: Path, spec):
    v = spec.get("video") or {}
    if not v.get("quelle"):
        sys.exit('In der Spec fehlt "video": {"quelle": "roh.mp4"}')
    quelle = projekt / v["quelle"]
    if not quelle.exists():
        sys.exit(f"Quelle fehlt: {quelle}")
    aus = projekt / "aus"; aus.mkdir(exist_ok=True)
    ziel = aus / "schnitt.mp4"
    worte = worte_holen(projekt, spec, quelle)
    befehl = [sys.executable, HIER / "schnitt.py", quelle, "--aus", ziel]
    if worte:
        befehl += ["--worte", worte]
    if v.get("behalte_fueller"):
        befehl.append("--behalte-fueller")
    if v.get("pause_max"):
        befehl += ["--pause-max", str(v["pause_max"])]
    if v.get("bild"):
        befehl += ["--bild", v["bild"]]
    p = subprocess.run([str(c) for c in befehl])
    if p.returncode:
        sys.exit("Schnitt fehlgeschlagen")
    return ziel


def untertitel(projekt: Path, spec):
    v = spec.get("video") or {}
    aus = projekt / "aus"
    quelle = aus / "schnitt.mp4"
    if not quelle.exists():
        quelle = projekt / v.get("quelle", "")
    if not quelle.exists():
        sys.exit("Weder aus/schnitt.mp4 noch video.quelle vorhanden")
    worte = worte_holen(projekt, spec, quelle)
    if not worte:
        sys.exit("Ohne Wortzeiten keine Untertitel - Modell in video.transkript.modell setzen")
    ziel = aus / "untertitelt.mp4"
    p = subprocess.run([str(c) for c in
                        [sys.executable, HIER / "untertitel.py", quelle, "--worte", worte,
                         "--aus", ziel, "--stil", spec.get("stil", "papier"),
                         "--gruppe", str(v.get("gruppe", 3))]])
    if p.returncode:
        sys.exit("Untertitel fehlgeschlagen")
    return ziel


def auflegen(projekt: Path, spec):
    """Die gerenderte Ebene auf das Material legen."""
    aus = projekt / "aus"
    ebene = aus / "ebene.mov"
    if not ebene.exists():
        sys.exit("aus/ebene.mov fehlt - erst `szene` mit \"ueberlagerung\": true laufen lassen")
    stufen = ["untertitelt.mp4", "schnitt.mp4"]
    unten = next((aus / s for s in stufen if (aus / s).exists()), None)
    if unten is None:
        v = (spec.get("video") or {}).get("quelle")
        unten = projekt / v if v else None
    if not unten or not unten.exists():
        sys.exit("kein Material gefunden - video.quelle setzen oder erst schneiden")
    ziel = aus / "belegt.mp4"
    masse = lauf(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                  "stream=width,height", "-of", "csv=p=0", unten]).stdout.strip().split(",")
    vb, vh = int(masse[0]), int(masse[1])
    # Die Ebene entsteht in der Groesse aus der Spec. Weicht das Material ab,
    # wuerde overlay nur die linke obere Ecke zeigen.
    print(f"  {unten.name} + {ebene.name} -> {vb}x{vh}")
    lauf(["ffmpeg", "-v", "error", "-y", "-i", unten, "-i", ebene,
          "-filter_complex", f"[1:v]scale={vb}:{vh}[e];[0:v][e]overlay=0:0:format=auto[v]",
          "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-crf", "18",
          "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "copy", ziel])
    # Stoesse aufs Bild: wenn im Ton "dynamic" faellt, soll auch am Bild
    # etwas passieren - nicht nur eine Grafik daneben.
    for i, st in enumerate(spec.get("stoesse") or []):
        zwischen = aus / f"stoss-{i}.mp4"
        befehl = [sys.executable, HIER / "dynamik.py", ziel, zwischen,
                  "--von", str(st["von"]), "--bis", str(st["bis"])]
        if st.get("punch"):
            befehl += ["--punch"] + [str(x) for x in st["punch"]]
        if st.get("staerke"):
            befehl += ["--staerke", str(st["staerke"])]
        p = subprocess.run([str(c) for c in befehl])
        if p.returncode:
            sys.exit("Stoss fehlgeschlagen")
        zwischen.replace(ziel)
    print(f"  {ziel}")
    return ziel


# ------------------------------------------------------------------- Ton ----
STIMMUNGEN = {   # Akkord in Hertz, tief genug, dass Sprache darueber frei bleibt
    "ruhig":    [110.00, 164.81, 220.00, 329.63],
    "warm":     [98.00, 146.83, 196.00, 293.66],
    "spannung": [87.31, 116.54, 174.61, 233.08],
    "hell":     [130.81, 196.00, 261.63, 392.00],
}


def bett_bauen(stimmung, dauer, ziel: Path):
    """Flaches Bett aus gestimmten Sinustoenen - kein Sample, keine fremden Rechte."""
    toene = STIMMUNGEN.get(stimmung, STIMMUNGEN["ruhig"])
    ein, teile = [], []
    for i, hz in enumerate(toene):
        ein += ["-f", "lavfi", "-t", f"{dauer:.2f}", "-i", f"sine=frequency={hz}:sample_rate=48000"]
        teile.append(f"[{i}:a]volume={0.5/len(toene):.3f},tremolo=f=0.13:d=0.25[t{i}]")
    n = len(toene)
    ein += ["-f", "lavfi", "-t", f"{dauer:.2f}", "-i", "anoisesrc=color=brown:sample_rate=48000"]
    teile.append(f"[{n}:a]lowpass=f=900,volume=0.05[rausch]")
    misch = "".join(f"[t{i}]" for i in range(n)) + "[rausch]" + \
            f"amix=inputs={n+1}:normalize=0,alimiter=limit=0.7[aus]"
    lauf(["ffmpeg", "-v", "error", "-y", *ein, "-filter_complex", ";".join(teile + [misch]),
          "-map", "[aus]", "-c:a", "libmp3lame", "-b:a", "192k", ziel])


def hat_ton(datei) -> bool:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0",
                        "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(datei)],
                       capture_output=True, text=True)
    return "audio" in r.stdout


def lautheit(datei) -> float:
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(datei),
                        "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    for zeile in reversed(p.stderr.splitlines()):
        if zeile.strip().startswith("I:") and "LUFS" in zeile:
            return float(zeile.split()[1])
    return float("nan")


def ton(projekt: Path, spec, video: Path):
    t = spec.get("ton") or {}
    aus = projekt / "aus"
    ziel = aus / (spec.get("name", "film") + ".mp4")
    # Bei geschnittenem Material steckt die Stimme schon im Video - dann ist
    # die eigene Tonspur die Quelle, nicht eine separate Datei.
    if t.get("stimme"):
        stimm_weg = projekt / t["stimme"]
        if not stimm_weg.exists():
            sys.exit(f"Stimme fehlt: {stimm_weg}")
    elif hat_ton(video):
        stimm_weg = video
        print("  Stimme kommt aus der Tonspur des Videos")
    elif t.get("bett"):
        # Ohne Sprecher, aber mit Bett: dann traegt das Bett allein. Frueher
        # fiel dieser Fall durch und das Video blieb stumm.
        stimm_weg = None
        print("  ohne Sprecher - nur Musikbett")
    else:
        shutil.copy(video, ziel); print(f"  ohne Ton\n\n  {ziel}"); return ziel

    dauer = spec.get("dauer", 30)
    roh = projekt / "arbeit" / "roh.mp4"
    poliert = projekt / "arbeit" / "stimme.wav"
    if stimm_weg:
        lauf(["ffmpeg", "-v", "error", "-y", "-i", stimm_weg,
              "-af", "highpass=f=85,acompressor=threshold=-20dB:ratio=3:attack=8:release=180,"
                     "alimiter=limit=0.94",
              "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", poliert])

    if t.get("bett") and not stimm_weg:
        bett = projekt / "arbeit" / "bett.mp3"
        bett_bauen(t["bett"], dauer + 2, bett)
        lauf(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", bett,
              "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "pcm_s16le",
              "-shortest", roh])
    elif t.get("bett"):
        bett = projekt / "arbeit" / "bett.mp3"
        bett_bauen(t["bett"], dauer + 2, bett)
        # Das Bett gehoert rund 20 LU unter die Stimme. Fest eingestellte
        # Dezibel treffen das nicht - also messen und daraus rechnen.
        lu_stimme, lu_bett = lautheit(poliert), lautheit(bett)
        gain = (lu_stimme - t.get("abstand", 20)) - lu_bett
        print(f"  Stimme {lu_stimme:.1f} LUFS, Bett {lu_bett:.1f} LUFS -> {gain:+.1f} dB")
        fc = (f"[2:a]atrim=0:{dauer:.2f},volume={gain:.1f}dB,asetpts=PTS-STARTPTS[bett];"
              f"[bett][1:a]sidechaincompress=threshold=0.015:ratio=12:attack=5:release=300[duck];"
              f"[1:a][duck]amix=inputs=2:duration=first:normalize=0[mix]")
        lauf(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", poliert, "-i", bett,
              "-filter_complex", fc, "-map", "0:v", "-map", "[mix]",
              "-c:v", "copy", "-c:a", "pcm_s16le", "-shortest", roh])
    else:
        lauf(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", poliert,
              "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "pcm_s16le",
              "-shortest", roh])

    # Zweistufige Lautheit: einstufiges loudnorm schaetzt nur und liegt daneben.
    ziel_lufs = t.get("ziel_lufs", -14)
    mess = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(roh), "-af",
                           f"loudnorm=I={ziel_lufs}:TP=-1.5:LRA=11:print_format=json",
                           "-f", "null", "-"], capture_output=True, text=True).stderr
    af = f"loudnorm=I={ziel_lufs}:TP=-1.5:LRA=11"
    try:
        m = json.loads(mess[mess.rindex("{"):mess.rindex("}") + 1])
        af += (f":measured_I={m['input_i']}:measured_TP={m['input_tp']}"
               f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}"
               f":offset={m['target_offset']}:linear=true")
    except (ValueError, KeyError):
        print("  Messlauf unbrauchbar, einstufig normalisiert")
    # loudnorm rechnet intern mit 192 kHz und zieht die Ausgabe mit hoch.
    af += ",aresample=48000"
    lauf(["ffmpeg", "-v", "error", "-y", "-i", roh, "-af", af, "-c:v", "copy",
          "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", ziel])
    print(f"  Lautheit {lautheit(ziel):.1f} LUFS\n\n  {ziel}")
    return ziel


# ------------------------------------------------------------------ neu -----
def neu(projekt: Path, raster=False):
    if projekt.exists() and any(projekt.iterdir()):
        sys.exit(f"{projekt} ist nicht leer")
    (projekt / "bilder").mkdir(parents=True, exist_ok=True)
    if raster:
        shutil.copy(BEISPIEL / "spec.json", projekt / "spec.json")
        print(f"Angelegt: {projekt} (Rasteranordnung)\n"
              f"  spec.json anpassen, Fotos nach bilder/ legen, dann:\n"
              f"    vox.py bauen {projekt}")
        return
    # Standard ist die eigene Szene. Das Raster ist die Ausnahme, nicht die
    # Regel - sonst sieht jedes Video gleich aus.
    (projekt / "spec.json").write_text(json.dumps({
        "name": projekt.name, "masse": [1920, 1080], "fps": 30, "dauer": 20.0,
        "stil": "papier", "ton": {"bett": "ruhig", "ziel_lufs": -14},
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    shutil.copy(VORLAGE / "szene-geruest.js", projekt / "szene.js")
    print(f"Angelegt: {projekt}\n"
          f"  szene.js ist ein Geruest - die Anordnung baut man am Inhalt entlang.\n"
          f"  API: docs/laufzeit.md\n"
          f"  Fertiges Raster stattdessen:  vox.py neu {projekt} --raster\n\n"
          f"    vox.py bauen {projekt}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("befehl", choices=["neu", "bilder", "szene", "schnitt",
                                       "untertitel", "auflegen", "ton", "bauen"])
    ap.add_argument("projekt")
    ap.add_argument("--raster", action="store_true",
                    help="mitgelieferte Rasteranordnung statt einer eigenen Szene")
    a = ap.parse_args()
    projekt = Path(a.projekt).resolve()

    if a.befehl == "neu":
        return neu(projekt, a.raster)
    spec = spec_lesen(projekt)
    material = bool((spec.get("video") or {}).get("quelle"))

    if a.befehl == "bilder" or (a.befehl == "bauen" and not material):
        print("Bilder aufbereiten ..."); bilder(projekt, spec)
    if a.befehl == "szene" or (a.befehl == "bauen"
                               and (not material or spec.get("ueberlagerung"))):
        print("Szene rendern ..."); szene(projekt, spec)
    if a.befehl == "schnitt" or (a.befehl == "bauen" and material):
        print("Rohschnitt ..."); schnitt(projekt, spec)
    if a.befehl == "untertitel" or (a.befehl == "bauen" and material
                                    and (spec.get("video") or {}).get("untertitel")):
        print("Untertitel ..."); untertitel(projekt, spec)

    if a.befehl == "auflegen" or (a.befehl == "bauen" and spec.get("ueberlagerung") and material):
        print("Ebene auflegen ..."); auflegen(projekt, spec)

    if a.befehl in ("ton", "bauen"):
        # Die zuletzt entstandene Stufe ist die Grundlage.
        stufen = ["belegt.mp4", "untertitelt.mp4", "schnitt.mp4", "szene.mp4"]
        v = next((projekt / "aus" / s for s in stufen if (projekt / "aus" / s).exists()), None)
        if not v:
            sys.exit("Nichts zu vertonen - erst `szene` oder `schnitt` laufen lassen")
        print(f"Ton mischen (Grundlage {v.name}) ..."); ton(projekt, spec, v)


if __name__ == "__main__":
    main()
