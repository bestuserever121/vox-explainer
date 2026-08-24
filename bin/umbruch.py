#!/usr/bin/env python3
"""Untertitel nach den Netflix-Regeln setzen (deutsche Fassung).

Die Werte stammen aus dem Netflix Timed Text Style Guide, German:

  Zeichen je Zeile   42
  Zeilen je Karte     2
  Lesetempo          17 Zeichen/Sekunde (Erwachsene)
  Mindeststandzeit    5/6 Sekunde
  Hoechststandzeit    7 Sekunden
  Umbruch            entlang grammatischer Einheiten

Der letzte Punkt ist der, an dem es bisher schiefging: "5,2 / ct bekommen"
trennt die Zahl von ihrer Einheit, "Dafuer sollen / Sie ab 2027" reisst das
Subjekt vom Verb. Netflix formuliert das als Verbot, bestimmte Paare zu
trennen. Genau diese Paare stehen unten.

Fuer den Reel-Brenner ist die Zeile kuerzer als 42 Zeichen - der Satz steht
gross und mittig im Hochformat, nicht klein am unteren Rand. Die Regel bleibt
dieselbe, nur der Grenzwert ist ein anderer.
"""

import re

ZEICHEN_JE_ZEILE = 42
ZEILEN = 2
ZEICHEN_JE_SEKUNDE = 17.0
MIN_STANDZEIT = 5 / 6
MAX_STANDZEIT = 7.0
MIN_ABSTAND = 2 / 24  # zwei Bilder

SATZENDE = (".", "!", "?", "…", ".\"", "!\"", "?\"")

# --- Woerter, nach denen keine Zeile enden darf ---------------------------
# Sie eroeffnen eine Einheit, die erst das naechste Wort schliesst.
ARTIKEL = {"der", "die", "das", "den", "dem", "des", "ein", "eine", "einen",
           "einem", "einer", "eines", "kein", "keine", "keinen", "keinem",
           "keiner", "keines"}
PRAEPOSITION = {"in", "im", "an", "am", "auf", "für", "mit", "bei", "beim",
                "von", "vom", "zu", "zum", "zur", "aus", "nach", "über",
                "unter", "vor", "hinter", "neben", "zwischen", "um", "durch",
                "gegen", "ohne", "seit", "ab", "bis", "pro", "je", "trotz",
                "wegen", "während", "statt", "samt", "nebst", "binnen"}
BESITZ = {"mein", "meine", "meinen", "meinem", "meiner", "dein", "deine",
          "sein", "seine", "seinen", "seinem", "seiner", "ihr", "ihre",
          "ihren", "ihrem", "ihrer", "unser", "unsere", "euer", "eure",
          "dieser", "diese", "dieses", "diesem", "diesen", "jeder", "jede",
          "jedes", "jedem", "jeden", "welche", "welcher", "welches",
          "derselbe", "dieselbe", "dasselbe", "denselben", "demselben",
          "derselben", "dieselben", "jener", "jene", "jenes", "beide",
          "beiden", "alle", "allen", "aller", "manche", "solche", "solcher"}
# Gradwoerter haengen nach vorn: "exakt | dieselbe" reisst die Steigerung
# von dem ab, was gesteigert wird. Schwerer Fehler ist es nicht - deshalb
# eine mittlere Strafe wie bei der Satzklammer.
GRADWORT = {"exakt", "genau", "nur", "schon", "sehr", "ganz", "fast", "rund",
            "etwa", "knapp", "gut", "mehr", "weniger", "gleich", "besonders",
            "völlig", "ziemlich", "wirklich", "richtig", "echt", "kaum"}
# Nebensatz- und Reihungswoerter: die Zeile soll VOR ihnen brechen, nicht
# nach ihnen.
FUEGEWORT = {"und", "oder", "aber", "denn", "sondern", "dass", "weil", "wenn",
             "ob", "als", "wie", "da", "damit", "obwohl", "sobald", "solange",
             "bevor", "nachdem", "während", "falls", "sodass", "dennoch",
             "doch", "also", "deshalb", "darum", "trotzdem"}
# Hilfs- und Modalverben halten die Satzklammer auf; das Vollverb kommt spaeter.
KLAMMER = {"ist", "sind", "war", "waren", "hat", "haben", "hatte", "hatten",
           "wird", "werden", "wurde", "wurden", "kann", "können", "muss",
           "müssen", "soll", "sollen", "will", "wollen", "darf", "dürfen",
           "mag", "mögen", "sollte", "sollten", "könnte", "könnten"}
# Artikel und Praeposition von ihrem Bezugswort zu trennen ist ein Fehler;
# die Satzklammer zu trennen ist nur unschoen. Deshalb zwei Stufen.
NICHT_ANS_ZEILENENDE = ARTIKEL | PRAEPOSITION | BESITZ

# --- Woerter, mit denen keine Zeile beginnen darf -------------------------
# Sie gehoeren an das Wort davor.
EINHEIT = {"ct/kWh", "ct", "Cent", "Euro", "€", "Uhr", "Prozent", "%", "kWh",
           "kW", "kWp", "Watt", "Grad", "Jahre", "Jahren", "Jahr", "Meter",
           "mal", "Mal", "×", "x", "Stück", "Personen", "Leute"}

# Ein Personalpronomen im Nominativ gehoert an das Verb davor: "Abends holen |
# Sie ihn zurueck." liest sich falsch, "Abends holen Sie | ihn zurueck." nicht.
PRONOMEN = {"ich", "du", "er", "sie", "es", "wir", "ihr", "man"}

ZAHL = re.compile(r"^\d+([.,]\d+)?$")


def _blank(w):
    return w.strip("\"'»«„“”().,;:!?…-–—")


def _darf_enden(wort):
    """Darf eine Zeile nach diesem Wort enden?"""
    roh = wort.rstrip("\"'»“”")
    if roh.endswith((",", ";", ":")) or roh.endswith(SATZENDE):
        return True          # Satzzeichen sind immer eine gute Naht
    k = _blank(wort).lower()
    if not k:
        return True
    if k in NICHT_ANS_ZEILENENDE:
        return False
    if ZAHL.match(_blank(wort)):
        return False         # Zahl nie von ihrer Einheit trennen
    return True


def _klammer(wort):
    """Steht hier eine offene Satzklammer? Unschoen, aber kein Fehler."""
    return _blank(wort).lower() in KLAMMER


def _darf_beginnen(wort):
    """Darf eine Zeile mit diesem Wort beginnen?"""
    k = _blank(wort)
    if k in EINHEIT or k.lower() in {"uhr", "mal"}:
        return False
    if k.startswith("-") or wort.startswith(("-", "–", ",", ".")):
        return False
    return True


def zwei_zeilen(woerter, breite=ZEICHEN_JE_ZEILE):
    """Woerter auf hoechstens zwei Zeilen verteilen.

    Bewertet jede moegliche Naht statt die erste passende zu nehmen. Eine
    Naht am Komma ist besser als eine mitten in der Wendung, und eine
    ausgewogene Aufteilung besser als ein einzelnes Wort auf einer Zeile.
    """
    text = " ".join(woerter)
    # Kleine Toleranz: "Über das Siebenfache!" hat 21 Zeichen bei 20 Grenze.
    # Jede Trennung darin verstiesse gegen eine Regel - eine Zeile, die zwei
    # Zeichen ueberhaengt, ist das kleinere Uebel.
    if len(text) <= breite * 1.12:
        return [text]

    bester, bestwert = None, -1e9
    for i in range(1, len(woerter)):
        o, u = " ".join(woerter[:i]), " ".join(woerter[i:])
        # Dieselbe Toleranz wie oben. Ohne sie faellt die einzige gute Naht
        # ("Dafuer sollen Sie | ab 2027 5,2 ct bekommen.") wegen eines
        # Zeichens raus, und uebrig bleibt die verbotene nach "ab".
        if len(o) > breite * 1.12 or len(u) > breite * 1.12:
            continue
        wert = 0.0
        vor, nach = woerter[i - 1], woerter[i]
        # 1. Grammatische Naht - das ist die eigentliche Netflix-Regel.
        if not _darf_enden(vor):
            wert -= 100
        elif _klammer(vor):
            wert -= 35
        elif _blank(vor).lower() in GRADWORT:
            wert -= 45
        if not _darf_beginnen(nach):
            wert -= 100
        roh = vor.rstrip("\"'»“”")
        if roh.endswith(SATZENDE):
            wert += 40
        elif roh.endswith((",", ";", ":")):
            wert += 30
        if _blank(nach).lower() in FUEGEWORT:
            wert += 20       # vor dem Fuegewort brechen ist richtig
        if _blank(nach) in ("Sie",) or _blank(nach).lower() in PRONOMEN:
            wert -= 30       # das Pronomen bleibt beim Verb
        if _blank(vor).lower() in FUEGEWORT:
            wert -= 25       # danach zu brechen ist es nicht
        # 2. Kein einzelnes Wort allein auf einer Zeile.
        if i == 1 or i == len(woerter) - 1:
            wert -= 30
        if min(len(o), len(u)) < breite * 0.3:
            wert -= 15       # ein Woertchen allein liest sich wie ein Fehler
        # 3. Ausgewogen, obere Zeile eher kuerzer (Netflix bevorzugt das).
        wert -= abs(len(o) - len(u)) * 0.5
        if len(o) <= len(u):
            wert += 4
        if wert > bestwert:
            bester, bestwert = i, wert
    if bester is None:
        # Nichts passt in die Breite - hart in der Mitte trennen, damit
        # wenigstens nichts aus dem Bild laeuft.
        m = len(woerter) // 2 or 1
        bester = m
    return [" ".join(woerter[:bester]), " ".join(woerter[bester:])]


def karten(worte, breite=ZEICHEN_JE_ZEILE, zeilen=ZEILEN,
           zps=ZEICHEN_JE_SEKUNDE, min_s=MIN_STANDZEIT, max_s=MAX_STANDZEIT):
    """Wortliste zu Karten gruppieren.

    worte: [{"wort": str, "von": float, "bis": float}, ...]
    Rueckgabe: [{"von","bis","zeilen":[str,...]}, ...]

    Die Kartengrenze richtet sich nach drei Groessen in dieser Reihenfolge:
    Satzende, Platz (Zeichen mal Zeilen) und Lesetempo. Zu kurze Karten
    werden verschmolzen, zu lange spaeter beschnitten.
    """
    platz = breite * zeilen
    roh, akt = [], []

    def zu():
        if akt:
            roh.append(akt.copy()); akt.clear()

    for w in worte:
        akt.append(w)
        text = " ".join(x["wort"] for x in akt)
        if w["wort"].rstrip("\"'»“”").endswith(SATZENDE):
            zu(); continue
        if len(text) >= platz:
            # Lieber am letzten Satzzeichen trennen als mitten im Satz.
            naht = max((i for i, x in enumerate(akt[:-1])
                        if x["wort"].rstrip().endswith((",", ";", ":"))),
                       default=None)
            if naht is None:
                # Keine Satzzeichen-Naht: dann wenigstens nicht auf einem
                # Artikel oder einer Praeposition enden. Eine Karte, die mit
                # "ab" aufhoert, ist derselbe Fehler wie eine Zeile, die es
                # tut - nur eine Ebene hoeher.
                naht = next((i for i in range(len(akt) - 2, 0, -1)
                             if _darf_enden(akt[i]["wort"])), None)
            if naht is not None and naht >= 1:
                rest = akt[naht + 1:]; del akt[naht + 1:]
                zu(); akt.extend(rest)
            else:
                zu()
    zu()

    # Zu kurze Karten mit der naechsten verschmelzen - unter 5/6 Sekunde
    # flackert es nur, und Netflix verbietet es ohnehin.
    dicht = []
    for k in roh:
        if dicht:
            d = k[-1]["bis"] - k[0]["von"]
            zus = " ".join(x["wort"] for x in dicht[-1] + k)
            if d < min_s and len(zus) <= platz:
                dicht[-1].extend(k); continue
        dicht.append(k)

    # Eine Karte, die sich nicht auf zwei Zeilen bringen laesst, wird geteilt.
    # Sonst laeuft die zweite Zeile aus dem Bild - der Notausgang in
    # zwei_zeilen() ist keine Loesung, nur ein Auffangnetz.
    def passt(k):
        """Passt die Karte - und ist die Naht auch erlaubt?

        Nur auf die Laenge zu sehen reicht nicht: "Dafuer sollen Sie ab |
        2027 5,2 ct bekommen." passt in zwei Zeilen und ist trotzdem falsch,
        weil die erste auf einer Praeposition endet. Dann muss die Karte
        geteilt werden, nicht die Zeile.
        """
        w = [x["wort"] for x in k]
        z = zwei_zeilen(w, breite)
        if any(len(x) > breite * 1.12 for x in z):
            return False
        if len(z) == 2:
            letztes = z[0].split()[-1]
            if not _darf_enden(letztes) or not _darf_beginnen(z[1].split()[0]):
                return False
        return True

    # So lange teilen, bis jede Karte sitzt. Eine einzige Teilung reicht
    # nicht - eine Haelfte kann selbst wieder zu lang sein.
    offen, passend = list(dicht), []
    while offen:
        k = offen.pop(0)
        if len(k) < 2 or passt(k):
            passend.append(k); continue
        m = next((i for i in range(len(k) - 1, 0, -1)
                  if _darf_enden(k[i - 1]["wort"]) and _darf_beginnen(k[i]["wort"])),
                 len(k) // 2 or 1)
        offen[:0] = [k[:m], k[m:]]
    dicht = sorted(passend, key=lambda k: k[0]["von"])

    aus = []
    for i, k in enumerate(dicht):
        von, bis = k[0]["von"], k[-1]["bis"]
        text = " ".join(x["wort"] for x in k)
        # Lesetempo: 17 Zeichen je Sekunde. Reicht die Zeit nicht, wird bis
        # kurz vor die naechste Karte verlaengert.
        noetig = len(text) / zps
        grenze = (dicht[i + 1][0]["von"] - MIN_ABSTAND
                  if i + 1 < len(dicht) else von + max_s)
        if bis - von < noetig:
            bis = max(bis, von + noetig)
        bis = max(bis, von + min_s)
        bis = min(bis, von + max_s)
        # Zuletzt an die naechste Karte anstossen. Diese Klammer muss ganz am
        # Ende stehen - sonst schiebt die Mindeststandzeit sie wieder darueber
        # hinaus, und zwei Einblendungen ueberlappen.
        if grenze > von:
            bis = min(bis, grenze)
        if aus and von - aus[-1]["bis"] < MIN_ABSTAND:
            aus[-1]["bis"] = max(aus[-1]["von"] + min_s, von - MIN_ABSTAND)
        aus.append({"von": von, "bis": bis,
                    "zeilen": zwei_zeilen([x["wort"] for x in k], breite)})
    return aus
