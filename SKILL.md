---
name: vox-explainer
description: Make videos two ways - build collage explainer scenes from a JSON spec (halftone cutouts, flat colour, arrows, a camera travelling a grid), or cut existing footage for YouTube (transcribe, strip filler words and dead air, burn captions, master the audio). Four looks: paper, dark, blueprint, riso. Use for "explainer video", "vox style", "erklaervideo", "rough cut", "cut this footage", "remove filler words", "add subtitles", "edit my video", "motion graphics from a script".
---

# vox — explainer videos from a spec

Four looks, one spec: `papier` · `dunkel` · `blaupause` · `riso`.

```
bin/vox.py neu    projekt/       # scaffold from the example

# build a scene from a spec
bin/vox.py bilder projekt/       # cut out and halftone the photos
bin/vox.py szene  projekt/       # render the scene

# or cut existing footage
bin/vox.py schnitt    projekt/   # strip filler words and dead air
bin/vox.py untertitel projekt/   # burn captions

bin/vox.py ton    projekt/       # polish audio, bed, normalise
bin/vox.py bauen  projekt/       # whichever path the spec implies
```

`"video": {"quelle": "raw.mp4"}` in the spec switches to footage mode.

Everything lives in one `spec.json`. Panels are laid out on a grid in a snake
path; arrows between them are drawn automatically; `schluss` pulls the camera
out to show the whole sheet.

## Styles

`"stil"` in the spec switches the whole look: `papier` (warm off-white, creases,
print misregistration), `dunkel` (near-black, glowing type), `blaupause` (graph
paper, technical), `riso` (cream, heavy duotone offset). Palette names are
identical across styles, so switching never means touching the panels.

**A `palette` block in the spec overrides the style.** If a style switch appears
to do nothing, that is why.

## How to approach a video

**Measure the reference before copying it.** If the user points at an example,
pull frames as a contact sheet first — that shows the *mechanic* (how the
camera moves, what accumulates) — then pull a few full-resolution frames for
the *craft* (halftone, colour, type, print offset). Sample the palette from the
image instead of guessing hex values.

**One claim per panel.** A panel that carries two statements needs splitting.
Six to nine panels carry a 45-second voiceover comfortably.

**Time the panels to the words.** Transcribe the voiceover with
`bin/transkript.py`, then set each panel's `bei` to the moment its claim starts.
A panel that lands even half a second late reads as unrelated.

**Show the thing, do not label it.** If the voiceover names something, the
picture has to do it. A card with the word written on it is an caption, not an
illustration.

**Only real numbers.** Counters and bars assert magnitude. If a figure cannot be
verified, use a label instead of inventing one — or attribute it in the kicker
("A study rates …").

## Cutting footage

**Two sources, never one.** The transcript says where speech is; the level
measurement says where silence is. Many models emit zero-length gaps between
words, so pauses are not derivable from a transcript — and a level measurement
mistakes quiet speech for silence. **A cut that touches a word is discarded.**

**Compute the silence threshold from the recording.** A fixed value is a bet on
the level. On one phone recording the loudest speech peaked at −36 dB; a fixed
−33 dB classified the whole clip as silence and destroyed it.

**"also" and "genau" are not filler.** At the start of a sentence they carry it;
removing them wrecks the syntax.

**Remap caption times through the cut.** Otherwise they run ahead by exactly
the removed duration.

## Pitfalls

- **A `<svg>` without `width`/`height` is 300×150.** CSS `inset:0` does not
  stretch it. A grain overlay then sits as a small box in one corner and the
  paper just looks "a bit too clean".
- **Halftone contrast above ~1.2 destroys faces.** They collapse into black and
  white blobs. Keep midtones and lighten dark kit instead.
- **Crop cutouts to their silhouette** (`--eng`). Otherwise every photo carries
  a different amount of empty margin and the heights in the layout no longer
  relate to each other.
- **HyperFrames reads `data-duration` from the static HTML** before any script
  runs. Setting it at runtime is too late — `vox.py` writes it in.
- **Do not guess `transformOrigin`.** The world is `0 0`, bars are
  `left center`. A blanket `center center` pushes the world out of frame when it
  zooms out.
- **A camera move needs a start *and* an end.** Giving only the target makes
  every move jump.
- **An ASS `Format:` line must list `SecondaryColour`.** Leave it out and
  libass misassigns every following field — the text simply never appears, with
  no error anywhere.
- **`-ss` before `-i` resets timestamps to zero**, so a subtitle test frame
  pulled that way shows nothing even when the burn is fine.
- **Dark styles need inverted photos.** Black halftone dots on a black ground
  are invisible; `vox.py` sets this from the style, `fotos_negativ` overrides.

## Checking the result

Never call it done from a green exit code. Build a contact sheet
(`ffmpeg -vf "fps=0.5,scale=300:-1,tile=6x4"`) and look at it, then check the
final pull-out frame separately — that is where layout mistakes show up.
