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
