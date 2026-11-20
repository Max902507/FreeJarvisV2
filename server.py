#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FreeJarvis · JARVIS YouTube-Edition
Ein Server für drei Arten von KI:
  - Ollama (lokal, kostenlos, ohne Schlüssel)
  - Claude (Anthropic, API-Schlüssel)
  - OpenAI-kompatibel (OpenAI, Groq, OpenRouter, LM Studio ... mit Basis-Adresse und Schlüssel)
Nur Python-Standardbibliothek, nichts zu installieren.
Start:  python server.py     danach im Browser:  http://localhost:5050
"""
import datetime
import hashlib
import ipaddress
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

if sys.version_info < (3, 8):
    sys.exit("Python 3.8 oder neuer wird benötigt.")

VERSION = "2.1"
BASE = os.path.dirname(os.path.realpath(__file__))
SETTINGS_FILE = os.path.join(BASE, "einstellungen.json")
MEMORY_FILE = os.path.join(BASE, "gedaechtnis.json")
BOTSTAT_FILE = os.path.join(BASE, "bot_statistik.json")
KOSTEN_FILE = os.path.join(BASE, "kosten.json")
CLOUD_VERLAUF_FILE = os.path.join(BASE, "cloud_verlauf.json")   # nur Prüfsummen, keine Texte
FEHLER_FILE = os.path.join(BASE, "fehler.log")                  # Fehlermeldungen, die den Browser nicht mehr erreicht haben
PORT = int(os.environ.get("JARVIS_PORT", "5050"))
AKTIV_PORT = [PORT]               # der Port, auf dem Jarvis wirklich läuft (für die Herkunftsprüfung)
HOST = "127.0.0.1"
LOCK = threading.Lock()
SECRET = ("claude_key", "openai_key", "eleven_key", "ha_token")
MASK = "••••"

DEFAULTS = {
    "name": "Jarvis",
    "nutzer": "",
    "persona": "",
    "anbieter": "ollama",            # ollama | claude | openai
    "modell": "",                    # leer = erstes verfügbares Modell
    "ollama_url": "http://localhost:11434",
    "claude_key": "",
    "openai_key": "",
    "openai_url": "https://api.openai.com/v1",
    "websuche": False,               # Claude-Websuche oder SearXNG (suche_dienst); standardmäßig aus
    "sparmodus": True,               # weniger Token: kurzer Verlauf, knappes Gedächtnis, Befehle ohne KI-Rückfrage bestätigen
    "antwortlaenge": "kurz",         # kurz | normal | ausfuehrlich
    "stimme": "browser",             # browser | elevenlabs | aus
    "browser_stimme": "",
    "tempo": 1.0,
    "tonhoehe": 1.0,
    "lautstaerke": 1.0,
    "eleven_key": "",
    "eleven_voice": "",
    "eleven_modell": "eleven_multilingual_v2",
    "mikro": "nach_antwort",         # aus | immer | nach_antwort
    "weckwort_an": False,
    "weckwort": "Jarvis",
    "sprache": "de-DE",
    "auto_merken": True,
    "ort": "Berlin",
    "briefing_beim_start": False,
    "oberflaeche": "vortex",
    "chat_sichtbar": True,
    "sounds": True,
    "strikt_lokal": False,          # nichts verlässt den PC (nur Ollama, keine Online-Dienste)
    "privat_weiche": True,          # private Daten automatisch lokal statt Cloud
    "gedaechtnis_cloud": False,     # Gedächtnis auch an Cloud-KI senden
    "privat_woerter": "",           # eigene Stichwörter, die als privat gelten (Komma getrennt)
    "lokal_modell": "",             # Ollama-Modell für private Nachrichten
    "bots": [],                     # Bot-Team: eigene KI-Helfer mit eigenem Auftrag, Modell und Schlüssel
    "bots_sichtbar": True,          # Bots kreisen sichtbar um Jarvis
    "bot_namen": True,              # Namen unter den Bots anzeigen
    "bot_delegieren": True,         # Jarvis darf Aufgaben selbst an passende Bots abgeben
    "bot_groesse": 1.0,             # Anzeigegröße aller Bots (Faktor)
    "bot_tempo": 1.0,               # Umlauf-Tempo der Bots (Faktor)
    "sound_hintergrund": True,      # leiser Hintergrundklang (sounds/hintergrund.mp3)
    "sound_hg_vol": 0.15,           # Lautstärke Hintergrund 0..1
    "sound_fx_vol": 0.5,            # Lautstärke Effekte 0..1
    "maus_spur": True,              # Lichtspur hinter dem Mauszeiger
    "module_sichtbar": False,       # Vortex: Status-Kugeln für Stimme, Gedächtnis, Wetter ... anzeigen
    "chat_speichern": True,         # Chatverlauf im Browser merken
    "widget_wetter": False, "widget_notizen": False, "widget_uhr": False, "widget_system": False, "widget_kosten": False,
    "kosten_limit": 0.0,            # Monatslimit in US-Dollar für Cloud-KI (0 = kein Limit)
    "kosten_guthaben": 0.0,         # dein Guthaben beim Anbieter in US-Dollar (selbst eingetragen, 0 = unbekannt)
    "kosten_preise": "",
    "prompt_cache": True,
    "suche_dienst": "claude",
    "suche_url": "",            # eigene Preise je Zeile: modellteil = eingabe / ausgabe (US-Dollar je 1 Mio. Token)
    "ha_an": False,                 # Home Assistant: Geräte per Sprache und Routine schalten (standardmäßig AUS)
    "ha_url": "http://homeassistant.local:8123",
    "ha_token": "",                 # Langlebiger Zugriffstoken aus Home Assistant
    "ha_bereiche": "light, switch, scene, script, media_player, cover, fan, input_boolean",   # nur diese Gerätearten sind erlaubt
    "maus_effekt": True,            # Oberflächen reagieren auf die Maus (Ausweichen, Wirbel, Klick-Welle)
    "maus_kippen": True,            # Ansicht kippt leicht zum Mauszeiger
    "bot_verlauf": True,            # Aufgaben und Ergebnisse der Bots in bot_statistik.json mitschreiben
    "pc_an": False,                 # PC-Steuerung: Ordner, Dateien, Programme (standardmäßig AUS)
    "pc_ordner": [],                # freigegebene Ordner: [{"name": "Dokumente", "pfad": "C:/..."}]
    "pc_programme": [],             # freigegebene Programme: [{"name": "Editor", "pfad": "notepad.exe"}]
    "pc_schreiben": False,          # Jarvis darf Textdateien in freigegebenen Ordnern anlegen und ändern
    "pc_nachfragen": True,          # vor jeder Aktion am PC nachfragen
    "pc_cloud": False,              # Ordnerlisten und Datei-Inhalte auch an eine Cloud-KI geben
    "routinen": [
        {"satz": "guten morgen", "aktion": "briefing", "wert": ""},
        {"satz": "öffne youtube", "aktion": "webseite", "wert": "https://www.youtube.com"},
        {"satz": "pause machen", "aktion": "timer", "wert": "15"},
    ],
}

THEMES = {"vortex": "/jarvis.html", "nova": "/oberflaechen/nova.html", "sphaeren": "/oberflaechen/sphaeren.html",
          "aura": "/oberflaechen/aura.html", "gitter": "/oberflaechen/gitter.html",
          "begleiter": "/oberflaechen/begleiter.html", "band": "/oberflaechen/band.html",
          "saga": "/oberflaechen/saga.html", "membran": "/oberflaechen/membran.html",
          "prisma": "/oberflaechen/prisma.html", "geodaet": "/oberflaechen/geodaet.html",
          "helix": "/oberflaechen/helix.html", "strata": "/oberflaechen/strata.html",
          "bluete": "/oberflaechen/bluete.html", "galaxie": "/oberflaechen/galaxie.html",
          "multiversum": "/oberflaechen/multiversum.html", "avatar": "/oberflaechen/avatar.html",
          "singularitaet": "/oberflaechen/singularitaet.html", "synapse": "/oberflaechen/synapse.html",
          "ozean": "/oberflaechen/ozean.html", "tesserakt": "/oberflaechen/tesserakt.html",
          "reaktor": "/oberflaechen/reaktor.html", "retro": "/oberflaechen/retro.html", "kosmos": "/oberflaechen/kosmos.html",
          "phantom": "/oberflaechen/phantom.html"}
THEME_WORDS = {"vortex": "vortex", "wirbel": "vortex", "nova": "nova", "orange": "nova", "funken": "nova",
               "sphären": "sphaeren", "sphaeren": "sphaeren", "kugel": "sphaeren", "aura": "aura", "gitter": "gitter",
               "lattice": "gitter", "begleiter": "begleiter", "companion": "begleiter", "augen": "begleiter",
               "band": "band", "ribbon": "band", "ring": "band",
               "saga": "saga", "nebel": "saga", "membran": "membran", "membrane": "membran",
               "prisma": "prisma", "kristall": "prisma", "geodät": "geodaet", "geodaet": "geodaet",
               "helix": "helix", "spirale": "helix", "strata": "strata", "schichten": "strata",
               "blüte": "bluete", "bluete": "bluete", "baum": "bluete",
               "galaxie": "galaxie", "galaxy": "galaxie", "multiversum": "multiversum", "multiverse": "multiversum",
               "avatar": "avatar", "gesicht": "avatar", "humanoid": "avatar", "singularität": "singularitaet",
               "singularitaet": "singularitaet", "schwarzes loch": "singularitaet", "synapse": "synapse",
               "neuronen": "synapse", "ozean": "ozean", "wellen": "ozean", "tesserakt": "tesserakt",
               "hyperwürfel": "tesserakt", "reaktor": "reaktor", "arc": "reaktor",
               "retro": "retro", "uml": "retro", "diagramm": "retro", "übersicht": "retro",
               "kosmos": "kosmos", "3d": "kosmos", "webgl": "kosmos", "raum": "kosmos",
               "phantom": "phantom", "schemen": "phantom", "geist": "phantom"}
SITES = {"youtube": "https://www.youtube.com", "google": "https://www.google.com", "twitch": "https://www.twitch.tv",
         "github": "https://github.com", "wikipedia": "https://de.wikipedia.org", "gmail": "https://mail.google.com",
         "netflix": "https://www.netflix.com", "spotify": "https://open.spotify.com", "amazon": "https://www.amazon.de",
         "reddit": "https://www.reddit.com", "maps": "https://maps.google.com", "google maps": "https://maps.google.com",
         "wetter": "https://www.wetteronline.de", "nachrichten": "https://www.tagesschau.de", "tagesschau": "https://www.tagesschau.de"}


# ---------------------------------------------------------------- Einstellungen
def load_settings():
    s = dict(DEFAULTS)
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            s.update({k: v for k, v in data.items() if k in DEFAULTS})
    except FileNotFoundError:
        save_settings(s)
    except (OSError, ValueError) as e:
        print(f"! einstellungen.json konnte nicht gelesen werden ({e}). Standardwerte werden genutzt.")
    return s


def write_json(pfad, daten, indent=2):
    """Schreibt erst in eine Hilfsdatei und tauscht dann aus: Bei einem Absturz bleibt die alte Datei heil.
    Auf Linux und macOS darf nur der eigene Benutzer die Datei lesen (dort stehen Schlüssel und Notizen)."""
    tmp = pfad + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=indent)
    if os.name != "nt":
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
    os.replace(tmp, pfad)


def save_settings(s):
    write_json(SETTINGS_FILE, s)


def public_settings(s):
    out = dict(s)
    for k in SECRET:
        v = str(s.get(k) or "")
        out[k] = (MASK + v[-4:]) if v else ""
    out["bots"] = [dict(b, api_key=(MASK + b["api_key"][-4:]) if b.get("api_key") else "") for b in s.get("bots") or []]
    # Die Anzeige im Browser übernimmt die Einstufung vom Server (pc, netz, internet), statt selbst zu raten
    urls = [s.get("ollama_url"), s.get("openai_url"), s.get("ha_url"), s.get("suche_url")] + [b.get("api_url") for b in s.get("bots") or []]
    out["_orte"] = {u: adresse_art(u) for u in urls if u}
    return out


def clean_pc_liste(v):
    out = []
    for r in (v if isinstance(v, list) else [])[:30]:
        if not isinstance(r, dict):
            continue
        pfad = str(r.get("pfad") or "").strip().strip('"')[:400]
        if not pfad:
            continue
        name = re.sub(r"[\[\]|]", "", str(r.get("name") or "")).strip()[:40] or os.path.basename(pfad.rstrip("/\\")) or pfad
        out.append({"name": name, "pfad": pfad})
    return out


BOT_FORMEN = ("kugel", "wuerfel", "diamant", "pyramide", "kristall", "ring", "stern", "atom", "plasma",
              "punktmensch", "arc", "hud", "auge", "globus")


def clean_bots(v, alt):
    """Prüft die Bot-Liste aus der Oberfläche. Maskierte Schlüssel bleiben, wie sie gespeichert sind."""
    keys = {b.get("id"): b.get("api_key", "") for b in alt or [] if isinstance(b, dict)}
    out, seen = [], set()
    for r in (v if isinstance(v, list) else [])[:24]:
        if not isinstance(r, dict):
            continue
        name = re.sub(r"\s+", " ", str(r.get("name") or "")).strip(" @,:")[:32]
        if not name:
            continue
        bid = re.sub(r"[^a-z0-9]", "", str(r.get("id") or "").lower())[:12] or uuid.uuid4().hex[:8]
        if bid in seen:
            bid = uuid.uuid4().hex[:8]
        seen.add(bid)
        key = str(r.get("api_key") or "").strip()[:400]
        if key.startswith(MASK):
            key = keys.get(bid, "")
        anb = str(r.get("anbieter") or "")
        farbe = str(r.get("farbe") or "")
        try:
            gr = max(0.4, min(2.5, float(r.get("groesse", 1))))
        except (TypeError, ValueError):
            gr = 1.0
        out.append({
            "id": bid, "name": name,
            "rolle": str(r.get("rolle") or "")[:140].strip(),
            "auftrag": str(r.get("auftrag") or "")[:4000].strip(),
            "anbieter": anb if anb in ("ollama", "claude", "openai") else "",     # leer = wie Jarvis
            "modell": str(r.get("modell") or "")[:120].strip(),
            "api_key": key,
            "api_url": str(r.get("api_url") or "")[:300].strip().rstrip("/"),
            "websuche": bool(r.get("websuche")),
            "stichwoerter": str(r.get("stichwoerter") or "")[:300].strip(),
            "form": r.get("form") if r.get("form") in BOT_FORMEN else "kugel",
            "farbe": farbe if re.match(r"^#[0-9a-fA-F]{6}$", farbe) else "#4fb6ff",
            "groesse": gr,
            "aktiv": bool(r.get("aktiv", True)),
        })
    return out


GRENZEN = {"kosten_limit": (0.0, 100000.0), "kosten_guthaben": (0.0, 100000.0)}


def update_settings(data):
    with LOCK:
        s = load_settings()
        guthaben_alt = s.get("kosten_guthaben")
        for k, v in (data or {}).items():
            if k not in DEFAULTS:
                continue
            if k in SECRET:
                v = str(v or "").strip()
                if v.startswith(MASK):
                    continue          # unverändert (nur die Maske kam zurück)
            d = DEFAULTS[k]
            if k == "bots":
                s[k] = clean_bots(v, s.get("bots"))
                continue
            if k in ("pc_ordner", "pc_programme"):
                s[k] = clean_pc_liste(v)
                continue
            try:
                if isinstance(d, bool):
                    v = bool(v)
                elif isinstance(d, float):
                    lo, hi = GRENZEN.get(k) or ((0.0, 1.0) if k.endswith("_vol") else (0.1, 3.0))
                    v = float(str(v).replace(",", ".") or 0)
                    v = max(lo, min(hi, v)) if v == v else lo        # v != v wäre "keine Zahl"
                elif isinstance(d, list):
                    v = [r for r in v if isinstance(r, dict) and str(r.get("satz", "")).strip()][:40]
                    v = [{"satz": str(r.get("satz", ""))[:80].strip(), "aktion": str(r.get("aktion", "sagen"))[:20],
                          "wert": str(r.get("wert", ""))[:400]} for r in v]
                else:
                    v = str(v)[:4000].strip()
            except (TypeError, ValueError):
                continue
            if k in ("ollama_url", "openai_url", "ha_url"):
                v = v.rstrip("/")
            s[k] = v
        save_settings(s)
        if s.get("kosten_guthaben") != guthaben_alt:
            kosten_stichtag()            # neues Guthaben eingetragen: ab jetzt wird davon abgezogen
        return s


# ---------------------------------------------------------------- Gedächtnis
def mem_load():
    try:
        with open(MEMORY_FILE, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def mem_save(items):
    write_json(MEMORY_FILE, items)


def _norm(t):
    return re.sub(r"[^a-z0-9äöüß ]", "", t.lower()).strip()


def mem_add(text):
    text = re.sub(r"\s+", " ", str(text or "")).strip(" .,:;-")[:300]
    if len(text) < 3:
        return None
    with LOCK:
        items = mem_load()
        n = _norm(text)
        for it in items:
            if _norm(it.get("text", "")) == n:
                return it
        it = {"id": uuid.uuid4().hex[:8], "text": text[0].upper() + text[1:], "datum": datetime.date.today().isoformat()}
        items.append(it)
        mem_save(items[-300:])
        return it


def mem_delete(mid=None, match=None):
    with LOCK:
        items = mem_load()
        if mid:
            keep = [i for i in items if i.get("id") != mid]
        else:
            words = [w for w in _norm(match or "").split() if len(w) > 2]
            if not words:
                return 0
            keep = [i for i in items if not all(w in _norm(i.get("text", "")) for w in words)]
        n = len(items) - len(keep)
        mem_save(keep)
        return n


def mem_text(limit=4000):
    items = mem_load()
    lines, size = [], 0
    for it in reversed(items):
        line = f"- {it.get('text', '')} ({it.get('datum', '')})"
        size += len(line)
        if size > limit:
            break
        lines.append(line)
    return "\n".join(reversed(lines))


# ---------------------------------------------------------------- HTTP-Helfer
class Umweg(urllib.error.HTTPError):
    """Der Dienst wollte auf eine andere Adresse umleiten. Jarvis folgt dem nicht."""

    def __init__(self, req, fp, code, headers, ziel):
        super().__init__(req.full_url, code, "Weiterleitung blockiert", headers, fp)
        self.ziel = ziel


class _KeinUmweg(urllib.request.HTTPRedirectHandler):
    # Python schickt bei einer Weiterleitung die Kopfzeilen mit, also auch den API-Schlüssel. Außerdem könnte eine
    # Adresse im Heimnetz so ins Internet umleiten, obwohl strikt lokal an ist. Deshalb: keine Weiterleitungen.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Umweg(req, fp, code, headers, newurl)


OPENER = urllib.request.build_opener(_KeinUmweg())


def http(url, data=None, headers=None, timeout=20, method=None):
    body = json.dumps(data).encode("utf-8") if data is not None else None
    h = {"User-Agent": "Jarvis-YouTube-Edition/" + VERSION}
    if body is not None:
        h["Content-Type"] = "application/json"
    h.update(headers or {})
    return OPENER.open(urllib.request.Request(url, data=body, headers=h, method=method), timeout=timeout)


def get_json(url, headers=None, timeout=10):
    with http(url, headers=headers, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def http_error_text(e):
    if isinstance(e, Umweg):
        ziel = urllib.parse.urlparse(e.ziel).hostname or e.ziel[:80]
        return (f"Die Adresse leitet weiter (nach {ziel}). Jarvis folgt Weiterleitungen aus Sicherheitsgründen nicht. "
                "Trag bitte die endgültige Adresse direkt ein.")
    try:
        raw = e.read().decode("utf-8", "replace")
        j = json.loads(raw)
        if isinstance(j.get("error"), dict):
            return j["error"].get("message") or raw[:200]
        return str(j.get("error") or j.get("message") or j.get("detail") or raw[:200])
    except Exception:
        return f"HTTP {getattr(e, 'code', '?')}"


CACHE = {}


def cached(key, sec, fn):
    hit = CACHE.get(key)
    if hit and time.time() - hit[0] < sec:
        return hit[1]
    val = fn()
    CACHE[key] = (time.time(), val)
    return val


# ---------------------------------------------------------------- Modelle
STRIKT_SPERRE = "Strikt lokal ist an: keine Verbindung ins Internet."


def ollama_models(s):
    if s.get("strikt_lokal") and adresse_art(s.get("ollama_url") or "") == "internet":
        return {"ok": False, "models": [], "fehler": STRIKT_SPERRE + " Die Ollama-Adresse liegt im Internet."}
    try:
        j = get_json(s["ollama_url"] + "/api/tags", timeout=2.5)
        names = [m.get("name") for m in j.get("models", []) if m.get("name")]
        chat = [n for n in names if "embed" not in n.lower()]
        if not chat:
            return {"ok": False, "models": [], "fehler": "Ollama läuft, aber es ist kein Sprachmodell installiert. Im Terminal: ollama pull llama3.2"}
        return {"ok": True, "models": chat}
    except urllib.error.HTTPError as e:
        return {"ok": False, "models": [], "fehler": f"Ollama antwortet mit Fehler: {http_error_text(e)}"}
    except Exception:
        return {"ok": False, "models": [], "fehler": f"Ollama nicht erreichbar unter {s['ollama_url']}. Läuft Ollama? (Taskleiste oder: ollama serve)"}


def claude_models(s):
    if s.get("strikt_lokal"):                       # Claude ist immer Internet: im strikten Modus nicht einmal die Modellliste holen
        return {"ok": False, "models": [], "fehler": STRIKT_SPERRE}
    key = s.get("claude_key")
    if not key:
        return {"ok": False, "models": [], "fehler": "Kein Claude-Schlüssel eingetragen."}

    def fetch():
        j = get_json(ANTHROPIC + "/v1/models?limit=100",
                     headers={"x-api-key": key, "anthropic-version": "2023-06-01"}, timeout=8)
        return [m["id"] for m in j.get("data", []) if m.get("id")]
    try:
        ids = cached("claude:" + key[-6:], 600, fetch)
        return {"ok": bool(ids), "models": ids, "fehler": "" if ids else "Keine Modelle gefunden."}
    except urllib.error.HTTPError as e:
        msg = http_error_text(e)
        if e.code == 401:
            msg = "Schlüssel ungültig (401). Bitte prüfen, ob er vollständig kopiert wurde."
        return {"ok": False, "models": [], "fehler": "Claude: " + msg}
    except Exception as e:
        return {"ok": False, "models": [], "fehler": f"Claude nicht erreichbar ({type(e).__name__})."}


NON_CHAT = re.compile(r"embed|tts|whisper|dall-e|moderation|audio|realtime|transcribe|image|davinci|babbage|search|computer-use|sora", re.I)


def openai_models(s):
    base, key = s.get("openai_url") or "", s.get("openai_key") or ""
    if not base:
        return {"ok": False, "models": [], "fehler": "Keine Basis-Adresse eingetragen."}
    art = adresse_art(base)                         # dieselbe Prüfung wie überall: pc, netz oder internet
    if s.get("strikt_lokal") and art == "internet":
        return {"ok": False, "models": [], "fehler": STRIKT_SPERRE}
    local = art != "internet"
    if not key and not local:
        return {"ok": False, "models": [], "fehler": "Kein Schlüssel eingetragen."}

    def fetch():
        j = get_json(base + "/models", headers={"Authorization": "Bearer " + key} if key else None, timeout=8)
        ids = [m.get("id") for m in j.get("data", []) if m.get("id")]
        if "api.openai.com" in base:
            ids = [i for i in ids if not NON_CHAT.search(i)]
        return sorted(ids)
    try:
        ids = cached("openai:" + base + key[-6:], 600, fetch)
        return {"ok": bool(ids), "models": ids, "fehler": "" if ids else "Keine Modelle gefunden."}
    except urllib.error.HTTPError as e:
        return {"ok": False, "models": [], "fehler": f"API-Fehler: {http_error_text(e)}"}
    except Exception as e:
        return {"ok": False, "models": [], "fehler": f"Nicht erreichbar: {base} ({type(e).__name__})"}


def all_models(s):
    out = {}
    threads = []

    def run(k, fn):
        out[k] = fn(s)
    for k, fn in (("ollama", ollama_models), ("claude", claude_models), ("openai", openai_models)):
        t = threading.Thread(target=run, args=(k, fn))
        t.start()
        threads.append(t)
    for t in threads:
        t.join(12)
    return out


def pick_model(s, models=None):
    a = s.get("anbieter")
    if a not in ("ollama", "claude", "openai"):
        a = "ollama"
    m = s.get("modell") or ""
    lst = (models or {}).get(a, {}).get("models") if models else None
    if m and (lst is None or m in lst):
        return a, m
    if lst is None:
        lst = {"ollama": ollama_models, "claude": claude_models, "openai": openai_models}[a](s).get("models", [])
    if a == "claude":
        pref = [x for x in lst if "sonnet" in x] or lst
        return a, (pref[0] if pref else "")
    return a, (lst[0] if lst else "")


# ---------------------------------------------------------------- System und Wetter
CPU_PREV = [None, 0.0, None]
CPU_LOCK = threading.Lock()


def _cpu_sample():
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            class FT(ctypes.Structure):
                _fields_ = [("lo", wintypes.DWORD), ("hi", wintypes.DWORD)]
            i, k, u = FT(), FT(), FT()
            if not ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(i), ctypes.byref(k), ctypes.byref(u)):
                return None
            f = lambda x: (x.hi << 32) | x.lo
            return f(i), f(k) + f(u)
        if sys.platform == "darwin":
            return None
        with open("/proc/stat") as fh:
            v = [int(x) for x in fh.readline().split()[1:]]
        return v[3] + (v[4] if len(v) > 4 else 0), sum(v[:8])
    except Exception:
        return None


def cpu_prozent():
    with CPU_LOCK:
        now = time.time()
        if CPU_PREV[0] and now - CPU_PREV[1] < 0.6 and CPU_PREV[2] is not None:
            return CPU_PREV[2]
        a = CPU_PREV[0] if (CPU_PREV[0] and now - CPU_PREV[1] < 20) else None
        if a is None:
            a = _cpu_sample()
            if a is None:
                return None
            time.sleep(0.3)
        b = _cpu_sample()
        if b is None:
            return None
        di, dt = b[0] - a[0], b[1] - a[1]
        CPU_PREV[0], CPU_PREV[1] = b, time.time()
        if dt > 0:
            CPU_PREV[2] = max(0.0, min(100.0, 100.0 * (1 - di / dt)))
        return CPU_PREV[2]


def ram_gb():
    try:
        if os.name == "nt":
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MS()
            m.dwLength = ctypes.sizeof(MS)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
                return m.ullTotalPhys / 2 ** 30, m.ullAvailPhys / 2 ** 30
            return None
        mi = {}
        with open("/proc/meminfo") as f:
            for line in f:
                k, v = line.split(":", 1)
                mi[k] = int(v.split()[0])
        return mi["MemTotal"] / 1048576, mi.get("MemAvailable", mi.get("MemFree", 0)) / 1048576
    except Exception:
        return None


def uptime_s():
    try:
        if os.name == "nt":
            import ctypes
            k = ctypes.windll.kernel32
            k.GetTickCount64.restype = ctypes.c_ulonglong
            return k.GetTickCount64() / 1000.0
        with open("/proc/uptime") as f:
            return float(f.read().split()[0])
    except Exception:
        return None


def dauer(sec):
    sec = int(sec)
    d, h, m = sec // 86400, sec % 86400 // 3600, sec % 3600 // 60
    if d:
        return f"{d} Tag{'e' if d > 1 else ''} {h} Std"
    if h:
        return f"{h} Std {m} Min"
    return f"{m} Min"


def system_info():
    s = {"kerne": os.cpu_count()}
    c = cpu_prozent()
    s["cpu"] = None if c is None else round(c)
    r = ram_gb()
    if r and r[0]:
        s["ram"] = round(100 * (r[0] - r[1]) / r[0])
        s["ram_belegt"], s["ram_gesamt"] = round(r[0] - r[1], 1), round(r[0], 1)
    else:
        s["ram"] = s["ram_belegt"] = s["ram_gesamt"] = None
    try:
        du = shutil.disk_usage(BASE)
        s["platte"] = round(100 * (du.total - du.free) / du.total)
        s["platte_frei"] = round(du.free / 1e9)
    except OSError:
        s["platte"] = s["platte_frei"] = None
    up = uptime_s()
    s["laufzeit"] = None if up is None else dauer(up)
    warn = []
    if s["cpu"] is not None and s["cpu"] >= 85:
        warn.append(f"CPU {s['cpu']} Prozent")
    if s["ram"] is not None and s["ram"] >= 90:
        warn.append(f"Arbeitsspeicher {s['ram']} Prozent")
    if s["platte"] is not None and s["platte"] >= 95:
        warn.append(f"Festplatte {s['platte']} Prozent")
    s["auffaellig"] = warn
    return s


WMO = {0: ("klar", "sonne"), 1: ("überwiegend klar", "sonne"), 2: ("teils bewölkt", "wolkig"), 3: ("bedeckt", "bedeckt"),
       45: ("Nebel", "nebel"), 48: ("Nebel", "nebel"), 51: ("leichter Nieselregen", "regen"), 53: ("Nieselregen", "regen"),
       55: ("Nieselregen", "regen"), 56: ("gefrierender Nieselregen", "regen"), 57: ("gefrierender Nieselregen", "regen"),
       61: ("leichter Regen", "regen"), 63: ("Regen", "regen"), 65: ("starker Regen", "regen"), 66: ("gefrierender Regen", "regen"),
       67: ("gefrierender Regen", "regen"), 71: ("leichter Schneefall", "schnee"), 73: ("Schneefall", "schnee"),
       75: ("starker Schneefall", "schnee"), 77: ("Schneegriesel", "schnee"), 80: ("Regenschauer", "regen"),
       81: ("Regenschauer", "regen"), 82: ("heftige Regenschauer", "regen"), 85: ("Schneeschauer", "schnee"),
       86: ("Schneeschauer", "schnee"), 95: ("Gewitter", "gewitter"), 96: ("Gewitter mit Hagel", "gewitter"),
       99: ("Gewitter mit Hagel", "gewitter")}
GEO_URL = os.environ.get("JARVIS_GEO_URL") or "https://geocoding-api.open-meteo.com/v1/search"
WETTER_URL = os.environ.get("JARVIS_WETTER_URL") or "https://api.open-meteo.com/v1/forecast"
ANTHROPIC = os.environ.get("JARVIS_ANTHROPIC_URL") or "https://api.anthropic.com"


def geocode(ort):
    def fetch():
        q = urllib.parse.urlencode({"name": ort, "count": 1, "language": "de", "format": "json"})
        j = get_json(GEO_URL + "?" + q, timeout=8)
        r = (j.get("results") or [None])[0]
        if not r:
            raise ValueError(f"Ort '{ort}' nicht gefunden")
        return r["latitude"], r["longitude"], r.get("name", ort)
    return cached("geo:" + ort.lower(), 86400, fetch)


def wetter(s):
    ort = (s.get("ort") or "Berlin").strip()
    if s.get("strikt_lokal"):
        return {"fehler": "Strikt lokal ist an, deshalb wird kein Wetter aus dem Internet geladen.", "ort": ort}

    def fetch():
        lat, lon, name = geocode(ort)
        q = urllib.parse.urlencode({"latitude": lat, "longitude": lon,
                                    "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m,is_day",
                                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                                    "timezone": "auto", "forecast_days": 1})
        j = get_json(WETTER_URL + "?" + q, timeout=8)
        c, d = j["current"], j.get("daily") or {}
        text, icon = WMO.get(int(c["weather_code"]), ("wechselhaft", "wolkig"))
        if icon == "sonne" and not c.get("is_day", 1):
            icon = "mond"
        first = lambda k: (d.get(k) or [None])[0]
        return {"ort": name, "temp": round(float(c["temperature_2m"])), "gefuehlt": round(float(c["apparent_temperature"])),
                "text": text, "icon": icon, "wind": round(float(c.get("wind_speed_10m") or 0)),
                "tmax": None if first("temperature_2m_max") is None else round(first("temperature_2m_max")),
                "tmin": None if first("temperature_2m_min") is None else round(first("temperature_2m_min")),
                "regen": first("precipitation_probability_max"), "quelle": "Open-Meteo"}
    try:
        return cached("wetter:" + ort.lower(), 600, fetch)
    except Exception as e:
        return {"fehler": str(e)[:160] or type(e).__name__, "ort": ort}


def wetter_satz(w):
    if w.get("fehler"):
        return f"Wetter für {w.get('ort')}: nicht abrufbar ({w['fehler']}). Sag ehrlich, dass das Wetter gerade nicht lädt."
    t = f"Wetter in {w['ort']} jetzt: {w['temp']} Grad (gefühlt {w['gefuehlt']}), {w['text']}, Wind {w['wind']} km/h"
    if w.get("tmax") is not None:
        t += f", heute {w['tmin']} bis {w['tmax']} Grad"
    if w.get("regen") is not None:
        t += f", Regenwahrscheinlichkeit bis {w['regen']} Prozent"
    return t + ". Quelle: Open-Meteo."


def system_satz(si):
    p = lambda v, u: "nicht messbar" if v is None else f"{v}{u}"
    return (f"System jetzt: CPU {p(si['cpu'], ' Prozent')}, Arbeitsspeicher {p(si['ram'], ' Prozent')}, "
            f"Festplatte {p(si['platte'], ' Prozent belegt')}, Rechner läuft seit {p(si['laufzeit'], '')}. "
            f"Auffällig: {', '.join(si['auffaellig']) if si['auffaellig'] else 'nichts'}.")


# ---------------------------------------------------------------- Befehle erkennen (funktioniert mit jedem Modell)
ZAHL = {"ein": 1, "eine": 1, "einer": 1, "einem": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "fuenf": 5, "sechs": 6,
        "sieben": 7, "acht": 8, "neun": 9, "zehn": 10, "elf": 11, "zwölf": 12, "fünfzehn": 15, "zwanzig": 20,
        "dreißig": 30, "dreissig": 30, "vierzig": 40, "fünfzig": 50, "sechzig": 60, "halbe": 0.5}
BRIEF_RE = re.compile(r"\b(bist du da|bist du wach|was geht ab|wach auf|aufwachen|briefing|lagebericht|status ?bericht|status bitte|guten morgen|moin|melde dich)\b")
WETTER_RE = re.compile(r"wetter|regnet|regen|schnee|grad (draußen|draussen)|temperatur|draußen|draussen|regenschirm|jacke|sonnig|sonne scheint")
SYS_RE = re.compile(r"\b(system|cpu|prozessor|arbeitsspeicher|ram|festplatte|auslastung|speicherplatz|rechner)\b")
TIMER_RE = re.compile(r"(?:in|nach|für|auf)\s+(\d+(?:[.,]\d+)?|" + "|".join(ZAHL) + r")\s*(sekunden?|sek|minuten?|min|stunden?|std)\b")


def parse_timer(u):
    if not re.search(r"erinner|timer|wecker|weck mich|stopp?uhr|countdown|sag mir bescheid|sag bescheid", u):
        return None
    m = TIMER_RE.search(u)
    if not m:
        return None
    raw = m.group(1).replace(",", ".")
    n = ZAHL.get(raw)
    if n is None:
        try:
            n = float(raw)
        except ValueError:
            return None
    unit = m.group(2)
    sek = n * (3600 if unit.startswith(("stunde", "std")) else 60 if unit.startswith("min") else 1)
    if not 1 <= sek <= 86400:
        return None
    rest = u[m.end():].strip()
    rest = re.sub(r"^(an|daran|dass|das|zu|ans|mich|bitte)\s+", "", rest)
    rest = re.sub(r"^(dass|das|an)\s+", "", rest).strip(" .!?")
    rest = re.split(r"\s+(?:und|dann)\s+(?:öffne|oeffne|mach|zeig|stell|sag|wechsel|merk|starte|such)\b", rest)[0].strip(" ,.")
    if not rest:
        pre = re.sub(r".*?(erinner\w*\s+(mich\s+)?(an|daran)?)", "", u[:m.start()]).strip(" ,.")
        rest = pre if pre and len(pre) < 80 and not re.search(r"timer|weck|stell|countdown|stopp", pre) else ""
    return {"sek": int(sek), "text": rest[:120] or "Timer abgelaufen"}


def find_url(u, s):
    if not re.search(r"\b(öffne|oeffne|öffnen|mach .* auf|geh auf|gehe auf|zeig mir die seite|ruf .* auf|starte)\b", u):
        return None
    m = re.search(r"(https?://\S+|\b[\w-]+\.(?:de|com|org|net|io|tv|eu|info)\b\S*)", u)
    if m:
        url = m.group(1)
        return {"url": url if url.startswith("http") else "https://" + url, "name": url}
    for name in sorted(SITES, key=len, reverse=True):
        if re.search(r"\b" + re.escape(name) + r"\b", u):
            return {"url": SITES[name], "name": name.title()}
    return None


def merk_text(t):
    """'dass ich am Freitag Zahnarzt habe' -> 'Ich habe am Freitag Zahnarzt'."""
    t = t.strip(" .!?")
    m = re.match(r"(?i)(?:dass|das)\s+(.*)", t)
    if m:
        w = m.group(1).split()
        if len(w) >= 3:
            n = 2 if w[0].lower() in ("mein", "meine", "meinem", "meinen", "meiner", "dein", "deine", "unser", "unsere") else 1
            w = w[:n] + [w[-1]] + w[n:-1]
        t = " ".join(w)
    return t


# Sätze, die nichts auslösen dürfen: verneint ("Kinoabend bitte nicht starten"), Erklärfragen ("Was macht die Routine
# Kinoabend?") und echte Fragen. Höfliche Bitten mit Fragezeichen ("Kannst du Kinoabend starten?") gelten als Befehl.
VERNEINT_RE = re.compile(r"\b(nicht|nichts|kein|keine|keinen|keinem|keiner|nie|niemals)\b")
ERKLAER_RE = re.compile(r"^\s*(?:bitte\s+)?(?:erklär\w*|erklaer\w*|beschreib\w*|warum|wieso|weshalb|"
                        r"was\s+(?:macht|passiert|bedeutet|bewirkt|tut)|wie\s+funktioniert)\b")
FRAGE_RE = re.compile(r"^\s*(?:und\s+|aber\s+)?(?:was|wie|warum|wieso|weshalb|wann|wer|wo|welche\w*|ist|sind|läuft|laeuft|"
                      r"hast|hat|gibt|erklär\w*|erklaer\w*|beschreib\w*)\b")
HOEFLICH_RE = re.compile(r"^\s*(?:bitte\s+)?(?:kannst|könntest|koenntest|würdest|wuerdest|magst|kann ich)\b")


def kein_befehl(u, satz=""):
    """True, wenn der Satz zwar die Routine oder das Gerät nennt, aber nichts ausgelöst werden soll."""
    n, sn = _norm(u), _norm(satz)
    if VERNEINT_RE.search(n) and not VERNEINT_RE.search(sn):
        return True
    if sn and FRAGE_RE.search(sn):                 # die Routine ist selbst als Frage formuliert ("wie spät ist es")
        return False
    if FRAGE_RE.search(n):
        return True
    return u.rstrip().endswith("?") and not HOEFLICH_RE.search(n)


def route(u, s, orig=None, ohne_url=False):
    """Erkennt Befehle vor dem KI-Aufruf. Liefert (aktionen, kontext, direkte_antwort)."""
    orig = orig or u
    actions, ctx, direct, kurz = [], [], None, []       # kurz: fertige Bestätigungen, die keine KI brauchen
    for r in s.get("routinen") or []:
        satz = _norm(r.get("satz", ""))
        if satz and satz in _norm(u) and not kein_befehl(u, r.get("satz", "")):
            a, w = r.get("aktion"), (r.get("wert") or "").strip()
            if a == "briefing":
                u += " briefing"
            elif a == "webseite" and w:
                actions.append({"typ": "webseite", "url": w if w.startswith("http") else "https://" + w, "name": r["satz"]})
                ctx.append(f"Die Webseite {w} wird gerade geöffnet (Routine '{r['satz']}'). Bestätige in einem kurzen Satz.")
                kurz.append("Ich öffne die Seite.")
            elif a == "sagen" and w:
                direct = w
            elif a == "oberflaeche" and w in THEMES:
                actions.append({"typ": "oberflaeche", "name": w, "url": THEMES[w]})
                ctx.append(f"Die Oberfläche wechselt gleich auf {w}. Bestätige kurz.")
                kurz.append(f"Ich wechsle auf die Oberfläche {w.title()}.")
            elif a in ("homeassistant", "webhook") and w:
                ok, info = (ha_routine if a == "homeassistant" else webhook_routine)(s, w)
                actions.append({"typ": "ha", "ok": ok, "text": r["satz"], "info": info})
                ctx.append(f"Routine '{r['satz']}': {info}. Sag das dem Nutzer in einem kurzen Satz, erfinde nichts dazu.")
                kurz.append(("Erledigt: " if ok else "Das hat nicht geklappt: ") + info + ".")
            elif a == "timer":
                try:
                    mins = float(w.replace(",", "."))
                    actions.append({"typ": "timer", "sek": int(mins * 60), "text": r["satz"]})
                    ctx.append(f"Ein Timer über {w} Minuten läuft jetzt (Routine '{r['satz']}'). Bestätige kurz.")
                    kurz.append(f"Timer läuft: {w} {'Minute' if mins == 1 else 'Minuten'}.")
                except ValueError:
                    pass
            actions.append({"typ": "routine", "satz": r["satz"]})

    m = re.search(r"\b(merk dir|merke dir|speicher dir|speichere dir|notier dir|notiere dir|vergiss nicht)\b[:,]?\s*(.+)", orig, re.I | re.S)
    if m:
        it = mem_add(merk_text(m.group(2)))
        if it:
            actions.append({"typ": "gedaechtnis", "aktion": "gespeichert", "text": it["text"]})
            ctx.append(f"Du hast gerade im Gedächtnis gespeichert: '{it['text']}'. Bestätige kurz und natürlich.")
            kurz.append(f"Gemerkt: {it['text']}.")
    m = re.search(r"\bvergiss\b\s+(?:bitte\s+)?(?:dass|das|die notiz)?\s*(.+)", u)
    if m and not re.search(r"vergiss nicht", u):
        n = mem_delete(match=m.group(1))
        actions.append({"typ": "gedaechtnis", "aktion": "geloescht", "text": m.group(1), "anzahl": n})
        ctx.append(f"Du hast {n} passende Notiz(en) aus dem Gedächtnis gelöscht." if n else
                   "Im Gedächtnis gab es dazu keine passende Notiz. Sag das ehrlich.")
        kurz.append(("Erledigt, " + ("eine Notiz" if n == 1 else f"{n} Notizen") + " gelöscht.") if n else "Dazu habe ich nichts gespeichert.")

    t = parse_timer(u)
    if t:
        actions.append({"typ": "timer", **t})
        mins = t["sek"] / 60
        dauer_text = (('%g Minute' if mins == 1 else '%g Minuten') % mins) if t['sek'] >= 60 else (f"{t['sek']} Sekunde" if t['sek'] == 1 else f"{t['sek']} Sekunden")
        ctx.append(f"Ein Timer läuft jetzt: {dauer_text}, Erinnerungstext: '{t['text']}'. Bestätige kurz.")
        kurz.append(f"Timer läuft: {dauer_text}.")

    w = None if ohne_url else find_url(u, s)
    if w and not any(a["typ"] == "webseite" for a in actions):
        actions.append({"typ": "webseite", **w})
        ctx.append(f"Die Webseite {w['name']} wird gerade geöffnet. Bestätige in einem kurzen Satz.")
        kurz.append(f"Ich öffne {w['name']}.")

    if re.search(r"oberfläche|oberflaeche|design|aussehen|skin|ansicht", u):
        for word, tid in THEME_WORDS.items():
            if re.search(r"\b" + word + r"\b", u):
                actions.append({"typ": "oberflaeche", "name": tid, "url": THEMES[tid]})
                ctx.append(f"Die Oberfläche wechselt gleich auf {tid}. Bestätige kurz.")
                kurz.append(f"Ich wechsle auf die Oberfläche {tid.title()}.")
                break

    brief = bool(BRIEF_RE.search(u))
    if brief:
        si, w = system_info(), wetter(s)
        actions.append({"typ": "briefing", "system": si, "wetter": w})
        ctx.append("WECK-BRIEFING. Nutze nur diese echten Daten:\n" + system_satz(si) + "\n" + wetter_satz(w) +
                   "\nAblauf, locker gesprochen, ohne Aufzählungszeichen: 1) Sag, dass du da bist. Ist 'Auffällig' = nichts, sag "
                   "'dein System läuft sauber', sonst nenne das Auffällige. Nenne zwei der Werte. 2) Das Wetter in einem Satz. "
                   "3) 'Heute steht an': nur, was im GEDÄCHTNIS nach Termin, Vorhaben oder To-do klingt. Steht nichts drin, sag das "
                   "in einem Satz. 4) Kurze Frage, womit du helfen kannst. Höchstens sechs Sätze.")
    else:
        if WETTER_RE.search(u):
            w = wetter(s)
            actions.append({"typ": "wetter", "wetter": w})
            ctx.append(wetter_satz(w))
        if SYS_RE.search(u):
            si = system_info()
            actions.append({"typ": "system", "system": si})
            ctx.append(system_satz(si))
    # Nur wenn JEDER Kontext eine fertige Bestätigung hat, kann die KI-Rückfrage entfallen
    return actions, ctx, direct, (kurz if kurz and len(kurz) == len(ctx) else [])


# ---------------------------------------------------------------- Datenschutz
def adresse_art(url):
    """'pc' = dieser Rechner, 'netz' = eigenes Heimnetz, 'internet' = alles andere.
    Geprüft wird der echte Rechnername der Adresse. 'localhost.beispiel.com' ist Internet, nicht lokal."""
    try:
        host = (urllib.parse.urlparse(url if "//" in url else "//" + url).hostname or "").lower().rstrip(".")
    except ValueError:
        return "internet"
    if host in ("localhost", "") or host.endswith(".localhost"):
        return "pc" if host else "internet"
    try:
        ip = ipaddress.ip_address(host)
        return "pc" if ip.is_loopback else "netz" if (ip.is_private or ip.is_link_local) else "internet"
    except ValueError:
        return "netz" if host.endswith((".local", ".lan", ".home", ".fritz.box", ".internal")) or "." not in host else "internet"


def ist_cloud(s, anbieter):
    """Cloud = die Nachricht geht ins Internet. Dieser PC und das eigene Heimnetz (z. B. Ollama auf einem
    zweiten Rechner) gelten als lokal."""
    if anbieter == "claude":
        return True
    return adresse_art(s.get("openai_url" if anbieter == "openai" else "ollama_url") or "") == "internet"


def _luhn(num):
    d = [int(x) for x in num][::-1]
    return sum(x if i % 2 == 0 else (x * 2 - 9 if x * 2 > 9 else x * 2) for i, x in enumerate(d)) % 10 == 0


PRIV_RE = [
    ("E-Mail-Adresse", re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", re.I)),
    ("IBAN", re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){3,7}(?: ?[A-Z0-9]{1,3})?\b")),
    ("Adresse", re.compile(r"\b[A-ZÄÖÜa-zäöü][\wäöüß-]*(?:straße|strasse|str\.|weg|gasse|platz|allee|ring|damm|chaussee)\s+\d{1,4}\s?[a-z]?\b", re.I)),
    ("Postleitzahl", re.compile(r"\b\d{5}\s+[A-ZÄÖÜ][a-zäöüß]{2,}")),
    ("API-Schlüssel", re.compile(r"\b(?:sk|pk|gsk|xai)[-_][A-Za-z0-9_-]{12,}")),
]
PHONE_RE = re.compile(r"(?<![\w.,])(?:\+|00)\d[\d\s/()-]{6,}\d|(?<![\w.,])0\d{2,5}[\s/-]?\d[\d\s/-]{3,}\d")
CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
PRIV_WORT = {
    "Zugangsdaten": r"passwort|kennwort|password|\bpin\b|\btan\b|zugangsdaten|logindaten|login-daten|geheimzahl|api[- ]?key|api[- ]?schlüssel",
    "Gesundheit": r"diagnose|befund|\bkrank|arzt\b|ärztin|klinik|medikament|therapie|depression|arztbrief|blutwerte|krankschreibung|psychiat|schwanger",
    "Ausweis oder Steuer": r"ausweisnummer|personalausweis|reisepass|steuer-?id|steuernummer|steueridentifikation|sozialversicherungsnummer|versichertennummer",
    "Finanzen": r"kontonummer|kontostand|\bgehalt|kreditkarte|bankverbindung|schulden|kredit über",
}


def privat_erkennen(text, s):
    """Liefert eine Liste von Gründen, warum die Nachricht privat aussieht (leer = nichts erkannt)."""
    t = text or ""
    found = []
    if re.match(r"^\s*(privat|vertraulich|geheim)\b", t, re.I):
        found.append("als privat markiert")
    for name, rx in PRIV_RE:
        if rx.search(t):
            found.append(name)
    for m in ([] if "IBAN" in found else PHONE_RE.finditer(t)):
        if len(re.sub(r"\D", "", m.group(0))) >= 7:
            found.append("Telefonnummer")
            break
    for m in CARD_RE.finditer(t):
        d = re.sub(r"\D", "", m.group(0))
        if 13 <= len(d) <= 19 and _luhn(d):
            found.append("Kartennummer")
            break
    low = t.lower()
    for name, rx in PRIV_WORT.items():
        if re.search(rx, low):
            found.append(name)
    for w in re.split(r"[,;\n]+", s.get("privat_woerter") or ""):
        w = w.strip().lower()
        if len(w) >= 2 and re.search(r"(?<![\wäöüß])" + re.escape(w) + r"(?![\wäöüß])", low):
            found.append("eigenes Stichwort")
            break
    out = []
    for f in found:
        if f not in out:
            out.append(f)
    return out


def lokales_modell(s):
    om = ollama_models(s)
    if not om.get("ok"):
        return ""
    lst = om["models"]
    for cand in (s.get("lokal_modell"), s.get("modell") if s.get("anbieter") == "ollama" else ""):
        if cand and cand in lst:
            return cand
    return lst[0]


# ---------------------------------------------------------------- Prompt
LAENGE = {"kurz": "Antworte in der Regel in 1 bis 3 kurzen Sätzen.",
          "normal": "Antworte in der Regel in 2 bis 5 Sätzen.",
          "ausfuehrlich": "Antworte gründlich, aber gut vorlesbar."}
TAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]


class Prompt(str):
    """Systemprompt aus einem festen Teil (ändert sich selten, darf zwischengespeichert werden) und einem wechselnden
    Teil (Uhrzeit, gerade erledigte Befehle). Für Ollama und OpenAI ist es einfach der ganze Text."""

    def __new__(cls, stabil, variabel=""):
        o = super().__new__(cls, stabil + ("\n\n" + variabel if variabel else ""))
        o.stabil, o.variabel = stabil, variabel
        return o


def system_prompt(s, ctx, websuche, mit_gedaechtnis=True, ohne_team=False, pc_ok=False, lokal=False, suche_tag=False):
    now = datetime.datetime.now()
    name = s.get("name") or "Jarvis"
    p = [f"Du bist {name}, ein persönlicher KI-Assistent im Stil von J.A.R.V.I.S.: ruhig, schlagfertig, hilfsbereit, mit einem "
         "Hauch trockenem Humor. Du sprichst Deutsch.",
         "Deine Antworten werden laut vorgelesen: kurze, natürliche Sätze. Kein Markdown, keine Sternchen, keine Aufzählungszeichen, "
         "keine Emojis, keine Links ausschreiben. " + LAENGE.get(s.get("antwortlaenge"), LAENGE["kurz"]),
         "Erfinde nichts. Wenn du etwas nicht weißt oder nicht nachsehen kannst, sag das ehrlich.",
         f"Heute ist {TAGE[now.weekday()]}, der {now.day}. {MONATE[now.month - 1]} {now.year}. Die genaue Uhrzeit steht ganz unten."]
    if s.get("nutzer"):
        p.append(f"Dein Nutzer heißt {s['nutzer']}. Sprich ihn ab und zu mit Namen an.")
    if s.get("persona"):
        p.append("Zusätzliche Anweisungen deines Nutzers zu deiner Persönlichkeit: " + s["persona"])
    p.append("Fähigkeiten, die die Oberfläche selbst ausführt (der Nutzer muss es nur sagen): Timer und Erinnerungen, Webseiten "
             "öffnen, Wetter, Systemwerte, Weck-Briefing, Notizen merken und vergessen, Oberfläche wechseln. Behaupte nie, dass "
             "du etwas ausgeführt hast, wenn es unten nicht als erledigt steht.")
    if websuche:
        p.append("Du kannst das Web durchsuchen. Nutze es für aktuelle Fragen und nenne die Quelle in Worten.")
    elif suche_tag:
        p.append("Du kannst eine Websuche anfordern. Brauchst du für die Antwort aktuelle Informationen aus dem Internet, "
                 "antworte mit GENAU einer Zeile und sonst nichts: [suche: wenige Suchbegriffe]. Danach bekommst du die "
                 "Suchergebnisse. Für Smalltalk und Allgemeinwissen suchst du nicht.")
    else:
        p.append("Du hast keinen Internetzugang. Für aktuelle Ereignisse sag ehrlich, dass dein Wissen einen Stand hat.")
    if mit_gedaechtnis:
        p.append("GEDÄCHTNIS (was du dir über deinen Nutzer gemerkt hast):\n" + (mem_text(1500 if s.get("sparmodus") else 4000) or "(noch leer)"))
    else:
        p.append("GEDÄCHTNIS: Aus Datenschutzgründen bleibt das Gedächtnis auf dem PC des Nutzers und wird dir nicht geschickt. "
                 "Fragt er danach oder nach 'heute steht an', sag kurz, dass die Notizen nur bei der lokalen KI verfügbar sind.")
    if s.get("auto_merken") and mit_gedaechtnis:
        p.append("Wenn der Nutzer dir etwas Dauerhaftes über sich erzählt (Name, Vorlieben, Projekte, Termine, Ziele), das noch "
                 "nicht im Gedächtnis steht, hänge ganz am Ende genau eine Zeile an: [merken: kurzer Satz in der dritten Person]. "
                 "Diese Zeile wird nicht vorgelesen. Sonst nie.")
    if s.get("pc_an") and pc_ok:
        p.append(pc_prompt(s))
    team = [b for b in s.get("bots") or [] if b.get("aktiv")]
    if lokal:                                       # lokales Gespräch: nichts von sich aus an einen Cloud-Bot abgeben
        team = [b for b in team if not bot_ist_cloud(s, b)]
    if team and s.get("bot_delegieren") and not ohne_team:
        p.append("DEIN TEAM (Bots mit Spezialgebiet):\n" + "\n".join(f"- {b['name']}: {b.get('rolle') or 'ohne Beschreibung'}" for b in team) +
                 "\nFällt eine Aufgabe klar in das Spezialgebiet eines Bots, antworte mit GENAU einer Zeile und sonst nichts: "
                 "[bot: Name | vollständige Aufgabe mit allem nötigen Kontext]. Der Bot kennt das Gespräch nicht, schreib also alles "
                 "Nötige in die Aufgabe. Einfache Fragen und Smalltalk beantwortest du selbst. Höchstens ein Bot pro Antwort.")
    elif team:
        p.append("Es gibt Bots im Team: " + ", ".join(b["name"] for b in team) + ". Der Nutzer spricht sie mit @Name selbst an.")
    v = [f"Es ist jetzt {now:%H:%M} Uhr."]
    if ctx:
        v.append("GERADE ERLEDIGT / ECHTE DATEN:\n" + "\n".join(ctx))
    return Prompt("\n\n".join(p), "\n\n".join(v))


def bot_prompt(s, bot, websuche):
    now = datetime.datetime.now()
    p = [f"Du bist {bot['name']}, ein spezialisierter KI-Bot im Team von {s.get('name') or 'Jarvis'}. Du sprichst Deutsch.",
         "Deine Rolle: " + (bot.get("rolle") or "Allgemeiner Helfer") + ".",
         "Deine Antworten werden laut vorgelesen: klare, natürliche Sätze. Kein Markdown, keine Sternchen, keine Emojis. "
         "Code darfst du in einem Codeblock ausgeben, er wird nicht vorgelesen. " + LAENGE.get(s.get("antwortlaenge"), LAENGE["kurz"]),
         "Erfinde nichts. Wenn du etwas nicht weißt oder nicht nachsehen kannst, sag das ehrlich.",
         f"Heute ist {TAGE[now.weekday()]}, der {now.day}. {MONATE[now.month - 1]} {now.year}."]
    if bot.get("auftrag"):
        p.insert(2, "Dein Auftrag: " + bot["auftrag"])
    if s.get("nutzer"):
        p.append(f"Der Nutzer heißt {s['nutzer']}.")
    p.append("Du kannst das Web durchsuchen. Nutze es für aktuelle Fragen und nenne die Quelle in Worten." if websuche else
             "Du hast keinen Internetzugang. Für aktuelle Ereignisse sag ehrlich, dass dein Wissen einen Stand hat.")
    return Prompt("\n\n".join(p), f"Es ist jetzt {now:%H:%M} Uhr.")


# ---------------------------------------------------------------- KI-Anbieter (Streaming)
class KIError(Exception):
    pass


class Abgebrochen(Exception):
    """Der Browser hat die Verbindung getrennt (Seite neu geladen, Fenster zu, Stopp gedrückt)."""


def fehler_log(text):
    """Schreibt eine Fehlermeldung ins Terminalfenster und in fehler.log (nur die Meldung, nie der Chat)."""
    zeile = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S") + "  " + re.sub(r"\s+", " ", str(text))[:400]
    print("! " + zeile, flush=True)
    with LOCK:
        try:
            alt = open(FEHLER_FILE, encoding="utf-8").read().splitlines()[-199:] if os.path.exists(FEHLER_FILE) else []
            with open(FEHLER_FILE, "w", encoding="utf-8") as f:
                f.write("\n".join(alt + [zeile]) + "\n")
        except OSError:
            pass


# ---------------------------------------------------------------- Cloud-Verlauf
# Welche früheren Nachrichten dürfen als Verlauf an eine Cloud-KI? Nur die, die schon einmal in der Cloud waren.
# Das entscheidet der Server, nicht der Browser: Er merkt sich von jeder Nachricht, die er selbst an eine Cloud-KI
# geschickt hat (und von deren Antwort), eine Prüfsumme. Alles andere aus dem Verlauf (lokale Ollama-Gespräche,
# von der Privat-Weiche umgeleitete Nachrichten, Befehle, die ohne KI erledigt wurden) bleibt draußen.
# Die Datei cloud_verlauf.json enthält nur diese Prüfsummen, keine Texte. Sie überlebt Neuladen und Neustart.
CLOUD_VERLAUF = {}
CLOUD_MAX = 4000


def _vk(role, text):
    r = "assistant" if role == "assistant" else "user"
    return hashlib.sha256((r + "\n" + str(text or "").strip()[:6000]).encode("utf-8")).hexdigest()[:32]


def cloud_verlauf_load():
    try:
        with open(CLOUD_VERLAUF_FILE, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, list):
            CLOUD_VERLAUF.clear()
            CLOUD_VERLAUF.update((str(k), True) for k in d[-CLOUD_MAX:])
    except (OSError, ValueError):
        pass


def cloud_merken(role, text):
    if not str(text or "").strip():
        return
    with LOCK:
        CLOUD_VERLAUF.pop(_vk(role, text), None)
        CLOUD_VERLAUF[_vk(role, text)] = True
        while len(CLOUD_VERLAUF) > CLOUD_MAX:
            CLOUD_VERLAUF.pop(next(iter(CLOUD_VERLAUF)))
        try:
            write_json(CLOUD_VERLAUF_FILE, list(CLOUD_VERLAUF), None)
        except OSError:
            pass


def fuer_cloud(msgs):
    """Nur die Nachrichten, die der Server selbst schon an eine Cloud-KI geschickt oder von ihr bekommen hat."""
    return [m for m in msgs if isinstance(m, dict) and _vk(m.get("role"), m.get("content")) in CLOUD_VERLAUF]


def clean_history(msgs, ohne_privat=False, n=20):
    """Bereitet den Verlauf für die KI auf. n = wie viele Nachrichten mitgehen (Sparmodus: weniger, ältere gekürzt)."""
    out = []
    for m in msgs or []:
        if ohne_privat and m.get("privat"):
            continue
        role = "assistant" if m.get("role") == "assistant" else "user"
        text = str(m.get("content") or "").strip()[:6000]
        if not text:
            continue
        if out and out[-1]["role"] == role:
            out[-1]["content"] += "\n" + text
        else:
            out.append({"role": role, "content": text})
    if len(out) > n:
        # In Stufen kürzen statt jede Runde eine Nachricht vorne abzuschneiden: So bleibt der Anfang des Verlaufs
        # mehrere Runden gleich und Claude kann ihn aus dem Zwischenspeicher lesen (deutlich billiger).
        stufe = max(2, n // 2)
        out = out[-(-(len(out) - n) // stufe) * stufe:]
    while out and out[0]["role"] != "user":
        out.pop(0)
    if n < 20:
        for m in out[:-1]:
            if len(m["content"]) > 1500:
                m["content"] = m["content"][:1500] + " …"
    return out


def stream_ollama(s, model, system, msgs, z):
    body = {"model": model, "stream": True, "messages": [{"role": "system", "content": system}] + msgs,
            "options": {"num_predict": s.get("_maxtok") or 900}}
    try:
        with http(s["ollama_url"] + "/api/chat", body, timeout=300) as r:
            for line in r:
                if not line.strip():
                    continue
                j = json.loads(line.decode("utf-8"))
                if j.get("error"):
                    raise KIError("Ollama: " + str(j["error"]))
                c = (j.get("message") or {}).get("content") or ""
                if c:
                    yield c
                if j.get("done"):
                    z["ein"], z["aus"] = j.get("prompt_eval_count") or 0, j.get("eval_count") or 0
                    break
    except urllib.error.HTTPError as e:
        msg = http_error_text(e)
        if e.code == 404 or "not found" in msg.lower():
            raise KIError(f"Das Modell '{model}' ist in Ollama nicht installiert. Im Terminal: ollama pull {model}")
        raise KIError("Ollama: " + msg)
    except urllib.error.URLError:
        raise KIError(f"Ollama ist nicht erreichbar ({s['ollama_url']}). Starte Ollama und versuch es nochmal.")


def _sse(r):
    for raw in r:
        line = raw.decode("utf-8", "replace").strip()
        if line.startswith("data:"):
            data = line[5:].strip()
            if data == "[DONE]":
                return
            try:
                yield json.loads(data)
            except ValueError:
                continue


def claude_cache(system, msgs):
    """Prompt-Caching: Der feste Teil des Systemprompts und der bisherige Verlauf werden bei Anthropic für 5 Minuten
    zwischengespeichert. Bei der nächsten Frage kostet dieser Teil nur noch einen Bruchteil (Lesen: 10 Prozent des
    Eingabepreises, bei manchen Modellen weniger). Das erste Speichern kostet 25 Prozent mehr. Zu kurze Texte speichert
    Anthropic nicht, dann kostet es nichts extra. Uhrzeit und gerade erledigte Befehle wechseln und stehen deshalb
    bei der aktuellen Frage, hinter dem gespeicherten Teil."""
    marke = {"type": "ephemeral"}
    sys_bl = [{"type": "text", "text": system.stabil, "cache_control": marke}]
    out = [dict(m) for m in msgs]
    letzte = out[-1]["content"]
    out[-1]["content"] = ([{"type": "text", "text": "[Hinweis vom Programm, nicht vom Nutzer]\n" + system.variabel}] if system.variabel else []) + \
        [{"type": "text", "text": letzte}]
    if len(out) >= 2:
        out[-2]["content"] = [{"type": "text", "text": out[-2]["content"], "cache_control": marke}]
    return sys_bl, out


def stream_claude(s, model, system, msgs, z, on_event):
    body = {"model": model, "max_tokens": s.get("_maxtok") or 1200, "system": system, "messages": msgs, "stream": True}
    if s.get("prompt_cache", True) and isinstance(system, Prompt) and msgs:
        body["system"], body["messages"] = claude_cache(system, msgs)
    if s.get("websuche"):
        body["tools"] = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}]
    hdr = {"x-api-key": s.get("claude_key", ""), "anthropic-version": "2023-06-01"}
    try:
        with http(ANTHROPIC + "/v1/messages", body, hdr, timeout=300) as r:
            had_text = False
            for ev in _sse(r):
                t = ev.get("type")
                us = (ev.get("message") or {}).get("usage") if t == "message_start" else ev.get("usage") if t == "message_delta" else None
                if us:                                   # Verbrauch, wie ihn Anthropic abrechnet
                    if us.get("input_tokens") is not None:
                        cw, cr = us.get("cache_creation_input_tokens") or 0, us.get("cache_read_input_tokens") or 0
                        z["ein"] = us["input_tokens"] + cw + cr          # gesamt, davon aus dem Zwischenspeicher:
                        z["cache_schreiben"], z["cache_lesen"] = cw, cr
                    if us.get("output_tokens") is not None:
                        z["aus"] = us["output_tokens"]
                    z["suchen"] = (us.get("server_tool_use") or {}).get("web_search_requests") or z.get("suchen", 0)
                if t == "content_block_start":
                    b = ev.get("content_block") or {}
                    if b.get("type") == "server_tool_use":
                        on_event({"typ": "suche", "text": "Websuche läuft"})
                    elif b.get("type") == "text" and had_text:
                        yield " "
                elif t == "content_block_delta":
                    d = ev.get("delta") or {}
                    if d.get("type") == "text_delta" and d.get("text"):
                        had_text = True
                        yield d["text"]
                elif t == "error":
                    raise KIError("Claude: " + str((ev.get("error") or {}).get("message", "Fehler")))
    except urllib.error.HTTPError as e:
        msg = http_error_text(e)
        if e.code == 401:
            msg = "Schlüssel ungültig. Bitte in den Einstellungen prüfen."
        elif e.code == 400 and "credit" in msg.lower():
            msg = "Kein Guthaben mehr auf dem Anthropic-Konto."
        elif e.code == 404:
            msg = f"Modell '{model}' nicht gefunden."
        elif e.code == 529:
            msg = "Claude ist gerade überlastet. Gleich nochmal versuchen."
        raise KIError("Claude: " + msg)
    except urllib.error.URLError:
        raise KIError("Claude ist nicht erreichbar. Besteht eine Internetverbindung?")


def stream_openai(s, model, system, msgs, z):
    base, key = s.get("openai_url", ""), s.get("openai_key", "")
    body = {"model": model, "stream": True, "messages": [{"role": "system", "content": system}] + msgs,
            "stream_options": {"include_usage": True}}          # der Anbieter soll den Verbrauch mitschicken
    # Obergrenze für die Antwortlänge, damit eine Antwort nicht beliebig teuer werden kann. OpenAI selbst will dafür
    # max_completion_tokens, und Denk-Modelle verbrauchen einen Teil davon fürs Nachdenken: dort mehr Spielraum.
    tok = s.get("_maxtok") or 1200
    if "api.openai.com" in base:
        body["max_completion_tokens"] = max(tok, 4000)
    else:
        body["max_tokens"] = tok
    hdr = {"Authorization": "Bearer " + key} if key else {}
    try:
        r = None
        while r is None:
            try:
                r = http(base + "/chat/completions", body, hdr, timeout=300)
            except urllib.error.HTTPError as e:     # manche Server kennen eine Option nicht: ohne sie nochmal
                weg = next((k for k in ("stream_options", "max_tokens", "max_completion_tokens") if k in body), None)
                if e.code != 400 or isinstance(e, Umweg) or not weg:
                    raise
                del body[weg]
        with r:
            for ev in _sse(r):
                if ev.get("error"):
                    raise KIError("API: " + str(ev["error"].get("message") if isinstance(ev["error"], dict) else ev["error"]))
                if ev.get("usage"):
                    z["ein"], z["aus"] = ev["usage"].get("prompt_tokens") or 0, ev["usage"].get("completion_tokens") or 0
                ch = (ev.get("choices") or [{}])[0]
                c = (ch.get("delta") or {}).get("content")
                if c:
                    yield c
    except urllib.error.HTTPError as e:
        msg = http_error_text(e)
        if e.code == 401:
            msg = "Schlüssel ungültig. Bitte in den Einstellungen prüfen."
        elif e.code == 429:
            msg = "Limit erreicht oder kein Guthaben (429)."
        raise KIError("API: " + msg)
    except urllib.error.URLError:
        raise KIError(f"API nicht erreichbar ({base}).")


class TagFilter:
    """Entfernt <think>...</think>, [merken: ...], [bot: ...], [suche: ...] und [pc: ...] aus dem Strom und sammelt sie."""

    def __init__(self):
        self.buf, self.think, self.merk, self.bots, self.pc, self.suche = "", False, [], [], [], []

    def feed(self, text, final=False):
        self.buf += text
        out = []
        while self.buf:
            if self.think:
                j = self.buf.find("</think>")
                if j < 0:
                    self.buf = self.buf[-8:] if not final else ""
                    break
                self.buf, self.think = self.buf[j + 8:], False
                continue
            i1, i2 = self.buf.find("<think>"), self.buf.find("[")
            cand = [i for i in (i1, i2) if i >= 0]
            if not cand:
                hold = 0
                if not final:
                    for k in range(min(6, len(self.buf)), 0, -1):
                        if "<think>".startswith(self.buf[-k:]):
                            hold = k
                            break
                out.append(self.buf[:len(self.buf) - hold])
                self.buf = self.buf[len(self.buf) - hold:]
                break
            i = min(cand)
            out.append(self.buf[:i])
            self.buf = self.buf[i:]
            if self.buf.startswith("<think>"):
                self.buf, self.think = self.buf[7:], True
                continue
            low = self.buf[:4].lower()
            if not final and len(low) < 4 and "[pc:".startswith(low):
                break                                   # könnte noch ein [pc: ...] werden
            if low == "[pc:":                           # PC-Aktion: steht am Ende der Antwort, darf lang sein und Klammern enthalten
                if not final and len(self.buf) < 12000:
                    break                               # bis zum Ende der Antwort sammeln
                j = self.buf.rfind("]")
                roh = self.buf[4:j] if j > 4 else self.buf[4:]
                self.buf = ""
                teile = [t.strip() for t in roh.split("|", 2)]
                if teile and teile[0]:
                    self.pc.append(teile + [""] * (3 - len(teile)))
                continue
            j = self.buf.find("]")
            if j < 0:
                if final or len(self.buf) > 300:
                    out.append(self.buf)
                    self.buf = ""
                break
            tag, self.buf = self.buf[:j + 1], self.buf[j + 1:]
            m = re.match(r"\[\s*merken\s*:\s*(.+?)\s*\]$", tag, re.I | re.S)
            mb = re.match(r"\[\s*bot\s*:\s*([^|\]]+?)\s*\|\s*(.+?)\s*\]$", tag, re.I | re.S)
            ms = re.match(r"\[\s*suche\s*:\s*(.+?)\s*\]$", tag, re.I | re.S)
            if m:
                self.merk.append(m.group(1))
            elif ms:
                self.suche.append(ms.group(1)[:200])
            elif mb:
                self.bots.append((mb.group(1), mb.group(2)))
            else:
                out.append(tag)
        return "".join(out)


# ---------------------------------------------------------------- PC-Steuerung
# Standardmäßig AUS. Jarvis darf nur, was in den Einstellungen freigegeben ist:
#   - Ordner ansehen, Textdateien lesen, Dateien öffnen: nur in freigegebenen Ordnern
#   - Textdateien anlegen/ändern: nur mit eigenem Schalter
#   - Programme starten: nur aus der Liste, ohne eigene Parameter
# Es gibt bewusst KEIN Löschen, KEIN Verschieben und KEINE freien Befehle (Kommandozeile).
PC_LESBAR = {".txt", ".md", ".csv", ".json", ".log", ".ini", ".cfg", ".yaml", ".yml", ".xml", ".html", ".htm", ".css", ".js",
             ".py", ".bat", ".ps1", ".sh", ".srt", ".tex", ".rtf", ".toml", ".sql", ".c", ".cpp", ".h", ".cs", ".java", ".ts"}
PC_SCHREIBBAR = {".txt", ".md", ".csv", ".json", ".log", ".html", ".htm", ".srt", ".xml", ".yaml", ".yml", ".css", ".ini", ".cfg", ".toml",
                 ".tex", ".sql", ".py", ".js", ".ts", ".sh", ".bat", ".ps1", ".c", ".cpp", ".h", ".cs", ".java"}
# Öffnen heißt bei Skripten Ausführen. Deshalb steht hier eine eigene Liste ohne .py, .bat, .ps1, .sh und .js:
# Jarvis darf Skripte schreiben und lesen, starten muss sie der Nutzer selbst.
PC_OEFFNBAR = {".txt", ".md", ".csv", ".json", ".log", ".html", ".htm", ".srt", ".xml", ".yaml", ".yml", ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".odt", ".ods", ".odp", ".png", ".jpg",
                               ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".mp3", ".wav", ".flac", ".ogg", ".mp4", ".mkv", ".mov",
                               ".avi", ".webm", ".epub", ".ini", ".cfg", ".rtf"}
PC_SKRIPT = {".py", ".js", ".ts", ".sh", ".bat", ".ps1"}     # ausführbarer Code: wird nie ohne Nachfrage geschrieben
PC_LOG = []
PC_WARTEN = {}


class PCError(Exception):
    pass


def _nk(p):
    return os.path.normcase(os.path.realpath(os.path.expanduser(p)))


def pc_pfad(s, ziel, muss_existieren=True):
    """Macht aus 'Dokumente/notiz.txt' oder einem vollen Pfad einen echten Pfad und prüft, dass er in einem
    freigegebenen Ordner liegt (auch nach Auflösen von '..' und Verknüpfungen)."""
    ziel = str(ziel or "").strip().strip('"').strip("'")
    ordner = [o for o in s.get("pc_ordner") or [] if o.get("pfad")]
    if not ordner:
        raise PCError("Es ist noch kein Ordner freigegeben (Einstellungen, PC-Steuerung).")
    if not ziel:
        raise PCError("Kein Pfad angegeben.")
    kand = []
    if os.path.isabs(os.path.expanduser(ziel)):
        kand.append(os.path.expanduser(ziel))
    else:
        teile = re.split(r"[\\/]+", ziel, maxsplit=1)
        for o in sorted(ordner, key=lambda x: -len(x["name"])):
            if teile[0].lower() in (o["name"].lower(), os.path.basename(o["pfad"].rstrip("/\\")).lower()):
                kand.append(os.path.join(os.path.expanduser(o["pfad"]), teile[1] if len(teile) > 1 else ""))
        if not kand:
            kand = [os.path.join(os.path.expanduser(o["pfad"]), ziel) for o in ordner]
    wurzeln = [_nk(o["pfad"]) for o in ordner]
    erlaubt = [k for k in kand if any(_nk(k) == w or _nk(k).startswith(w.rstrip(os.sep) + os.sep) for w in wurzeln)]
    if not erlaubt:
        raise PCError(f"'{ziel}' liegt in keinem freigegebenen Ordner. Freigegeben: " + ", ".join(o["name"] for o in ordner))
    for k in erlaubt:
        if os.path.exists(k):
            return os.path.realpath(k)
    if muss_existieren:
        raise PCError(f"'{ziel}' wurde nicht gefunden.")
    return os.path.realpath(erlaubt[0])


def _groesse(n):
    for e in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {e}"
        n /= 1024
    return f"{n:.1f} TB"


def _oeffnen(pfad):
    """Öffnet Datei, Ordner oder Programm so, als hätte der Nutzer es doppelt angeklickt."""
    if os.name == "nt":
        os.startfile(pfad)                                              # noqa: nur Windows
    elif sys.platform == "darwin":
        subprocess.Popen(["open", pfad])
    else:
        subprocess.Popen(["xdg-open", pfad], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def pc_text(aktion, ziel):
    return {"liste": "Ordner ansehen: ", "lesen": "Datei lesen: ", "schreiben": "Datei schreiben: ", "programm": "Programm starten: ",
            "ordner": "Ordner im Dateimanager öffnen: ", "datei": "Datei öffnen: "}.get(aktion, aktion + ": ") + ziel


def pc_ausfuehren(s, aktion, ziel, inhalt=""):
    """Führt genau eine geprüfte Aktion aus. Liefert (kurztext_für_nutzer, ergebnis_für_die_ki)."""
    aktion = aktion.lower().strip()
    if aktion == "programm":
        progs = s.get("pc_programme") or []
        pr = next((x for x in progs if x["name"].lower() == ziel.lower()), None) or \
            next((x for x in progs if ziel.lower() in x["name"].lower()), None)
        if not pr:
            raise PCError(f"Das Programm '{ziel}' ist nicht freigegeben. Freigegeben: " + (", ".join(x["name"] for x in progs) or "keines"))
        pfad = os.path.expanduser(pr["pfad"])
        try:
            if os.name == "nt":
                _oeffnen(pfad)
            elif sys.platform == "darwin" and (pfad.endswith(".app") or os.sep not in pfad):
                subprocess.Popen(["open", "-a", pfad])
            else:
                subprocess.Popen([pfad], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as e:
            raise PCError(f"'{pr['name']}' konnte nicht gestartet werden: {e.strerror or e}")
        return f"{pr['name']} gestartet", f"Das Programm {pr['name']} wurde gestartet."
    if aktion == "ordner":
        p = pc_pfad(s, ziel)
        if not os.path.isdir(p):
            p = os.path.dirname(p)
        _oeffnen(p)
        return "Ordner geöffnet", f"Der Ordner {p} wurde im Dateimanager geöffnet."
    if aktion == "liste":
        p = pc_pfad(s, ziel)
        if not os.path.isdir(p):
            raise PCError(f"'{ziel}' ist kein Ordner.")
        zeilen = []
        with os.scandir(p) as it:
            for e in sorted(it, key=lambda x: (not x.is_dir(), x.name.lower())):
                if e.name.startswith(".") or len(zeilen) >= 200:
                    continue
                try:
                    zeilen.append(f"[Ordner] {e.name}" if e.is_dir() else
                                  f"{e.name} ({_groesse(e.stat().st_size)}, {datetime.date.fromtimestamp(e.stat().st_mtime):%d.%m.%Y})")
                except OSError:
                    pass
        return f"{len(zeilen)} Einträge", f"Inhalt von {p}:\n" + ("\n".join(zeilen) or "(leer)")
    if aktion == "lesen":
        p = pc_pfad(s, ziel)
        if os.path.isdir(p):
            raise PCError(f"'{ziel}' ist ein Ordner. Nimm dafür die Aktion liste.")
        if os.path.splitext(p)[1].lower() not in PC_LESBAR:
            raise PCError("Diesen Dateityp kann ich nicht lesen (nur Textdateien wie txt, md, csv, json). Ich kann die Datei aber öffnen.")
        if os.path.getsize(p) > 400_000:
            raise PCError("Die Datei ist zu groß zum Vorlesen (mehr als 400 KB).")
        with open(p, "rb") as f:
            roh = f.read()
        try:
            txt = roh.decode("utf-8")
        except UnicodeDecodeError:
            txt = roh.decode("cp1252", "replace")
        return f"{len(txt)} Zeichen gelesen", f"Inhalt der Datei {p}:\n" + txt[:20000] + ("\n[... gekürzt]" if len(txt) > 20000 else "")
    if aktion == "schreiben":
        if not s.get("pc_schreiben"):
            raise PCError("Schreiben ist in den Einstellungen nicht erlaubt (PC-Steuerung, Dateien anlegen und ändern).")
        p = pc_pfad(s, ziel, muss_existieren=False)
        if os.path.splitext(p)[1].lower() not in PC_SCHREIBBAR:
            raise PCError("Ich darf nur Textdateien schreiben: " + ", ".join(sorted(PC_SCHREIBBAR)))
        if os.path.isdir(p) or not os.path.isdir(os.path.dirname(p)):
            raise PCError("Der Zielordner existiert nicht. Neue Ordner lege ich nicht an.")
        gab = os.path.exists(p)
        if gab:                                                         # alte Fassung nie verlieren
            shutil.copy2(p, p + ".bak")
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(pc_inhalt(inhalt))
        return ("Datei geändert (alte Fassung als .bak gesichert)" if gab else "Datei angelegt"), \
            f"Die Datei {p} wurde {'überschrieben, die alte Fassung liegt daneben als .bak' if gab else 'neu angelegt'}."
    if aktion == "datei":
        p = pc_pfad(s, ziel)
        if os.path.isdir(p):
            _oeffnen(p)
            return "Ordner geöffnet", f"{p} wurde geöffnet."
        if os.path.splitext(p)[1].lower() not in PC_OEFFNBAR:
            raise PCError("Diesen Dateityp öffne ich aus Sicherheitsgründen nicht (keine Programme, Skripte oder Verknüpfungen).")
        _oeffnen(p)
        return "Datei geöffnet", f"Die Datei {p} wurde mit dem Standardprogramm geöffnet."
    raise PCError(f"Unbekannte Aktion '{aktion}'. Möglich: liste, lesen, schreiben, programm, ordner, datei.")


def pc_inhalt(inhalt):
    """Genau der Text, der in die Datei geschrieben wird (manche Modelle schreiben Zeilenumbrüche als \\n)."""
    return inhalt.replace("\\n", "\n") if "\n" not in inhalt else inhalt


def pc_aktion(s, aktion, ziel, inhalt, emit, cloud):
    """Prüft Freigaben, fragt bei Bedarf nach, führt aus, protokolliert. Liefert den Text für die KI."""
    aktion = (aktion or "").lower().strip()
    ziel = (ziel or "").strip()
    eintrag = {"zeit": datetime.datetime.now().strftime("%d.%m. %H:%M:%S"), "aktion": aktion, "ziel": ziel[:200], "ok": False, "info": ""}
    try:
        if not s.get("pc_an"):
            raise PCError("Die PC-Steuerung ist ausgeschaltet (Einstellungen, PC-Steuerung).")
        if cloud and aktion in ("liste", "lesen") and not s.get("pc_cloud"):
            raise PCError("Ordnerlisten und Datei-Inhalte gebe ich nicht an eine Cloud-KI. Das lässt sich in den Einstellungen unter "
                          "PC-Steuerung erlauben, oder du wechselst auf eine lokale KI. Öffnen kann ich die Datei trotzdem.")
        skript = aktion == "schreiben" and os.path.splitext(ziel)[1].lower() in PC_SKRIPT
        if s.get("pc_nachfragen") or skript:             # Skripte immer erst zeigen, auch wenn das Nachfragen aus ist
            fid, ev = uuid.uuid4().hex[:10], threading.Event()
            PC_WARTEN[fid] = [ev, False]
            emit({"t": "action", "typ": "pc_frage", "id": fid, "aktion": aktion, "text": pc_text(aktion, ziel),
                  "vorschau": pc_inhalt(inhalt) if aktion == "schreiben" else ""})     # vollständig: freigegeben wird, was man sieht
            ev.wait(90)
            ja = PC_WARTEN.pop(fid, [None, False])[1]
            if not ja:
                raise PCError("Der Nutzer hat die Aktion nicht erlaubt.")
        kurz, lang = pc_ausfuehren(s, aktion, ziel, inhalt)
        eintrag.update(ok=True, info=kurz)
        emit({"t": "action", "typ": "pc", "ok": True, "aktion": aktion, "text": pc_text(aktion, ziel), "info": kurz})
        if aktion in ("liste", "lesen"):
            return "ERFOLGREICH. " + lang
        # Eindeutig formuliert: Sonst hielten manche Modelle die Rückmeldung für einen Fehler und lösten dieselbe Aktion
        # immer wieder aus, bis das Limit griff (Meldung aus der Community).
        return f"ERFOLGREICH ERLEDIGT. {lang} Diese Aktion ist abgeschlossen und darf nicht wiederholt werden."
    except PCError as e:
        eintrag["info"] = str(e)
        emit({"t": "action", "typ": "pc", "ok": False, "aktion": aktion, "text": pc_text(aktion, ziel), "info": str(e)})
        return "NICHT AUSGEFÜHRT: " + str(e)
    except OSError as e:
        eintrag["info"] = str(e.strerror or e)
        emit({"t": "action", "typ": "pc", "ok": False, "aktion": aktion, "text": pc_text(aktion, ziel), "info": eintrag["info"]})
        return "NICHT AUSGEFÜHRT: " + eintrag["info"]
    finally:
        PC_LOG.append(eintrag)
        del PC_LOG[:-60]


def pc_prompt(s):
    o = s.get("pc_ordner") or []
    pr = s.get("pc_programme") or []
    akt = ["[pc: liste | Ordner/Unterordner]   zeigt, was in einem Ordner liegt",
           "[pc: lesen | Ordner/datei.txt]      liest eine Textdatei",
           "[pc: datei | Ordner/datei.pdf]      öffnet eine Datei am Bildschirm",
           "[pc: ordner | Ordner]               öffnet den Ordner im Dateimanager",
           "[pc: programm | Name]               startet ein freigegebenes Programm"]
    if s.get("pc_schreiben"):
        akt.append("[pc: schreiben | Ordner/datei.txt | vollständiger Inhalt]   legt eine Textdatei oder ein Skript (z. B. .py, .bat, .html) an oder ersetzt es")
    return ("PC-STEUERUNG ist aktiv. Freigegebene Ordner: " + (", ".join(x["name"] for x in o) or "keine") +
            ". Freigegebene Programme: " + (", ".join(x["name"] for x in pr) or "keine") + ".\n"
            "Um etwas am PC zu tun, schreibe als LETZTE Zeile deiner Antwort genau eine Aktion in dieser Form:\n" + "\n".join(akt) +
            "\nDanach bekommst du das Ergebnis und antwortest dem Nutzer. Pfade beginnen immer mit dem Namen eines freigegebenen "
            "Ordners. Du kannst nichts löschen, nichts verschieben und keine Befehle ausführen. Behaupte nie, etwas getan zu haben, "
            "bevor das Ergebnis da ist. Steht im Ergebnis ERFOLGREICH, ist die Aktion erledigt: nicht wiederholen. Steht im Ergebnis "
            "NICHT AUSGEFÜHRT, sag ehrlich, warum.")


PC_PROG_RE = re.compile(r"\b(?:starte|start|öffne|oeffne|mach)\s+(?:mal\s+|bitte\s+)?(?:das\s+programm\s+|die\s+app\s+|den\s+|die\s+|das\s+)?(.+?)(?:\s+auf)?[\s.!]*$")
PC_ORD_RE = re.compile(r"\b(?:öffne|oeffne|zeig|zeige)\s+(?:mir\s+)?(?:mal\s+|bitte\s+)?(?:den\s+|meinen\s+)?ordner\s+(.+?)[\s.!?]*$")
PC_LISTE_RE = re.compile(r"\b(?:was\s+(?:ist|liegt|steht|befindet\s+sich)|welche\s+dateien\s+(?:sind|liegen))\s+(?:alles\s+)?(?:im|in\s+meinem|in\s+dem)\s+(?:ordner\s+)?(.+?)[\s.!?]*$")


def pc_befehl(u, s):
    """Feste Sprachbefehle, die mit JEDEM Modell funktionieren. Liefert (aktion, ziel) oder None."""
    if not s.get("pc_an"):
        return None
    namen = {o["name"].lower(): o["name"] for o in s.get("pc_ordner") or []}
    m = PC_ORD_RE.search(u)
    if m and m.group(1).strip() in namen:
        return "ordner", namen[m.group(1).strip()]
    m = PC_LISTE_RE.search(u)
    if m and m.group(1).strip() in namen:
        return "liste", namen[m.group(1).strip()]
    m = PC_PROG_RE.search(u)
    if m:
        z = m.group(1).strip()
        for pr in s.get("pc_programme") or []:
            if pr["name"].lower() == z:
                return "programm", pr["name"]
    return None


def pc_waehlen(art):
    """Öffnet auf dem PC den normalen Auswahl-Dialog (Ordner oder Programm) und liefert den Pfad."""
    code = ("import tkinter as tk\nfrom tkinter import filedialog\nr=tk.Tk()\nr.withdraw()\nr.attributes('-topmost',True)\n" +
            ("p=filedialog.askdirectory(title='Ordner für Jarvis freigeben')" if art == "ordner" else
             "p=filedialog.askopenfilename(title='Programm für Jarvis freigeben')") + "\nprint(p or '')")
    try:
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired):
        return {"ok": False, "fehler": "Der Auswahl-Dialog ließ sich nicht öffnen. Bitte den Pfad eintippen."}
    if r.returncode != 0:
        return {"ok": False, "fehler": "Der Auswahl-Dialog ist auf diesem System nicht verfügbar. Bitte den Pfad eintippen."}
    pfad = r.stdout.strip()
    return {"ok": bool(pfad), "pfad": os.path.normpath(pfad) if pfad else "", "fehler": "" if pfad else "Nichts ausgewählt."}


# ---------------------------------------------------------------- Bots (Team)
def ki_stream(s, anbieter, model, system, msgs, on_event):
    """Fragt die KI und liefert die Antwort stückweise. Zählt dabei den Verbrauch und hält das Kostenlimit ein."""
    cloud = ist_cloud(s, anbieter)
    if cloud and s.get("strikt_lokal"):             # letzte Sicherung, falls ein Weg die Weiche oben umgeht
        raise KIError(STRIKT_SPERRE)
    if cloud:
        sperre = kosten_sperre(s, anbieter, model)
        if sperre:
            raise KIError(sperre)
    z, zeichen = {}, 0
    try:
        if anbieter == "ollama":
            gen = stream_ollama(s, model, system, msgs, z)
        elif anbieter == "claude":
            gen = stream_claude(s, model, system, msgs, z, on_event)
        else:
            gen = stream_openai(s, model, system, msgs, z)
        for chunk in gen:
            zeichen += len(chunk)
            yield chunk
    finally:
        if not z.get("ein") and not z.get("aus"):                # kein Verbrauch gemeldet: grob schätzen (3,5 Zeichen je Token)
            z.update(ein=int((len(system) + sum(len(m["content"]) for m in msgs)) / 3.5), aus=int(zeichen / 3.5), geschaetzt=True)
        kosten_buchen(s, anbieter, model, z, cloud)


# ---------------------------------------------------------------- Kosten
# Listenpreise der Claude-API in US-Dollar je 1 Million Token (Eingabe, Ausgabe).
# Quelle: https://platform.claude.com/docs/en/about-claude/pricing · Stand siehe PREISE_STAND.
# Preise ändern sich. Eigene oder neuere Preise trägt man in den Einstellungen ein, sie gehen vor.
PREISE_STAND = "13.11.2026"
# Listenpreise in US-Dollar je 1 Mio. Token (Eingabe, Ausgabe), Stand 14.11.2026, platform.claude.com/docs/en/about-claude/pricing.
# Der erste passende Namensteil gewinnt, deshalb stehen die genaueren Namen vorn. Haiku 5.5 kostet ab 100.000 Token
# Eingabe je Anfrage mehr (0,50 / 2,50); bei Jarvis kommt das praktisch nicht vor.
PREISE = [("fable-5-2", 8, 40), ("mythos-5-2", 8, 40), ("fable-5", 10, 50), ("mythos-5", 10, 50),
          ("opus-5-5", 4, 20), ("opus-5", 5, 25), ("opus-4-8", 5, 25), ("opus-4-7", 5, 25), ("opus-4-6", 5, 25), ("opus-4-5", 5, 25),
          ("opus-4", 15, 75), ("sonnet-5", 2, 10), ("sonnet-4", 3, 15), ("haiku-5-5", 0.10, 0.50), ("haiku-4-5", 1, 5)]
SUCHE_USD = 0.01                     # Claude-Websuche: 10 US-Dollar je 1000 Suchen
KOSTEN = {"tage": {}, "ab": "", "seitdem": 0.0}


def kosten_load():
    try:
        with open(KOSTEN_FILE, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict) and isinstance(d.get("tage"), dict):
            KOSTEN.update(tage=d["tage"], ab=str(d.get("ab") or ""), seitdem=float(d.get("seitdem") or 0))
    except (OSError, ValueError, TypeError):
        pass


def kosten_save():
    for tag in sorted(KOSTEN["tage"])[:-400]:                    # gut ein Jahr reicht
        del KOSTEN["tage"][tag]
    try:
        write_json(KOSTEN_FILE, KOSTEN, 1)
    except OSError:
        pass


def kosten_stichtag():
    """Der Nutzer hat ein neues Guthaben eingetragen: Ab jetzt wird der Verbrauch davon abgezogen."""
    KOSTEN.update(ab=datetime.datetime.now().strftime("%d.%m.%Y %H:%M"), seitdem=0.0)
    kosten_save()


def preis(s, anbieter, model):
    """Preis je 1 Mio. Token als (Eingabe, Ausgabe) oder None, wenn unbekannt. Eigene Preise gehen vor."""
    name = (model or "").lower().replace(".", "-")
    for zeile in (s.get("kosten_preise") or "").splitlines():
        m = re.match(r"\s*([^=]+?)\s*=\s*([\d.,]+)\s*/\s*([\d.,]+)", zeile)
        if m and m.group(1).lower().replace(".", "-") in name:
            try:
                return float(m.group(2).replace(",", ".")), float(m.group(3).replace(",", "."))
            except ValueError:
                continue
    if anbieter == "claude":
        for teil, ein, aus in PREISE:
            if teil in name:
                return ein, aus
    return None


def cache_faktor(model):
    """Preis für gelesene Zwischenspeicher-Token im Verhältnis zum Eingabepreis (Stand siehe PREISE_STAND).
    Quelle: platform.claude.com/docs/en/build-with-claude/prompt-caching. Schreiben kostet das 1,25-Fache."""
    name = (model or "").lower().replace(".", "-")
    if any(t in name for t in ("fable-5-2", "mythos-5-2", "fable-5-1", "mythos-5-1")):
        return 0.025
    if any(t in name for t in ("opus-5-5", "sonnet-5-5")):
        return 0.05
    return 0.1


def kosten_buchen(s, anbieter, model, z, cloud):
    ein, aus, suchen = int(z.get("ein") or 0), int(z.get("aus") or 0), int(z.get("suchen") or 0)
    cw, cr = int(z.get("cache_schreiben") or 0), int(z.get("cache_lesen") or 0)    # in "ein" enthalten
    if not ein and not aus:
        return
    pr = preis(s, anbieter, model) if cloud else (0, 0)
    if pr:
        normal = max(0, ein - cw - cr)
        usd = (normal * pr[0] + cw * pr[0] * 1.25 + cr * pr[0] * cache_faktor(model) + aus * pr[1]) / 1e6 + suchen * SUCHE_USD
    else:
        usd = 0.0
    with LOCK:
        tag = KOSTEN["tage"].setdefault(datetime.date.today().isoformat(), {})
        e = tag.setdefault(f"{anbieter}|{model}", {"ein": 0, "aus": 0, "anfragen": 0, "suchen": 0, "usd": 0.0})
        e["ein"] += ein
        e["aus"] += aus
        e["anfragen"] += 1
        e["suchen"] += suchen
        if cr:
            e["cache"] = e.get("cache", 0) + cr
        e["usd"] = round(e["usd"] + usd, 6)
        e["lokal"] = not cloud
        if z.get("geschaetzt"):
            e["geschaetzt"] = True
        if cloud and not pr:
            e["ohne_preis"] = True
        KOSTEN["seitdem"] = round(KOSTEN["seitdem"] + usd, 6)
        kosten_save()


def kosten_stand(s):
    """Zahlen für das Kosten-Widget: heute, dieser Monat, Limit, Guthaben."""
    heute, monat = datetime.date.today().isoformat(), datetime.date.today().strftime("%Y-%m")
    leer = lambda: {"ein": 0, "aus": 0, "anfragen": 0, "suchen": 0, "usd": 0.0}
    h, m, lokal, modelle, ohne, gesch = leer(), leer(), leer(), {}, set(), False
    with LOCK:
        for tag, eintraege in KOSTEN["tage"].items():
            if not tag.startswith(monat):
                continue
            for name, e in eintraege.items():
                ziel = [lokal] if e.get("lokal") else [m] + ([h] if tag == heute else [])
                for zl in ziel:
                    for k in zl:
                        zl[k] += e.get(k, 0)
                if not e.get("lokal"):
                    mo = modelle.setdefault(name.split("|", 1)[-1], leer())
                    for k in mo:
                        mo[k] += e.get(k, 0)
                    gesch = gesch or bool(e.get("geschaetzt"))
                    if e.get("ohne_preis"):
                        ohne.add(name.split("|", 1)[-1])
        seitdem, ab = KOSTEN["seitdem"], KOSTEN["ab"]
    limit, gut = float(s.get("kosten_limit") or 0), float(s.get("kosten_guthaben") or 0)
    return {"heute": h, "monat": m, "lokal": lokal, "limit": limit, "guthaben": gut, "ab": ab,
            "rest": round(gut - seitdem, 4) if gut else None, "seitdem": round(seitdem, 4),
            "modelle": sorted(({"name": k, **v} for k, v in modelle.items()), key=lambda x: -x["usd"])[:6],
            "ohne_preis": sorted(ohne), "geschaetzt": gesch, "preise_stand": PREISE_STAND,
            "gesperrt": bool(limit and m["usd"] >= limit)}


def kosten_sperre(s, anbieter="", model=""):
    limit = float(s.get("kosten_limit") or 0)
    if not limit:
        return ""
    if anbieter and preis(s, anbieter, model) is None:     # ohne Preis würde mit 0 gebucht und das Limit nie erreicht
        return (f"Kostenlimit ist gesetzt, für das Modell {model} kennt Jarvis aber keinen Preis. So könnte das Limit nicht "
                "greifen, deshalb habe ich nichts gesendet. Trag den Preis unter KI & Modelle, Eigene Preise ein "
                "(zum Beispiel: modellname = 1.25 / 10) oder setze das Limit auf 0.")
    monat = datetime.date.today().strftime("%Y-%m")
    with LOCK:
        usd = sum(e.get("usd", 0) for tag, es in KOSTEN["tage"].items() if tag.startswith(monat) for e in es.values() if not e.get("lokal"))
    if usd >= limit:
        return (f"Kostenlimit erreicht: Diesen Monat sind rund {usd:.2f} US-Dollar für Cloud-KI angefallen, dein Limit liegt bei "
                f"{limit:.2f}. Ich habe nichts gesendet. Erhöhe das Limit in den Einstellungen unter KI & Modelle oder nutze Ollama.")
    return ""


def bot_settings(s, bot):
    """Einstellungen von Jarvis, überlagert mit Anbieter, Modell, Schlüssel und Adresse des Bots."""
    b = dict(s)
    if bot.get("anbieter") in ("ollama", "claude", "openai"):
        b["anbieter"], b["modell"] = bot["anbieter"], bot.get("modell") or ""
    elif bot.get("modell"):
        b["modell"] = bot["modell"]
    a = b["anbieter"]
    if bot.get("api_url") and a in ("ollama", "openai"):
        if a == "openai" and bot["api_url"] != s.get("openai_url"):
            b["openai_key"] = ""         # eigene Adresse: Jarvis' Schlüssel bleibt zu Hause, der Bot braucht seinen eigenen
        b[a + "_url"] = bot["api_url"]
    if bot.get("api_key") and a in ("claude", "openai"):
        b[a + "_key"] = bot["api_key"]
    b["_maxtok"] = 2500                  # Bots dürfen ausführlich arbeiten
    b["websuche"] = bool(bot.get("websuche"))
    return b


def bot_ist_cloud(s, bot):
    """Würde dieser Bot ins Internet schicken? (ohne Privat-Weiche, nur nach Anbieter und Adresse)"""
    bs = bot_settings(s, bot)
    return ist_cloud(bs, bs["anbieter"]) and not s.get("strikt_lokal")


def bot_ziel(s, bot, text, erzwingen=False, privat=False):
    """Wohin geht die Aufgabe des Bots? Liefert (einstellungen, anbieter, modell, gruende, fehler).
    Für Bots gelten dieselben Datenschutz-Regeln wie für Jarvis."""
    bs = bot_settings(s, bot)
    a, m = pick_model(bs)
    gruende = []
    if ist_cloud(bs, a):
        lokal = bool(s.get("strikt_lokal")) or privat
        if not lokal and s.get("privat_weiche") and not erzwingen:
            gruende = privat_erkennen(text, s)
            lokal = bool(gruende)
        if lokal:
            lm = lokales_modell(s)
            if not lm:
                return bs, a, "", gruende, ("Der Bot " + bot["name"] + " nutzt eine Cloud-KI, die Nachricht darf den PC aber nicht "
                                            "verlassen, und die lokale KI (Ollama) ist nicht erreichbar. Es wurde nichts gesendet.")
            bs = dict(s, websuche=False)
            a, m = "ollama", lm
    if not m:
        return bs, a, "", gruende, f"Der Bot {bot['name']} hat kein nutzbares Modell. Bitte in den Einstellungen unter Bots prüfen."
    return bs, a, m, gruende, ""


def bot_finden(text, s):
    """Erkennt, ob ein Bot gemeint ist: @Name, 'Name, ...', 'frag Name ...' oder ein Stichwort. Liefert (bot, text)."""
    bots = [b for b in s.get("bots") or [] if b.get("aktiv")]
    low = text.lower()
    for b in sorted(bots, key=lambda x: -len(x["name"])):
        n = re.escape(b["name"].lower())
        m = re.search(r"@" + n + r"(?![\wäöüß])[\s,:]*", low)
        if m:
            return b, (text[:m.start()] + text[m.end():]).strip() or text
        m = re.match(r"\s*(?:hey |hallo )?" + n + r"\s*[,:]\s*", low)
        if m:
            return b, text[m.end():].strip() or text
        m = re.match(r"\s*(?:frag|frage|bitte|sag|lass)\s+(?:mal\s+)?(?:den|dem|die|der|das)?\s*(?:bot\s+)?" + n + r"(?![\wäöüß])[\s,:]*", low)
        if m:
            return b, text[m.end():].strip() or text
    for b in bots:
        for w in re.split(r"[,;\n]+", b.get("stichwoerter") or ""):
            w = w.strip().lower()
            if len(w) >= 3 and re.search(r"(?<![\wäöüß])" + re.escape(w) + r"(?![\wäöüß])", low):
                return b, text
    return None, text


BOT_STATS = {}


def botstat_load():
    try:
        with open(BOTSTAT_FILE, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict):
            BOT_STATS.update({k: v for k, v in d.items() if isinstance(v, dict)})
    except (OSError, ValueError):
        pass


def botstat(bid, eintrag=None, **kw):
    with LOCK:
        st = BOT_STATS.setdefault(bid, {"anzahl": 0, "zuletzt": "", "aufgabe": "", "dauer": 0, "modell": "", "fehler": "", "verlauf": []})
        st.update(kw)
        if eintrag and load_settings().get("bot_verlauf", True):
            st.setdefault("verlauf", []).append(eintrag)
            del st["verlauf"][:-8]
        try:
            write_json(BOTSTAT_FILE, BOT_STATS, 1)
        except OSError:
            pass


def bot_lauf(s, bot, aufgabe, msgs, emit, strom=True, erzwingen=False, privat=False, wie=""):
    """Lässt einen Bot arbeiten. strom=True: Antwort geht direkt an den Nutzer. Liefert den Text oder None bei Fehler."""
    bs, a, m, gruende, fehler = bot_ziel(s, bot, aufgabe, erzwingen, privat)
    if fehler:
        if gruende and strom:
            emit({"t": "privat", "weiter": "blockiert", "gruende": gruende, "message": fehler})
        elif strom:
            emit({"t": "error", "message": fehler})
        botstat(bot["id"], fehler=fehler)
        return None
    if gruende and strom:
        emit({"t": "privat", "weiter": "lokal", "gruende": gruende, "modell": m})
    cloud = ist_cloud(bs, a)
    emit({"t": "bot", "phase": "start", "id": bot["id"], "name": bot["name"], "aufgabe": aufgabe[:200], "anbieter": a,
          "modell": m, "cloud": cloud, "wie": wie})
    if strom:
        emit({"t": "model", "anbieter": a, "modell": m, "cloud": cloud})
    t0, tf, full, err = time.time(), TagFilter(), [], ""
    try:
        for chunk in ki_stream(bs, a, m, bot_prompt(bs, bot, a == "claude" and bs.get("websuche")), msgs,
                               lambda e: emit({"t": "action", **e})):
            out = tf.feed(chunk)
            if out:
                full.append(out)
                if strom:
                    emit({"t": "delta", "text": out})
        out = tf.feed("", final=True)
        if out:
            full.append(out)
            if strom:
                emit({"t": "delta", "text": out})
    except Abgebrochen:
        raise
    except KIError as e:
        err = str(e)
    except Exception as e:
        err = f"Unerwarteter Fehler: {type(e).__name__}: {e}"[:300]
    text = "".join(full).strip()
    sek = round(time.time() - t0, 1)
    old = BOT_STATS.get(bot["id"], {}).get("anzahl", 0)
    geheim = bool(gruende or privat)
    kurz = "(privat, nicht gespeichert)" if geheim else aufgabe[:120]
    antwort = "" if geheim or err else re.sub(r"\s+", " ", text)[:220]
    botstat(bot["id"], {"zeit": datetime.datetime.now().strftime("%H:%M:%S"), "aufgabe": kurz, "antwort": err or antwort,
                        "dauer": sek, "modell": m, "ok": not err},
            anzahl=old + (0 if err else 1), zuletzt=datetime.datetime.now().strftime("%d.%m. %H:%M"),
            aufgabe=kurz if s.get("bot_verlauf", True) else "", dauer=sek, modell=m, fehler=err)   # Verlauf aus: auch die letzte Aufgabe nicht
    emit({"t": "bot", "phase": "ende", "id": bot["id"], "name": bot["name"], "dauer": sek, "ok": not err})
    if err:
        if strom:
            emit({"t": "error", "message": f"{bot['name']}: {err}"})
        return None
    return text


# ---------------------------------------------------------------- Home Assistant und Webhooks
# Schnittstelle für Bastler: Jarvis schaltet Geräte über die REST-API von Home Assistant.
# Nötig sind die Adresse und ein "Langlebiger Zugriffstoken" (Home Assistant: Profil -> Sicherheit).
# Erlaubt sind nur die Gerätearten aus den Einstellungen. Schlösser und Alarmanlagen stehen absichtlich nicht drin.
def ha_bereiche(s):
    return {b.strip().lower() for b in re.split(r"[,;\s]+", s.get("ha_bereiche") or "") if b.strip()}


def ha_pruefen(s):
    if not s.get("ha_an"):
        return "Home Assistant ist ausgeschaltet (Einstellungen, Automation)."
    if not s.get("ha_url") or not s.get("ha_token"):
        return "Für Home Assistant fehlen Adresse oder Token (Einstellungen, Automation)."
    if s.get("strikt_lokal") and adresse_art(s["ha_url"]) == "internet":
        return "Strikt lokal ist an: Home Assistant ist nur über eine Adresse im eigenen Netz erlaubt."
    return ""


def ha_abruf(s, pfad, daten=None):
    try:
        with http(s["ha_url"] + pfad, daten, {"Authorization": "Bearer " + s["ha_token"]}, timeout=8) as r:
            return json.loads(r.read().decode("utf-8") or "null")
    except Umweg as e:
        raise KIError("Home Assistant: " + http_error_text(e))
    except urllib.error.HTTPError as e:
        raise KIError({401: "Home Assistant lehnt den Token ab.", 404: "Home Assistant kennt das Gerät oder den Dienst nicht."}.get(
            e.code, f"Home Assistant meldet Fehler {e.code}."))
    except (urllib.error.URLError, OSError, ValueError):
        raise KIError(f"Home Assistant ist nicht erreichbar ({s['ha_url']}).")


def ha_geraete(s):
    """Alle Geräte der erlaubten Arten: [{id, name, zustand}]. 30 Sekunden zwischengespeichert."""
    def holen():
        erlaubt = ha_bereiche(s)
        return sorted(({"id": e["entity_id"], "name": str((e.get("attributes") or {}).get("friendly_name") or e["entity_id"]),
                        "zustand": str(e.get("state") or "")}
                       for e in ha_abruf(s, "/api/states") or [] if isinstance(e, dict) and str(e.get("entity_id", "")).split(".")[0] in erlaubt),
                      key=lambda g: g["name"].lower())
    return cached("ha|" + s["ha_url"], 30, holen)


def ha_dienst(s, dienst, geraet, daten=None):
    """Ruft einen Dienst auf, z. B. ha_dienst(s, 'light.turn_on', 'light.wohnzimmer', {'brightness_pct': 40})."""
    fehler = ha_pruefen(s)
    if fehler:
        raise KIError(fehler)
    m = re.match(r"^([a-z_]+)\.([a-z0-9_]+)$", dienst.strip().lower())
    if not m or not re.match(r"^[a-z_]+\.[a-z0-9_]+$", geraet.strip().lower()):
        raise KIError("Dienst und Gerät müssen so aussehen: light.turn_on und light.wohnzimmer.")
    if m.group(1) not in ha_bereiche(s) or geraet.split(".")[0].lower() not in ha_bereiche(s):
        raise KIError(f"Die Geräteart {m.group(1)} ist nicht freigegeben (Einstellungen, Automation).")
    ha_abruf(s, f"/api/services/{m.group(1)}/{m.group(2)}", dict(daten or {}, entity_id=geraet.strip().lower()))
    CACHE.pop("ha|" + s["ha_url"], None)


def ha_routine(s, wert):
    """Routine-Wert: 'light.turn_on light.wohnzimmer' oder mit Zusatzdaten 'light.turn_on light.wohnzimmer {"brightness_pct": 40}'."""
    teile = wert.strip().split(None, 2)
    if len(teile) < 2:
        return False, "Die Routine braucht Dienst und Gerät, zum Beispiel light.turn_on light.wohnzimmer"
    try:
        daten = json.loads(teile[2]) if len(teile) > 2 else {}
        ha_dienst(s, teile[0], teile[1], daten if isinstance(daten, dict) else {})
        return True, f"{teile[1]} geschaltet ({teile[0]})"
    except ValueError:
        return False, "Die Zusatzdaten der Routine sind kein gültiges JSON"
    except KIError as e:
        return False, str(e).rstrip(".")


def webhook_routine(s, wert):
    """Routine-Wert: eine Adresse, optional dahinter JSON. Jarvis schickt einen POST dorthin (z. B. an einen
    Home-Assistant-Webhook, Node-RED oder ein eigenes Skript)."""
    url, _, rest = wert.strip().partition(" ")
    if not re.match(r"^https?://", url):
        return False, "Die Adresse muss mit http:// oder https:// beginnen"
    if s.get("strikt_lokal") and adresse_art(url) == "internet":
        return False, "Strikt lokal ist an, die Adresse liegt aber im Internet"
    try:
        daten = json.loads(rest) if rest.strip() else {}
        with http(url, daten, timeout=8) as r:
            return True, f"Webhook gesendet (Antwort {r.status})"
    except ValueError:
        return False, "Die Zusatzdaten sind kein gültiges JSON"
    except Umweg as e:
        return False, "Der Webhook leitet weiter. " + http_error_text(e).split(". ", 1)[-1].rstrip(".")
    except urllib.error.HTTPError as e:
        return False, f"Der Webhook antwortet mit Fehler {e.code}"
    except (urllib.error.URLError, OSError):
        return False, "Der Webhook ist nicht erreichbar"


HA_AN = re.compile(r"\b(an|ein|anschalten|einschalten|anmachen|aktiviere|aktivieren|starte|starten)\b")
HA_AUS = re.compile(r"\b(aus|ab|ausschalten|abschalten|ausmachen|deaktiviere|deaktivieren|stopp|stoppe)\b")
HA_FRAGE = re.compile(r"^\s*(ist|sind|läuft|laeuft|brennt|wie|was|welche|status)\b|\?\s*$")
HA_START = re.compile(r"\b(los|ausführen|ausfuehren|führe|fuehre|abspielen)\b")       # Szenen und Skripte brauchen ein Startwort


def ha_befehl(u, s):
    """Erkennt Sätze wie 'Schalte das Wohnzimmerlicht an', 'Stehlampe auf 40 Prozent' oder 'Ist der Fernseher an?'.
    Das Gerät wird am Namen aus Home Assistant erkannt. Läuft ohne KI, also mit jedem Modell und ohne Token.
    Liefert (ok, text) oder None, wenn kein Gerät gemeint ist."""
    if ha_pruefen(s):
        return None
    try:
        geraete = ha_geraete(s)
    except KIError:
        return None
    satz = " " + _norm(u) + " "
    treffer = [g for g in geraete if len(_norm(g["name"])) >= 3 and " " + _norm(g["name"]) + " " in satz]
    if not treffer:
        return None
    g = max(treffer, key=lambda x: len(x["name"]))
    art = g["id"].split(".")[0]
    if VERNEINT_RE.search(_norm(u)) or ERKLAER_RE.search(_norm(u)):
        return None                                # "Licht bitte nicht ausschalten", "Was macht Kinoabend?": nichts schalten
    try:
        if HA_FRAGE.search(u) and not HOEFLICH_RE.search(_norm(u)):
            z = {"on": "an", "off": "aus", "unavailable": "nicht erreichbar", "playing": "spielt", "paused": "pausiert",
                 "open": "offen", "closed": "geschlossen", "idle": "bereit"}.get(g["zustand"], g["zustand"])
            return True, f"{g['name']} ist {z}."
        proz = re.search(r"(\d{1,3})\s*(?:%|prozent)", u)
        if proz and art == "light":
            ha_dienst(s, "light.turn_on", g["id"], {"brightness_pct": max(1, min(100, int(proz.group(1))))})
            return True, f"{g['name']} steht auf {proz.group(1)} Prozent."
        if art == "cover" and re.search(r"\b(öffne|oeffne|hoch|auf)\b", u):
            ha_dienst(s, "cover.open_cover", g["id"])
            return True, f"{g['name']} fährt auf."
        if art == "cover" and re.search(r"\b(schließe|schliesse|runter|zu)\b", u):
            ha_dienst(s, "cover.close_cover", g["id"])
            return True, f"{g['name']} fährt zu."
        if art == "media_player" and re.search(r"\b(pause|pausiere|anhalten)\b", u):
            ha_dienst(s, "media_player.media_pause", g["id"])
            return True, f"{g['name']} ist pausiert."
        if art == "media_player" and re.search(r"\b(weiter|fortsetzen|abspielen|play)\b", u):
            ha_dienst(s, "media_player.media_play", g["id"])
            return True, f"{g['name']} spielt weiter."
        if HA_AUS.search(u) and art not in ("scene", "script"):
            ha_dienst(s, art + ".turn_off", g["id"])
            return True, f"{g['name']} ist aus."
        if HA_AN.search(u) or (art in ("scene", "script") and HA_START.search(u)):
            ha_dienst(s, art + ".turn_on", g["id"])
            return True, f"{g['name']} ist an." if art not in ("scene", "script") else f"{g['name']} gestartet."
    except KIError as e:
        return False, str(e)
    return None


# ---------------------------------------------------------------- Websuche über eine eigene SearXNG-Instanz
# Für Ollama und OpenAI-kompatible KIs, die selbst nicht ins Netz können. Jarvis fragt SearXNG und gibt der KI die
# Treffer (Titel, Adresse, kurzer Auszug) mit. Ganze Webseiten werden nicht geladen: Das hält die Anfrage klein.
SUCH_RE = re.compile(r"\b(such\w*|google\w*|recherchier\w*|im\s+(?:internet|netz|web)|online|aktuell\w*|neueste\w*|"
                     r"nachrichten|news|schlagzeilen)\b")
SUCH_VORN = re.compile(r"^\s*(?:hey\s+\w+[,\s]+)?(?:bitte\s+)?(?:kannst du\s+)?(?:mal\s+)?(?:such\w*|google\w*|recherchier\w*|schau)\s+"
                       r"(?:mal\s+|bitte\s+)*(?:im\s+(?:internet|netz|web)\s+)?(?:nach\s+)?", re.I)


def suche_an(s):
    return bool(s.get("websuche")) and s.get("suche_dienst") == "searxng" and bool(s.get("suche_url")) and not s.get("strikt_lokal")


def searx_suche(s, frage, n=5):
    """Fragt die eigene SearXNG-Instanz. Liefert [{titel, url, text}] oder wirft KIError."""
    url = (s.get("suche_url") or "").rstrip("/")
    if not url:
        raise KIError("Keine SearXNG-Adresse eingetragen (Einstellungen, KI & Modelle, Websuche).")
    if s.get("strikt_lokal"):
        raise KIError(STRIKT_SPERRE + " Auch die Websuche ist gesperrt, denn SearXNG fragt Suchmaschinen im Internet.")
    q = urllib.parse.urlencode({"q": frage.strip()[:200], "format": "json", "language": "de", "safesearch": 1})
    try:
        j = get_json(url + "/search?" + q, timeout=12)
    except urllib.error.HTTPError as e:
        if e.code == 403 and not isinstance(e, Umweg):
            raise KIError("SearXNG lehnt die Anfrage ab (403). Meist ist das JSON-Format aus: In der settings.yml der Instanz "
                          "unter search, formats die Zeile json ergänzen und SearXNG neu starten.")
        raise KIError("SearXNG: " + http_error_text(e))
    except (urllib.error.URLError, OSError, ValueError):
        raise KIError(f"SearXNG ist nicht erreichbar ({url}).")
    out = []
    for r in (j.get("results") if isinstance(j, dict) else None) or []:
        if isinstance(r, dict) and str(r.get("url", "")).startswith("http") and len(out) < n:
            out.append({"titel": re.sub(r"\s+", " ", str(r.get("title") or ""))[:160],
                        "url": str(r["url"])[:300], "text": re.sub(r"\s+", " ", str(r.get("content") or ""))[:320]})
    return out


def such_kontext(begriff, treffer):
    if not treffer:
        return f"WEBSUCHE nach '{begriff}': keine Treffer. Sag ehrlich, dass du dazu nichts gefunden hast."
    zeilen = [f"{i}. {t['titel']} ({urllib.parse.urlparse(t['url']).hostname or ''}): {t['text']}" for i, t in enumerate(treffer, 1)]
    return (f"WEBSUCHE nach '{begriff}' (Auszüge, nicht ganze Seiten):\n" + "\n".join(zeilen) +
            "\nNutze für aktuelle Fakten nur diese Treffer und nenne die Quelle in Worten (zum Beispiel: laut tagesschau.de). "
            "Steht die Antwort nicht drin, sag das ehrlich.")


# ---------------------------------------------------------------- Chat
MAXTOK = {"kurz": 600, "normal": 1000, "ausfuehrlich": 2500}      # Obergrenze je Antwort (nur eine Bremse, gezahlt wird der echte Verbrauch)


def run_chat(payload, emit):
    s = load_settings()
    raw = [m for m in (payload.get("messages") or []) if isinstance(m, dict)]
    n = 8 if s.get("sparmodus") else 20                # so viele Nachrichten des Verlaufs gehen mit
    msgs = clean_history(raw, n=n)
    if not msgs or not raw or raw[-1].get("role") == "assistant":
        return emit({"t": "error", "message": "Leere Nachricht."})
    # Die aktuelle Frage ist genau die letzte Nachricht. clean_history fasst aufeinanderfolgende Nachrichten zusammen,
    # dann stünde hier auch eine frühere (vielleicht lokale) Nachricht mit drin.
    text = str(raw[-1].get("content") or "").strip()[:6000]
    if not text:
        return emit({"t": "error", "message": "Leere Nachricht."})
    u = text.lower()
    zr = {"cloud": False, "rein": True}               # wurde in dieser Runde eine Cloud-KI gefragt, und nur sie?
    erzwingen = bool(payload.get("erzwingen_cloud"))
    s["_maxtok"] = 2500 if s.get("pc_an") and s.get("pc_schreiben") else MAXTOK.get(s.get("antwortlaenge"), 600)
    full = []

    def sag(t):
        full.append(t)
        emit({"t": "delta", "text": t})

    def fertig(t=None):
        if t:
            sag(t)
        ende = "".join(full).strip()
        if zr["cloud"] and zr["rein"]:
            cloud_merken("assistant", ende)              # die Antwort der Cloud-KI darf später wieder als Verlauf mit
        emit({"t": "done", "text": ende})

    def frage_ki(system, tf, leise=False):
        """Schickt die Frage an die gewählte KI und reicht die Antwort durch. Liefert False, wenn es einen Fehler gab."""
        if ist_cloud(s, anbieter) and not zr["cloud"]:
            zr["cloud"] = True
            cloud_merken("user", text)                   # diese Frage hat den PC verlassen und darf später als Verlauf mit
        try:
            for chunk in ki_stream(s, anbieter, model, system, msgs, lambda e: emit({"t": "action", **e})):
                out = tf.feed(chunk)
                if out:
                    sag(out)
            out = tf.feed("", final=True)
            if out:
                sag(out)
            return True
        except Abgebrochen:
            raise
        except KIError as e:
            fehler = str(e)
        except Exception as e:
            fehler = f"Unerwarteter Fehler: {type(e).__name__}: {e}"[:300]
        if not leise:
            emit({"t": "error", "message": fehler})
        return False

    # ---- Home Assistant: 'Schalte das Licht an' wird direkt ausgeführt, ohne KI und ohne Token
    ha = ha_befehl(u, s)
    if ha:
        emit({"t": "action", "typ": "ha", "ok": ha[0], "text": "Home Assistant", "info": ha[1]})
        return fertig(ha[1])

    # ---- Bot direkt angesprochen (@Name, "Name, ..." oder Stichwort): der Bot antwortet selbst
    bot, aufgabe = bot_finden(text, s)
    if bot:
        bs = bot_settings(s, bot)
        ziel_cloud = ist_cloud(bs, bs["anbieter"]) and not s.get("strikt_lokal")
        vorher = fuer_cloud(raw[:-1]) if ziel_cloud else raw[:-1]
        bmsgs = clean_history(vorher + [{"role": "user", "content": aufgabe}], n=n)
        ort = {}

        def bemit(e):
            if e.get("t") == "bot" and e.get("phase") == "start":
                ort["cloud"] = bool(e.get("cloud"))
            emit(e)
        res = bot_lauf(s, bot, aufgabe, bmsgs, bemit, strom=True, erzwingen=erzwingen, wie="direkt")
        if ort.get("cloud") and res:
            cloud_merken("user", text)
            cloud_merken("assistant", (res or "").strip())
        return emit({"t": "done", "text": res or ""})
    anbieter, model = pick_model(s)

    # ---- Datenschutz-Weiche: entscheidet VOR allem anderen, ob diese Nachricht den PC verlassen darf
    if s.get("strikt_lokal") and ist_cloud(s, anbieter):
        anbieter, model = "ollama", lokales_modell(s)
        if not model:
            return emit({"t": "error", "message": "Strikt lokal ist an, aber Ollama läuft nicht oder hat kein Modell. Es wurde nichts gesendet."})
    gruende = []
    if ist_cloud(s, anbieter) and s.get("privat_weiche") and not erzwingen:
        gruende = privat_erkennen(text, s)
        if gruende:
            lm = lokales_modell(s)
            if not lm:
                return emit({"t": "privat", "weiter": "blockiert", "gruende": gruende,
                             "message": "Private Daten erkannt (" + ", ".join(gruende) + "). Die lokale KI (Ollama) ist nicht erreichbar, "
                                        "deshalb habe ich nichts an die Cloud geschickt."})
            anbieter, model = "ollama", lm
            emit({"t": "privat", "weiter": "lokal", "gruende": gruende, "modell": lm})
    cloud = ist_cloud(s, anbieter)
    mem_ok = (not cloud) or bool(s.get("gedaechtnis_cloud"))

    # ---- Befehle, die Jarvis selbst ausführt (Timer, Webseiten, Wetter, Routinen, PC)
    pcb = pc_befehl(u, s)
    pc_ctx = []
    if pcb:
        pc_ctx.append("PC-AKTION (" + pc_text(*pcb) + "): " + pc_aktion(s, pcb[0], pcb[1], "", emit, cloud) +
                      "\nBestätige kurz oder gib das Ergebnis wieder. Löse keine weitere Aktion aus.")
    actions, ctx, direct, kurz = route(u, s, text, ohne_url=bool(pcb))
    ctx += pc_ctx
    for a in actions:
        emit({"t": "action", **a})
    if direct:
        return fertig(direct)
    # Sparmodus: Ein reiner Befehl ("Timer 10 Minuten") braucht keine bezahlte KI-Antwort als Bestätigung
    # Schaltbefehle (Home Assistant, Webhook) bestätigt Jarvis immer selbst: Das Ergebnis steht fest, die KI würde nur raten.
    if kurz and not pc_ctx and len(text) <= 90 and ((cloud and s.get("sparmodus")) or any(a.get("typ") == "ha" for a in actions)):
        return fertig(" ".join(kurz))
    # Merk-Befehle in der Cloud ohne Gedächtnis-Freigabe: lokal bestätigen, nichts senden
    if cloud and not mem_ok and kurz and any(a.get("typ") == "gedaechtnis" for a in actions):
        emit({"t": "privat", "weiter": "lokal", "gruende": ["Gedächtnis bleibt lokal"], "modell": "ohne KI"})
        return fertig(" ".join(kurz))
    if cloud:     # In die Cloud geht nur Verlauf, der schon in der Cloud war (siehe fuer_cloud). Eine Markierung aus dem Browser zählt nicht.
        msgs = clean_history(fuer_cloud(raw[:-1]) + [{"role": "user", "content": text}], n=n)
    if not model and kurz:                             # keine KI erreichbar, der Befehl (Timer, Wetter ...) ist aber erledigt
        return fertig(" ".join(kurz))
    if not model:
        return emit({"t": "error", "message": {
            "ollama": "Kein Ollama-Modell gefunden. Läuft Ollama und ist ein Modell installiert? (ollama pull llama3.2)",
            "claude": "Kein Claude-Modell verfügbar. Ist der Schlüssel in den Einstellungen eingetragen?",
            "openai": "Kein Modell verfügbar. Sind Basis-Adresse und Schlüssel in den Einstellungen eingetragen?"}[anbieter]})
    emit({"t": "model", "anbieter": anbieter, "modell": model, "cloud": cloud})
    websuche = anbieter == "claude" and bool(s.get("websuche")) and s.get("suche_dienst") != "searxng"
    searx = suche_an(s) and not gruende           # private Nachricht: auch keine Suchbegriffe ins Netz

    def suchen(begriff):
        if privat_erkennen(begriff, s):
            return "WEBSUCHE nicht ausgeführt: Der Suchbegriff enthält private Daten. Sag das dem Nutzer kurz."
        emit({"t": "action", "typ": "suche", "text": "Websuche: " + begriff[:60]})
        try:
            return such_kontext(begriff, searx_suche(s, begriff))
        except KIError as e:
            emit({"t": "action", "typ": "suche", "text": "Websuche fehlgeschlagen"})
            return f"WEBSUCHE fehlgeschlagen ({e}). Sag dem Nutzer ehrlich, dass die Suche nicht geklappt hat."
    gesucht = False
    if searx and SUCH_RE.search(u) and not actions:    # "Such mal nach ...", "aktuelle Nachrichten": gleich suchen (kein anderer Befehl erkannt)
        ctx.append(suchen(SUCH_VORN.sub("", text).strip(" ?.!") or text))
        gesucht = True
    tf = TagFilter()
    if not frage_ki(system_prompt(s, ctx, websuche, mem_ok, pc_ok=not pcb, lokal=not cloud, suche_tag=searx and not gesucht), tf):
        return
    if tf.suche and searx and not gesucht:         # die KI hat selbst eine Suche angefordert ([suche: ...]), höchstens eine
        ctx.append(suchen(tf.suche[0]))
        tf = TagFilter()
        if full and not "".join(full).endswith((" ", "\n")):
            sag(" ")
        if not frage_ki(system_prompt(s, ctx, False, mem_ok, pc_ok=not pcb, lokal=not cloud), tf):
            return
    if s.get("auto_merken"):
        for m in tf.merk[:2]:
            it = mem_add(m)
            if it:
                emit({"t": "action", "typ": "gedaechtnis", "aktion": "gelernt", "text": it["text"]})

    # ---- PC-Steuerung: Jarvis hat eine Aktion verlangt ([pc: aktion | ziel | inhalt]). Bis zu 4 Schritte nacheinander.
    s_ohne_suche = dict(s, websuche=False)
    schritt, verlauf, getan = 0, [], set()
    while tf.pc and s.get("pc_an") and schritt < 4:
        schritt += 1
        ak, ziel, inhalt = tf.pc[0]
        schluessel = (ak.strip().lower(), ziel.strip().lower(), inhalt.strip())
        doppelt = schluessel in getan
        getan.add(schluessel)
        if doppelt:                                    # dieselbe Aktion nochmal: nicht ausführen, Schleife beenden
            verlauf.append(f"HINWEIS: Die Aktion ({pc_text(ak, ziel)}) wurde in dieser Runde bereits erfolgreich ausgeführt. "
                           "Sie wird nicht wiederholt.")
        else:
            verlauf.append(f"ERGEBNIS DER PC-AKTION {schritt} ({pc_text(ak, ziel)}):\n{pc_aktion(s, ak, ziel, inhalt, emit, cloud)}")
        weiter = schritt < 4 and not doppelt
        extra = "\n\n".join(verlauf) + ("\n\nAntworte dem Nutzer jetzt auf Grundlage dieses Ergebnisses. Eine weitere Aktion nur, "
                                         "wenn sie etwas anderes tut als die bisherigen." if weiter else "\n\nAntworte jetzt, keine weitere Aktion.")
        tf = TagFilter()
        if full and not "".join(full).endswith((" ", "\n")):
            sag(" ")
        if not frage_ki(system_prompt(s_ohne_suche, ctx + [extra], False, mem_ok, pc_ok=weiter, lokal=not cloud), tf):
            return
        if not weiter:
            break

    # ---- Delegation: Jarvis hat eine Aufgabe an einen Bot abgegeben ([bot: Name | Aufgabe])
    if tf.bots and s.get("bot_delegieren"):
        bname, aufgabe = tf.bots[0]
        team = [b for b in s.get("bots") or [] if b.get("aktiv")]
        bot = next((b for b in team if b["name"].lower() == bname.strip().lower()), None) or \
            next((b for b in team if bname.strip().lower() in b["name"].lower()), None)
        if not bot:
            return fertig(f"Den Bot {bname} gibt es nicht.")
        if full and not "".join(full).endswith((" ", "\n")):
            sag(" ")
        if not cloud and bot_ist_cloud(s, bot):
            # Ein lokales Gespräch kann Gedächtnis, Dateien und lokalen Verlauf enthalten. Was davon in der Aufgabe steht,
            # würde mit an den Cloud-Bot gehen. Deshalb gibt Jarvis lokal nichts selbst an die Cloud ab.
            return fertig(f"Das wäre eine Aufgabe für {bot['name']}, aber {bot['name']} arbeitet in der Cloud. Aus einem lokalen "
                          f"Gespräch gebe ich nichts selbst dorthin ab. Wenn du willst, sprich ihn direkt an: @{bot['name']} und die Aufgabe.")
        spar = bool(s.get("sparmodus"))
        # Sparmodus: Die Antwort des Bots geht direkt an den Nutzer. Sonst fasst Jarvis sie in eigenen Worten zusammen (ein KI-Aufruf mehr).
        ort = {}

        def bemit(e):
            if e.get("t") == "bot" and e.get("phase") == "start":
                ort["cloud"] = bool(e.get("cloud"))
            emit(e)
        res = bot_lauf(s, bot, aufgabe, [{"role": "user", "content": aufgabe}], bemit, strom=spar, erzwingen=erzwingen,
                       privat=bool(gruende), wie="delegiert")
        if spar:
            if res:
                full.append(res)
                if not ort.get("cloud"):
                    zr["rein"] = False                 # ein lokaler Bot hat mitgeschrieben: diese Antwort bleibt lokal
            return fertig()
        extra = (f"ERGEBNIS VON BOT {bot['name']} (Aufgabe: {aufgabe}):\n{res[:6000]}\n\nGib dem Nutzer jetzt die Antwort in deinen "
                 f"Worten weiter und erwähne kurz, dass {bot['name']} das erledigt hat. Erfinde nichts dazu.") if res else \
            f"Der Bot {bot['name']} konnte die Aufgabe nicht erledigen (Fehler). Sag das ehrlich und biete an, es selbst zu versuchen."
        if not frage_ki(system_prompt(s_ohne_suche, ctx + [extra], False, mem_ok, ohne_team=True), TagFilter(), leise=bool(res)):
            if not res:
                return
            sag(res)                                   # Zusammenfassen ging schief: dann eben das Ergebnis des Bots im Original
    fertig()


# ---------------------------------------------------------------- Sprachausgabe ElevenLabs
def eleven_tts(s, text):
    if s.get("strikt_lokal"):
        raise KIError("Strikt lokal ist an: ElevenLabs ist gesperrt.")
    key, vid = s.get("eleven_key"), s.get("eleven_voice")
    if not key or not vid:
        raise KIError("ElevenLabs: Schlüssel oder Stimmen-ID fehlt.")
    body = {"text": text[:1200], "model_id": s.get("eleven_modell") or "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.8}}
    try:
        with http(f"https://api.elevenlabs.io/v1/text-to-speech/{urllib.parse.quote(vid)}?output_format=mp3_44100_128", body,
                  {"xi-api-key": key, "accept": "audio/mpeg"}, timeout=60) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        raise KIError("ElevenLabs: " + http_error_text(e))
    except urllib.error.URLError:
        raise KIError("ElevenLabs nicht erreichbar.")


# ---------------------------------------------------------------- Webserver
STATIC = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
          ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml", ".ico": "image/x-icon",
          ".mp3": "audio/mpeg", ".wav": "audio/wav", ".webp": "image/webp", ".gif": "image/gif", ".woff2": "font/woff2"}


ORDNER = ("core/", "oberflaechen/", "sounds/")           # nur von hier werden Dateien ausgeliefert, dazu jarvis.html
CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
       "media-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")


class Server(ThreadingHTTPServer):
    # Unter Windows erlaubt SO_REUSEADDR, einen schon belegten Port ein zweites Mal zu öffnen. Dann liefen zwei
    # Jarvis-Fenster auf demselben Port und Antworten kämen mal vom einen, mal vom anderen. Deshalb dort aus.
    allow_reuse_address = os.name != "nt"
    daemon_threads = True


class Handler(BaseHTTPRequestHandler):
    server_version = "Jarvis"

    def log_message(self, fmt, *args):
        pass

    def local(self):
        return self.client_address[0] in ("127.0.0.1", "::1", "::ffff:127.0.0.1")

    def schutz(self):
        """Kopfzeilen für jede Antwort:
        - nosniff: der Browser rät keinen Dateityp
        - DENY / frame-ancestors: keine fremde Seite kann Jarvis unsichtbar einbetten und Klicks unterschieben
        - Content-Security-Policy: die Oberfläche lädt und sendet nur an Jarvis selbst, nie an fremde Adressen
        - no-referrer: geöffnete Webseiten erfahren nicht, woher der Klick kam"""
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", CSP)

    def send_json(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.schutz()
        self.end_headers()
        self.wfile.write(b)

    def body(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 0 or n > 2_000_000:
                return {}
            d = json.loads(self.rfile.read(n).decode("utf-8"))
            return d if isinstance(d, dict) else {}
        except (ValueError, OSError):
            return {}

    def eigen(self, post=False):
        """Schutz vor fremden Webseiten (CSRF und DNS-Rebinding).
        1. Host muss localhost/127.0.0.1 mit unserem Port sein -> keine fremde Adresse, die auf 127.0.0.1 zeigt.
        2. Ein mitgeschickter Origin muss genau dieser Adresse entsprechen -> auch kein anderer Dienst auf localhost.
        3. Jede schreibende Anfrage braucht den Kopfzeilen-Eintrag X-Jarvis: 1. Den darf eine fremde Seite nur
           nach einer CORS-Vorabfrage setzen, und die beantworten wir mit 403 (siehe do_OPTIONS)."""
        host = (self.headers.get("Host") or "").strip().lower()
        hn, _, hp = host.rpartition(":")
        if not hn:
            hn, hp = host, ""
        if hn.strip("[]") not in ("localhost", "127.0.0.1", "::1") or hp != str(AKTIV_PORT[0]):
            return False
        org = (self.headers.get("Origin") or "").strip().lower()
        if org and org.split("//", 1)[-1] != host:
            return False
        if post and self.headers.get("X-Jarvis") != "1":
            return False
        return True

    def do_OPTIONS(self):
        """Keine CORS-Freigabe. Damit scheitert jede Vorabfrage einer fremden Webseite."""
        self.send_json(403, {"error": "Nur vom eigenen Rechner erreichbar."})

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if not self.local() or not self.eigen():
            return self.send_json(403, {"error": "Nur vom eigenen Rechner erreichbar."})
        if path == "/api/pc/log":
            return self.send_json(200, {"log": PC_LOG[-30:][::-1]})
        if path == "/":
            s = load_settings()
            self.send_response(302)
            self.send_header("Location", THEMES.get(s.get("oberflaeche"), "/jarvis.html"))
            self.end_headers()
            return
        if path == "/api/settings":
            return self.send_json(200, public_settings(load_settings()))
        if path == "/api/models":
            s = load_settings()
            ms = all_models(s)
            a, m = pick_model(s, ms)
            return self.send_json(200, {"anbieter": a, "modell": m, "liste": ms})
        if path == "/api/memory":
            return self.send_json(200, {"items": mem_load()})
        if path == "/api/system":
            return self.send_json(200, system_info())
        if path == "/api/wetter":
            return self.send_json(200, wetter(load_settings()))
        if path == "/api/bots/status":
            return self.send_json(200, {"stats": BOT_STATS})
        if path == "/api/kosten":
            return self.send_json(200, kosten_stand(load_settings()))
        if path == "/api/ha/geraete":
            s = load_settings()
            try:
                fehler = ha_pruefen(s)
                return self.send_json(200, {"ok": not fehler, "fehler": fehler, "geraete": [] if fehler else ha_geraete(s)})
            except KIError as e:
                return self.send_json(200, {"ok": False, "fehler": str(e), "geraete": []})
        if path == "/api/status":
            return self.send_json(200, {"ok": True, "version": VERSION, "themes": THEMES})
        return self.static(path)

    def static(self, path):
        rel = urllib.parse.unquote(path).lstrip("/").replace("\\", "/")
        full = os.path.realpath(os.path.join(BASE, rel))
        ext = os.path.splitext(full)[1].lower()
        innen = full.startswith(BASE + os.sep)
        echt = os.path.relpath(full, BASE).replace("\\", "/") if innen else ""     # erst auflösen (core/../x), dann prüfen
        erlaubt = echt == "jarvis.html" or echt.startswith(ORDNER)
        if not erlaubt or not innen or ext not in STATIC or not os.path.isfile(full):
            return self.send_json(404, {"error": "Nicht gefunden: " + path})
        with open(full, "rb") as f:
            data = f.read()
        code, rng = 200, self.headers.get("Range") or ""
        m = re.match(r"bytes=(\d*)-(\d*)$", rng.strip())
        if m and (m.group(1) or m.group(2)) and ext in (".mp3", ".wav"):       # Teilabruf: Browser brauchen ihn für Audio-Schleifen
            n = len(data)
            a, b = (int(m.group(1)), int(m.group(2) or n - 1)) if m.group(1) else (max(0, n - int(m.group(2))), n - 1)
            a, b = min(a, n - 1), min(b, n - 1)
            data, code = data[a:b + 1], 206
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {a}-{b}/{n}")
        else:
            self.send_response(200)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Type", STATIC[ext])
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.schutz()
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if not self.local() or not self.eigen(post=True):
            return self.send_json(403, {"error": "Nur vom eigenen Rechner erreichbar. Schreibende Anfragen brauchen den Kopfzeilen-Eintrag X-Jarvis: 1."})
        if "json" not in (self.headers.get("Content-Type") or "").lower():
            return self.send_json(415, {"error": "Nur JSON."})      # blockt Formulare fremder Webseiten
        data = self.body()
        if path == "/api/pc/antwort":
            w = PC_WARTEN.get(str(data.get("id") or ""))
            if w:
                w[1] = bool(data.get("ok"))
                w[0].set()
            return self.send_json(200, {"ok": bool(w)})
        if path == "/api/pc/waehlen":
            return self.send_json(200, pc_waehlen("ordner" if data.get("art") == "ordner" else "programm"))
        if path == "/api/pc/pruefen":
            s = load_settings()
            o = [{"name": x["name"], "ok": os.path.isdir(os.path.expanduser(x["pfad"]))} for x in clean_pc_liste(data.get("pc_ordner"))]
            pr = [{"name": x["name"], "ok": bool(os.path.exists(os.path.expanduser(x["pfad"])) or shutil.which(x["pfad"]))}
                  for x in clean_pc_liste(data.get("pc_programme"))]
            return self.send_json(200, {"ordner": o, "programme": pr, "system": "windows" if os.name == "nt" else sys.platform})
        if path == "/api/settings":
            s = update_settings(data)
            CACHE.clear()
            return self.send_json(200, public_settings(s))
        if path == "/api/test":
            s = load_settings()
            if data.get("anbieter") == "searxng":
                try:
                    t = searx_suche(s, "Wetter Berlin", 3)
                    return self.send_json(200, {"ok": True, "models": [x["titel"] for x in t], "treffer": len(t)})
                except KIError as e:
                    return self.send_json(200, {"ok": False, "models": [], "fehler": str(e)})
            fn = {"ollama": ollama_models, "claude": claude_models, "openai": openai_models}.get(data.get("anbieter"))
            if not fn:
                return self.send_json(400, {"ok": False, "fehler": "Unbekannter Anbieter"})
            CACHE.clear()
            return self.send_json(200, fn(s))
        if path == "/api/bots/clear":
            with LOCK:
                bid = str(data.get("id") or "")
                if bid:
                    BOT_STATS.pop(bid, None)
                else:
                    BOT_STATS.clear()
                try:
                    if BOT_STATS:
                        write_json(BOTSTAT_FILE, BOT_STATS, 1)
                    elif os.path.exists(BOTSTAT_FILE):
                        os.remove(BOTSTAT_FILE)
                except OSError:
                    pass
            return self.send_json(200, {"stats": BOT_STATS})
        if path == "/api/bots/test":
            s = load_settings()
            lst = clean_bots([data.get("bot")], s.get("bots"))
            if not lst:
                return self.send_json(400, {"ok": False, "fehler": "Der Bot braucht einen Namen."})
            bs = bot_settings(s, lst[0])
            a = bs["anbieter"]
            if s.get("strikt_lokal") and ist_cloud(bs, a):
                return self.send_json(200, {"ok": False, "models": [], "anbieter": a, "cloud": True,
                                            "fehler": "Strikt lokal ist an: Dieser Bot würde eine Cloud-KI nutzen und ist gesperrt."})
            CACHE.clear()
            r = {"ollama": ollama_models, "claude": claude_models, "openai": openai_models}[a](bs)
            return self.send_json(200, dict(r, anbieter=a, cloud=ist_cloud(bs, a)))
        if path == "/api/kosten/reset":
            with LOCK:
                KOSTEN.update(tage={}, seitdem=0.0)
                kosten_save()
            return self.send_json(200, kosten_stand(load_settings()))
        if path == "/api/ha/schalten":                   # Schaltfläche in den Einstellungen: ein Gerät testweise umschalten
            s = load_settings()
            try:
                gid = str(data.get("id") or "")
                ha_dienst(s, gid.split(".")[0] + ".toggle", gid)
                return self.send_json(200, {"ok": True})
            except KIError as e:
                return self.send_json(200, {"ok": False, "fehler": str(e)})
        if path == "/api/memory":
            it = mem_add(data.get("text"))
            return self.send_json(200 if it else 400, {"item": it, "items": mem_load()})
        if path == "/api/memory/delete":
            mem_delete(mid=str(data.get("id") or ""))
            return self.send_json(200, {"items": mem_load()})
        if path == "/api/memory/clear":
            with LOCK:
                mem_save([])
            return self.send_json(200, {"items": []})
        if path == "/api/tts":
            try:
                audio = eleven_tts(load_settings(), str(data.get("text") or ""))
            except KIError as e:
                return self.send_json(502, {"error": str(e)})
            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("Content-Length", str(len(audio)))
            self.end_headers()
            self.wfile.write(audio)
            return
        if path == "/api/chat":
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

            weg = {"ja": False}

            def emit(obj):
                if weg["ja"]:
                    if obj.get("t") == "error":
                        fehler_log("Chat (Browser schon getrennt): " + str(obj.get("message")))
                    raise Abgebrochen()
                try:
                    self.wfile.write((json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"))
                    self.wfile.flush()
                except OSError:                          # BrokenPipe, ConnectionReset, unter Windows ConnectionAborted
                    weg["ja"] = True
                    if obj.get("t") == "error":
                        fehler_log("Chat (Browser getrennt): " + str(obj.get("message")))
                    raise Abgebrochen()
            try:
                run_chat(data, emit)
            except Abgebrochen:
                pass                                     # die laufende KI-Anfrage ist beendet, angefangene Kosten sind gebucht
            except Exception as e:                       # darf nie still verschwinden
                fehler_log(f"Chat: unerwarteter Fehler {type(e).__name__}: {e}")
                try:
                    emit({"t": "error", "message": f"Unerwarteter Fehler im Server: {type(e).__name__}. Details stehen in fehler.log."})
                except Abgebrochen:
                    pass
            return
        return self.send_json(404, {"error": "Unbekannt: " + path})


def main():
    load_settings()
    botstat_load()
    kosten_load()
    cloud_verlauf_load()
    srv, port = None, PORT
    for p in range(PORT, PORT + 10):
        try:
            srv = Server((HOST, p), Handler)
            port = p
            break
        except OSError:
            continue
    if not srv:
        sys.exit(f"Kein freier Port zwischen {PORT} und {PORT + 9}. Läuft Jarvis schon?")
    AKTIV_PORT[0] = port
    url = f"http://localhost:{port}/"
    s = load_settings()
    print("=" * 56)
    print(f"  FreeJarvis · JARVIS YouTube-Edition {VERSION}")
    print(f"  Oberfläche:  {url}")
    print(f"  KI:          {s['anbieter']}" + (f" ({s['modell']})" if s.get("modell") else " (Modell automatisch)"))
    nb = len([b for b in s.get("bots") or [] if b.get("aktiv")])
    print(f"  Bots:        {nb} aktiv" if nb else "  Bots:        noch keine (Einstellungen -> Bots)")
    print("  PC-Zugriff:  " + (f"AN ({len(s.get('pc_ordner') or [])} Ordner, {len(s.get('pc_programme') or [])} Programme)"
                              if s.get("pc_an") else "aus"))
    print("  Beenden:     Strg + C")
    print("=" * 56)
    if not os.environ.get("JARVIS_KEIN_BROWSER"):
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nJarvis beendet.")


if __name__ == "__main__":
    main()
