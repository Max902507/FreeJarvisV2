/* FreeJarvis · Maus-Schicht
   Gilt für jede Oberfläche, ohne dass diese etwas tun muss:
   1. Partikel reagieren auf den Zeiger (J.glowAt wird abgefangen):
        "abstossen"  weichen aus,  "anziehen"  folgen dem Zeiger,  "wirbel"  kreisen um den Zeiger.
   2. Klick auf freie Fläche löst eine Welle aus, die Partikel nach außen schiebt und sichtbar ist.
   3. Die ganze Ansicht kippt leicht in Richtung des Zeigers (CSS-3D, kostet kaum Leistung).
   Eine Oberfläche stellt das in registerTheme({ maus: ... }) ein:
        maus: "abstossen" | "anziehen" | "wirbel" | "aus"      (Standard: "abstossen")
        kippen: false                                            (Kippen abschalten)
   Der Nutzer kann alles in den Einstellungen abschalten (maus_effekt, maus_kippen).
   Oberflächen mit eigener Mausbedienung (Retro: bots "eigene") bekommen keine Kippung. */
(function () {
  "use strict";
  const J = window.Jarvis; if (!J || J.maus) return;
  const TAU = Math.PI * 2, clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const BLOCK = "#jv-dock,#jv-set,#jv-tl,#jv-tr,#jv-brief,#jv-timers,#jv-intro,#jv-toast,#jv-botdash,#jv-pcask,.jv-widget,button,input,select,textarea,a";
  const M = J.maus = { x: 0, y: 0, sx: 0, sy: 0, an: 0, frei: false, waves: [], kx: 0, ky: 0, vx: 0, vy: 0, W: innerWidth, H: innerHeight };
  const RM = 140;                            // Wirkradius des Zeigers in Pixeln
  const SPEED = 560, LIFE = 1.7;             // Wellengeschwindigkeit (px/s) und Lebensdauer (s)

  const cfg = () => J.settings || {};
  const modus = () => { const t = J.theme || {}; const m = t.maus || "abstossen"; return cfg().maus_effekt === false ? "aus" : m; };

  document.addEventListener("pointermove", e => {
    M.x = e.clientX; M.y = e.clientY;
    M.frei = J.started && !(e.target.closest && e.target.closest(BLOCK));
    if (!M.an && M.frei) { M.sx = M.x; M.sy = M.y; }
    M.last = performance.now();
  }, { passive: true });
  document.addEventListener("pointerleave", () => { M.frei = false; }, { passive: true });
  document.addEventListener("pointerdown", e => {
    if (e.button || !J.started || modus() === "aus") return;
    if (e.target.closest && e.target.closest(BLOCK)) return;
    if (document.body.classList.contains("jv-bothover") || document.body.classList.contains("jv-botdrag")) return;
    M.waves.push({ x: e.clientX, y: e.clientY, t: 0 });
    if (M.waves.length > 5) M.waves.shift();
  }, { passive: true });

  /* ---------- Partikel abfangen ---------- */
  const orig = J.glowAt;
  J.glowAt = function (ctx, spr, x, y, size, alpha) {
    if (size < 56 && M.on) {
      let dx = 0, dy = 0, plus = 0;
      const m = M.modus;
      if (m !== "aus" && M.an > 0.01) {
        const ex = x - M.sx, ey = y - M.sy, d2 = ex * ex + ey * ey;
        if (d2 < RM * RM && d2 > 0.01) {
          const d = Math.sqrt(d2), f = (1 - d / RM), f2 = f * f * M.an, ux = ex / d, uy = ey / d;
          if (m === "abstossen") { dx = ux * f2 * 54; dy = uy * f2 * 54; }
          else if (m === "anziehen") { const p = Math.min(f2 * 40, d * 0.85); dx = -ux * p; dy = -uy * p; }
          else { const a = f2 * 1.1, c = Math.cos(a), s = Math.sin(a); dx = (ex * c - ey * s) - ex - ux * f2 * 8; dy = (ex * s + ey * c) - ey - uy * f2 * 8; }
          plus += f2 * 0.35;
        }
      }
      for (let i = 0; i < M.waves.length; i++) {
        const w = M.waves[i], ex = x - w.x, ey = y - w.y, d = Math.hypot(ex, ey) || 1, r = w.t * SPEED, df = d - r;
        if (df > -90 && df < 90) {
          const k = Math.exp(-(df * df) / 1300) * Math.max(0, 1 - w.t / LIFE);
          dx += ex / d * k * 34; dy += ey / d * k * 34; plus += k * 0.55;
        }
      }
      x += dx; y += dy; if (plus) { alpha += plus; size *= 1 + plus * 0.8; }
    }
    return orig.call(J, ctx, spr, x, y, size, alpha);
  };

  /* ---------- pro Bild: Zustand, Wellenring, Kippen ---------- */
  const rgb = () => (getComputedStyle(document.documentElement).getPropertyValue("--ac-rgb") || "120,190,255").trim();
  let ACC = null, cv = null, tx = 0, ty = 0;
  M.frame = function (ctx, W, H, S) {
    const dt = S.dt; M.W = W; M.H = H;
    M.modus = modus(); M.on = M.modus !== "aus";
    const aktiv = M.on && M.frei && J.started && performance.now() - (M.last || 0) < 6000;
    M.an += ((aktiv ? 1 : 0) - M.an) * Math.min(1, dt * (aktiv ? 9 : 3));
    M.sx += (M.x - M.sx) * Math.min(1, dt * 14); M.sy += (M.y - M.sy) * Math.min(1, dt * 14);
    for (let i = M.waves.length - 1; i >= 0; i--) { M.waves[i].t += dt; if (M.waves[i].t > LIFE) M.waves.splice(i, 1); }
    if (M.waves.length || M.an > 0.02) {                  // sichtbarer Ring der Welle und leises Zeigerlicht
      if (!ACC) ACC = rgb();
      ctx.save(); ctx.globalCompositeOperation = "lighter";
      for (const w of M.waves) {
        const r = w.t * SPEED, a = Math.max(0, 1 - w.t / LIFE);
        ctx.globalAlpha = a * 0.5; ctx.strokeStyle = `rgb(${ACC})`; ctx.lineWidth = 1.5 + a * 2.5;
        ctx.beginPath(); ctx.arc(w.x, w.y, r, 0, TAU); ctx.stroke();
        ctx.globalAlpha = a * 0.16; ctx.lineWidth = 14 * a; ctx.stroke();
      }
      ctx.restore();
    }
    kippen(dt, W, H);
  };

  /* Wie weit muss die gekippte Fläche vergrößert werden, damit an keiner Kante
     ein schwarzer Streifen auftaucht? Die vier Ecken werden durch dieselbe
     Drehung und Perspektive gerechnet wie im Browser; die Ecke, die am weitesten
     nach innen rutscht, gibt den Maßstab vor. Ohne das wirkt die Oberfläche wie
     eine starre Platte, die man wegkippt. */
  const TIEFE = 1600;
  function noetig(ry, rx, W, H, ox, oy) {
    const ca = Math.cos(ry), sa = Math.sin(ry), cb = Math.cos(rx), sb = Math.sin(rx);
    const ecken = [[-ox, -oy], [W - ox, -oy], [-ox, H - oy], [W - ox, H - oy]];
    let s = 1;
    for (let runde = 0; runde < 3; runde++) {
      let brauch = 1;
      for (const [ex, ey] of ecken) {
        const x = ex * s, y = ey * s;
        const x1 = x * ca, z1 = -x * sa;
        const y1 = y * cb - z1 * sb, z2 = y * sb + z1 * cb;
        const k = TIEFE / Math.max(1, TIEFE - z2);
        const X = Math.abs(x1 * k), Y = Math.abs(y1 * k);
        if (Math.abs(ex) > 2 && X > 1) brauch = Math.max(brauch, Math.abs(ex) / X * s);
        if (Math.abs(ey) > 2 && Y > 1) brauch = Math.max(brauch, Math.abs(ey) / Y * s);
      }
      s = brauch;
    }
    return Math.min(1.25, s * 1.006);
  }
  function kippen(dt, W, H) {
    if (!cv) cv = document.getElementById("jv-canvas"); if (!cv) return;
    const t = J.theme || {};
    const ok = cfg().maus_kippen !== false && t.kippen !== false && t.bots !== "eigene" && M.on;
    const o = J.orbit || { x: W / 2, y: H / 2 };
    // Weiche Kennlinie: in der Bildmitte kippt es kaum, zum Rand hin voll
    const kurve = v => { const a = clamp(v, -1, 1); return a * (0.35 + 0.65 * a * a); };
    const zx = ok && M.frei ? kurve((M.x - o.x) / (W / 2)) : 0, zy = ok && M.frei ? kurve((M.y - o.y) / (H / 2)) : 0;
    /* Gedämpfte Feder statt starrem Nachlaufen: die Ansicht setzt sich weich in
       Bewegung und läuft weich aus, ohne über das Ziel hinauszuschwingen.
       Zwei leicht verschiedene Frequenzen, damit es nicht wie ein Scharnier wirkt. */
    const h = Math.min(0.04, dt);
    for (const [w, pk, pv] of [[3.1, "kx", "vx"], [2.7, "ky", "vy"]]) {
      const ziel = pk === "kx" ? zx : zy;
      M[pv] += (w * w * (ziel - M[pk]) - 2 * w * M[pv]) * h;
      M[pk] += M[pv] * h;
    }
    if (Math.abs(M.kx) + Math.abs(M.ky) < 0.0015 && Math.abs(M.vx) + Math.abs(M.vy) < 0.01) {
      M.kx = M.ky = M.vx = M.vy = 0;
      if (cv.style.transform) { cv.style.transform = ""; cv.style.transformOrigin = ""; }
      return;
    }
    const ry = M.kx * 4.2 * Math.PI / 180, rx = -M.ky * 3.2 * Math.PI / 180;
    cv.style.transformOrigin = `${o.x}px ${o.y}px`;
    cv.style.transform = `perspective(${TIEFE}px) rotateX(${(rx * 180 / Math.PI).toFixed(3)}deg) rotateY(${(ry * 180 / Math.PI).toFixed(3)}deg) scale(${noetig(ry, rx, W, H, o.x, o.y).toFixed(4)})`;
  }
})();
