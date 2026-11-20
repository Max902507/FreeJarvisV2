# FreeJarvis · JARVIS YouTube-Edition 2.1

Persönlicher KI-Assistent im Browser: mit Stimme, Gedächtnis, Automation, **25 Oberflächen** und einem **Team aus Bots**, das sichtbar um Jarvis kreist.

Keine Pakete zu installieren, nur Python. Start per Doppelklick.

**Eine Version für alles:** lokal mit **Ollama** (kostenlos, ohne Schlüssel), **Claude** per API oder **OpenAI-kompatible** Dienste (OpenAI, Groq, OpenRouter, LM Studio). Gewechselt wird oben rechts per Klick, ohne Code zu ändern.

## Download

Rechts auf dieser Seite unter **Releases** die neueste Version als ZIP herunterladen (oder oben über **Code → Download ZIP**).

> **Update von einer älteren Version:** Immer in einen **neuen, leeren Ordner** entpacken, nie über den alten kopieren. Danach nur `einstellungen.json` und `gedaechtnis.json` aus dem alten Ordner übernehmen. Sonst mischen sich alte und neue Dateien, und es gibt Fehler, die nur manchmal auftreten.
>
> **FreeJarvis und der Max-Klon** aus den Videos sind zwei getrennte Programme. Nicht in denselben Ordner legen.

## Start

1. Python 3.8 oder neuer installieren (unter Windows den Haken bei „Add python.exe to PATH“ setzen)
2. Ordner entpacken, `start.bat` doppelklicken (Mac/Linux: `sh start.sh`)
3. Der Browser öffnet `http://localhost:5050`. Warten, bis der Ladescreen fertig ist, dann **STARTEN**
4. Oben links **Einstellungen** → KI einrichten

Die komplette Anleitung mit Fehlerbehebung steht in **`anleitung.txt`**.

**Ollama muss nicht auf demselben PC laufen.** Ein Ollama auf einem anderen Rechner im Heimnetz (z. B. mit stärkerer Grafikkarte) geht genauso: Adresse wie `http://192.168.1.50:11434` eintragen. Jarvis zählt das als lokal. Anleitung, Abschnitt 14.

## Was Jarvis kann

| Bereich | Inhalt |
| --- | --- |
| **Sprechen und Zuhören** | Browser-Stimme oder ElevenLabs, Mikrofon mit Weckwort |
| **Gedächtnis** | „Merk dir …“ und „Vergiss …“, bleibt standardmäßig auf dem PC |
| **Befehle ohne KI** | Timer, Webseiten, Wetter, Systemwerte, Weck-Briefing, eigene Routinen |
| **Bots** | Eigene KI-Helfer mit Auftrag, Modell und Schlüssel. Ansprechen mit `@Name`, „Name, …“ oder Stichwort. Jarvis kann Aufgaben selbst abgeben |
| **Oberflächen** | 25 Designs mit Vorschau, darunter Avatar und Kosmos 3D in WebGL und Retro als Arbeitsübersicht |
| **Widgets** | Wetter, Notizen, Uhr, System, Kosten. Verschiebbar, Größe änderbar |
| **Kostenkontrolle** | Sparmodus, Monatslimit, Kosten-Widget mit Verbrauch und Guthaben |
| **PC-Steuerung** | Freigegebene Ordner und Programme, Textdateien und Skripte lesen und schreiben. Standardmäßig aus, mit Nachfrage |
| **Home Assistant** | Geräte per Sprache und Routine schalten, dazu Webhooks. Standardmäßig aus |
| **Websuche** | Mit Claude oder für alle KIs über eine eigene SearXNG-Instanz. Standardmäßig aus |

## Kann und kann nicht

| Kann | Kann nicht |
| --- | --- |
| Chatten per Text und Sprache, vorlesen | Bilder, Videos, Musik oder 3D-Modelle erzeugen |
| Sich Dinge merken | Bilder oder Videos ansehen |
| Timer, Wetter, Webseiten öffnen, Routinen | Dateien löschen, verschieben, Ordner anlegen |
| Bots mit eigenem Auftrag und Modell | Beliebige Befehle oder die Kommandozeile ausführen |
| Websuche (Claude oder SearXNG, kurze Auszüge) | Selbstständig über viele Schritte recherchieren, ganze Webseiten lesen |
| Textdateien lesen und schreiben, Programme starten (nur Freigegebenes) | E-Mails, Kalender, Messenger bedienen |
| Home Assistant schalten, Webhooks | Echtzeit-Gespräch mit Dazwischenreden (Unterbrechen geht mit „Stopp“) |
| Kosten zählen, Monatslimit | Ohne Terminalfenster laufen (es gibt keinen Installer) |

## Kosten

Ollama kostet nichts. Bei Claude und anderen API-Diensten zahlt man nach Verbrauch. Dafür gibt es:

- **Sparmodus** (an): kürzerer Verlauf, Befehle wie Timer ohne KI-Rückfrage, Bots antworten direkt
- **Zwischenspeicher** (Prompt-Caching, an): Bei Claude kosten Anweisungen und bisheriger Verlauf ab der zweiten Frage nur noch einen Bruchteil
- **Websuche** standardmäßig aus. Bei Claude kostet jede Suche extra, und die gefundenen Seiten zählen als Eingabe. SearXNG gibt nur kurze Auszüge mit
- **Monatslimit** in US-Dollar: Ist es erreicht, sendet Jarvis nichts mehr an eine Cloud-KI. Für ein Modell ohne bekannten Preis sendet er bei gesetztem Limit gar nichts
- **Kosten-Widget**: Verbrauch heute und im Monat, Limit, Guthaben

Das echte Guthaben lässt sich mit einem normalen API-Schlüssel nicht abfragen. Jarvis rechnet deshalb mit dem Guthaben, das man einträgt, und zieht den eigenen Verbrauch ab. Verbindlich ist die Abrechnung beim Anbieter. Details in `anleitung.txt`, Abschnitt 21.

## Home Assistant

Adresse und langlebigen Zugriffstoken eintragen (Einstellungen → Automation), dann gehen Sätze wie „Schalte das Wohnzimmerlicht an“, „Stehlampe auf 40 Prozent“ oder „Ist der Fernseher an?“. Das läuft ohne KI. Szenen und Skripte brauchen ein Startwort („Starte Kinoabend“), verneinte Sätze und Erklärfragen schalten nichts. Per Routine lassen sich beliebige Dienste und Webhooks auslösen, zum Beispiel für Node-RED. Schlösser und Alarmanlagen sind absichtlich nicht direkt freigegeben. Ein Skript in Home Assistant kann sie trotzdem schalten: Was deine Skripte tun, legst du dort fest. Details in Abschnitt 22.

## Datenschutz

- Anzeige **LOKAL / CLOUD** oben rechts
- **Privat-Weiche:** Nachrichten mit Telefonnummer, IBAN, Passwort oder eigenen Stichwörtern gehen an die lokale KI statt in die Cloud
- Das **Gedächtnis** bleibt standardmäßig lokal
- **Strikt lokal**: Nichts geht ins Internet. Gesperrt sind alle Online-Dienste, auch Modellliste, Verbindungstest und Websuche. Adressen im eigenen Heimnetz (z. B. Ollama auf einem zweiten PC) bleiben erlaubt. Ohne lokale Browser-Stimme bleibt Jarvis stumm
- Das gilt auch für Bots. Ein lokal arbeitender Jarvis gibt keine Aufgabe von sich aus an einen Cloud-Bot ab, `@Name` geht weiter
- **Websuche über SearXNG:** Die Suchbegriffe gehen an deine Instanz und von dort an Suchmaschinen. Mit privaten Daten im Suchbegriff wird nicht gesucht
- **Verlauf:** Eine Cloud-KI bekommt nur Verlauf, der schon in der Cloud war. Lokale Gespräche bleiben beim Wechsel zu Claude auf dem PC. Das prüft der Server, nicht der Browser

`einstellungen.json`, `gedaechtnis.json`, `bot_statistik.json`, `kosten.json`, `cloud_verlauf.json` und `fehler.log` enthalten persönliche Daten, Schlüssel oder Meldungen. Sie entstehen erst beim Benutzen und werden durch `.gitignore` nicht mit hochgeladen. Details in Abschnitt 15.

## Sicherheit

- Der Server ist nur über localhost erreichbar.
- Schreibende Anfragen müssen an genau diesen Port gehen, einen passenden `Origin` haben und die Kopfzeile `X-Jarvis: 1` tragen. CORS-Vorabfragen werden mit 403 beantwortet. Damit kann keine Webseite im Browser Jarvis steuern, auch keine, die ein anderes Programm auf dem Rechner ausliefert. (Bis Version 1.1 war das möglich. Danke an Pascal für den Hinweis.)
- **Ehrlich:** Ein Programm, das direkt auf deinem PC unter deinem Benutzerkonto läuft, kann diese Prüfungen erfüllen. So ein Programm könnte aber ohnehin deine `einstellungen.json` lesen. Gegen Schadsoftware auf dem eigenen PC schützt Jarvis nicht.
- Weiterleitungen von KI-Diensten, Home Assistant und Webhooks folgt Jarvis nicht. Sonst ginge der Schlüssel an die neue Adresse mit.
- Schutz-Kopfzeilen verhindern, dass fremde Seiten Jarvis einbetten, und erlauben der Oberfläche nur Verbindungen zu Jarvis selbst.
- Ausgeliefert werden nur `core`, `oberflaechen`, `sounds` und `jarvis.html`.
- Skripte schreibt Jarvis nur nach Nachfrage und startet sie nie.

Jarvis ist ein Hobby-Projekt ohne Gewähr, Nutzung auf eigene Verantwortung. Wer eine Lücke findet: bitte direkt melden statt öffentlich posten. Details in Abschnitt 16.

## Dateien

| Datei | Zweck |
| --- | --- |
| `start.bat`, `start.sh` | Start |
| `server.py` | der Server: verbindet Oberfläche und KI, nur Python-Standardbibliothek |
| `jarvis.html` | Oberfläche Vortex |
| `oberflaechen/` | die 24 weiteren Oberflächen und ihre Vorschaubilder |
| `core/core.js`, `core/core.css` | gemeinsame Technik und Aussehen |
| `core/bots.js` | Bots auf der Oberfläche und der Reiter „Bots“ |
| `core/widgets.js` | Widgets |
| `core/klang.js`, `sounds/` | Klang |
| `core/maus.js` | Maus-Effekte |
| `core/pc.js` | PC-Steuerung |
| `fehler.log` | entsteht erst bei Bedarf: Fehlermeldungen, die den Browser nicht mehr erreicht haben |
| `anleitung.txt` | die ausführliche Anleitung |
| `LICENSE`, `Rechtshinweis.txt` | Lizenz (PolyForm Noncommercial 1.0.0) und Erklärung in einfachen Worten |
| `einstellungen.beispiel.json` | alle Einstellungen mit Standardwerten, nur zum Nachschlagen |

## Eigene Oberfläche bauen

Eine Datei aus `oberflaechen/` kopieren und den Teil in `Jarvis.registerTheme({...})` ändern. Siehe `anleitung.txt`, Abschnitt 17.

## Lizenz

PolyForm Noncommercial 1.0.0, siehe LICENSE. Nicht-kommerzielle Nutzung erlaubt, kommerzielle Nutzung nur mit meiner Erlaubnis.
