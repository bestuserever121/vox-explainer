/* Eine mitgelieferte Anordnung: Felder auf einem Raster, die Kamera laeuft im
 * Schlangenweg hindurch, am Ende Zug auf das ganze Blatt.
 *
 * Das ist EIN Weg, nicht DER Weg. Fuer ein eigenes Video schreibt man eine
 * eigene szene.js gegen `vox` - siehe vorlage/vox.js.
 */
(function () {
  "use strict";
  const { el, tween, tippen, zaehlen, streuwert } = vox;

  /* --- Aufbau ------------------------------------------------------------ */
  function aufbau(spec) {
    const pal = vox.stil(spec);
    const [B, H] = spec.masse || [1920, 1080];
    const [SP, ZE] = spec.raster || [3, 3];
    const welt = document.getElementById("welt");
    const wurzel = document.getElementById("root");
    welt.style.width = SP * B + "px";
    welt.style.height = ZE * H + "px";
    wurzel.setAttribute("data-width", B);
    wurzel.setAttribute("data-height", H);
    wurzel.setAttribute("data-duration", (spec.dauer || 30).toFixed(3));
    document.documentElement.style.width = B + "px";
    document.documentElement.style.height = H + "px";

    // Schlangenweg: rechts, runter, links, runter, rechts ...
    const platz = (i) => {
      const z = Math.floor(i / SP);
      const s = z % 2 === 0 ? i % SP : SP - 1 - (i % SP);
      return [s, z];
    };

    (spec.felder || []).forEach((f, i) => {
      const [s, z] = platz(i);
      const feld = el("div", "feld", `left:${s * B}px;top:${z * H}px;width:${B}px;height:${H}px`);
      const mitte = el("div", "mitte");
      feld.appendChild(mitte);
      welt.appendChild(feld);
      bauFeld(f, i, mitte, pal, B, H);
    });

    // Pfeile entlang des Weges zwischen den Feldern
    for (let i = 0; i + 1 < (spec.felder || []).length; i++) {
      const [s1, z1] = platz(i), [s2, z2] = platz(i + 1);
      welt.appendChild(pfeil(s1, z1, s2, z2, B, H));
    }

    kamera(spec, platz, B, H, SP, ZE);
    vox.fertig();
  };

  function pfeil(s1, z1, s2, z2, B, H) {
    const L = 330, D = 80, mx = ((s1 + s2) / 2 + 0.5) * B, my = ((z1 + z2) / 2 + 0.5) * H;
    const waagerecht = z1 === z2;
    const p = el("div", "pfeil");
    if (waagerecht) {
      p.style.left = (mx - L / 2) + "px"; p.style.top = (my - D / 2) + "px";
      const rechts = s2 > s1;
      p.innerHTML = `<svg width="${L}" height="${D}">` +
        (rechts
          ? `<path d="M6 40 H286" stroke="currentColor" stroke-width="15" fill="none"/><path d="M270 14 L318 40 L270 66 Z" fill="currentColor"/>`
          : `<path d="M324 40 H44" stroke="currentColor" stroke-width="15" fill="none"/><path d="M60 14 L12 40 L60 66 Z" fill="currentColor"/>`) + `</svg>`;
    } else {
      p.style.left = (mx - D / 2) + "px"; p.style.top = (my - L / 2) + "px";
      p.innerHTML = `<svg width="${D}" height="${L}"><path d="M40 6 V286" stroke="currentColor" stroke-width="15" fill="none"/><path d="M14 270 L40 318 L66 270 Z" fill="currentColor"/></svg>`;
    }
    return p;
  }

  /* --- Feldarten --------------------------------------------------------- */
  function bauFeld(f, i, mitte, pal, B, H) {
    const t0 = f.bei || 0;
    if (f.kicker) {
      const k = el("div", "kicker"); k.textContent = f.kicker;
      mitte.appendChild(k); tween(k, { opacity: [0, 1], y: [34, 0] }, t0 + 0.15, 0.42);
    }
    const art = f.art || "wort";

    if (art === "titel" || art === "wort") {
      const huelle = el("div", null, "position:relative");
      if (f.balken) {
        const bl = el("div", "balken",
          `background:${pal[f.balken] || f.balken};height:34px;width:1000px;bottom:6px;` +
          `transform:translateX(-50%) scaleX(0);transform-origin:left center`);
        huelle.appendChild(bl);
        tween(bl, { scaleX: [0, 1] }, t0 + 0.65, 0.6);
      }
      const g = el("div", "gross"); huelle.appendChild(g);
      mitte.appendChild(huelle);
      tippen(g, f.titel || f.wort || "", t0 + 0.7, Math.max(0.5, (f.titel || f.wort || "").length * 0.075));
    }

    if (art === "titel" && f.bilder) {
      const reihe = el("div", null, "display:flex;align-items:flex-end;gap:70px;margin-top:4px");
      f.bilder.forEach((b, j) => {
        if (b.trenner) {
          const v = el("div", "mittel", "font-size:104px;padding-bottom:190px");
          v.textContent = b.trenner; reihe.appendChild(v);
          tween(v, { opacity: [0, 1], scale: [0.6, 1] }, t0 + 1.5, 0.42, "back");
          return;
        }
        const sp = el("div", null, "text-align:center;position:relative");
        if (b.strahl) {
          const st = el("div", "strahl",
            `background:${pal[b.strahl] || b.strahl};width:700px;height:700px;` +
            `margin:-350px 0 0 -350px;margin-top:-330px;transform:scale(0)`);
          sp.appendChild(st);
          tween(st, { scale: [0, 1], rotate: [-40, 0] }, t0 + 1.0, 0.55, "back");
        }
        const im = el("img", "foto"); im.src = b.datei; im.style.height = (b.hoehe || 500) + "px";
        sp.appendChild(im);
        const nm = el("div", "mittel", "font-size:82px;margin-top:2px"); nm.textContent = b.name || "";
        sp.appendChild(nm); reihe.appendChild(sp);
        tween(sp, { opacity: [0, 1], y: [50, 0], scale: [0.9, 1] }, t0 + 1.1 + j * 0.2, 0.45);
      });
      mitte.appendChild(reihe);
    }

    if (f.unter) {
      const u = el("div", "unter"); u.innerHTML = f.unter;
      mitte.appendChild(u);
      tween(u, { opacity: [0, 1], y: [26, 0] }, t0 + (f.unter_bei || 3.0), 0.5);
    }

    if (art === "zaehler") {
      const reihe = el("div", null, "display:flex;gap:120px;align-items:center");
      (f.reihen || []).forEach((r, j) => {
        const sp = el("div", null, "text-align:center");
        const kug = el("div", null, "display:flex;gap:20px;flex-wrap:wrap;width:800px;justify-content:center");
        for (let k = 0; k < (r.max || r.wert); k++) {
          const ku = el("span", "kugel" + (k < r.wert ? "" : " leer"), "width:92px;height:92px;transform:scale(0)");
          kug.appendChild(ku);
          tween(ku, { scale: [0, 1] }, t0 + 0.7 + k * 0.09, 0.32, "back");
        }
        sp.appendChild(kug);
        const bez = el("div", "mittel", "margin-top:22px");
        const z = el("span"); z.textContent = "0"; bez.appendChild(z);
        bez.appendChild(document.createTextNode("× " + r.name));
        sp.appendChild(bez); reihe.appendChild(sp);
        zaehlen(z, r.wert, t0 + 0.7, 1.15, 0);
      });
      mitte.appendChild(reihe);
    }

    if (art === "objekte") {
      const reihe = el("div", null, "display:flex;gap:100px;align-items:flex-end");
      (f.objekte || []).forEach((o, j) => {
        const p = el("div", "pokal", "transform:scale(0.85);opacity:0");
        p.innerHTML = `<div class="form"></div><div class="sockel"></div>` +
                      `<div class="label">${o.label}</div>`;
        reihe.appendChild(p);
        tween(p, { opacity: [0, 1], y: [40, 0], scale: [0.85, 1] }, t0 + 0.7 + j * 1.4, 0.45);
      });
      mitte.appendChild(reihe);
    }

    if (art === "balken") {
      const box = el("div", null, "display:flex;flex-direction:column;gap:44px;width:1560px");
      const max = f.max || Math.max.apply(null, (f.reihen || []).map((r) => r.wert));
      (f.reihen || []).forEach((r) => {
        const b = el("div", "bahn");
        b.innerHTML = `<div class="nam">${r.name}</div><div class="sp"><i style="background:${
          pal[r.farbe] || r.farbe || pal.koralle};width:${(r.wert / max) * 100}%;transform:scaleX(0)"></i></div>` +
          `<div class="wert">0,00</div>`;
        box.appendChild(b);
        tween(b.querySelector("i"), { scaleX: [0, 1] }, t0 + (r.bei || 1.7), 1.1);
        zaehlen(b.querySelector(".wert"), r.wert, t0 + (r.bei || 1.7), 1.1, 2);
      });
      mitte.appendChild(box);
    }

    if (art === "umringt") {
      const raum = el("div", null, "position:relative;width:660px;height:660px");
      if (f.strahl !== false) {
        const st = el("div", "strahl",
          `background:${pal[f.strahl] || pal.lila};width:600px;height:600px;margin:-300px 0 0 -300px;transform:scale(0)`);
        raum.appendChild(st);
        tween(st, { scale: [0, 1], rotate: [30, 0] }, t0 + 0.6, 0.5, "back");
      }
      const ball = el("div", "ball", "width:140px;height:140px;margin:-70px 0 0 -70px;transform:scale(0)");
      raum.appendChild(ball);
      tween(ball, { scale: [0, 1] }, t0 + 0.8, 0.4, "back");
      const n = f.gegner || 7;
      for (let k = 0; k < n; k++) {
        const w = (k / n) * Math.PI * 2;
        const g = el("span", "gegner",
          `width:88px;height:88px;left:${286 + Math.cos(w) * 268}px;top:${286 + Math.sin(w) * 268}px;transform:scale(0)`);
        raum.appendChild(g);
        tween(g, { scale: [0, 1] }, t0 + 1.2 + k * 0.085, 0.34, "back");
      }
      mitte.appendChild(raum);
      if (f.wort) {
        const w = el("div", "mittel", "font-size:82px"); w.textContent = f.wort;
        mitte.appendChild(w); tween(w, { opacity: [0, 1], y: [26, 0] }, t0 + 2.8, 0.42);
      }
    }

    if (art === "streuung") {
      const plan = el("div", "plan", "width:1300px;height:740px");
      plan.innerHTML = `<div class="linie"></div><div class="kreis"></div>`;
      const n = f.punkte || 46;
      for (let k = 0; k < n; k++) {
        const x = 3 + streuwert(k, 1) * 92, y = 5 + streuwert(k, 2) * 88,
              r = 12 + streuwert(k, 3) * 24, o = 0.35 + streuwert(k, 4) * 0.45;
        const pt = el("span", "punkt",
          `left:${x}%;top:${y}%;width:${r}px;height:${r}px;opacity:${o};transform:scale(0)`);
        plan.appendChild(pt);
        tween(pt, { scale: [0, 1] }, t0 + 0.8 + k * 0.012, 0.3, "back");
      }
      mitte.appendChild(plan);
      if (f.wort) {
        const w = el("div", "mittel", "font-size:74px"); w.textContent = f.wort;
        mitte.appendChild(w); tween(w, { opacity: [0, 1], y: [26, 0] }, t0 + 2.5, 0.42);
      }
    }
  }

  /* --- Kamera ------------------------------------------------------------ */
  function kamera(spec, platz, B, H, SP, ZE) {
    const welt = document.getElementById("welt");
    // Jede Fahrt braucht Start UND Ziel. Nur das Ziel anzugeben laesst die
    // Kamera springen, weil der Startwert dann aus der Luft gegriffen ist.
    let vorher = { x: 0, y: 0, scale: 1 };
    (spec.felder || []).forEach((f, i) => {
      const [s, z] = platz(i);
      const nach = { x: -s * B, y: -z * H, scale: 1 };
      if (i > 0) {
        tween(welt, { x: [vorher.x, nach.x], y: [vorher.y, nach.y],
                      scale: [vorher.scale, nach.scale] },
              Math.max(0, (f.bei || 0) - 0.1), f.fahrt || 0.8, "inOut");
      }
      vorher = nach;
    });
    if (spec.schluss) {
      // So weit herauszoomen, dass das ganze Raster hineinpasst - und dann
      // mittig setzen. Bei einem quadratischen Raster geht 1/Spalten genau
      // auf, bei allen anderen bliebe sonst einseitig Papier stehen.
      const k = Math.min(1 / SP, 1 / ZE);
      const x = (B - SP * B * k) / 2, y = (H - ZE * H * k) / 2;
      tween(welt, { x: [vorher.x, x], y: [vorher.y, y], scale: [vorher.scale, k] },
            spec.schluss.bei, spec.schluss.dauer || 1.5, "inOut");
    }
  }

  window.__voxAufbau = aufbau;
})();
