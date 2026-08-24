/* vox-Laufzeit: der Werkzeugkasten, nicht die Vorlage.
 *
 * Stellt bereit, was jede Szene braucht - Stile und Untergrund, Uebergaenge,
 * Kamera, Schreibmaschine, Zaehler, Pfeile - und uebersetzt am Ende alles in
 * eine GSAP-Zeitleiste, die HyperFrames Bild fuer Bild abfaehrt.
 *
 * Die LAGE der Dinge legt die Laufzeit bewusst NICHT fest. Ein Raster ist eine
 * moegliche Anordnung (raster.js), keine Vorschrift. Fuer ein eigenes Video
 * schreibt man eine eigene szene.js gegen dieses vox-Objekt.
 *
 * Beispiel:
 *   const p = vox.stil({ stil: "riso", masse: [1920, 1080], dauer: 12 });
 *   const welt = vox.welt(3840, 2160);
 *   const t = vox.el("div", "gross"); welt.appendChild(t);
 *   vox.tippen(t, "HALLO", 0.4, 0.6);
 *   vox.fahrt({ x: 0, y: 0, s: 1 }, { x: -1920, y: 0, s: 1 }, 4.0, 0.8);
 *   vox.fertig();
 */
(function () {
  "use strict";

  const tweens = [];
  const zahlDe = (v, komma) =>
    komma ? v.toFixed(komma).replace(".", ",") : String(Math.round(v));

  function tween(ziel, eig, bei, dauer, ease) {
    tweens.push({ ziel, eig, bei, dauer: dauer || 0.4, ease: ease || "out" });
  }
  function tippen(ziel, text, bei, dauer) {
    tweens.push({ ziel, art: "text", text, bei, dauer, ease: "linear" });
  }
  function zaehlen(ziel, bis, bei, dauer, komma) {
    tweens.push({ ziel, art: "zahl", bis, komma, bei, dauer, ease: "out" });
  }

  const GSAP_EASE = { linear: "none", out: "power3.out", inOut: "power2.inOut", back: "back.out(1.9)" };

  /* --- Stile -------------------------------------------------------------
   * Ein Stil legt Palette, Untergrund und die Behandlung der Schrift fest.
   * Die Palettennamen bleiben ueber alle Stile gleich, damit eine Spec beim
   * Umschalten nicht angefasst werden muss: "balken": "gelb" trifft immer die
   * warme Signalfarbe des jeweiligen Stils.
   */
  const STILE = {
    papier: {
      palette: { papier: "#e9e6e1", tinte: "#14110f", gedeckt: "#7a6f66",
                 gelb: "#f5e050", koralle: "#f0664a", lila: "#9b8cf0", gold: "#c99a1e" },
      schrift: { anzeige: "Anton", text: "Adwaita Sans" },
      // Farbversatz wie schlecht liegende Druckplatten
      schatten_gross: "-2px 0 rgba(240,70,60,.38), 2px 0 rgba(40,110,240,.30)",
      schatten_mittel: "-1.5px 0 rgba(240,70,60,.34), 1.5px 0 rgba(40,110,240,.28)",
      korn: { deckung: 0.42, mischen: "multiply" },
      negativ: false,
      struktur: (B, H) => `
        opacity:.85; background:
        linear-gradient(90deg, transparent ${B * 0.327}px, rgba(255,255,255,.55) ${B * 0.332}px,
                        rgba(96,84,72,.22) ${B * 0.334}px, transparent ${B * 0.339}px),
        linear-gradient(90deg, transparent ${B * 0.66}px, rgba(255,255,255,.5) ${B * 0.665}px,
                        rgba(96,84,72,.20) ${B * 0.667}px, transparent ${B * 0.672}px),
        linear-gradient(180deg, transparent ${H * 0.322}px, rgba(255,255,255,.5) ${H * 0.331}px,
                        rgba(96,84,72,.18) ${H * 0.335}px, transparent ${H * 0.344}px),
        linear-gradient(180deg, transparent ${H * 0.655}px, rgba(255,255,255,.45) ${H * 0.664}px,
                        rgba(96,84,72,.16) ${H * 0.668}px, transparent ${H * 0.677}px),
        radial-gradient(ellipse 380px 260px at 14% 22%, rgba(120,104,86,.10), transparent 70%),
        radial-gradient(ellipse 420px 300px at 82% 74%, rgba(120,104,86,.09), transparent 70%);
        background-size:${B}px ${H}px;`,
      vignette: "radial-gradient(ellipse at 50% 45%, transparent 55%, rgba(70,60,50,.16) 100%)",
    },

    dunkel: {
      palette: { papier: "#0e0f13", tinte: "#f2f0ec", gedeckt: "#8a8f9c",
                 gelb: "#ffd34d", koralle: "#ff5f4d", lila: "#8f7dff", gold: "#e8b53a" },
      schrift: { anzeige: "Anton", text: "Adwaita Sans" },
      // Auf dunklem Grund wirkt Druckversatz falsch - dort leuchtet Schrift.
      schatten_gross: "0 0 34px rgba(255,255,255,.22)",
      schatten_mittel: "0 0 22px rgba(255,255,255,.18)",
      korn: { deckung: 0.16, mischen: "screen" },
      negativ: true,
      struktur: (B, H) => `
        opacity:.5; background:
        radial-gradient(ellipse 700px 520px at 22% 18%, rgba(143,125,255,.16), transparent 70%),
        radial-gradient(ellipse 760px 560px at 80% 78%, rgba(255,95,77,.12), transparent 70%);
        background-size:${B}px ${H}px;`,
      vignette: "radial-gradient(ellipse at 50% 45%, transparent 42%, rgba(0,0,0,.55) 100%)",
    },

    blaupause: {
      palette: { papier: "#0b2f52", tinte: "#eaf3ff", gedeckt: "#7fa6c9",
                 gelb: "#ffd34d", koralle: "#ff7a5c", lila: "#9ec5ff", gold: "#cfe4ff" },
      schrift: { anzeige: "Anton", text: "JetBrainsMono NF" },
      schatten_gross: "0 2px 0 rgba(0,0,0,.35)",
      schatten_mittel: "0 2px 0 rgba(0,0,0,.30)",
      korn: { deckung: 0.12, mischen: "screen" },
      negativ: true,
      // Millimeterpapier: feines Gitter, darueber ein groeberes
      struktur: (B, H) => `
        opacity:.55; background:
        repeating-linear-gradient(0deg, rgba(255,255,255,.09) 0 1px, transparent 1px 40px),
        repeating-linear-gradient(90deg, rgba(255,255,255,.09) 0 1px, transparent 1px 40px),
        repeating-linear-gradient(0deg, rgba(255,255,255,.16) 0 2px, transparent 2px 200px),
        repeating-linear-gradient(90deg, rgba(255,255,255,.16) 0 2px, transparent 2px 200px);`,
      vignette: "radial-gradient(ellipse at 50% 45%, transparent 50%, rgba(2,16,30,.5) 100%)",
    },

    // Hausstil von Nomobo, aus nomobo.de gezogen: Akzent #FF4500, dunkler
    // Grund #07090E, Poppins bis 700, Pillen als Formensignatur.
    nomobo: {
      palette: { papier: "#07090E", tinte: "#FFFFFF", gedeckt: "#8A8F98",
                 gelb: "#FF7040", koralle: "#FF4500", lila: "#D93A00", gold: "#FF8C42" },
      schrift: { anzeige: "Poppins", text: "Poppins" },
      // Kein Druckversatz - die Marke ist digital, nicht Papier.
      schatten_gross: "0 18px 60px rgba(0,0,0,.55)",
      schatten_mittel: "0 12px 40px rgba(0,0,0,.5)",
      korn: { deckung: 0.06, mischen: "screen" },
      negativ: true,
      struktur: (B, H) => `
        opacity:1; background:
        radial-gradient(circle 900px at 12% 8%, rgba(255,69,0,.30), transparent 68%),
        radial-gradient(circle 760px at 88% 78%, rgba(255,112,64,.16), transparent 70%);
        background-size:${B}px ${H}px;`,
      vignette: "radial-gradient(ellipse at 50% 45%, transparent 46%, rgba(0,0,0,.55) 100%)",
    },

    riso: {
      palette: { papier: "#f4efe2", tinte: "#1b1b1b", gedeckt: "#8a7f6d",
                 gelb: "#ffd400", koralle: "#ff4b3e", lila: "#3d5afe", gold: "#ff8a00" },
      schrift: { anzeige: "Anton", text: "Adwaita Sans" },
      // Risodruck versetzt die Farben deutlich sichtbar - das ist der Reiz.
      schatten_gross: "-5px 3px rgba(61,90,254,.55), 5px -3px rgba(255,75,62,.45)",
      schatten_mittel: "-4px 2px rgba(61,90,254,.5), 4px -2px rgba(255,75,62,.4)",
      korn: { deckung: 0.8, mischen: "multiply" },
      negativ: false,
      struktur: (B, H) => `
        opacity:.5; background:
        radial-gradient(ellipse 620px 460px at 18% 26%, rgba(255,75,62,.10), transparent 72%),
        radial-gradient(ellipse 660px 500px at 84% 72%, rgba(61,90,254,.10), transparent 72%);
        background-size:${B}px ${H}px;`,
      vignette: "none",
    },
  };

  function stilSchreiben(spec) {
    const stil = STILE[spec.stil] || STILE.papier;
    // Ueberlagerung: die Szene liegt spaeter auf einem Video. Dann darf kein
    // Grund gemalt werden - Papier, Knicke, Korn und Vignette wuerden das
    // Material zudecken. Palette, Schrift und Bewegung bleiben.
    const drueber = !!spec.ueberlagerung;
    const p = Object.assign({}, stil.palette, stil.schrift, spec.palette || {});
    const [B, H] = spec.masse || [1920, 1080];
    // Aus der Tinte abgeleitete Fuellungen - fest verdrahtete Grauwerte
    // wuerden auf dunklem Grund verschwinden.
    const zart = spec.stil && stil.negativ ? "rgba(255,255,255,.10)" : "rgba(20,17,15,.07)";
    const zarter = stil.negativ ? "rgba(255,255,255,.16)" : "rgba(20,17,15,.13)";
    document.getElementById("grundstil").textContent = `
@font-face { font-family:'${p.anzeige}'; src: local('${p.anzeige}'); font-display: block; }
@font-face { font-family:'${p.text}'; src: local('${p.text}'); font-display: block; }
* { margin:0; padding:0; box-sizing:border-box; }
html, body { width:${B}px; height:${H}px; overflow:hidden;
  background:${drueber ? "transparent" : p.papier}; }
body { font-family:"${p.text}", system-ui, sans-serif; color:${p.tinte}; }
#papier { position:absolute; inset:0;
  background:${drueber ? "transparent" : p.papier}; }
#falten { position:absolute; inset:0; pointer-events:none;
  ${drueber ? "display:none" : stil.struktur(B, H)} }
/* Ein <svg> ohne width/height ist 300x150 gross - dann liegt das Korn als
   Kaestchen in der Ecke statt ueber dem Blatt. */
#korn { position:absolute; left:0; top:0; width:${B}px; height:${H}px;
        opacity:${drueber ? 0 : stil.korn.deckung};
        mix-blend-mode:${stil.korn.mischen}; pointer-events:none; }
#vignette { position:absolute; inset:0; pointer-events:none;
  background:${drueber ? "none" : stil.vignette}; }
#buehne { position:absolute; inset:0; overflow:hidden; }
#welt { position:absolute; left:0; top:0; transform-origin:0 0; }
.feld { position:absolute; overflow:hidden; }
.mitte { position:absolute; inset:0; display:flex; flex-direction:column;
         align-items:center; justify-content:center; gap:20px; padding:60px; }
.kicker { font-weight:700; font-size:38px; letter-spacing:.20em;
          text-transform:uppercase; color:${p.gedeckt}; }
.gross { font-family:"${p.anzeige}"; font-weight:700; font-size:170px;
         line-height:.94; text-align:center; letter-spacing:-.03em;
         text-shadow:${stil.schatten_gross}; }
.mittel { font-family:"${p.anzeige}"; font-weight:700; font-size:120px;
          line-height:1.06; text-align:center; letter-spacing:-.025em;
          text-shadow:${stil.schatten_mittel}; }
.unter { font-weight:700; font-size:56px; text-align:center; max-width:1400px; line-height:1.28; }
.unter mark { background:${p.gelb}; color:${stil.negativ ? "#111" : "inherit"};
              box-shadow:0 0 0 10px ${p.gelb}; }
.unter chip { background:${p.koralle}; color:#fff; padding:6px 24px; display:inline-block; }
.foto { filter:drop-shadow(0 18px 34px rgba(0,0,0,.35)); }
.pfeil { position:absolute; color:${p.tinte}; }
.pfeil svg { display:block; ${stil.negativ ? "" :
  "filter:drop-shadow(-2px 0 rgba(240,70,60,.5)) drop-shadow(2px 0 rgba(40,110,240,.4));"} }
.strahl { position:absolute; left:50%; top:50%; z-index:-1;
  clip-path:polygon(50% 0,58% 30%,76% 8%,70% 36%,94% 22%,80% 46%,100% 50%,80% 56%,
                    94% 78%,70% 66%,76% 92%,58% 70%,50% 100%,42% 70%,24% 92%,30% 66%,
                    6% 78%,20% 56%,0 50%,20% 46%,6% 22%,30% 36%,24% 8%,42% 30%); }
.balken { position:absolute; left:50%; z-index:-1; }
.kugel { border-radius:50%; background:radial-gradient(circle at 34% 30%, #f7e07a, ${p.gold} 62%, #8a6511); }
.kugel.leer { background:${zarter}; }
.bahn { display:flex; align-items:center; gap:26px; }
.bahn .nam { font-family:"${p.anzeige}"; font-size:70px; width:330px; text-align:right; }
.bahn .sp { height:104px; position:relative; flex:1; background:${zart}; }
.bahn .sp i { position:absolute; left:0; top:0; bottom:0; display:block; transform-origin:left center; }
.bahn .wert { font-family:"${p.anzeige}"; font-size:84px; width:250px; }
.pokal { text-align:center; }
.pokal .form { width:230px; height:280px; margin:0 auto; background:${p.gold};
  clip-path:polygon(16% 0,84% 0,80% 46%,62% 66%,62% 82%,84% 82%,84% 100%,16% 100%,
                    16% 82%,38% 82%,38% 66%,20% 46%); }
.pokal .sockel { background:${p.koralle}; height:26px; width:230px; margin:-14px auto 12px; }
.pokal .label { font-family:"${p.anzeige}"; font-size:46px; }
.gegner { position:absolute; border-radius:50%; background:${p.tinte}; }
.ball { position:absolute; left:50%; top:50%; border-radius:50%; background:${p.papier};
        border:9px solid ${p.tinte}; }
.plan { border:8px solid ${p.tinte}; position:relative; background:${zart}; }
.plan .linie { position:absolute; left:50%; top:0; bottom:0; width:8px; background:${p.tinte}; margin-left:-4px; }
.plan .kreis { position:absolute; left:50%; top:50%; width:180px; height:180px;
               margin:-90px 0 0 -90px; border:8px solid ${p.tinte}; border-radius:50%; }
.punkt { position:absolute; border-radius:50%; background:${p.koralle}; }
`;
    return p;
  }

  /* Ein linearer Schritt modulo N legt Punkte auf eine Diagonale statt sie zu
     streuen. Ein Hash je Achse streut wirklich. */

  function streuwert(i, salz) {
    let h = (i * 374761393 + salz * 668265263) >>> 0;
    h = ((h ^ (h >>> 13)) * 1274126177) >>> 0;
    return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
  }

  /* --- Bruecke zu HyperFrames (GSAP) ------------------------------------- */
  function verdrahten(spec) {
    if (!window.gsap) {
      throw new Error("GSAP fehlt - die Szene wird ueber HyperFrames gerendert.");
    }
    const tl = gsap.timeline({ paused: true });
    // fromTo setzt seinen Anfangszustand sonst schon bei Zeit 0 - bei mehreren
    // Fahrten hintereinander stuende die Kamera dann von Beginn an am Ende.
    const schonGesetzt = new Set();
    tweens.forEach((tw) => {
      if (tw.art === "text") {
        const o = { n: 0 };
        tl.to(o, { n: tw.text.length, duration: tw.dauer, ease: "none",
          onUpdate: () => { tw.ziel.textContent = tw.text.slice(0, Math.round(o.n)); } }, tw.bei);
        return;
      }
      if (tw.art === "zahl") {
        const o = { n: 0 };
        tl.to(o, { n: tw.bis, duration: tw.dauer, ease: "power3.out",
          onUpdate: () => { tw.ziel.textContent = zahlDe(o.n, tw.komma); } }, tw.bei);
        return;
      }
      const von = {}, nach = {};
      for (const k in tw.eig) {
        const [a, b] = tw.eig[k];
        const name = k === "rotate" ? "rotation" : k;
        if (a !== null) von[name] = a;
        nach[name] = b;
      }
      nach.duration = tw.dauer;
      nach.ease = GSAP_EASE[tw.ease];
      // Den Ursprung NICHT raten: die Welt steht auf "0 0", Balken auf
      // "left center". Ein pauschales "center center" schiebt die Welt beim
      // Herauszoomen aus dem Bild und laesst Balken aus der Mitte wachsen.
      nach.transformOrigin = getComputedStyle(tw.ziel).transformOrigin;
      nach.immediateRender = false;
      if (Object.keys(von).length) {
        if (!schonGesetzt.has(tw.ziel)) {
          tl.set(tw.ziel, Object.assign({}, von,
                 { transformOrigin: nach.transformOrigin }), 0);
          schonGesetzt.add(tw.ziel);
        }
        tl.fromTo(tw.ziel, von, nach, tw.bei);
      } else {
        tl.to(tw.ziel, nach, tw.bei);
      }
    });
    window.__timelines = window.__timelines || {};
    window.__timelines["main"] = tl;
  }

  /* --- Bausteine ---------------------------------------------------------- */
  const el = (tag, cls, stil) => {
    const d = document.createElement(tag);
    if (cls) d.className = cls;
    if (stil) d.setAttribute("style", stil);
    return d;
  };

  function welt(breite, hoehe) {
    const w = document.getElementById("welt");
    w.style.width = breite + "px";
    w.style.height = hoehe + "px";
    return w;
  }

  /* Eine Kamerafahrt braucht Start UND Ziel. Nur das Ziel anzugeben laesst
     die Kamera springen, weil der Startwert dann geraten ist. */
  function fahrt(von, nach, bei, dauer) {
    tween(document.getElementById("welt"),
          { x: [von.x, nach.x], y: [von.y, nach.y],
            scale: [von.s === undefined ? 1 : von.s, nach.s === undefined ? 1 : nach.s] },
          bei, dauer || 0.8, "inOut");
  }

  /* So weit herauszoomen, dass die ganze Welt hineinpasst, und mittig setzen. */
  function ueberblick(von, bei, dauer, B, H, weltB, weltH) {
    const k = Math.min(B / weltB, H / weltH);
    fahrt(von, { x: (B - weltB * k) / 2, y: (H - weltH * k) / 2, s: k }, bei, dauer);
  }

  /* Pfeil zwischen zwei Punkten. Waagerecht oder senkrecht - Diagonalen
     lesen sich in dieser Bildsprache schlecht. */
  function pfeil(x, y, laenge, richtung) {
    const D = 80, p = el("div", "pfeil");
    const waagerecht = richtung === "rechts" || richtung === "links";
    p.style.left = (x - (waagerecht ? laenge / 2 : D / 2)) + "px";
    p.style.top = (y - (waagerecht ? D / 2 : laenge / 2)) + "px";
    const L = laenge, spitze = 48;
    const pfade = {
      rechts: `<path d="M6 40 H${L - spitze}" stroke="currentColor" stroke-width="15" fill="none"/>`
            + `<path d="M${L - spitze - 16} 14 L${L - 12} 40 L${L - spitze - 16} 66 Z" fill="currentColor"/>`,
      links:  `<path d="M${L - 6} 40 H${spitze}" stroke="currentColor" stroke-width="15" fill="none"/>`
            + `<path d="M${spitze + 16} 14 L12 40 L${spitze + 16} 66 Z" fill="currentColor"/>`,
      runter: `<path d="M40 6 V${L - spitze}" stroke="currentColor" stroke-width="15" fill="none"/>`
            + `<path d="M14 ${L - spitze - 16} L40 ${L - 12} L66 ${L - spitze - 16} Z" fill="currentColor"/>`,
      hoch:   `<path d="M40 ${L - 6} V${spitze}" stroke="currentColor" stroke-width="15" fill="none"/>`
            + `<path d="M14 ${spitze + 16} L40 12 L66 ${spitze + 16} Z" fill="currentColor"/>`,
    };
    p.innerHTML = `<svg width="${waagerecht ? L : D}" height="${waagerecht ? D : L}">`
                + (pfade[richtung] || pfade.rechts) + `</svg>`;
    document.getElementById("welt").appendChild(p);
    return p;
  }

  /* --- Zeitanker ---------------------------------------------------------
   * Eine Szene soll nicht auf Sekunden festgenagelt sein. Jede neue Stimme
   * verschiebt alles, und dann muessen zwanzig Zeitstempel von Hand nach -
   * das ist der eigentliche Engpass beim Neubauen.
   *
   * Stattdessen fragt die Szene nach dem Wort:  zeit("Fünffache")
   * Die Wortzeiten liegen als window.WORTE bereit.
   */
  /* Aehnlichkeit zweier Woerter, 0 bis 1. Reicht fuer Verhoerer der
     Spracherkennung - kein Rechtschreibpruefer. */
  function aehnlich(a, b) {
    if (a === b) return 1;
    if (!a.length || !b.length) return 0;
    const d = [];
    for (let i = 0; i <= a.length; i++) d[i] = [i];
    for (let j = 0; j <= b.length; j++) d[0][j] = j;
    for (let i = 1; i <= a.length; i++) {
      for (let j = 1; j <= b.length; j++) {
        d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1,
                           d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      }
    }
    return 1 - d[a.length][b.length] / Math.max(a.length, b.length);
  }

  /* --- Saetze statt Woerter ----------------------------------------------
   * Der verlaesslichere Anker. Ein Satz ist eine Aussage, und das Bild zeigt
   * eine Aussage - die Einheit passt. Vor allem aber kann sich die
   * Erkennung nicht verhoeren: die Grenzen kommen aus dem geschriebenen
   * Text, nur die Zeiten aus der Spur.
   */
  function satz(nr) {
    const s = window.SAETZE || [];
    if (!s.length) throw new Error("keine Satzzeiten - saetze.json fehlt");
    const g = s[nr < 0 ? s.length + nr : nr];
    if (!g) throw new Error(`Satz ${nr} gibt es nicht (${s.length} Saetze)`);
    return g.von;
  }
  function satzEnde(nr) {
    const s = window.SAETZE || [];
    const g = s[nr < 0 ? s.length + nr : nr];
    if (!g) throw new Error(`Satz ${nr} gibt es nicht (${s.length} Saetze)`);
    return g.bis;
  }

  function zeit(muster, opt) {
    // Mehrere Schreibweisen erlaubt: zeit(["fast", "über"]) nimmt die erste,
    // die vorkommt. Vorlagen formulieren nicht immer gleich.
    if (Array.isArray(muster)) {
      for (const m of muster) {
        try { return zeit(m, opt); } catch (e) { /* naechste probieren */ }
      }
      throw new Error("keine dieser Schreibweisen in der Sprachspur: " + muster.join(", "));
    }
    const w = window.WORTE || [];
    if (!w.length) {
      console.warn("keine Wortzeiten - zeit() liefert 0");
      return 0;
    }
    const norm = (x) => String(x).toLowerCase().replace(/[^\wäöüß]/g, "");
    const ziel = norm(muster);
    let treffer = w.filter((x) => norm(x.wort) === ziel);
    const nr = (opt && opt.nr) || 0;
    if (!treffer[nr]) {
      // Die Erkennung verhoert sich: "Raten" wird zu "Ratten", "Kuehlschrank"
      // zu "Kuehl Schrank". Ein Anker darf daran nicht scheitern - ein
      // aehnliches Wort an der richtigen Stelle ist besser als eine
      // abgebrochene Szene. Nur wenn gar nichts passt, wird geworfen.
      const nah = w.map((x) => ({ x, g: aehnlich(norm(x.wort), ziel) }))
                   .filter((c) => c.g >= 0.72)
                   .sort((a, b) => b.g - a.g);
      if (nah.length) {
        console.warn(`zeit("${muster}") -> "${nah[0].x.wort}" (unscharf)`);
        treffer = [nah[0].x];
      }
    }
    const gefunden = treffer[nr] || treffer[0];
    if (!gefunden) {
      // Nicht still 0 liefern - sonst rutscht ein Element an den Anfang und
      // niemand sieht, woran es lag.
      throw new Error(`Wort nicht in der Sprachspur: "${muster}"`
                      + (treffer.length ? ` (nur ${treffer.length} Vorkommen)` : ""));
    }
    return gefunden.von + ((opt && opt.plus) || 0);
  }

  /* Ende des Wortes - praktisch fuer "danach ausblenden". */
  function zeitEnde(muster, opt) {
    if (Array.isArray(muster)) {
      for (const m of muster) {
        try { return zeitEnde(m, opt); } catch (e) { /* naechste */ }
      }
      throw new Error("keine dieser Schreibweisen in der Sprachspur: " + muster.join(", "));
    }
    const w = window.WORTE || [];
    const norm = (x) => String(x).toLowerCase().replace(/[^\wäöüß]/g, "");
    let treffer = w.filter((x) => norm(x.wort) === norm(muster));
    if (!treffer[(opt && opt.nr) || 0]) {
      const nah = w.map((x) => ({ x, g: aehnlich(norm(x.wort), norm(muster)) }))
                   .filter((c) => c.g >= 0.72).sort((a, b) => b.g - a.g);
      if (nah.length) treffer = [nah[0].x];
    }
    const g = treffer[(opt && opt.nr) || 0] || treffer[0];
    if (!g) throw new Error(`Wort nicht in der Sprachspur: "${muster}"`);
    return g.bis + ((opt && opt.plus) || 0);
  }

  window.vox = {
    zeit, zeitEnde,
    stil: stilSchreiben, STILE,
    el, welt, fahrt, ueberblick, pfeil, satz, satzEnde,
    tween, tippen, zaehlen, streuwert,
    fertig: verdrahten,
  };
})();
