/* FreeJarvis · Bot-Team
   - zeichnet die Bots, die im Uhrzeigersinn um die Mitte der Oberfläche kreisen
   - Maus über einem Bot: der Bot hält an und eine Info-Karte zeigt, was er verarbeitet hat
   - Klick: Bot-Dashboard mit den Reitern Übersicht und Einstellungen
   - gedrückt halten: Bot auf eine andere Bahn ziehen
   - Reiter "Bots" in den Einstellungen
   Oberflächen melden ihren Mittelpunkt mit  J.orbit = { x, y, r }.
   Eine Oberfläche, die ihre Bots selbst zeichnet (z.B. Retro), setzt im Theme  bots: "eigene"
   und nutzt J.bots.karte(), J.bots.dash(), J.bots.aktiv(), J.bots.stats(). */
(function () {
  "use strict";
  const J = window.Jarvis; if (!J) return;
  const TAU = Math.PI * 2, esc = J.esc, $ = id => document.getElementById(id);
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const rgbOf = hex => { const m = /^#?([0-9a-f]{6})$/i.exec(hex || ""); const n = m ? parseInt(m[1], 16) : 0x4fb6ff; return [n >> 16 & 255, n >> 8 & 255, n & 255]; };
  const mix = (c, w) => c.map(v => Math.round(v + (255 - v) * w));
  const rgba = (c, a) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;

  const FORMEN = [["kugel", "Kugel"], ["wuerfel", "Würfel"], ["diamant", "Diamant"], ["pyramide", "Pyramide"], ["kristall", "Kristall"], ["ring", "Ring"], ["stern", "Stern"], ["atom", "Atom"], ["plasma", "Plasma"],
                  ["punktmensch", "Punktmensch"], ["arc", "Arc-Reaktor"], ["hud", "HUD-Ring"], ["auge", "Cyber-Auge"], ["globus", "Datenglobus"]];
  const FARBEN = ["#4fb6ff", "#39e6a8", "#ffc93c", "#ff8a1f", "#ff5fa2", "#ff3d6e", "#c77dff", "#7c8cff", "#35d6e8", "#e8f1ff"];
  const VORLAGEN = [
    { name: "Recherche", rolle: "Recherchiert Fakten und aktuelle Infos", auftrag: "Du recherchierst gründlich. Nenne die wichtigsten Fakten zuerst, sag klar, was gesichert ist und was nicht, und nenne Quellen in Worten.", websuche: true, stichwoerter: "recherchiere, such heraus", form: "kugel", farbe: "#4fb6ff" },
    { name: "Coder", rolle: "Schreibt, erklärt und prüft Code", auftrag: "Du bist ein erfahrener Programmierer. Gib lauffähigen Code in einem Codeblock aus und erkläre ihn danach in zwei, drei Sätzen. Weise auf Fehlerquellen hin.", stichwoerter: "programmiere, schreib ein skript", form: "wuerfel", farbe: "#39e6a8" },
    { name: "Texter", rolle: "Schreibt Texte, Mails und Posts", auftrag: "Du schreibst klare, lebendige Texte auf Deutsch. Frag nicht lange nach, liefere einen fertigen Entwurf im passenden Ton.", stichwoerter: "formuliere, schreib eine mail", form: "diamant", farbe: "#ff5fa2" },
    { name: "Übersetzer", rolle: "Übersetzt zwischen Sprachen", auftrag: "Du übersetzt genau und natürlich. Gib nur die Übersetzung aus, außer es gibt eine wichtige Anmerkung zur Bedeutung.", stichwoerter: "übersetze, übersetz", form: "ring", farbe: "#ffc93c" },
    { name: "Planer", rolle: "Plant Tage, Projekte und To-dos", auftrag: "Du machst aus Vorhaben konkrete Pläne: Schritte in sinnvoller Reihenfolge, mit Zeitbedarf und dem nächsten kleinen Schritt.", stichwoerter: "plane, mach einen plan", form: "pyramide", farbe: "#ff8a1f" },
    { name: "Analyst", rolle: "Prüft Zahlen und Argumente kritisch", auftrag: "Du prüfst Aussagen, Zahlen und Pläne kritisch. Nenne Schwächen, Annahmen und Gegenargumente ehrlich und knapp.", stichwoerter: "analysiere, prüf das", form: "kristall", farbe: "#c77dff" }
  ];
  const PROVN = { "": "wie Jarvis", ollama: "Lokal · Ollama", claude: "Claude · API", openai: "OpenAI-kompatibel" };

  /* =============================================================== Formen zeichnen (auch für die Vorschauen) */
  const PH = (1 + Math.sqrt(5)) / 2;
  const POLY = {
    wuerfel: { v: [[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1], [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]], f: [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [2, 3, 7, 6], [1, 2, 6, 5], [0, 3, 7, 4]], s: 0.62 },
    diamant: { v: [[1, 0, 0], [-1, 0, 0], [0, 1.35, 0], [0, -1.35, 0], [0, 0, 1], [0, 0, -1]], f: [[0, 2, 4], [0, 4, 3], [0, 3, 5], [0, 5, 2], [1, 2, 4], [1, 4, 3], [1, 3, 5], [1, 5, 2]], s: 0.82 },
    pyramide: { v: [[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]], f: [[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]], s: 0.74 },
    kristall: { v: [[-1, PH, 0], [1, PH, 0], [-1, -PH, 0], [1, -PH, 0], [0, -1, PH], [0, 1, PH], [0, -1, -PH], [0, 1, -PH], [PH, 0, -1], [PH, 0, 1], [-PH, 0, -1], [-PH, 0, 1]],
      f: [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]], s: 0.55 }
  };
  function glow(ctx, x, y, r, c, a) {
    const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, rgba(c, a)); g.addColorStop(0.35, rgba(c, a * 0.35)); g.addColorStop(1, rgba(c, 0));
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill();
  }
  function drawPoly(ctx, P, x, y, r, c, t, ph) {
    const a = t * 0.7 + ph, b = t * 0.45 + ph * 1.7, ca = Math.cos(a), sa = Math.sin(a), cb = Math.cos(b), sb = Math.sin(b), k = r * P.s;
    const pts = P.v.map(v => { const x1 = v[0] * ca + v[2] * sa, z1 = -v[0] * sa + v[2] * ca, y1 = v[1] * cb - z1 * sb, z2 = v[1] * sb + z1 * cb; return [x + x1 * k, y + y1 * k, z2]; });
    const faces = P.f.map(f => {
      const p0 = pts[f[0]], p1 = pts[f[1]], p2 = pts[f[2]];
      const ux = p1[0] - p0[0], uy = p1[1] - p0[1], uz = (p1[2] - p0[2]) * k, vx = p2[0] - p0[0], vy = p2[1] - p0[1], vz = (p2[2] - p0[2]) * k;
      let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx; const nl = Math.hypot(nx, ny, nz) || 1;
      const z = f.reduce((s, i) => s + pts[i][2], 0) / f.length; if (nz * z < 0) { nx = -nx; ny = -ny; nz = -nz; }
      return { f, z, li: clamp((-nx * 0.45 - ny * 0.7 + Math.abs(nz) * 0.55) / nl, -1, 1) };
    }).sort((p, q) => p.z - q.z);
    ctx.lineJoin = "round";
    for (const F of faces) {
      const front = F.z > 0, l = 0.5 + 0.5 * F.li;
      ctx.beginPath(); F.f.forEach((i, n) => n ? ctx.lineTo(pts[i][0], pts[i][1]) : ctx.moveTo(pts[i][0], pts[i][1])); ctx.closePath();
      ctx.fillStyle = rgba(mix(c, l * 0.55), front ? 0.2 + l * 0.42 : 0.1);
      ctx.fill();
      ctx.strokeStyle = rgba(mix(c, 0.55 + l * 0.4), front ? 0.9 : 0.28); ctx.lineWidth = Math.max(0.8, r * 0.035); ctx.stroke();
    }
  }
  /* ---------- Punktmensch: Figur aus vielen Lichtpunkten (feste Verteilung, einmal berechnet) */
  const MENSCH = (() => {
    let sd = 7; const rnd = () => (sd = (sd * 16807) % 2147483647) / 2147483647, pts = [];
    const disc = (cx, cy, rx, ry, n) => { for (let i = 0; i < n; i++) { const a = rnd() * TAU, d = Math.sqrt(rnd()); pts.push([cx + Math.cos(a) * d * rx, cy + Math.sin(a) * d * ry, rnd()]); } };
    const strich = (x1, y1, x2, y2, br, n) => { for (let i = 0; i < n; i++) { const u = rnd(), o = (rnd() - 0.5) * br; pts.push([x1 + (x2 - x1) * u + o, y1 + (y2 - y1) * u + o * 0.4, rnd()]); } };
    disc(0, -0.72, 0.17, 0.2, 46);                                   // Kopf
    strich(0, -0.52, 0, -0.44, 0.1, 6);                              // Hals
    for (let i = 0; i < 80; i++) { const y = -0.44 + rnd() * 0.5, w = 0.3 - (y + 0.44) * 0.12; pts.push([(rnd() - 0.5) * 2 * w, y, rnd()]); }   // Rumpf
    strich(-0.3, -0.4, -0.52, 0.05, 0.1, 22); strich(0.3, -0.4, 0.52, 0.05, 0.1, 22);   // Arme
    strich(-0.12, 0.06, -0.17, 0.78, 0.13, 30); strich(0.12, 0.06, 0.17, 0.78, 0.13, 30); // Beine
    return pts;
  })();

  function drawShape(ctx, form, x, y, r, c, t, ph, act) {
    ph = ph || 0; act = act || 0;
    ctx.save();
    ctx.globalCompositeOperation = "lighter";
    glow(ctx, x, y, r * (2.1 + act * 1.1), c, 0.2 + act * 0.25);
    ctx.globalCompositeOperation = "source-over";
    if (POLY[form]) {
      drawPoly(ctx, POLY[form], x, y, r, c, t, ph);
      ctx.globalCompositeOperation = "lighter"; glow(ctx, x, y, r * 0.5, mix(c, 0.7), 0.55 + act * 0.3);
    } else if (form === "ring") {
      const tilt = 0.35 + 0.5 * (0.5 + 0.5 * Math.sin(t * 0.9 + ph)), rot = t * 0.5 + ph;
      ctx.translate(x, y); ctx.rotate(rot);
      for (let i = 0; i < 2; i++) {
        ctx.beginPath(); ctx.ellipse(0, 0, r * 0.82, r * 0.82 * (i ? 1 - tilt * 0.75 : tilt), i ? 1.2 : 0, 0, TAU);
        ctx.strokeStyle = rgba(c, 0.28); ctx.lineWidth = r * 0.3; ctx.stroke();
        ctx.strokeStyle = rgba(mix(c, 0.75), 0.95); ctx.lineWidth = Math.max(1, r * 0.07); ctx.stroke();
      }
      ctx.globalCompositeOperation = "lighter"; glow(ctx, 0, 0, r * 0.55, mix(c, 0.8), 0.9);
    } else if (form === "stern") {
      ctx.translate(x, y); ctx.rotate(t * 0.6 + ph);
      const sq = 0.55 + 0.45 * Math.abs(Math.cos(t * 0.8 + ph));
      const star = (R, w) => { ctx.beginPath(); for (let i = 0; i < 10; i++) { const a = i / 10 * TAU - Math.PI / 2, rr = i % 2 ? R * 0.42 : R; ctx[i ? "lineTo" : "moveTo"](Math.cos(a) * rr * w, Math.sin(a) * rr); } ctx.closePath(); };
      const g = ctx.createRadialGradient(0, 0, 0, 0, 0, r); g.addColorStop(0, rgba(mix(c, 0.9), 0.95)); g.addColorStop(0.5, rgba(mix(c, 0.3), 0.7)); g.addColorStop(1, rgba(c, 0.25));
      star(r, sq); ctx.fillStyle = g; ctx.fill(); ctx.strokeStyle = rgba(mix(c, 0.8), 0.95); ctx.lineWidth = Math.max(1, r * 0.05); ctx.lineJoin = "round"; ctx.stroke();
      star(r * 0.45, sq); ctx.fillStyle = rgba(mix(c, 0.95), 0.6); ctx.fill();
    } else if (form === "atom") {
      ctx.translate(x, y);
      for (let i = 0; i < 3; i++) {
        const rot = i * Math.PI / 3 + t * 0.25 + ph;
        ctx.save(); ctx.rotate(rot);
        ctx.beginPath(); ctx.ellipse(0, 0, r * 0.95, r * 0.34, 0, 0, TAU); ctx.strokeStyle = rgba(mix(c, 0.5), 0.75); ctx.lineWidth = Math.max(1, r * 0.045); ctx.stroke();
        const a = t * (2.2 + i * 0.5) + i * 2 + ph, ex = Math.cos(a) * r * 0.95, ey = Math.sin(a) * r * 0.34;
        ctx.fillStyle = rgba(mix(c, 0.9), 1); ctx.beginPath(); ctx.arc(ex, ey, Math.max(1.5, r * 0.1), 0, TAU); ctx.fill();
        ctx.restore();
      }
      const g = ctx.createRadialGradient(-r * 0.08, -r * 0.08, 0, 0, 0, r * 0.34); g.addColorStop(0, "rgba(255,255,255,1)"); g.addColorStop(0.5, rgba(mix(c, 0.4), 1)); g.addColorStop(1, rgba(c, 0.6));
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0, 0, r * 0.32, 0, TAU); ctx.fill();
    } else if (form === "punktmensch") {
      ctx.globalCompositeOperation = "lighter";
      const atem = 1 + Math.sin(t * 1.6 + ph) * 0.012, hs = r * 0.95;
      for (const p of MENSCH) {
        const tw = 0.55 + 0.45 * Math.sin(t * (1.2 + p[2] * 2.6) + p[2] * 40 + ph);
        glow(ctx, x + p[0] * hs * atem + Math.sin(t * 0.9 + p[2] * 20) * r * 0.012, y + p[1] * hs * atem, r * (0.07 + p[2] * 0.07), mix(c, 0.35 + p[2] * 0.5), (0.45 + act * 0.3) * tw);
      }
      glow(ctx, x, y - hs * 0.72, r * 0.5, mix(c, 0.7), 0.35 + act * 0.3);
    } else if (form === "arc") {                       // Arc-Reaktor wie bei Iron Man
      ctx.translate(x, y);
      ctx.beginPath(); ctx.arc(0, 0, r * 0.92, 0, TAU); ctx.strokeStyle = rgba(mix(c, 0.55), 0.95); ctx.lineWidth = Math.max(1.4, r * 0.1); ctx.stroke();
      ctx.beginPath(); ctx.arc(0, 0, r * 0.8, 0, TAU); ctx.fillStyle = "rgba(4,10,20,.55)"; ctx.fill();
      for (let i = 0; i < 10; i++) {
        const a = i / 10 * TAU + t * 0.15 + ph, a2 = a + TAU / 10 * 0.62;
        ctx.beginPath(); ctx.arc(0, 0, r * 0.7, a, a2); ctx.arc(0, 0, r * 0.46, a2, a, true); ctx.closePath();
        ctx.fillStyle = rgba(mix(c, 0.25 + 0.15 * Math.sin(t * 2 + i)), 0.55 + act * 0.25); ctx.fill();
        ctx.strokeStyle = rgba(mix(c, 0.8), 0.8); ctx.lineWidth = Math.max(0.8, r * 0.025); ctx.stroke();
      }
      ctx.beginPath(); ctx.arc(0, 0, r * 0.4, 0, TAU); ctx.strokeStyle = rgba(mix(c, 0.7), 0.9); ctx.lineWidth = Math.max(1, r * 0.05); ctx.stroke();
      ctx.globalCompositeOperation = "lighter"; glow(ctx, 0, 0, r * 0.62, [255, 255, 255], 0.9 + act * 0.1); glow(ctx, 0, 0, r * 1.05, mix(c, 0.5), 0.45 + 0.15 * Math.sin(t * 3 + ph) + act * 0.2);
    } else if (form === "hud") {                       // HUD-Ring: drehende Bögen mit Skala, wie in Jarvis-Szenen
      ctx.translate(x, y);
      const ring = (rr, n, lw, sp, al, dash) => {
        ctx.save(); ctx.rotate(t * sp + ph); ctx.lineWidth = lw; ctx.strokeStyle = rgba(mix(c, 0.55), al);
        for (let i = 0; i < n; i++) { const a = i / n * TAU, w = TAU / n * dash; ctx.beginPath(); ctx.arc(0, 0, rr, a, a + w); ctx.stroke(); }
        ctx.restore();
      };
      ring(r * 0.94, 3, Math.max(1.4, r * 0.07), 0.7, 0.95, 0.62); ring(r * 0.78, 12, Math.max(1, r * 0.04), -1.1, 0.8, 0.45);
      ring(r * 0.6, 2, Math.max(1.2, r * 0.06), 1.7 + act, 0.95, 0.4);
      ctx.save(); ctx.rotate(-t * 0.4 + ph); ctx.strokeStyle = rgba(mix(c, 0.7), 0.7); ctx.lineWidth = 1;
      for (let i = 0; i < 36; i++) { const a = i / 36 * TAU, l = i % 3 ? 0.05 : 0.1; ctx.beginPath(); ctx.moveTo(Math.cos(a) * r * 0.5, Math.sin(a) * r * 0.5); ctx.lineTo(Math.cos(a) * r * (0.5 - l), Math.sin(a) * r * (0.5 - l)); ctx.stroke(); }
      ctx.restore();
      ctx.globalCompositeOperation = "lighter"; glow(ctx, 0, 0, r * 0.5, mix(c, 0.8), 0.6 + act * 0.3);
      ctx.fillStyle = "rgba(255,255,255,.95)"; ctx.beginPath(); ctx.arc(0, 0, Math.max(1.5, r * 0.06), 0, TAU); ctx.fill();
    } else if (form === "auge") {                      // Cyber-Auge: schaut umher, blinzelt
      ctx.translate(x, y);
      const bl = Math.max(0.08, Math.abs(Math.sin(t * 0.55 + ph)) > 0.985 ? 0.08 : 1), lx = Math.sin(t * 0.7 + ph) * r * 0.16, ly = Math.cos(t * 0.5 + ph) * r * 0.08;
      ctx.beginPath(); ctx.moveTo(-r, 0); ctx.quadraticCurveTo(0, -r * 0.78 * bl, r, 0); ctx.quadraticCurveTo(0, r * 0.78 * bl, -r, 0); ctx.closePath();
      ctx.fillStyle = rgba(mix(c, 0), 0.18); ctx.fill(); ctx.strokeStyle = rgba(mix(c, 0.6), 0.95); ctx.lineWidth = Math.max(1.2, r * 0.06); ctx.stroke();
      ctx.save(); ctx.clip(); ctx.translate(lx, ly);
      ctx.beginPath(); ctx.arc(0, 0, r * 0.44, 0, TAU); ctx.fillStyle = rgba(mix(c, 0.15), 0.6); ctx.fill(); ctx.strokeStyle = rgba(mix(c, 0.8), 0.95); ctx.lineWidth = Math.max(1, r * 0.04); ctx.stroke();
      ctx.strokeStyle = rgba(mix(c, 0.7), 0.5); ctx.lineWidth = 1;
      for (let i = 0; i < 24; i++) { const a = i / 24 * TAU + t * 0.3; ctx.beginPath(); ctx.moveTo(Math.cos(a) * r * 0.2, Math.sin(a) * r * 0.2); ctx.lineTo(Math.cos(a) * r * 0.42, Math.sin(a) * r * 0.42); ctx.stroke(); }
      ctx.beginPath(); ctx.arc(0, 0, r * (0.16 + act * 0.05), 0, TAU); ctx.fillStyle = "rgba(5,10,18,.95)"; ctx.fill();
      ctx.globalCompositeOperation = "lighter"; glow(ctx, -r * 0.12, -r * 0.12, r * 0.22, [255, 255, 255], 0.8); ctx.restore();
    } else if (form === "globus") {                    // Datenglobus: drehendes Gitter mit Knotenpunkten
      ctx.translate(x, y);
      const rot = t * 0.5 + ph, R = r * 0.88; ctx.lineWidth = Math.max(0.8, r * 0.03);
      ctx.beginPath(); ctx.arc(0, 0, R, 0, TAU); ctx.strokeStyle = rgba(mix(c, 0.6), 0.9); ctx.stroke();
      for (let i = 0; i < 6; i++) {                    // Längengrade
        const w = Math.abs(Math.cos(rot + i * Math.PI / 6));
        ctx.beginPath(); ctx.ellipse(0, 0, R * w, R, 0, 0, TAU); ctx.strokeStyle = rgba(mix(c, 0.4), 0.35 + 0.25 * w); ctx.stroke();
      }
      for (let k = -2; k <= 2; k++) { const yy = k * R * 0.3, rr = Math.sqrt(Math.max(0, R * R - yy * yy)); ctx.beginPath(); ctx.ellipse(0, yy, rr, rr * 0.16, 0, 0, TAU); ctx.strokeStyle = rgba(mix(c, 0.4), 0.3); ctx.stroke(); }
      ctx.globalCompositeOperation = "lighter";
      for (let i = 0; i < 16; i++) {                   // leuchtende Knoten auf der Oberfläche
        const lo = rot * 1.3 + i * 2.4, la = Math.sin(i * 1.7) * 1.1, cl = Math.cos(la), z = Math.cos(lo) * cl;
        if (z > -0.15) glow(ctx, Math.sin(lo) * cl * R, Math.sin(la) * R, r * (0.12 + z * 0.08), mix(c, 0.8), 0.35 + z * 0.55);
      }
      glow(ctx, 0, 0, r * 0.7, mix(c, 0.3), 0.3 + act * 0.25);
    } else if (form === "plasma") {
      ctx.translate(x, y);
      for (let L = 0; L < 3; L++) {
        ctx.beginPath();
        for (let i = 0; i <= 48; i++) {
          const a = i / 48 * TAU, rr = r * (0.9 - L * 0.22) * (1 + 0.13 * Math.sin(3 * a + t * (1.4 + L * 0.5) + ph + L) + 0.08 * Math.sin(5 * a - t * 2.1 + L * 2) + act * 0.08 * Math.sin(9 * a + t * 9));
          ctx[i ? "lineTo" : "moveTo"](Math.cos(a) * rr, Math.sin(a) * rr);
        }
        ctx.closePath();
        const g = ctx.createRadialGradient(0, 0, 0, 0, 0, r); g.addColorStop(0, rgba(mix(c, 0.85 - L * 0.1), 0.85)); g.addColorStop(1, rgba(c, 0.18));
        ctx.fillStyle = g; ctx.globalCompositeOperation = L ? "lighter" : "source-over"; ctx.fill();
        if (!L) { ctx.strokeStyle = rgba(mix(c, 0.7), 0.8); ctx.lineWidth = Math.max(1, r * 0.04); ctx.stroke(); }
      }
    } else {   // kugel: Glaskugel
      const g = ctx.createRadialGradient(x - r * 0.3, y - r * 0.35, r * 0.05, x, y, r * 0.86);
      g.addColorStop(0, rgba(mix(c, 0.85), 0.95)); g.addColorStop(0.45, rgba(c, 0.6)); g.addColorStop(0.9, rgba(c, 0.32)); g.addColorStop(1, rgba(mix(c, 0.6), 0.85));
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r * 0.86, 0, TAU); ctx.fill();
      ctx.strokeStyle = rgba(mix(c, 0.8), 0.9); ctx.lineWidth = Math.max(1, r * 0.04); ctx.stroke();
      ctx.save(); ctx.beginPath(); ctx.arc(x, y, r * 0.84, 0, TAU); ctx.clip(); ctx.globalCompositeOperation = "lighter";
      for (let i = 0; i < 3; i++) { ctx.beginPath(); ctx.ellipse(x, y, r * 0.84, r * 0.84 * Math.abs(Math.sin(t * 0.6 + ph + i * 1.05)), t * 0.3 + i * 1.05 + ph, 0, TAU); ctx.strokeStyle = rgba(mix(c, 0.6), 0.3); ctx.lineWidth = Math.max(0.7, r * 0.025); ctx.stroke(); }
      glow(ctx, x, y + r * 0.1, r * 0.5, mix(c, 0.8), 0.6 + act * 0.4); ctx.restore();
      const hl = ctx.createRadialGradient(x - r * 0.32, y - r * 0.42, 0, x - r * 0.32, y - r * 0.42, r * 0.4);
      hl.addColorStop(0, "rgba(255,255,255,.75)"); hl.addColorStop(1, "rgba(255,255,255,0)"); ctx.fillStyle = hl;
      ctx.beginPath(); ctx.ellipse(x - r * 0.32, y - r * 0.42, r * 0.36, r * 0.2, -0.6, 0, TAU); ctx.fill();
    }
    ctx.restore();
  }

  /* =============================================================== Ebene über der Oberfläche */
  const B = { list: [], cv: null, ctx: null, W: 0, H: 0, DPR: 1, hover: null, drag: null, stats: {}, first: true, px: 0, py: 0, pfree: false, spur: [] };
  const cv = document.createElement("canvas"); cv.id = "jv-bots"; document.body.appendChild(cv);
  B.cv = cv; B.ctx = cv.getContext("2d");
  const orbSave = J.store.get("botorbit", {});
  let ACC = null;
  const eigene = () => !!(J.theme && J.theme.bots === "eigene");   // Oberfläche zeichnet ihre Bots selbst
  const setOffen = () => { const s = $("jv-set"); return !!(s && s.classList.contains("on")); };

  function sync() {
    const st = J.settings || {}, want = (st.bots_sichtbar === false ? [] : (st.bots || []).filter(b => b.aktiv));
    const n = want.length;
    want.forEach((cfg, i) => {
      let b = B.list.find(x => x.id === cfg.id);
      if (!b) {
        const sv = orbSave[cfg.id] || {};
        b = { id: cfg.id, a: sv.a != null && !B.first ? sv.a : i / Math.max(1, n) * TAU - Math.PI / 2, rf: sv.rf || 1.42 + (i % 3) * 0.3, x: null, y: null, vx: 0, vy: 0, sc: 0, born: B.first ? -i * 0.14 : 0, act: 0, ph: Math.random() * TAU, hov: 0, burst: B.first ? 0 : 1, busy: false };
        B.list.push(b);
      }
      b.cfg = cfg; b.rgb = rgbOf(cfg.farbe); b.gone = false;
    });
    B.list.forEach(b => { if (!want.some(c => c.id === b.id)) b.gone = true; });
    B.first = false;
    if (D.id && !want.some(c => c.id === D.id)) dashZu();
    if (D.id) dashKopf();
  }
  J.on("settings", sync);
  function loadStats(dann) { return J.api("/api/bots/status").then(r => { B.stats = r.stats || {}; if (dann) dann(); }).catch(() => { }); }
  loadStats();
  J.on("bot", ev => {
    const b = B.list.find(x => x.id === ev.id);
    if (b) { if (ev.phase === "start") { b.busy = true; b.burst = 1; } else { b.busy = false; b.burst = 1; } }
    if (ev.phase === "ende") setTimeout(() => loadStats(() => { if (D.id === ev.id) dashBody(); }), 350);
    if (D.id === ev.id) dashKopf();
  });
  J.on("state", s => { if (s === "idle") { B.list.forEach(b => { b.busy = false; }); if (D.id) dashKopf(); } });

  function geo() {
    const W = B.W, H = B.H, o = J.orbit || { x: W / 2, y: H * 0.46, r: Math.min(W * 0.3, H * 0.33) };
    const R = Math.max(60, o.r || 160), k = clamp(Math.min(W, H) / 900, 0.7, 1.25);
    return { x: o.x, y: o.y, R, k, sq: 0.44, maxRf: Math.max(1.1, Math.min((W * 0.47) / R, (H * 0.42) / (R * 0.44))) };
  }
  function radius(b, g) { const st = J.settings || {}; return 27 * g.k * clamp(+b.cfg.groesse || 1, 0.4, 2.5) * clamp(+st.bot_groesse || 1, 0.3, 3); }
  function target(b, g) {
    const rf = Math.min(b.rf, g.maxRf), tl = b.tilt || 0, ex = Math.cos(b.a) * g.R * rf, ey = Math.sin(b.a) * g.R * rf * g.sq;
    return { x: g.x + ex * Math.cos(tl) - ey * Math.sin(tl), y: g.y + ex * Math.sin(tl) + ey * Math.cos(tl), d: Math.sin(b.a) };
  }

  /* ---------- Lichtspur am Mauszeiger (auf jeder Oberfläche) */
  function zeiger(ctx, dt) {
    if (!ACC) ACC = (getComputedStyle(document.documentElement).getPropertyValue("--ac-rgb") || "120,190,255").trim();
    const S = B.spur;
    if ((J.settings || {}).maus_spur === false) { S.length = 0; return; }       // in den Einstellungen abgeschaltet
    if (B.px && B.pfree && J.started && !setOffen()) {
      const l = S[S.length - 1];
      if (!l || Math.hypot(l.x - B.px, l.y - B.py) > 3) S.push({ x: B.px, y: B.py, a: 1 });
    }
    for (let i = S.length - 1; i >= 0; i--) { S[i].a -= dt * 1.7; if (S[i].a <= 0) S.splice(i, 1); }
    if (S.length > 26) S.splice(0, S.length - 26);
    if (S.length < 2) return;
    // Weich und halb durchsichtig: zwei unscharfe Schichten (Weichzeichner, wo der Browser ihn kann)
    const blur = "filter" in ctx;
    ctx.save(); ctx.globalCompositeOperation = "lighter"; ctx.lineCap = "round"; ctx.lineJoin = "round";
    const bahn = () => { ctx.beginPath(); S.forEach((p, i) => i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)); };
    const alpha = S[S.length - 1].a;
    ctx.globalAlpha = 0.5 * Math.min(1, alpha + 0.3); ctx.strokeStyle = `rgb(${ACC})`;
    if (blur) ctx.filter = "blur(7px)"; ctx.lineWidth = 9; bahn(); ctx.stroke();
    if (blur) ctx.filter = "blur(2.5px)"; ctx.lineWidth = 2.4; ctx.globalAlpha = 0.5 * Math.min(1, alpha + 0.3); bahn(); ctx.stroke();
    ctx.restore();
  }

  function frame(S, W, H) {
    if (B.W !== W || B.H !== H) {
      B.W = W; B.H = H; B.DPR = Math.min(window.devicePixelRatio || 1, 2);
      cv.width = Math.round(W * B.DPR); cv.height = Math.round(H * B.DPR);
    }
    const ctx = B.ctx, dt = S.dt, t = S.t, st = J.settings || {};
    ctx.setTransform(B.DPR, 0, 0, B.DPR, 0, 0); ctx.clearRect(0, 0, W, H);
    zeiger(ctx, dt);
    if (eigene()) return;                       // Retro und Co. zeichnen ihre Bots selbst
    if (!B.list.length) { if (B.hover) { B.hover = null; hideCard(); } return; }
    if (!B.drag) {                              // Bots wandern unter dem ruhenden Zeiger weg: jedes Bild prüfen
      const h = setOffen() || !B.px || !B.pfree ? null : hit(B.px, B.py);
      if (h !== B.hover) { B.hover = h; document.body.classList.toggle("jv-bothover", !!h); if (!h) hideCard(); }
    }
    const g = geo(), speed = 0.16 * clamp(+st.bot_tempo || 1, 0.1, 4);
    B.list.forEach((b, i) => { b.tilt = ((i % 3) - 1) * 0.16; });
    ctx.lineWidth = 1;
    const seen = {};
    for (const b of B.list) {                   // Umlaufbahnen
      const rf = Math.min(b.rf, g.maxRf), key = rf.toFixed(2) + b.tilt; if (seen[key] || b.gone) continue; seen[key] = 1;
      ctx.beginPath(); ctx.ellipse(g.x, g.y, g.R * rf, g.R * rf * g.sq, b.tilt, 0, TAU);
      ctx.strokeStyle = rgba(b.rgb, 0.1 + b.hov * 0.2 + b.act * 0.15); ctx.setLineDash([2, 7]); ctx.stroke();
    }
    ctx.setLineDash([]);
    const order = B.list.slice().sort((p, q) => Math.sin(p.a) - Math.sin(q.a));
    for (const b of order) {
      const dragging = B.drag && B.drag.b === b;
      b.born += dt;
      b.hov += (((B.hover === b || dragging) ? 1 : 0) - b.hov) * Math.min(1, dt * 11);
      if (!dragging) b.a += dt * speed * (1 + b.act * 2.2) / Math.pow(Math.min(b.rf, g.maxRf), 1.15) * (1 - b.hov);   // Hover hält den Bot an
      const T = dragging ? { x: B.drag.x, y: B.drag.y, d: 0.6 } : target(b, g);
      if (b.x == null) { b.x = g.x; b.y = g.y; }
      const kf = dragging ? 160 : 30, cf = dragging ? 22 : 8.5;
      b.vx += ((T.x - b.x) * kf - b.vx * cf) * dt; b.vy += ((T.y - b.y) * kf - b.vy * cf) * dt;
      b.x += b.vx * dt; b.y += b.vy * dt;
      b.sc = clamp(b.sc + (b.born > 0 ? (b.gone ? -1 : 1) : 0) * dt * 2.6, 0, 1);
      b.act += ((b.busy ? 1 : 0) - b.act) * Math.min(1, dt * 5);
      b.burst = Math.max(0, b.burst - dt * 1.1);
      if (b.sc <= 0) continue;
      const e = b.sc, ease = e < 1 ? 1 - Math.pow(1 - e, 3) + Math.sin(e * Math.PI) * 0.18 : 1;
      const r = radius(b, g) * ease * (1 + 0.13 * T.d) * (1 + b.hov * 0.18 + (dragging ? 0.1 : 0)) * (1 + b.act * 0.1 * Math.sin(t * 9));
      b.r = r; b.alpha = dragging ? 1 : 0.78 + 0.22 * (0.5 + 0.5 * T.d);
      const link = Math.max(b.act, b.hov * 0.6, b.burst * 0.8);
      if (link > 0.02) {                        // Leitung zum Kern
        const gr = ctx.createLinearGradient(g.x, g.y, b.x, b.y); gr.addColorStop(0, rgba(b.rgb, 0)); gr.addColorStop(0.25, rgba(b.rgb, 0.5 * link)); gr.addColorStop(1, rgba(mix(b.rgb, 0.5), 0.85 * link));
        ctx.strokeStyle = gr; ctx.lineWidth = 1 + b.act * 1.5; ctx.beginPath(); ctx.moveTo(g.x, g.y); ctx.lineTo(b.x, b.y); ctx.stroke();
        if (b.act > 0.05) for (let i = 0; i < 3; i++) {
          const u = ((t * 0.9 + i / 3) % 1), px = b.x + (g.x - b.x) * u, py = b.y + (g.y - b.y) * u;
          ctx.globalCompositeOperation = "lighter"; glow(ctx, px, py, 7 + b.act * 5, mix(b.rgb, 0.6), 0.9 * b.act * Math.sin(u * Math.PI)); ctx.globalCompositeOperation = "source-over";
        }
      }
      if (b.burst > 0) { const q = 1 - b.burst; ctx.strokeStyle = rgba(mix(b.rgb, 0.5), b.burst * 0.8); ctx.lineWidth = 2 * b.burst + 0.5; ctx.beginPath(); ctx.arc(b.x, b.y, r * (1 + q * 2.4), 0, TAU); ctx.stroke(); }
      const vl = Math.hypot(b.vx, b.vy);
      if (vl > 40) { const m = Math.min(1, vl / 900); ctx.globalCompositeOperation = "lighter"; for (let i = 1; i <= 4; i++) glow(ctx, b.x - b.vx / vl * r * i * 0.7 * (0.4 + m), b.y - b.vy / vl * r * i * 0.7 * (0.4 + m), r * (1.1 - i * 0.16), b.rgb, 0.16 * m * (1 - i / 5)); ctx.globalCompositeOperation = "source-over"; }
      ctx.globalAlpha = b.alpha * Math.min(1, e * 1.6);
      drawShape(ctx, b.cfg.form, b.x, b.y, r, b.rgb, t, b.ph, Math.max(b.act, b.hov * 0.5));
      if (b.hov > 0.02) {                       // Ring: der Bot ist angefasst
        ctx.globalAlpha = b.hov * 0.9; ctx.strokeStyle = rgba(mix(b.rgb, 0.65), 0.95); ctx.lineWidth = 1.4; ctx.setLineDash([4, 4]); ctx.lineDashOffset = -t * 14;
        ctx.beginPath(); ctx.arc(b.x, b.y, r * 1.35, 0, TAU); ctx.stroke(); ctx.setLineDash([]);
      }
      // Name IMMER über dem Bot
      ctx.globalAlpha = Math.min(1, e * 1.6) * (st.bot_namen === false ? Math.max(0.12, b.hov) : 0.8 + b.hov * 0.2);
      const fs = Math.round(clamp(r * 0.42, 10, 15));
      ctx.font = `600 ${fs}px "Segoe UI",system-ui,sans-serif`; ctx.textAlign = "center"; ctx.textBaseline = "bottom";
      ctx.shadowColor = "rgba(0,0,0,.9)"; ctx.shadowBlur = 7; ctx.fillStyle = "#fff";
      ctx.fillText(b.cfg.name, b.x, b.y - r * 1.16 - 2);
      if (b.act > 0.3) { ctx.textBaseline = "top"; ctx.font = `600 ${Math.round(fs * 0.76)}px "Segoe UI",system-ui,sans-serif`; ctx.fillStyle = rgba(mix(b.rgb, 0.6), 1); ctx.fillText("arbeitet …", b.x, b.y + r * 1.16 + 2); }
      ctx.shadowBlur = 0; ctx.globalAlpha = 1;
    }
    B.list = B.list.filter(b => !(b.gone && b.sc <= 0));
    if (B.hover && !B.drag) zeigeKarte(B.hover.cfg, B.hover.x, B.hover.y, B.hover.r || 24, B.hover.busy); else if (B.drag) hideCard();
  }

  /* =============================================================== Maus: schweben, klicken, ziehen */
  const BLOCK = "#jv-dock,#jv-set,#jv-tl,#jv-tr,#jv-brief,#jv-timers,#jv-intro,#jv-toast,#jv-botdash,#jv-pcask,.jv-widget,button,input,select,textarea,a";
  function hit(x, y) {
    let best = null, bd = 1e9;
    for (const b of B.list) { if (b.gone || b.sc < 0.6 || b.x == null) continue; const d = Math.hypot(x - b.x, y - b.y); if (d < Math.max(24, (b.r || 20) * 1.3) && d < bd) { best = b; bd = d; } }
    return best;
  }
  function frei(e) { return J.started && !(e.target.closest && e.target.closest(BLOCK)); }
  document.addEventListener("pointermove", e => {
    B.px = e.clientX; B.py = e.clientY; B.pfree = frei(e);
    if (eigene()) return;
    if (B.drag) {
      B.drag.x = e.clientX; B.drag.y = e.clientY;
      if (Math.hypot(e.clientX - B.drag.sx, e.clientY - B.drag.sy) > 6) B.drag.moved = true;
      return;
    }
    const b = B.pfree ? hit(e.clientX, e.clientY) : null;
    if (b !== B.hover) { B.hover = b; document.body.classList.toggle("jv-bothover", !!b); if (!b) hideCard(); }
  });
  document.addEventListener("pointerdown", e => {
    if (e.button || eigene() || !frei(e)) return;
    const b = hit(e.clientX, e.clientY); if (!b) return;
    e.preventDefault();
    B.drag = { b, x: e.clientX, y: e.clientY, sx: e.clientX, sy: e.clientY, moved: false };
    document.body.classList.add("jv-botdrag");
  });
  const drop = e => {
    const d = B.drag; if (!d) return; B.drag = null; document.body.classList.remove("jv-botdrag");
    const b = d.b;
    if (!d.moved) { if (e.type === "pointerup") { hideCard(); dashAuf(b.id, b.x, b.y); } return; }
    const g = geo(), tl = b.tilt || 0, dx = b.x - g.x, dy = b.y - g.y, ex = dx * Math.cos(tl) + dy * Math.sin(tl), ey = -dx * Math.sin(tl) + dy * Math.cos(tl);
    b.a = Math.atan2(ey / g.sq, ex); b.rf = clamp(Math.hypot(ex, ey / g.sq) / g.R, 0.75, g.maxRf); b.burst = 0.7;
    orbSave[b.id] = { a: b.a, rf: b.rf }; J.store.set("botorbit", orbSave);
  };
  document.addEventListener("pointerup", drop); document.addEventListener("pointercancel", drop);
  document.addEventListener("pointerleave", () => { B.px = 0; B.spur.length = 0; if (!B.drag) { B.hover = null; hideCard(); document.body.classList.remove("jv-bothover"); } });

  /* =============================================================== Info-Karte beim Schweben */
  const card = document.createElement("div"); card.id = "jv-botcard"; card.className = "jv-glass"; document.body.appendChild(card);
  function ort(cfg) {
    const st = J.settings || {}, prov = cfg.anbieter || st.anbieter;
    return { prov, cloud: !st.strikt_lokal && J.isCloud(prov, cfg.api_url ? Object.assign({}, st, { openai_url: cfg.api_url, ollama_url: cfg.api_url }) : st) };
  }
  function modellVon(cfg) { const st = J.settings || {}; return cfg.modell || (cfg.anbieter ? "automatisch" : (st.modell || "automatisch")); }
  function cardHtml(cfg, busy) {
    const s = B.stats[cfg.id] || {}, o = ort(cfg), v = (s.verlauf || []).slice(-3).reverse();
    return `<div class="bc-h"><i style="background:${esc(cfg.farbe)};box-shadow:0 0 10px ${esc(cfg.farbe)}"></i><b>${esc(cfg.name)}</b><span class="${o.cloud ? "cl" : "lo"}">${o.cloud ? "CLOUD" : "LOKAL"}</span></div>
<p>${esc(cfg.rolle || "Kein Kurztext hinterlegt")}</p>
<dl><dt>KI</dt><dd>${esc(PROVN[cfg.anbieter || ""])} · ${esc(modellVon(cfg))}</dd>
<dt>Erledigt</dt><dd>${+s.anzahl || 0} Aufgabe${s.anzahl === 1 ? "" : "n"}${s.dauer ? " · zuletzt " + (+s.dauer || 0) + " s" : ""}</dd></dl>
<div class="bc-v"><u>${busy ? "Arbeitet gerade" : "Verarbeitet"}</u>${v.length ? v.map(x => `<div class="${x.ok ? "" : "er"}"><b>${esc(x.zeit)}</b> ${esc(x.aufgabe)}${x.antwort ? `<span>→ ${esc(x.antwort)}</span>` : ""}</div>`).join("") : '<div class="le">Noch nichts verarbeitet.</div>'}</div>
<small>${busy ? "arbeitet gerade …" : "Klick: Dashboard · Ziehen: verschieben · im Chat: @" + esc(cfg.name)}</small>`;
  }
  function zeigeKarte(cfg, x, y, r, busy) {
    const key = cfg.id + "|" + !!busy + "|" + ((B.stats[cfg.id] || {}).anzahl || 0);
    if (card.dataset.key !== key) { card.innerHTML = cardHtml(cfg, busy); card.dataset.key = key; card.style.setProperty("--bc", cfg.farbe); }
    card.classList.add("on");
    const w = card.offsetWidth, h = card.offsetHeight;
    let px = x + r + 16, py = y - h / 2;
    if (px + w > B.W - 10) px = x - r - 16 - w;
    card.style.transform = `translate(${Math.round(clamp(px, 10, Math.max(10, B.W - w - 10)))}px,${Math.round(clamp(py, 10, Math.max(10, B.H - h - 10)))}px)`;
  }
  function hideCard() { card.classList.remove("on"); card.dataset.key = ""; }

  /* =============================================================== Bot-Dashboard (Klick auf einen Bot) */
  const D = { id: null, cfg: null, tab: "ueber", raf: 0 };
  const dash = document.createElement("div"); dash.id = "jv-botdash"; dash.className = "jv-glass";
  dash.innerHTML = `<header><canvas id="bd-ic"></canvas><div class="bd-t"><b></b><small></small></div><span class="bd-chip"></span><button class="bd-x" title="Schließen">×</button></header>
<nav><button data-t="ueber" class="on">Übersicht</button><button data-t="einst">Einstellungen</button></nav><div class="bd-body"></div>`;
  document.body.appendChild(dash);
  const dq = s => dash.querySelector(s);
  dash.querySelector(".bd-x").onclick = () => dashZu();
  dash.querySelectorAll("nav button").forEach(b => b.onclick = () => { D.tab = b.dataset.t; dash.querySelectorAll("nav button").forEach(x => x.classList.toggle("on", x === b)); dashBody(); });
  document.addEventListener("keydown", e => { if (e.key === "Escape" && D.id && !setOffen()) dashZu(); });
  (function dragbar() {   // Dashboard am Kopf verschieben
    let d = null; const hd = dash.querySelector("header");
    hd.addEventListener("pointerdown", e => { if (e.target.closest("button")) return; d = { x: e.clientX, y: e.clientY, l: parseFloat(dash.style.left) || 0, t: parseFloat(dash.style.top) || 0 }; hd.setPointerCapture(e.pointerId); });
    hd.addEventListener("pointermove", e => { if (!d) return; dash.style.left = clamp(d.l + e.clientX - d.x, 6, innerWidth - dash.offsetWidth - 6) + "px"; dash.style.top = clamp(d.t + e.clientY - d.y, 6, innerHeight - 60) + "px"; });
    hd.addEventListener("pointerup", () => { d = null; }); hd.addEventListener("pointercancel", () => { d = null; });
  })();
  function botVon(id) { return ((J.settings || {}).bots || []).find(b => b.id === id); }
  function dashAuf(id, x, y) {
    const cfg = botVon(id); if (!cfg) return;
    D.id = id; D.cfg = JSON.parse(JSON.stringify(cfg)); D.tab = "ueber";
    dash.querySelectorAll("nav button").forEach(b => b.classList.toggle("on", b.dataset.t === "ueber"));
    dash.classList.add("on");
    dash.style.left = clamp((x || innerWidth / 2) + 40, 8, Math.max(8, innerWidth - 392)) + "px";
    dash.style.top = clamp((y || innerHeight / 2) - 120, 8, Math.max(8, innerHeight - 440)) + "px";
    dashKopf(); dashBody(); loadStats(() => { if (D.id === id) dashBody(); });
    cancelAnimationFrame(D.raf);
    const tick = () => { if (!D.id) return; const c = dq("#bd-ic"); if (c && c.offsetParent) { const d = Math.min(devicePixelRatio || 1, 2), w = c.clientWidth, h = c.clientHeight; if (c.width !== Math.round(w * d)) { c.width = Math.round(w * d); c.height = Math.round(h * d); } const x2 = c.getContext("2d"); x2.setTransform(d, 0, 0, d, 0, 0); x2.clearRect(0, 0, w, h); drawShape(x2, D.cfg.form, w / 2, h / 2, Math.min(w, h) * 0.3, rgbOf(D.cfg.farbe), performance.now() / 1000, 1, (B.list.find(b => b.id === D.id) || {}).busy ? 1 : 0); } D.raf = requestAnimationFrame(tick); };
    D.raf = requestAnimationFrame(tick);
  }
  function dashZu() { D.id = null; dash.classList.remove("on"); cancelAnimationFrame(D.raf); }
  function dashKopf() {
    if (!D.id) return;
    const cfg = botVon(D.id) || D.cfg, b = B.list.find(x => x.id === D.id), o = ort(cfg);
    dq(".bd-t b").textContent = cfg.name;
    dq(".bd-t small").textContent = cfg.rolle || PROVN[cfg.anbieter || ""];
    const chip = dq(".bd-chip");
    chip.textContent = b && b.busy ? "ARBEITET" : cfg.aktiv === false ? "PAUSIERT" : "BEREIT";
    chip.className = "bd-chip " + (b && b.busy ? "run" : cfg.aktiv === false ? "off" : "ok");
    dash.style.setProperty("--bc", cfg.farbe);
  }
  function dashBody() {
    if (!D.id) return;
    const box = dq(".bd-body"), cfg = D.cfg, s = B.stats[D.id] || {}, o = ort(cfg);
    if (D.tab === "ueber") {
      const v = (s.verlauf || []).slice().reverse();
      box.innerHTML = `<div class="bd-kpi"><div><b>${+s.anzahl || 0}</b><small>Aufgaben</small></div><div><b>${s.dauer ? (+s.dauer || 0) + " s" : "—"}</b><small>letzte Dauer</small></div><div><b>${o.cloud ? "Cloud" : "Lokal"}</b><small>Ort</small></div></div>
<dl class="bd-dl"><dt>KI</dt><dd>${esc(PROVN[cfg.anbieter || ""])}</dd><dt>Modell</dt><dd>${esc(modellVon(cfg))}</dd>
<dt>Auftrag</dt><dd>${esc(cfg.auftrag || cfg.rolle || "—")}</dd>${cfg.stichwoerter ? `<dt>Stichwörter</dt><dd>${esc(cfg.stichwoerter)}</dd>` : ""}
${s.fehler ? `<dt>Fehler</dt><dd class="er">${esc(s.fehler)}</dd>` : ""}</dl>
<h5>Verarbeitet</h5><div class="bd-log">${v.length ? v.map(x => `<div class="${x.ok ? "" : "er"}"><span>${esc(x.zeit)} · ${+x.dauer || 0} s · ${esc(x.modell || "")}</span><b>${esc(x.aufgabe)}</b>${x.antwort ? `<p>${esc(x.antwort)}</p>` : ""}</div>`).join("") : '<div class="le">Noch nichts verarbeitet. Schreib im Chat „@' + esc(cfg.name) + ' …“.</div>'}</div>
<div class="bd-foot"><button type="button" class="jv-btn" id="bd-task">Aufgabe geben</button><button type="button" class="jv-btn" id="bd-ref">Aktualisieren</button></div>`;
      dq("#bd-task").onclick = () => { const i = $("jv-input"); if (i) { i.value = "@" + cfg.name + " "; i.focus(); } dashZu(); };
      dq("#bd-ref").onclick = () => loadStats(dashBody);
      return;
    }
    box.innerHTML = `<div class="row"><label>Name</label><input type="text" data-d="name" maxlength="32" value="${esc(cfg.name)}"></div>
<div class="row"><label>Aktiv</label><label class="sw"><input type="checkbox" data-d="aktiv"${cfg.aktiv ? " checked" : ""}><i></i><span>im Team und sichtbar</span></label></div>
<div class="row"><label>Kurzbeschreibung</label><input type="text" data-d="rolle" maxlength="140" value="${esc(cfg.rolle)}"></div>
<div class="row"><label>Auftrag</label><textarea data-d="auftrag">${esc(cfg.auftrag)}</textarea></div>
<div class="row"><label>Stichwörter</label><input type="text" data-d="stichwoerter" value="${esc(cfg.stichwoerter)}" placeholder="optional"></div>
<div class="row"><label>Anbieter</label><select data-d="anbieter"><option value="">Wie ${esc((J.settings || {}).name || "Jarvis")}</option><option value="ollama">Lokal · Ollama</option><option value="claude">Claude · API</option><option value="openai">OpenAI-kompatibel</option></select></div>
<div class="row"><label>Modell</label><input type="text" data-d="modell" value="${esc(cfg.modell)}" placeholder="automatisch"></div>
<div class="row" data-z="key"><label>API-Schlüssel</label><input type="password" data-d="api_key" autocomplete="off" value="${esc(cfg.api_key)}" placeholder="optional"></div>
<div class="row" data-z="url"><label>Adresse</label><input type="url" data-d="api_url" value="${esc(cfg.api_url)}" placeholder="optional"></div>
<div class="row" data-z="web"><label>Websuche</label><label class="sw"><input type="checkbox" data-d="websuche"${cfg.websuche ? " checked" : ""}><i></i><span>im Web nachsehen (nur Claude)</span></label></div>
<div class="row"><label>Form</label><div class="bd-forms">${FORMEN.map(f => `<button type="button" class="${f[0] === cfg.form ? "on" : ""}" data-form="${f[0]}" title="${f[1]}"></button>`).join("")}</div></div>
<div class="row"><label>Farbe</label><div class="bt-cols">${FARBEN.map(c => `<button type="button" class="${c === (cfg.farbe || "").toLowerCase() ? "on" : ""}" data-col="${c}" style="--c:${c}"></button>`).join("")}<input type="color" data-d="farbe" value="${esc(cfg.farbe)}"></div></div>
<div class="row"><label>Größe <small>${Math.round((+cfg.groesse || 1) * 100)} %</small></label><input type="range" min="0.5" max="2.2" step="0.05" data-d="groesse" value="${+cfg.groesse || 1}"></div>
<div class="bd-foot"><span class="res" id="bd-res"></span><button type="button" class="jv-btn" id="bd-all">Alle Einstellungen</button><button type="button" class="jv-btn jv-primary" id="bd-save">Speichern</button></div>`;
    const vis = () => { const a = cfg.anbieter, eff = a || (J.settings || {}).anbieter;
      box.querySelector('[data-z="key"]').style.display = a === "claude" || a === "openai" ? "" : "none";
      box.querySelector('[data-z="url"]').style.display = a === "openai" || a === "ollama" ? "" : "none";
      box.querySelector('[data-z="web"]').style.display = eff === "claude" ? "" : "none"; };
    box.querySelector('[data-d="anbieter"]').value = cfg.anbieter || ""; vis();
    box.querySelectorAll("[data-d]").forEach(el => {
      const k = el.dataset.d, ev = el.type === "checkbox" || el.tagName === "SELECT" || el.type === "color" ? "change" : "input";
      el.addEventListener(ev, () => {
        cfg[k] = el.type === "checkbox" ? el.checked : el.type === "range" ? parseFloat(el.value) : el.value;
        if (k === "anbieter") { cfg.modell = ""; box.querySelector('[data-d="modell"]').value = ""; vis(); }
        if (k === "groesse") el.closest(".row").querySelector("label small").textContent = Math.round(cfg.groesse * 100) + " %";
        if (k === "farbe") box.querySelectorAll(".bt-cols button").forEach(x => x.classList.remove("on"));
        if (k === "name" || k === "rolle" || k === "aktiv") dashKopf();
      });
    });
    box.querySelectorAll(".bd-forms button").forEach(el => { el.style.setProperty("--c", cfg.farbe); const c = document.createElement("canvas"); c.width = c.height = 56; el.appendChild(c);
      drawShape(c.getContext("2d"), el.dataset.form, 28, 28, 17, rgbOf(cfg.farbe), 1.2, 1, 0);
      el.onclick = () => { cfg.form = el.dataset.form; box.querySelectorAll(".bd-forms button").forEach(x => x.classList.toggle("on", x === el)); }; });
    box.querySelectorAll(".bt-cols button").forEach(el => el.onclick = () => { cfg.farbe = el.dataset.col; box.querySelector('[data-d="farbe"]').value = cfg.farbe; box.querySelectorAll(".bt-cols button").forEach(x => x.classList.toggle("on", x === el)); dashKopf(); });
    dq("#bd-all").onclick = () => { const id = D.id; dashZu(); J.openSettings("bots", id); };
    dq("#bd-save").onclick = async () => {
      const res = dq("#bd-res"); res.className = "res"; res.textContent = "speichere …";
      try {
        const liste = ((J.settings || {}).bots || []).map(x => x.id === D.id ? Object.assign({}, x, cfg) : x);
        J.settings = await J.api("/api/settings", { bots: liste });
        J.emit("settings", J.settings);
        const neu = botVon(D.id); if (neu) D.cfg = JSON.parse(JSON.stringify(neu));
        res.className = "res ok"; res.textContent = "✓ gespeichert"; dashKopf();
      } catch (e) { res.className = "res bad"; res.textContent = "✗ " + e.message; }
    };
  }

  /* =============================================================== Einstellungen: Reiter "Bots" */
  let ED = [], cur = -1, prevRaf = 0, root = null;
  const newId = () => Math.random().toString(36).slice(2, 10);
  function mount(box, focusId) {
    root = box.querySelector("#jv-botsui"); if (!root) return;
    const cb = box.querySelector("#bt-clear"), cr = box.querySelector("#bt-cres");
    if (cb) cb.onclick = async () => {
      if (!cb.dataset.sure) { cb.dataset.sure = 1; cb.textContent = "Wirklich? Nochmal klicken"; setTimeout(() => { if (cb.isConnected) { delete cb.dataset.sure; cb.textContent = "Verlauf löschen"; } }, 4000); return; }
      try { await J.api("/api/bots/clear", {}); await loadStats(); cr.textContent = "✓ Verlauf gelöscht"; } catch (x) { cr.textContent = "✗ " + x.message; }
      cb.textContent = "Verlauf löschen"; delete cb.dataset.sure;
    };
    ED = JSON.parse(JSON.stringify((J.settings && J.settings.bots) || []));
    cur = focusId ? ED.findIndex(b => b.id === focusId) : (ED.length ? 0 : -1);
    render();
    cancelAnimationFrame(prevRaf);
    const tick = () => { if (!root.isConnected || !box.classList.contains("on")) return; previews(); prevRaf = requestAnimationFrame(tick); };
    prevRaf = requestAnimationFrame(tick);
  }
  function previews() {
    const t = performance.now() / 1000;
    root.querySelectorAll("canvas[data-pv]").forEach(c => {
      if (!c.offsetParent) return;
      const d = Math.min(window.devicePixelRatio || 1, 2), w = c.clientWidth, h = c.clientHeight;
      if (c.width !== Math.round(w * d)) { c.width = Math.round(w * d); c.height = Math.round(h * d); }
      const x = c.getContext("2d"); x.setTransform(d, 0, 0, d, 0, 0); x.clearRect(0, 0, w, h);
      const b = ED[cur] || {}, form = c.dataset.form || b.form, col = rgbOf(c.dataset.col || b.farbe), big = c.dataset.pv === "big";
      drawShape(x, form, w / 2, h / 2, Math.min(w, h) * (big ? 0.2 * clamp(+b.groesse || 1, 0.4, 2.5) * 0.9 + 0.08 : 0.3), col, t, 1, 0);
    });
  }
  function render() {
    const list = ED.map((b, i) => `<button type="button" class="bt-it${i === cur ? " on" : ""}${b.aktiv ? "" : " off"}" data-i="${i}"><canvas data-pv="s" data-form="${esc(b.form)}" data-col="${esc(b.farbe)}"></canvas><span><b>${esc(b.name || "Neuer Bot")}</b><small>${esc(b.aktiv ? (b.rolle || PROVN[b.anbieter || ""]) : "pausiert")}</small></span></button>`).join("");
    const tpl = VORLAGEN.map((v, i) => `<button type="button" class="bt-tp" data-tpl="${i}"><i style="background:${v.farbe}"></i>${esc(v.name)}</button>`).join("");
    const b = ED[cur];
    let ed = `<div class="bt-empty"><b>${ED.length ? "Bot links auswählen" : "Noch kein Bot im Team"}</b><p>Wähle unten eine Vorlage oder lege einen leeren Bot an. Danach nur noch „Speichern“ klicken, und der Bot erscheint auf der Oberfläche.</p></div>`;
    if (b) {
      ed = `<div class="bt-head"><canvas data-pv="big"></canvas><div><div class="row"><label>Name<small>so sprichst du ihn an: @${esc(b.name || "Name")}</small></label><input type="text" data-b="name" maxlength="32" value="${esc(b.name)}"></div>
<div class="row"><label>Aktiv</label><label class="sw"><input type="checkbox" data-b="aktiv"${b.aktiv ? " checked" : ""}><i></i><span>Bot ist im Team und sichtbar</span></label></div></div></div>
<div class="box"><h4>Aufgabe</h4>
<div class="row"><label>Kurzbeschreibung<small>steht in der Info-Karte; daran erkennt ${esc(J.settings.name)}, wofür der Bot da ist</small></label><input type="text" data-b="rolle" maxlength="140" value="${esc(b.rolle)}" placeholder="z.B. Recherchiert Fakten und aktuelle Infos"></div>
<div class="row"><label>Auftrag<small>die genaue Anweisung an den Bot</small></label><textarea data-b="auftrag" placeholder="z.B. Du recherchierst gründlich und nennst Quellen.">${esc(b.auftrag)}</textarea></div>
<div class="row"><label>Stichwörter<small>optional, mit Komma getrennt: fällt eines im Satz, übernimmt der Bot</small></label><input type="text" data-b="stichwoerter" value="${esc(b.stichwoerter)}" placeholder="z.B. recherchiere, such heraus"></div></div>
<div class="box"><h4>KI des Bots</h4>
<div class="row"><label>Anbieter</label><select data-b="anbieter"><option value="">Wie ${esc(J.settings.name)} (aktuelle KI und Schlüssel)</option><option value="ollama">Lokal · Ollama</option><option value="claude">Claude · API</option><option value="openai">OpenAI-kompatibel (OpenAI, Groq, OpenRouter, LM Studio …)</option></select></div>
<div class="row"><label>Modell<small>leer = automatisch. „Verbindung testen“ füllt die Liste</small></label><input type="text" data-b="modell" list="bt-models" value="${esc(b.modell)}" placeholder="automatisch"><datalist id="bt-models"></datalist></div>
<div class="row" data-show="key"><label>Eigener API-Schlüssel<small>leer = der Schlüssel aus „KI & Modelle“</small></label><input type="password" data-b="api_key" autocomplete="off" value="${esc(b.api_key)}" placeholder="optional"></div>
<div class="row" data-show="url"><label>Eigene Adresse<small>leer = die Adresse aus „KI & Modelle“</small></label><input type="url" data-b="api_url" value="${esc(b.api_url)}" placeholder="optional, z.B. https://api.groq.com/openai/v1"></div>
<div class="row" data-show="web"><label>Websuche</label><label class="sw"><input type="checkbox" data-b="websuche"${b.websuche ? " checked" : ""}><i></i><span>Bot darf im Web nachsehen (nur Claude)</span></label></div>
<div class="row"><label></label><div class="inl"><span class="res" id="bt-res"></span><button type="button" class="jv-btn" id="bt-test">Verbindung testen</button></div></div></div>
<div class="box"><h4>Aussehen</h4>
<div class="row"><label>Form</label><div class="bt-forms">${FORMEN.map(f => `<button type="button" class="${f[0] === b.form ? "on" : ""}" data-form="${f[0]}" title="${f[1]}"><canvas data-pv="s" data-form="${f[0]}"></canvas><small>${f[1]}</small></button>`).join("")}</div></div>
<div class="row"><label>Farbe</label><div class="bt-cols">${FARBEN.map(c => `<button type="button" class="${c === (b.farbe || "").toLowerCase() ? "on" : ""}" data-col="${c}" style="--c:${c}"></button>`).join("")}<input type="color" data-b="farbe" value="${esc(b.farbe)}" title="Eigene Farbe"></div></div>
<div class="row"><label>Angezeigte Größe<small>${Math.round((+b.groesse || 1) * 100)} %</small></label><input type="range" min="0.5" max="2.2" step="0.05" data-b="groesse" value="${+b.groesse || 1}"></div></div>
<div class="bt-foot"><button type="button" class="jv-btn jv-danger" id="bt-del">Bot löschen</button><button type="button" class="jv-btn" id="bt-dup">Duplizieren</button></div>`;
    }
    root.innerHTML = `<div class="bt-wrap"><div class="bt-list">${list}<div class="bt-add"><small>BOT HINZUFÜGEN</small><div>${tpl}<button type="button" class="bt-tp" data-tpl="-1"><i></i>Leerer Bot</button></div></div></div><div class="bt-edit">${ed}</div></div>`;
    root.querySelectorAll(".bt-it").forEach(el => el.onclick = () => { cur = +el.dataset.i; render(); });
    root.querySelectorAll(".bt-tp").forEach(el => el.onclick = () => {
      const v = VORLAGEN[+el.dataset.tpl] || { name: "Bot " + (ED.length + 1), rolle: "", auftrag: "", form: FORMEN[ED.length % FORMEN.length][0], farbe: FARBEN[ED.length % FARBEN.length] };
      if (ED.length >= 24) { J.toast("Mehr als 24 Bots sind nicht möglich.", true); return; }
      let name = v.name, n = 2; while (ED.some(x => x.name.toLowerCase() === name.toLowerCase())) name = v.name + " " + n++;
      ED.push(Object.assign({ id: newId(), anbieter: "", modell: "", api_key: "", api_url: "", websuche: false, stichwoerter: "", groesse: 1, aktiv: true }, v, { name }));
      cur = ED.length - 1; render(); const i = root.querySelector('[data-b="name"]'); if (i) i.focus();
    });
    if (!b) return;
    const q = s => root.querySelector(s), vis = () => {
      const a = b.anbieter, eff = a || J.settings.anbieter;
      q('[data-show="key"]').style.display = a === "claude" || a === "openai" ? "" : "none";
      q('[data-show="url"]').style.display = a === "openai" || a === "ollama" ? "" : "none";
      q('[data-show="web"]').style.display = eff === "claude" ? "" : "none";
    };
    q('[data-b="anbieter"]').value = b.anbieter || ""; vis();
    root.querySelectorAll("[data-b]").forEach(el => {
      const k = el.dataset.b, ev = el.type === "checkbox" || el.tagName === "SELECT" || el.type === "color" ? "change" : "input";
      el.addEventListener(ev, e => {
        e.stopPropagation();
        b[k] = el.type === "checkbox" ? el.checked : el.type === "range" ? parseFloat(el.value) : el.value;
        if (k === "anbieter") { b.modell = ""; q('[data-b="modell"]').value = ""; q("#bt-models").innerHTML = ""; vis(); }
        if (k === "groesse") el.parentNode.querySelector("small").textContent = Math.round(b.groesse * 100) + " %";
        if (k === "farbe") root.querySelectorAll(".bt-cols button").forEach(x => x.classList.remove("on"));
        const it = root.querySelector(".bt-it.on");
        if (it) { it.querySelector("b").textContent = b.name || "Neuer Bot"; it.querySelector("small").textContent = b.aktiv ? (b.rolle || PROVN[b.anbieter || ""]) : "pausiert"; it.classList.toggle("off", !b.aktiv); const c = it.querySelector("canvas"); c.dataset.col = b.farbe; c.dataset.form = b.form; }
      });
    });
    root.querySelectorAll(".bt-forms button").forEach(el => el.onclick = () => { b.form = el.dataset.form; root.querySelectorAll(".bt-forms button").forEach(x => x.classList.toggle("on", x === el)); const c = root.querySelector(".bt-it.on canvas"); if (c) c.dataset.form = b.form; });
    root.querySelectorAll(".bt-cols button").forEach(el => el.onclick = () => { b.farbe = el.dataset.col; q('[data-b="farbe"]').value = b.farbe; root.querySelectorAll(".bt-cols button").forEach(x => x.classList.toggle("on", x === el)); const c = root.querySelector(".bt-it.on canvas"); if (c) c.dataset.col = b.farbe; });
    q("#bt-del").onclick = e => {
      const btn = e.currentTarget; if (!btn.dataset.sure) { btn.dataset.sure = 1; btn.textContent = "Wirklich löschen? Nochmal klicken"; setTimeout(() => { if (btn.isConnected) { delete btn.dataset.sure; btn.textContent = "Bot löschen"; } }, 4000); return; }
      ED.splice(cur, 1); cur = Math.min(cur, ED.length - 1); render();
    };
    q("#bt-dup").onclick = () => { if (ED.length >= 24) return; ED.push(Object.assign({}, b, { id: newId(), name: (b.name + " 2").slice(0, 32) })); cur = ED.length - 1; render(); };
    q("#bt-test").onclick = async () => {
      const res = q("#bt-res"); res.className = "res"; res.textContent = "teste …";
      try {
        const r = await J.api("/api/bots/test", { bot: b });
        res.className = "res " + (r.ok ? "ok" : "bad");
        res.textContent = r.ok ? `✓ verbunden · ${PROVN[r.anbieter]} · ${r.models.length} Modell${r.models.length === 1 ? "" : "e"} · ${r.cloud ? "Cloud" : "lokal"}` : "✗ " + r.fehler;
        if (r.ok) q("#bt-models").innerHTML = r.models.map(m => `<option value="${esc(m)}">`).join("");
      } catch (e) { res.className = "res bad"; res.textContent = "✗ " + e.message; }
    };
  }
  function read() { return ED.filter(b => (b.name || "").trim()); }

  J.bots = {
    frame, mount, read, sync, drawShape, FORMEN, PROVN,
    karte: zeigeKarte, karteAus: hideCard, dash: dashAuf, dashZu,
    aktiv: () => ((J.settings || {}).bots || []).filter(b => b.aktiv),
    stats: () => B.stats, ort, modell: modellVon, frei,
    busy: id => { const b = B.list.find(x => x.id === id); return !!(b && b.busy); },
    farbe: rgbOf
  };
  sync();
})();
