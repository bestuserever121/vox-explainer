# The spec format

One JSON file describes the whole video.

## Top level

| Key | Meaning |
|---|---|
| `name` | output filename (`aus/<name>.mp4`) |
| `masse` | `[width, height]` in pixels |
| `fps` | frames per second |
| `dauer` | total length in seconds |
| `stil` | `papier` · `dunkel` · `blaupause` · `riso` (default `papier`) |
| `raster` | `[columns, rows]` of panels |
| `palette` | overrides for the style's colours — omit unless you mean it |
| `fotos_negativ` | invert the halftone photos (defaults from the style) |
| `felder` | the panels, in the order the camera visits them |
| `schluss` | `{ "bei": <s>, "dauer": <s> }` — pull out to the whole sheet |
| `ton` | audio settings |

Panels are placed in a snake path: left to right, down, right to left, down …
Arrows between consecutive panels are drawn automatically.

## Styles and palette

Each style ships a full palette under the same names, so switching `stil` never
requires touching the panels:

`papier` `tinte` `gedeckt` `gelb` `koralle` `lila` `gold`, plus the font
families `anzeige` (display) and `text`. Any panel field that takes a colour
accepts either a palette name or a raw CSS colour.

**A `palette` block in the spec overrides the style.** Ship one only when you
actually want to deviate — a full palette silently disables the style switch.

| style | ground | type treatment | texture |
|---|---|---|---|
| `papier` | warm off-white | print misregistration | creases + grain |
| `dunkel` | near-black | glow | soft colour clouds |
| `blaupause` | deep blue | hard drop shadow | graph paper grid |
| `riso` | cream | heavy duotone offset | strong grain |

Dark styles set `fotos_negativ` automatically — black halftone dots on a black
ground are invisible.

## Panels (`felder`)

Every panel takes `bei` (when the camera arrives, in seconds), an optional
`kicker` (small caps line above), and an optional `fahrt` (travel duration,
default 0.8 s).

### `titel`
Big typed headline, optionally with photos.

```jsonc
{ "art": "titel", "bei": 0.0, "kicker": "A comparison", "titel": "THE REASONS",
  "bilder": [ { "datei": "a.png", "hoehe": 560, "name": "LEFT", "strahl": "gelb" },
              { "trenner": "vs" },
              { "datei": "b.png", "hoehe": 400, "name": "RIGHT" } ] }
```

`datei` refers to a file in the project's `bilder/` folder; `vox.py bilder`
cuts it out and halftones it into `arbeit/`. `strahl` puts a coloured starburst
behind the photo.

### `wort`
A large word, optionally with a coloured bar behind it and a sub-line.

```jsonc
{ "art": "wort", "bei": 4.0, "wort": "PRICES FALL", "balken": "gelb",
  "unter": "Ever more <mark>discounts</mark>.", "unter_bei": 2.4 }
```

`unter` accepts `<mark>` (highlighter) and `<chip>` (filled label).
`unter_bei` is relative to `bei`.

### `zaehler`
Counting comparison with filled/empty dots.

```jsonc
{ "art": "zaehler", "bei": 8.0,
  "reihen": [ { "name": "BEFORE", "wert": 8, "max": 8 },
              { "name": "AFTER",  "wert": 3, "max": 8 } ] }
```

### `objekte`
A row of trophy-like shapes with labels, appearing one after another.

```jsonc
{ "art": "objekte", "bei": 15.2, "objekte": [ { "label": "2022" }, { "label": "2024" } ] }
```

### `balken`
Bar comparison with counting values.

```jsonc
{ "art": "balken", "bei": 16.0, "max": 1.0,
  "reihen": [ { "name": "REVENUE", "wert": 1.0,  "bei": 1.6, "farbe": "koralle" },
              { "name": "PROFIT",  "wert": 0.34, "bei": 3.4, "farbe": "gedeckt" } ] }
```

### `umringt`
A ball surrounded by closing-in dots — pressure, being outnumbered.

```jsonc
{ "art": "umringt", "bei": 12.0, "wort": "FROM ALL SIDES", "gegner": 7, "strahl": "lila" }
```

### `streuung`
A pitch/area with scattered dots — spread, reach, coverage.

```jsonc
{ "art": "streuung", "bei": 20.0, "wort": "ACROSS THE MARKET", "punkte": 42 }
```

## Audio (`ton`)

| Key | Meaning |
|---|---|
| `stimme` | path to the voiceover, relative to the project |
| `bett` | `ruhig` · `warm` · `spannung` · `hell`, or omit for none |
| `abstand` | how far the bed sits under the voice, in LU (default 20) |
| `ziel_lufs` | final loudness (default −14) |

The bed level is derived by measuring both the voice and the bed, not from a
fixed dB value — a fixed value is a guess that misses whenever the recording
level changes.
