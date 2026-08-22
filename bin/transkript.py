#!/usr/bin/env python3
"""Sprachaufnahme in Wortzeiten verwandeln (optional, braucht whisper.cpp).

Die Wortzeiten sagen, wann welcher Beat sitzen muss. Ohne sie muss man die
Zeitpunkte in der Spec von Hand eintragen - das geht auch, dauert nur laenger.

    transkript.py stimme.ogg --modell ~/models/ggml-large-v3.bin > worte.json

`--split-on-word` ist entscheidend: ohne den Schalter schneidet `--max-len 1`
nach Subwort-Tokens statt nach Woertern, und die Zeiten sind unbrauchbar.
"""
import argparse, json, shutil, subprocess, sys, tempfile
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ton")
    ap.add_argument("--modell", required=True)
    ap.add_argument("--sprache", default="auto")
    ap.add_argument("--whisper", default="whisper-cli")
    a = ap.parse_args()
    bin_ = shutil.which(a.whisper) or a.whisper
    if not Path(bin_).exists():
        sys.exit(f"whisper-cli nicht gefunden ({a.whisper}). "
                 f"Bauen: https://github.com/ggml-org/whisper.cpp")
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "ton.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.ton, "-ac", "1",
                        "-ar", "16000", "-c:a", "pcm_s16le", str(wav)], check=True)
        subprocess.run([bin_, "-m", a.modell, "-f", str(wav), "-l", a.sprache,
                        "--max-len", "1", "--split-on-word", "-oj",
                        "-of", str(Path(tmp) / "t")], check=True,
                       stdout=subprocess.DEVNULL)
        roh = json.loads((Path(tmp) / "t.json").read_text(encoding="utf-8"))
    worte = [{"wort": s["text"].strip(),
              "von": s["offsets"]["from"] / 1000.0,
              "bis": s["offsets"]["to"] / 1000.0}
             for s in roh.get("transcription", []) if s["text"].strip()]
    json.dump(worte, sys.stdout, ensure_ascii=False, indent=1)
    print(f"\n{len(worte)} Woerter", file=sys.stderr)


if __name__ == "__main__":
    main()
