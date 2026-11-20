/* FreeJarvis · PC-Steuerung (Oberfläche)
   - Reiter "PC-Steuerung": Ordner und Programme freigeben
   - Nachfrage-Karte: "Darf ich ...?" mit Erlauben / Ablehnen
   Die eigentliche Prüfung und Ausführung passiert in server.py (Abschnitt PC-Steuerung). */
(function () {
  "use strict";
  const J = window.Jarvis; if (!J) return;
  const esc = J.esc;
  const VORSCHLAG = {
    windows: [["Editor", "notepad.exe"], ["Rechner", "calc.exe"], ["Explorer", "explorer.exe"], ["Paint", "mspaint.exe"], ["Aufgaben", "taskmgr.exe"]],
    darwin: [["Notizen", "Notes"], ["Rechner", "Calculator"], ["Safari", "Safari"], ["Terminal", "Terminal"], ["TextEdit", "TextEdit"]],
    linux: [["Dateien", "nautilus"], ["Rechner", "gnome-calculator"], ["Editor", "gedit"], ["Firefox", "firefox"]]
  };
  let O = [], P = [], root = null, sysname = "windows";

  /* ---------- Nachfrage-Karte */
  const wrap = document.createElement("div"); wrap.id = "jv-pcask"; document.body.appendChild(wrap);
  function frage(a) {
    const el = document.createElement("div"); el.className = "pa jv-glass";
    el.innerHTML = `<div class="pa-h"><i></i><b>${esc((J.settings && J.settings.name) || "Jarvis")} möchte etwas an deinem PC tun</b><em>90</em></div>
<p>${esc(a.text)}</p>${a.aktion === "schreiben" ? `<small class="pa-z">Vollständiger Inhalt, genau so wird die Datei geschrieben: ${a.vorschau.length.toLocaleString("de-DE")} Zeichen, ${a.vorschau.split("\n").length} Zeilen</small><pre>${esc(a.vorschau) || "(leer)"}</pre>` : ""}
<div class="pa-b"><button class="jv-btn" data-ok="0">Ablehnen</button><button class="jv-btn jv-primary" data-ok="1">Erlauben</button></div>`;
    wrap.appendChild(el);
    let left = 90, done = false;
    const end = ok => { if (done) return; done = true; clearInterval(iv); el.classList.add("out"); setTimeout(() => el.remove(), 250); J.api("/api/pc/antwort", { id: a.id, ok }).catch(() => { }); };
    const iv = setInterval(() => { left--; el.querySelector("em").textContent = left; if (left <= 0) end(false); }, 1000);
    el.querySelectorAll("button").forEach(b => b.onclick = () => end(b.dataset.ok === "1"));
    if (J.state !== "speaking") J.speak("Darf ich? " + a.text.split(":")[0] + ".");
  }

  /* ---------- Einstellungen */
  function rows(list, art) {
    return list.map((r, i) => `<div class="pc-row" data-art="${art}" data-i="${i}"><i class="st" title=""></i><input type="text" class="pn" placeholder="${art === "o" ? "Name, z.B. Dokumente" : "Name, z.B. Editor"}" value="${esc(r.name)}"><input type="text" class="pp" placeholder="${art === "o" ? "Pfad, z.B. C:\\Users\\Du\\Documents" : "Programm oder Pfad, z.B. notepad.exe"}" value="${esc(r.pfad)}"><button type="button" class="jv-btn pb" title="Auswählen">…</button><button type="button" class="px" title="Entfernen">×</button></div>`).join("") ||
      `<div class="hint" style="margin:0 0 8px">${art === "o" ? "Noch kein Ordner freigegeben." : "Noch kein Programm freigegeben."}</div>`;
  }
  function render() {
    if (!root) return;
    const vs = (VORSCHLAG[sysname] || VORSCHLAG.linux).filter(v => !P.some(p => p.name.toLowerCase() === v[0].toLowerCase()));
    root.innerHTML = `<div class="box"><h4>Freigegebene Ordner</h4><p class="hint" style="margin:0 0 10px">Nur in diesen Ordnern (und ihren Unterordnern) darf ${esc(J.settings.name)} arbeiten. Der Name ist das, was du sagst: „Öffne den Ordner <b>Dokumente</b>“.</p>
<div id="pc-o">${rows(O, "o")}</div><button type="button" class="jv-btn" id="pc-oadd">+ Ordner freigeben</button></div>
<div class="box"><h4>Freigegebene Programme</h4><p class="hint" style="margin:0 0 10px">Nur diese Programme darf ${esc(J.settings.name)} starten: „Starte <b>Editor</b>“. Als Pfad geht der Programmname (notepad.exe) oder der volle Pfad zur .exe oder Verknüpfung.</p>
<div id="pc-p">${rows(P, "p")}</div><div class="pc-add"><button type="button" class="jv-btn" id="pc-padd">+ Programm freigeben</button>${vs.map(v => `<button type="button" class="bt-tp" data-vn="${esc(v[0])}" data-vp="${esc(v[1])}"><i></i>${esc(v[0])}</button>`).join("")}</div></div>`;
    root.querySelectorAll(".pc-row").forEach(el => {
      const L = el.dataset.art === "o" ? O : P, i = +el.dataset.i;
      el.querySelector(".pn").oninput = e => { L[i].name = e.target.value; };
      el.querySelector(".pp").oninput = e => { L[i].pfad = e.target.value; };
      el.querySelector(".pp").onchange = check;
      el.querySelector(".px").onclick = () => { L.splice(i, 1); render(); check(); };
      el.querySelector(".pb").onclick = async e => {
        const b = e.currentTarget; b.textContent = "⏳"; b.disabled = true;
        try {
          const r = await J.api("/api/pc/waehlen", { art: el.dataset.art === "o" ? "ordner" : "programm" });
          if (r.ok) { L[i].pfad = r.pfad; if (!L[i].name.trim()) L[i].name = r.pfad.split(/[\\/]/).filter(Boolean).pop().replace(/\.(exe|lnk|app)$/i, ""); render(); check(); return; }
          if (r.fehler !== "Nichts ausgewählt.") J.toast(r.fehler, true, 5000);
        } catch (err) { J.toast(err.message, true); }
        b.textContent = "…"; b.disabled = false;
      };
    });
    root.querySelector("#pc-oadd").onclick = () => { O.push({ name: "", pfad: "" }); render(); const r = root.querySelectorAll("#pc-o .pc-row"); r[r.length - 1].querySelector(".pb").click(); };
    root.querySelector("#pc-padd").onclick = () => { P.push({ name: "", pfad: "" }); render(); const r = root.querySelectorAll("#pc-p .pn"); r[r.length - 1].focus(); };
    root.querySelectorAll("[data-vn]").forEach(b => b.onclick = () => { P.push({ name: b.dataset.vn, pfad: b.dataset.vp }); render(); check(); });
  }
  async function check() {
    if (!root) return;
    try {
      const r = await J.api("/api/pc/pruefen", { pc_ordner: O.filter(x => x.pfad.trim()), pc_programme: P.filter(x => x.pfad.trim()) });
      if (r.system !== sysname) { sysname = r.system; render(); }
      const mark = (sel, L, res, okT, badT) => { let k = 0; root.querySelectorAll(sel + " .pc-row").forEach((el, i) => { const st = el.querySelector(".st"); if (!L[i] || !L[i].pfad.trim()) { st.className = "st"; return; } const x = res[k++]; st.className = "st " + (x && x.ok ? "ok" : "bad"); st.title = x && x.ok ? okT : badT; }); };
      mark("#pc-o", O, r.ordner, "Ordner gefunden", "Ordner nicht gefunden");
      mark("#pc-p", P, r.programme, "Programm gefunden", "Nicht gefunden. Windows-Programme wie calc.exe starten oft trotzdem.");
    } catch (e) { }
  }
  async function log(box) {
    const el = box.querySelector("#jv-pclog"); if (!el) return;
    try {
      const r = await J.api("/api/pc/log");
      el.innerHTML = r.log.length ? r.log.map(x => `<div class="jv-li"><span><b style="font-weight:600">${esc(x.aktion)}</b> ${esc(x.ziel)}<br><small style="white-space:normal">${esc(x.info)}</small></span><small class="${x.ok ? "pl" : "po"}">${esc(x.zeit)}</small></div>`).join("") : '<div class="hint">Noch keine Aktionen.</div>';
    } catch (e) { el.innerHTML = '<div class="hint">Protokoll nicht lesbar.</div>'; }
  }
  function mount(box) {
    root = box.querySelector("#jv-pcui"); if (!root) return;
    O = JSON.parse(JSON.stringify(J.settings.pc_ordner || [])); P = JSON.parse(JSON.stringify(J.settings.pc_programme || []));
    render(); check(); log(box);
  }
  function read() { const f = L => L.map(x => ({ name: (x.name || "").trim(), pfad: (x.pfad || "").trim() })).filter(x => x.pfad); return { pc_ordner: f(O), pc_programme: f(P) }; }
  J.pc = { frage, mount, read };
})();
