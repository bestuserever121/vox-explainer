# Writing your own scene

The grid in `vorlage/raster.js` is **one arrangement, not the shape of every
video**. Put a `szene.js` in the project and it replaces the grid entirely —
the runtime still gives you the look, the camera and the timeline.

```js
(function () {
  const S = window.SPEC;
  const [B, H] = S.masse;
  const p = vox.stil(S);            // applies the style, returns the palette
  const welt = vox.welt(1920, 3400); // the sheet the camera moves over

  const t = vox.el("div", "gross", "position:absolute;left:0;right:0;top:150px;text-align:center");
  welt.appendChild(t);
  vox.tippen(t, "HEADLINE", 0.5, 1.1);

  const auf = (cx, cy, s) => ({ x: B / 2 - s * cx, y: H / 2 - s * cy, s });
  vox.fahrt({ x: 0, y: 0, s: 1 }, auf(960, 1600, 1), 4.0, 1.0);
  vox.ueberblick(auf(960, 1600, 1), 12.0, 1.6, B, H, 1920, 3400);

  vox.fertig();                     // hand the timeline to the renderer
})();
```

## The runtime

| Call | Does |
|---|---|
| `vox.stil(spec)` | applies the style's CSS, returns the palette object |
| `vox.welt(w, h)` | sizes the sheet, returns the `#welt` element |
| `vox.el(tag, cls, style)` | make an element |
| `vox.tween(el, props, at, dur, ease)` | `props` are `{opacity:[from,to], x, y, scale, rotate, scaleX}` |
| `vox.tippen(el, text, at, dur)` | typewriter |
| `vox.zaehlen(el, to, at, dur, decimals)` | counting number, German decimal comma |
| `vox.fahrt(from, to, at, dur)` | camera move; both states are `{x, y, s}` |
| `vox.ueberblick(from, at, dur, B, H, wW, wH)` | zoom out so the whole sheet fits, centred |
| `vox.pfeil(x, y, len, dir)` | arrow, `dir` is `rechts` `links` `hoch` `runter` |
| `vox.streuwert(i, salt)` | stable pseudo-random 0..1 for scattering |
| `vox.fertig()` | build the GSAP timeline — call once, at the end |

Eases: `linear` · `out` · `inOut` · `back`.

## Rules that bite

**A camera move needs a start and an end.** `vox.fahrt(from, to, …)` — giving
only the target makes it jump, because the start is then a guess.

**Compute camera targets, do not eyeball them.** To centre a world point:
`x = B/2 - s*cx`, `y = H/2 - s*cy`. Eyeballing put annotation arrows on a
subject's hip instead of the arm they were labelling.

**Measure elements before positioning things relative to them.** An arrow
placed at a guessed offset from a text box ends up *inside* it when the text is
long — and then it reads as a strikethrough. `el.offsetWidth` after appending.

**Everything you add is yours.** Custom shapes, custom CSS via a `<style>` you
append — the runtime only owns the ground, the palette and the clock.

## The classes the style provides

`gross` `mittel` `kicker` `unter` (with `<mark>` and `<chip>`) `foto` `pfeil`
`strahl` `balken` `kugel` `bahn` `pokal` `gegner` `ball` `plan` `punkt`.

Use them where they fit and ignore them where they do not.

## Overlaying graphics on footage

Set `"ueberlagerung": true` in the spec and the scene renders with an alpha
channel instead of a ground — no paper, no grain, no vignette, just the
elements. `vox.py auflegen` composites it over the cut footage.

```jsonc
{
  "masse": [1280, 720], "fps": 25, "dauer": 30.7,
  "stil": "dunkel",
  "ueberlagerung": true,
  "video": { "quelle": "roh.mp4", "bild": "eq=brightness=0.06:contrast=1.22" },
  "stoesse": [ { "von": 11.1, "bis": 13.6, "punch": [0.0, 1.1], "staerke": 1.15 } ]
}
```

`video.bild` is an ffmpeg filter applied during the cut — the place where the
material is re-encoded anyway. `stoesse` are zoom punches on the picture after
compositing: when the voiceover says something happens, something happens.

## Tracking

`bin/verfolgen.py` follows a patch through the footage by normalised
cross-correlation (numpy only, no OpenCV) and writes a track:

```bash
bin/verfolgen.py roh.mp4 --von 15.4 --bis 21.2 --start 675,400 \
                 --muster 190 --aus spur.json
```

Put the track into the spec and drive an element from it — one short linear
tween per sample:

```js
for (let i = 1; i < spur.length; i++) {
  const a = spur[i - 1], b = spur[i];
  vox.tween(el, { x: [a.x - spur[0].x, b.x - spur[0].x],
                  y: [a.y - spur[0].y, b.y - spur[0].y] },
            a.t, b.t - a.t, "linear");
}
```

The track reports a `guete` (match confidence) per sample. Look at it: below
about 0.6 the tracker is guessing, and an element that jumps is worse than one
that sits still.
