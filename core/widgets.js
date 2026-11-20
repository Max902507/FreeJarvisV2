/* FreeJarvis · Widgets
   Kleine Fenster vorne auf der Oberfläche: Wetter, Notizen, Uhr, System.
   Einschalten: Einstellungen -> Oberfläche -> Widgets.
   Verschieben: an der Titelleiste ziehen. Größe: an der Ecke unten rechts ziehen (die Schrift wächst mit).
   Plätze und Größen merkt sich der Browser. Notizen bleiben im Browser; „Merken“ gibt sie zusätzlich ins Gedächtnis von Jarvis.
   Eigene Widgets: einen Eintrag in WIDGETS ergänzen (id, Titel, bauen(), optional tick()). */
(function () {
  "use strict";
  const J = window.Jarvis; if (!J || J.widgets) return;
  const $ = id => document.getElementById(id), esc = J.esc || (s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])));
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const POS = J.store.get("widgets", {});
  const speichern = () => J.store.set("widgets", POS);
  const WOCHE = ["Sonntag", "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag"];
  const ICON = { sonne: "☀️", wolkig: "⛅", bedeckt: "☁️", nebel: "🌫️", regen: "🌧️", schnee: "❄️", gewitter: "⛈️" };

  const WIDGETS = [
    { id: "wetter", titel: "Wetter", w: 250, h: 190, x: -276, y: 84,
      bauen(el) {
        el.innerHTML = `<div class="wd-wx"><div class="wd-big"><span class="wd-ic">…</span><b class="wd-t">–</b></div><div class="wd-ort"></div><div class="wd-sub"></div><div class="wd-sub wd-q"></div></div>`;
        const lade = async () => {
          try {
            const w = await J.api("/api/wetter");
            if (w.fehler) { el.querySelector(".wd-t").textContent = "–"; el.querySelector(".wd-ic").textContent = "⚠"; el.querySelector(".wd-ort").textContent = w.ort || ""; el.querySelector(".wd-sub").textContent = w.fehler; el.querySelector(".wd-q").textContent = ""; return; }
            el.querySelector(".wd-ic").textContent = ICON[w.icon] || "⛅"; el.querySelector(".wd-t").textContent = w.temp + "°";
            el.querySelector(".wd-ort").textContent = w.ort + " · " + w.text;
            el.querySelector(".wd-sub").textContent = `gefühlt ${w.gefuehlt}° · Wind ${w.wind} km/h` + (w.regen != null ? ` · Regen ${w.regen} %` : "");
            el.querySelector(".wd-q").textContent = "Quelle: " + (w.quelle || "Open-Meteo");
          } catch (e) { el.querySelector(".wd-sub").textContent = "Wetter nicht abrufbar."; }
        };
        lade(); return { tick: lade, alle: 600000 };
      } },
    { id: "notizen", titel: "Notizen", w: 280, h: 230, x: -306, y: 290,
      bauen(el) {
        el.innerHTML = `<textarea class="wd-note" spellcheck="false" placeholder="Schreib hier etwas auf …"></textarea>
          <div class="wd-bar"><button type="button" class="wd-merk" title="Jede Zeile wird ein Eintrag im Gedächtnis von Jarvis">Merken</button><button type="button" class="wd-leer" title="Notiz leeren">Leeren</button><span class="wd-msg"></span></div>`;
        const ta = el.querySelector("textarea"), msg = el.querySelector(".wd-msg"); let tm = null;
        ta.value = J.store.get("notiz", "");
        ta.addEventListener("input", () => { clearTimeout(tm); tm = setTimeout(() => J.store.set("notiz", ta.value), 300); });
        const sag = t => { msg.textContent = t; clearTimeout(msg._t); msg._t = setTimeout(() => { msg.textContent = ""; }, 2600); };
        el.querySelector(".wd-merk").onclick = async () => {
          const zeilen = ta.value.split(/\n+/).map(z => z.trim()).filter(z => z.length >= 3).slice(0, 12);
          if (!zeilen.length) return sag("Nichts zu merken");
          try { for (const z of zeilen) await J.api("/api/memory", { text: z.slice(0, 300) }); sag(`✓ ${zeilen.length} gemerkt`); } catch (e) { sag("Nicht gespeichert"); }
        };
        el.querySelector(".wd-leer").onclick = e => { const b = e.currentTarget; if (!ta.value) return; if (!b.dataset.sure) { b.dataset.sure = 1; b.textContent = "Sicher?"; setTimeout(() => { delete b.dataset.sure; b.textContent = "Leeren"; }, 2500); return; } ta.value = ""; J.store.set("notiz", ""); delete b.dataset.sure; b.textContent = "Leeren"; };
        return {};
      } },
    { id: "uhr", titel: "Uhr", w: 230, h: 130, x: 24, y: 84,
      bauen(el) {
        el.innerHTML = `<div class="wd-clock"><b class="wd-zeit">00:00</b><span class="wd-sek">00</span><div class="wd-sub wd-dat"></div></div>`;
        const t = () => { const d = new Date(); el.querySelector(".wd-zeit").textContent = d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
          el.querySelector(".wd-sek").textContent = String(d.getSeconds()).padStart(2, "0"); el.querySelector(".wd-dat").textContent = WOCHE[d.getDay()] + ", " + d.toLocaleDateString("de-DE", { day: "numeric", month: "long", year: "numeric" }); };
        t(); return { tick: t, alle: 1000 };
      } },
    { id: "system", titel: "System", w: 250, h: 150, x: 24, y: 232,
      bauen(el) {
        el.innerHTML = ["cpu:Prozessor", "ram:Arbeitsspeicher", "platte:Festplatte"].map(s => { const [k, n] = s.split(":"); return `<div class="wd-bal" data-k="${k}"><span>${n}</span><i><u></u></i><em>–</em></div>`; }).join("") + `<div class="wd-sub wd-up"></div>`;
        const lade = async () => {
          try {
            const s = await J.api("/api/system");
            for (const k of ["cpu", "ram", "platte"]) { const r = el.querySelector(`[data-k="${k}"]`), v = s[k]; r.querySelector("u").style.width = (v == null ? 0 : v) + "%"; r.querySelector("em").textContent = v == null ? "–" : v + " %"; r.classList.toggle("hot", v != null && v >= 85); }
            el.querySelector(".wd-up").textContent = s.laufzeit ? "PC läuft seit " + s.laufzeit : "";
          } catch (e) { }
        };
        lade(); return { tick: lade, alle: 3000 };
      } }
  ];

  /* Kosten: Verbrauch der Cloud-KI. Die Zahlen kommen vom Server (kosten.json), der mitzählt, was der Anbieter meldet. */
  const usd = v => "$ " + (v || 0).toLocaleString("de-DE", { minimumFractionDigits: v && v < 1 ? 3 : 2, maximumFractionDigits: v && v < 1 ? 3 : 2 });
  const tok = n => n >= 1e6 ? (n / 1e6).toLocaleString("de-DE", { maximumFractionDigits: 2 }) + " Mio." : n >= 1000 ? Math.round(n / 1000).toLocaleString("de-DE") + " Tsd." : String(n || 0);
  WIDGETS.push({ id: "kosten", titel: "Kosten", w: 270, h: 236, x: -296, y: 536,
    bauen(el) {
      el.innerHTML = `<div class="wd-kost"><div class="wd-kz"><div><span>Heute</span><b class="k-h">–</b></div><div><span>Dieser Monat</span><b class="k-m">–</b></div></div>
        <div class="wd-bal k-lim" hidden><span>Limit</span><i><u></u></i><em></em></div>
        <div class="wd-sub k-gut"></div><div class="wd-sub k-tok"></div><div class="wd-sub k-hin"></div></div>`;
      const q = c => el.querySelector(c);
      const lade = async () => {
        try {
          const k = await J.api("/api/kosten");
          q(".k-h").textContent = usd(k.heute.usd); q(".k-m").textContent = usd(k.monat.usd);
          const lim = q(".k-lim"); lim.hidden = !k.limit;
          if (k.limit) { const p = Math.min(100, k.monat.usd / k.limit * 100); lim.querySelector("u").style.width = p + "%"; lim.querySelector("em").textContent = Math.round(p) + " %"; lim.classList.toggle("hot", p >= 80); lim.title = "Limit: " + usd(k.limit); }
          q(".k-gut").textContent = k.rest == null ? "" : `Guthaben: ${usd(Math.max(0, k.rest))} von ${usd(k.guthaben)}` + (k.rest <= 0 ? " · aufgebraucht" : "");
          q(".k-tok").textContent = `${k.monat.anfragen} Anfragen · ${tok(k.monat.ein)} rein, ${tok(k.monat.aus)} raus` + (k.monat.suchen ? ` · ${k.monat.suchen} Websuchen` : "");
          const h = [];
          if (k.gesperrt) h.push("Limit erreicht: Cloud-KI ist gesperrt.");
          if (k.ohne_preis.length) h.push("Kein Preis hinterlegt für: " + k.ohne_preis.join(", ") + " (Einstellungen → KI & Modelle).");
          if (k.geschaetzt) h.push("Teilweise geschätzt, weil der Anbieter keinen Verbrauch meldet.");
          if (!k.monat.anfragen) h.push(k.lokal.anfragen ? "Diesen Monat nur lokale KI: keine Kosten." : "Noch kein Verbrauch in diesem Monat.");
          q(".k-hin").textContent = h.join(" "); q(".k-hin").classList.toggle("warn", k.gesperrt || k.ohne_preis.length > 0);
        } catch (e) { q(".k-hin").textContent = "Kosten nicht abrufbar."; }
      };
      lade(); J.on("event", () => setTimeout(lade, 1500));
      return { tick: lade, alle: 20000 };
    } });

  const AKT = {};   // laufende Widgets: id -> { el, timer }

  function platz(w, el) {
    const p = POS[w.id] || {}, W = innerWidth, H = innerHeight;
    const bw = clamp(p.w || w.w, 160, Math.max(160, W - 20)), bh = clamp(p.h || w.h, 100, Math.max(100, H - 80));
    let x = p.x != null ? p.x : (w.x < 0 ? W + w.x : w.x), y = p.y != null ? p.y : w.y;
    x = clamp(x, 6, Math.max(6, W - bw - 6)); y = clamp(y, 54, Math.max(54, H - bh - 6));
    Object.assign(el.style, { left: x + "px", top: y + "px", width: bw + "px", height: bh + "px" });
  }
  function an(w) {
    if (AKT[w.id]) return;
    const el = document.createElement("div"); el.className = "jv-widget jv-glass"; el.dataset.w = w.id;
    el.innerHTML = `<div class="wd-head"><span>${esc(w.titel)}</span><button type="button" class="wd-x" title="Widget ausblenden" aria-label="Ausblenden">×</button></div><div class="wd-body"></div>`;
    document.body.appendChild(el); platz(w, el);
    const r = w.bauen(el.querySelector(".wd-body")) || {};
    const a = AKT[w.id] = { el, timer: r.tick && r.alle ? setInterval(r.tick, r.alle) : null };
    // Ziehen an der Titelleiste
    const hd = el.querySelector(".wd-head"); let d = null;
    hd.addEventListener("pointerdown", e => { if (e.target.closest("button")) return; d = { dx: e.clientX - el.offsetLeft, dy: e.clientY - el.offsetTop }; hd.setPointerCapture(e.pointerId); el.classList.add("zieht"); e.preventDefault(); });
    hd.addEventListener("pointermove", e => { if (!d) return; el.style.left = clamp(e.clientX - d.dx, 6, innerWidth - el.offsetWidth - 6) + "px"; el.style.top = clamp(e.clientY - d.dy, 54, innerHeight - 40) + "px"; });
    const ende = () => { if (!d) return; d = null; el.classList.remove("zieht"); merken(w.id, el); };
    hd.addEventListener("pointerup", ende); hd.addEventListener("pointercancel", ende);
    // Größe ändern (native Ecke), danach merken
    if (window.ResizeObserver) { let first = true, tm; new ResizeObserver(() => { if (first) { first = false; return; } clearTimeout(tm); tm = setTimeout(() => merken(w.id, el), 250); }).observe(el); }
    // Schließen = in den Einstellungen ausschalten
    el.querySelector(".wd-x").onclick = () => { J.api("/api/settings", { ["widget_" + w.id]: false }).then(s => { J.settings = s; abgleich(); }).catch(() => { aus(w.id); }); };
  }
  function merken(id, el) { POS[id] = { x: Math.round(el.offsetLeft), y: Math.round(el.offsetTop), w: Math.round(el.offsetWidth), h: Math.round(el.offsetHeight) }; speichern(); }
  function aus(id) { const a = AKT[id]; if (!a) return; if (a.timer) clearInterval(a.timer); a.el.remove(); delete AKT[id]; }
  function abgleich() {
    const st = J.settings || {};
    for (const w of WIDGETS) { if (st["widget_" + w.id]) an(w); else aus(w.id); }
  }
  addEventListener("resize", () => { for (const w of WIDGETS) if (AKT[w.id]) platz(w, AKT[w.id].el); });
  J.on("settings", abgleich);
  J.on("start", abgleich);
  abgleich();
  J.widgets = { abgleich, WIDGETS, zuruecksetzen() { for (const k in POS) delete POS[k]; speichern(); for (const w of WIDGETS) if (AKT[w.id]) platz(w, AKT[w.id].el); } };
})();
