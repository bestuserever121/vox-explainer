---
name: vox-explainer
description: Build paper-collage explainer videos in the style of explainer journalism - a paper sheet, halftone black-and-white photo cutouts, flat bold colour shapes, black arrows, and a camera travelling a grid of panels that pulls out at the end to reveal the whole argument. Use for "explainer video", "vox style", "erklaervideo", "video from a voiceover", "turn this argument into a video", "collage animation".
---

# vox — explainer videos from a spec

```
bin/vox.py neu    projekt/     # scaffold from the example
bin/vox.py bilder projekt/     # cut out and halftone the photos
bin/vox.py szene  projekt/     # render the scene (no audio)
bin/vox.py ton    projekt/     # mix voice and bed, normalise
bin/vox.py bauen  projekt/     # all of the above
```

Everything lives in one `spec.json`. Panels are laid out on a grid in a snake
path; arrows between them are drawn automatically; `schluss` pulls the camera
out to show the whole sheet.

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

## Checking the result

Never call it done from a green exit code. Build a contact sheet
(`ffmpeg -vf "fps=0.5,scale=300:-1,tile=6x4"`) and look at it, then check the
final pull-out frame separately — that is where layout mistakes show up.
