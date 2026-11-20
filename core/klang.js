/* FreeJarvis · Klang
   Leiser Hintergrundklang in Schleife (sounds/hintergrund.mp3) und kurze Effekt-Töne (sounds/*.mp3).
   Alles in Einstellungen -> Oberfläche -> Klang: Schalter und Regler, Änderungen sind sofort zu hören.
   Während Jarvis spricht, wird der Hintergrund automatisch leiser, damit man ihn gut versteht.
   Eigene Töne: einfach die Dateien in sounds/ austauschen (gleicher Name, mp3). */
(function () {
  "use strict";
  const J = window.Jarvis; if (!J || J.klang) return;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const DATEI = { start: "start.mp3", bot_an: "sound1.mp3", bot_aus: "sound2.mp3", denken: "sound3.mp3" };
  let live = {}, bg = null, laeuft = false, duck = 1, duckZiel = 1, kaputt = false;
  const cfg = k => (k in live ? live[k] : (J.settings || {})[k]);
  const hgAn = () => cfg("sound_hintergrund") !== false;
  const hgVol = () => clamp(+cfg("sound_hg_vol") || 0, 0, 1);
  const fxAn = () => cfg("sounds") !== false;
  const fxVol = () => clamp(cfg("sound_fx_vol") == null ? 0.5 : +cfg("sound_fx_vol"), 0, 1);

  function hintergrund() {
    if (!bg) {
      bg = new Audio("/sounds/" + "hintergrund.mp3"); bg.loop = true; bg.preload = "auto";
      bg.addEventListener("error", () => { kaputt = true; });
    }
    return bg;
  }
  function anwenden() {
    if (!J.started || kaputt) return;
    const a = hintergrund();
    a.volume = clamp(hgVol() * duck * 0.6, 0, 1);              // 0.6: Regler ganz rechts ist noch angenehm
    if (hgAn() && hgVol() > 0.001) {
      if (a.paused) { a.play().then(() => { laeuft = true; }).catch(() => { laeuft = false; }); }
    } else if (!a.paused) { a.pause(); laeuft = false; }
  }
  function effekt(name) {
    if (!J.started || !fxAn() || fxVol() < 0.01 || !DATEI[name]) return;
    try { const a = new Audio("/sounds/" + DATEI[name]); a.volume = clamp(fxVol() * 0.9, 0, 1); a.play().catch(() => { }); } catch (e) { }
  }
  // Stufenlos leiser, solange gesprochen wird
  setInterval(() => {
    if (!bg || bg.paused) return;
    duck += (duckZiel - duck) * 0.18; bg.volume = clamp(hgVol() * duck * 0.6, 0, 1);
  }, 80);

  J.on("start", () => { effekt("start"); anwenden(); });
  J.on("settings", () => { live = {}; anwenden(); });
  J.on("state", s => { duckZiel = s === "speaking" ? 0.35 : 1; if (s === "thinking") effekt("denken"); });
  J.on("bot", e => { if (e && e.phase === "start") effekt("bot_an"); else if (e && e.phase === "ende") effekt("bot_aus"); });
  // Live-Vorschau beim Verstellen in den Einstellungen
  const reg = e => {
    const el = e.target; if (!el || !el.dataset || !el.dataset.k) return;
    const k = el.dataset.k; if (!/^(sound_hintergrund|sound_hg_vol|sounds|sound_fx_vol)$/.test(k)) return;
    live[k] = el.type === "checkbox" ? el.checked : parseFloat(el.value);
    anwenden();
    if (e.type === "change" && (k === "sound_fx_vol" || (k === "sounds" && el.checked))) effekt("bot_aus");   // Hörprobe
  };
  document.addEventListener("input", reg); document.addEventListener("change", reg);
  J.fxScale = () => (fxAn() ? fxVol() * 2 : 0);
  J.klang = { effekt, anwenden };
})();
