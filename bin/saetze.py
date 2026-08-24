#!/usr/bin/env python3
"""Satzgrenzen mit Zeiten - die Bruecke von der Stimme zum Bild.

Bisher hing jedes Bildelement an einem einzelnen Wort ("Genau", "Abends",
"verkaufen"). Das hat die Richtung umgedreht: der Sprechertext wurde so
formuliert, dass die Szene ihre Ankerwoerter findet - Video, das dem Text
vorschreibt, wie er zu klingen hat. Und es brach ab, sobald die Erkennung
sich verhoerte ("Ratten" statt "Raten").

Ein Satz ist die natuerliche Einheit: er ist eine Aussage, und das Bild
zeigt eine Aussage.

Die Grenzen kommen aus dem geschriebenen Text, nie aus der Erkennung. Die
verschluckt Satzzeichen und zieht Saetze zusammen - dann verschiebt sich
jede Satznummer dahinter, und die halbe Szene sitzt falsch. Wer den Text
geschrieben hat, kennt seine Saetze; er gibt sie in rede.json vor.

    saetze.py <worte.json> <sprecher.txt> <saetze.json> [rede.json]
"""

import difflib, json, pathlib, re, sys

TAG = re.compile(r"\[[a-zA-Z _-]+\]")
ENDE = (".", "!", "?", "…")


def ohne_marken(text):
    """Ausdrucksmarken wie [emphatic] raus - die spricht niemand."""
    return re.sub(r"[ \t]{2,}", " ", TAG.sub("", text)).strip()


def _norm(x):
    return re.sub(r"[^\wäöüß]", "", x.lower())


def wortzeiten(worte, soll):
    """Jedem Wort des geschriebenen Textes eine Zeit geben.

    Die Erkennung hoert anders, als geschrieben wurde: sie zieht Woerter
    zusammen, verhoert sich, verschluckt Satzzeichen. Deshalb wird nicht
    ihr Ergebnis zerlegt, sondern der geschriebene Text auf ihre Zeiten
    gelegt. Stellen ohne Entsprechung bekommen die Zeit anteilig aus der
    Luecke - besser als gar keine.
    """
    ist = [w["wort"] for w in worte]
    ab = difflib.SequenceMatcher(a=[_norm(x) for x in ist], b=[_norm(x) for x in soll])
    zeiten = [None] * len(soll)
    for tag, i1, i2, j1, j2 in ab.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                zeiten[j1 + k] = (worte[i1 + k]["von"], worte[i1 + k]["bis"])
        elif tag in ("replace", "insert"):
            if i2 > i1:
                a0, a1 = worte[i1]["von"], worte[i2 - 1]["bis"]
            else:
                a0 = worte[i1 - 1]["bis"] if i1 > 0 else 0.0
                a1 = worte[i1]["von"] if i1 < len(worte) else a0 + 0.3
            n = max(1, j2 - j1)
            for k in range(j2 - j1):
                zeiten[j1 + k] = (a0 + (a1 - a0) * k / n, a0 + (a1 - a0) * (k + 1) / n)
        # "delete": gehoert, aber nicht geschrieben - ignorieren.
    # Restluecken schliessen, damit keine Zeit fehlt.
    letzte = 0.0
    for i, z in enumerate(zeiten):
        if z is None:
            naechste = next((zeiten[j][0] for j in range(i + 1, len(zeiten)) if zeiten[j]), letzte + 0.3)
            zeiten[i] = (letzte, max(letzte, naechste))
        letzte = zeiten[i][1]
    return zeiten


def nach_satzzeichen(text):
    saetze, akt = [], []
    for w in text.split():
        akt.append(w)
        if w.rstrip("\"'»“”").endswith(ENDE):
            saetze.append(" ".join(akt)); akt = []
    if akt:
        saetze.append(" ".join(akt))
    return saetze


def bauen(worte, sprechertext, rede=None):
    sauber = ohne_marken(sprechertext)
    # rede.json ist massgeblich. Nur wenn es fehlt, wird geraten.
    soll_saetze = [ohne_marken(s) for s in rede] if rede else nach_satzzeichen(sauber)
    woerter, grenzen = [], []
    for s in soll_saetze:
        teile = s.split()
        grenzen.append((len(woerter), len(woerter) + len(teile)))
        woerter += teile

    zeiten = wortzeiten(worte, woerter)
    aus = []
    for nr, (s, (a, b)) in enumerate(zip(soll_saetze, grenzen)):
        if a >= b:
            continue
        aus.append({"nr": len(aus), "text": s,
                    "von": round(zeiten[a][0], 3), "bis": round(zeiten[b - 1][1], 3)})
    return aus


def main():
    if len(sys.argv) not in (4, 5):
        sys.exit(__doc__.strip().splitlines()[-1])
    worte = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    text = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")
    rede = None
    if len(sys.argv) == 5 and pathlib.Path(sys.argv[4]).exists():
        rede = json.loads(pathlib.Path(sys.argv[4]).read_text(encoding="utf-8"))
    s = bauen(worte, text, rede)
    pathlib.Path(sys.argv[3]).write_text(
        json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"  {len(s)} Saetze mit Zeiten"
          + (" (aus rede.json)" if rede else " (nach Satzzeichen geraten)"))


if __name__ == "__main__":
    main()
