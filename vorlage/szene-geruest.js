/* Geruest fuer eine eigene Szene.
 *
 * Alles hier ist zum Wegwerfen gedacht - die Anordnung soll aus dem Inhalt
 * kommen, nicht aus dieser Datei. Was bleibt, ist der Ablauf:
 *   Stil holen -> Welt aufspannen -> Dinge bauen -> Kamera fuehren -> fertig.
 */
(function () {
  "use strict";
  const S = window.SPEC, [B, H] = S.masse;
  const p = vox.stil(S);              // wendet den Stil an, liefert die Palette

  const WB = B, WH = 2400;            // das Blatt, ueber das die Kamera faehrt
  const welt = vox.welt(WB, WH);

  // Eigene Formen brauchen eigenes CSS - die Laufzeit besitzt nur Grund,
  // Palette und Uhr.
  const stil = document.createElement("style");
  stil.textContent = `
  .meins { position:absolute; background:${p.koralle}; }`;
  document.head.appendChild(stil);

  /* --- Dinge --------------------------------------------------------------
     vox.el(tag, klasse, stil) baut, welt.appendChild(...) haengt ein.
     vox.tween(el, {opacity:[0,1], y:[30,0]}, bei, dauer, "out"|"back"|"inOut"|"linear")
     vox.tippen(el, "TEXT", bei, dauer)
     vox.zaehlen(el, 42, bei, dauer, 0)
     vox.pfeil(x, y, laenge, "rechts"|"links"|"hoch"|"runter")            */

  const titel = vox.el("div", "gross",
    "position:absolute;left:0;right:0;top:180px;text-align:center");
  welt.appendChild(titel);
  vox.tippen(titel, "TITEL", 0.4, 0.8);

  /* --- Kamera -------------------------------------------------------------
     Bildmitte auf einen Weltpunkt: x = B/2 - s*cx, y = H/2 - s*cy.
     Schaetzen fuehrt zuverlaessig daneben - rechnen.                      */
  const auf = (cx, cy, s) => ({ x: B / 2 - s * cx, y: H / 2 - s * cy, s });
  const start = { x: 0, y: 0, s: 1 };
  const zwei = auf(WB / 2, 1400, 1);
  vox.fahrt(start, zwei, 3.0, 0.9);
  vox.ueberblick(zwei, S.dauer - 1.8, 1.6, B, H, WB, WH);

  vox.fertig();                       // genau einmal, ganz am Ende
})();
