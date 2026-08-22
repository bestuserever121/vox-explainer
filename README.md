# vox — paper-collage explainer videos from a JSON spec

Renders Vox-style explainer videos: a paper sheet, halftone black-and-white
photo cutouts, flat bold colour shapes, thick black arrows, and a camera that
travels a grid of panels and pulls out at the end to reveal the whole argument.

![example](docs/beispiel.gif)

You describe the video in one `spec.json`. Everything else is generated.

![the full sheet](docs/beispiel-blatt.png)

## The grid is optional

The built-in arrangement — panels on a grid, snake path, pull-out — is one
option, and it makes every video look structurally the same. Drop a `szene.js`
into the project and it replaces the grid entirely; the runtime still gives you
the paper, the palette, the camera and the timeline.

![a hand-written composition](docs/frei.gif)

Above: a tall sheet the camera descends — drawn shapes, labels pointing into
them with arrows, a zoom, a pull-out at the end. No grid involved, and the
whole thing is about thirty lines of `szene.js`.

![the whole sheet](docs/frei-blatt.png)

See [docs/laufzeit.md](docs/laufzeit.md) for the runtime API — camera, tweens,
typewriter, counters, arrows — and the rules that bite (compute camera targets,
measure elements before placing things beside them).

## Styles

`"stil"` switches the whole look. The palette names stay the same across
styles, so a spec keeps working when you switch — `"balken": "gelb"` always
hits that style's warm signal colour.

![styles](docs/stile.png)

`papier` — warm off-white, creases and grain, black type with print
misregistration · `dunkel` — near-black, glowing type · `blaupause` — graph
paper, technical · `riso` — cream with heavy duotone offset.

Photos are inverted automatically on the dark styles (black halftone dots on a
black ground are invisible). Override with `"fotos_negativ": true|false`.

Anything in `palette` overrides the style — leave it out unless you mean it.

## Why

Bullet points on dark slides *list* claims. This *shows* them: every statement
gets an object, arrows build the causal chain, and the final pull-out proves it
was one connected argument rather than a list.

## Install

Requires `ffmpeg`, `node`, `python3` (with Pillow + numpy), and
[HyperFrames](https://github.com/heygen-com/hyperframes) for rendering.

```bash
git clone https://github.com/bestuserever121/vox-explainer
cd vox-explainer
./voraussetzungen.sh          # checks what is present and what is missing
```

Optional but recommended:

* **`rembg`** — cuts subjects out of photos. Without it, photos stay rectangles
  and the collage look breaks. `python3 -m venv .venv && .venv/bin/pip install "rembg[cpu]" pillow`
* **whisper.cpp** — turns a voiceover into word timings so you know where each
  beat belongs. You can also write the timings by hand.

## Two modes

**Build a scene from a spec** — the collage explainer above.

```bash
bin/vox.py neu    my-video/     # create a project from the example
bin/vox.py bauen  my-video/     # images, scene, audio, export
```

**Cut existing footage** — a talking head, a podcast, raw camera material.
Point the spec at a file and it transcribes, removes filler words and dead air,
burns captions, and masters the audio.

```jsonc
{
  "name": "episode-01",
  "stil": "papier",
  "video": {
    "quelle": "raw.mp4",
    "untertitel": true,
    "gruppe": 3,
    "transkript": { "modell": "/path/ggml-large-v3.bin", "sprache": "de" }
  },
  "ton": { "bett": "ruhig", "ziel_lufs": -14 }
}
```

```bash
bin/vox.py bauen my-video/      # cut, caption, mix, normalise
```

![captions burned in](docs/schnitt.png)

The cut uses **two sources, not one**: the transcript says where speech *is*,
the level measurement says where silence is. Neither is trustworthy alone —
many models report zero-length gaps between words, and a level measurement
mistakes quiet speech for silence. A cut that would touch a word is discarded.

The silence threshold is computed from the recording itself. A fixed threshold
is a bet on the level: on one phone recording the loudest speech peaked at
−36 dB, so a fixed −33 dB would have classified the entire clip as silence.

Steps individually: `bilder` · `szene` · `schnitt` · `untertitel` · `ton`.

## The spec

```jsonc
{
  "name": "my-video",
  "masse": [1920, 1080],
  "fps": 30,
  "dauer": 24.0,
  "stil": "papier",                    // papier | dunkel | blaupause | riso
  "raster": [3, 2],                    // columns × rows of panels
  "felder": [                          // one panel per claim, in camera order
    { "art": "titel",    "bei": 0.0,  "kicker": "How it works", "titel": "THE CYCLE" },
    { "art": "wort",     "bei": 4.0,  "wort": "PRICES FALL", "balken": "gelb",
      "unter": "Ever more <mark>discounts</mark>.", "unter_bei": 2.4 },
    { "art": "zaehler",  "bei": 8.0,  "reihen": [{ "name": "BEFORE", "wert": 8, "max": 8 }] },
    { "art": "umringt",  "bei": 12.0, "wort": "FROM ALL SIDES", "gegner": 7 },
    { "art": "balken",   "bei": 16.0, "max": 1.0,
      "reihen": [{ "name": "REVENUE", "wert": 1.0, "bei": 1.6 }] },
    { "art": "streuung", "bei": 20.0, "wort": "ACROSS THE MARKET", "punkte": 42 }
  ],
  "schluss": { "bei": 22.4, "dauer": 1.5 },   // pull out to the whole sheet
  "ton": { "stimme": "voice.ogg", "bett": "ruhig", "ziel_lufs": -14 }
}
```

`bei` is when the camera arrives at that panel; everything inside animates
relative to it. Panels are laid out in a snake path (right, down, left, down …)
and arrows are drawn between them automatically.

Panel types: `titel` · `wort` · `zaehler` · `objekte` · `balken` · `umringt` ·
`streuung`. See [docs/spec.md](docs/spec.md) for every field.

## Audio

`ton.stimme` is your voiceover. The bed (`ruhig`, `warm`, `spannung`, `hell`) is
synthesised from tuned sine tones — no samples, no third-party rights. It is
placed ~20 LU under the voice by **measuring both**, not by a fixed dB value,
then side-chained so it ducks under speech. Output is normalised to −14 LUFS in
two passes.

## Notes

* Code comments are in German — that is the author's working language. The spec
  format, this README and the docs are English.
* The style is inspired by the visual language of explainer journalism. It is
  not affiliated with, endorsed by, or derived from any publisher's assets.
* Bring your own photos and check their licences. Nothing is bundled.

## Licence

MIT — see [LICENSE](LICENSE).
