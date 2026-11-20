# Änderungen

## 2.1 · Websuche für alle, günstigere Gespräche, zweiter Prüfbericht

Danke an **Thomas** für den zweiten Prüfbericht und an die **Community** für die Rückmeldungen. Nicht jeder Vorschlag ist umgesetzt: Was in einer Einzelplatz-Anwendung wenig bringt oder neue Abhängigkeiten bräuchte, ist bewusst draußen geblieben (siehe unten).

**Neu**
- Websuche für Ollama und OpenAI-kompatible KIs über eine eigene SearXNG-Instanz. Jarvis sucht bei „Such mal nach …“ sofort, sonst kann die KI selbst eine Suche anfordern. Die KI bekommt 5 Treffer als kurze Auszüge, keine ganzen Seiten. Mit privaten Daten im Suchbegriff und im strikten Modus wird nicht gesucht
- Zwischenspeicher (Prompt-Caching) für Claude: Feste Anweisungen und bisheriger Verlauf kosten ab der zweiten Frage nur noch einen Bruchteil. Dafür wird der Verlauf in Stufen gekürzt, und Uhrzeit und erledigte Befehle stehen bei der aktuellen Frage. Die Kostenrechnung berücksichtigt gelesene und geschriebene Zwischenspeicher-Token. Abschaltbar
- Fehlermeldungen gehen nicht mehr verloren, wenn der Browser die Verbindung trennt (unter Windows: ConnectionAbortedError). Der Server fängt das ab, beendet die laufende KI-Anfrage und schreibt die Meldung ins Terminal und nach `fehler.log`

**Aus dem Prüfbericht**
- F-09: Verneinte Sätze („Kinoabend bitte nicht starten“), Erklärfragen und echte Fragen lösen keine Home-Assistant-Aktion und keine Routine mehr aus. Szenen und Skripte brauchen ein Startwort. Höfliche Bitten („Kannst du das Licht anmachen?“) schalten jetzt. Dazu ein ehrlicher Hinweis: Skripte in Home Assistant können auch Schlösser schalten
- F-07: Ein lokal arbeitender Jarvis gibt keine Aufgabe mehr von sich aus an einen Cloud-Bot ab. Die Aufgabe hätte Gedächtnis, Datei-Inhalte oder lokalen Verlauf enthalten können. Cloud-Bots tauchen im lokalen Team-Hinweis gar nicht erst auf. Direkt mit `@Name` angesprochen geht es wie bisher
- F-08: Weiterleitungen werden nicht mehr verfolgt. Python hätte den API-Schlüssel an die neue Adresse mitgeschickt, und eine Heimnetz-Adresse hätte ins Internet umleiten können
- F-10: Die Freigabe-Karte beim Schreiben zeigt den vollständigen Inhalt, genau so, wie er in die Datei kommt
- F-01: Die Anzeige LOKAL/CLOUD übernimmt die Adress-Einstufung vom Server statt eines Textvergleichs (`192.168.x.x` war vorher „Cloud“, `localhost.beispiel.com` „lokal“)
- F-05: Ist der Bot-Verlauf aus, wird auch die letzte Aufgabe nicht mehr gespeichert
- Kostenlimit: Für ein Modell ohne hinterlegten Preis wird bei gesetztem Limit nichts gesendet, weil sonst mit 0 Dollar gerechnet würde
- OpenAI-kompatible Dienste bekommen eine Obergrenze für die Antwortlänge (bei api.openai.com als `max_completion_tokens`). Kennt ein Server die Option nicht, versucht Jarvis es ohne
- Dateifilter prüft den Pfad erst nach dem Auflösen (hatte keine praktische Auswirkung)
- F-11: README und Anleitung sagen ehrlich, dass Programme unter dem eigenen Benutzerkonto Jarvis ansprechen können. „Strikt lokal“ heißt jetzt korrekt „nichts geht ins Internet“, Heimnetz-Adressen bleiben erlaubt

**Aus der Community**
- PC-Steuerung, Endlosschleife beim Speichern (Danke Frank): Die Rückmeldung nach einer Dateiaktion ist jetzt eindeutig („ERFOLGREICH ERLEDIGT … nicht wiederholen“), und dieselbe Aktion läuft pro Frage nur einmal
- Home Assistant: Der Hinweis „Läuft ohne KI und ohne Token“ stand über dem Token-Feld. Jetzt: läuft ohne KI und ohne KI-Kosten, den Zugriffstoken braucht es trotzdem
- Doku: Update immer in einen neuen, leeren Ordner. Max-Klon und FreeJarvis nicht mischen. Ollama im Heimnetz Schritt für Schritt. Liste „Kann und kann nicht“

**Bewusst nicht umgesetzt**
- Schlüssel im Schlüsselspeicher des Betriebssystems: bräuchte Zusatzpakete und schützt kaum gegen Schadsoftware unter dem eigenen Konto
- Zugangs-Token gegen andere Programme auf demselben PC: Diese Programme können die Einstellungen ohnehin lesen. Vielleicht in Version 3
- Home Assistant mit App-Umschaltung, Heizung, Lichtfarben, Räumen: geplant für Version 3
- PC-Freigaben pro Aktion: weitgehend schon so (Schreiben eigener Schalter, Skripte immer mit Nachfrage, Löschen gibt es nicht)
- Echtzeit-Sprachmodus und Installer: zu großer Umbau für diese Version
- Schon erledigt: Websuche ist seit 2.0 standardmäßig aus, Kostenlimit und Kosten-Widget gibt es seit 2.0

## 2.0.1 · Datenschutz-Korrekturen

Danke an **Thomas** für den Prüfbericht. Alle Punkte sind umgesetzt und getestet.

**Sicherheit und Datenschutz**
- Hoch: Nach einem Gespräch mit Ollama ging beim Wechsel zu Claude der lokale Verlauf als Kontext mit in die Cloud. Jetzt bekommt eine Cloud-KI nur Verlauf, der schon in der Cloud war. Das entscheidet der Server anhand eigener Prüfsummen (`cloud_verlauf.json`, keine Texte), nicht eine Markierung aus dem Browser. Gilt auch nach Neuladen und Neustart, auch für Bots
- Die aktuelle Frage wird nicht mehr mit einer vorherigen, unbeantworteten Nachricht zusammengelegt
- Mittel: Der Name des Assistenten wurde in der Oberfläche Vortex als HTML eingesetzt. Jetzt nur noch als Text, der Zierpunkt ist ein eigenes Element. Auch die Ereignisliste baut keine HTML-Zeichenketten mehr
- Mittel: Im strikten Modus konnte die Sprachausgabe ohne festgelegte lokale Stimme starten, der Browser hätte dann eine Online-Stimme nehmen können. Jetzt bleibt Jarvis stumm und sagt einmal Bescheid, warum
- „Strikt lokal“ baute trotzdem Verbindungen zu Anthropic auf: beim Laden der Modellliste, beim Verbindungstest und bei automatischer Modellwahl im Chat. Jetzt entsteht keine einzige Verbindung ins Internet
- Niedrig: Die Modellabfrage für OpenAI-kompatible Dienste erkannte „lokal“ noch über einen Textvergleich (`localhost.beispiel.com` galt als lokal). Jetzt überall dieselbe Adressprüfung

**Sonstiges**
- Lizenz: PolyForm Noncommercial 1.0.0 statt MIT, dazu `Rechtshinweis.txt`
- Hinweis im Chat, wenn man von einer lokalen KI in die Cloud wechselt

## 2.0 · das große Update

**KI und Kosten**
- Sparmodus (Standard: an): kürzerer Verlauf, knappes Gedächtnis, Befehle wie Timer ohne KI-Rückfrage, Bots antworten direkt
- Websuche standardmäßig aus, weil jede Suche extra kostet
- Monatslimit in US-Dollar für Cloud-KI; ist es erreicht, wird nichts mehr gesendet
- Kosten-Widget: Verbrauch heute und im Monat, Limit, selbst eingetragenes Guthaben abzüglich Verbrauch
- Token werden so gezählt, wie der Anbieter sie meldet; Listenpreise der Claude-Modelle sind hinterlegt, eigene Preise lassen sich eintragen

**Bots**
- Eigenes KI-Team: jeder Bot mit Auftrag, Modell, Schlüssel und Adresse
- Ansprechen mit `@Name`, „Name, …“, „Frag den Name …“ oder Stichwort; Jarvis kann Aufgaben selbst abgeben
- Bots kreisen sichtbar um Jarvis: 14 Formen, Hover-Karte, Dashboard mit Übersicht und Einstellungen
- Für Bots gelten Privat-Weiche und „Strikt lokal“ wie für Jarvis

**Oberflächen**
- 25 Oberflächen (vorher 7), darunter Avatar (Gesicht aus 3D-Würfeln) und Kosmos 3D in WebGL, Phantom und Retro als Arbeitsübersicht
- Ladescreen mit den echten Startschritten, Vorschaubilder in der Auswahl
- Fenster und Knöpfe in Milchglas-Optik
- Maus-Effekte: Partikel reagieren, Klick-Welle, Ansicht neigt sich; alles abschaltbar
- Hintergrundklang und Effekt-Töne mit Reglern
- Widgets: Wetter, Notizen, Uhr, System, Kosten; verschiebbar und in der Größe änderbar

**Steuerung**
- PC-Steuerung (Standard: aus): freigegebene Ordner und Programme, Textdateien und Skripte lesen und schreiben, mit Nachfrage; kein Löschen, kein Ausführen
- Home Assistant (Standard: aus): Geräte per Sprache und Routine schalten, ohne KI und ohne Token
- Webhook-Routinen für eigene Automationen

**Sicherheit und Datenschutz**
- Schutz-Kopfzeilen: kein Einbetten durch fremde Seiten, Oberfläche lädt und sendet nur an Jarvis selbst
- Server liefert nur noch `core`, `oberflaechen`, `sounds` und `jarvis.html` aus
- „Lokal“ wird an der echten Adresse geprüft (eigener PC und Heimnetz), nicht am Wortlaut
- Der Hauptschlüssel geht nie an die eigene Adresse eines Bots
- Skripte werden nie ohne Nachfrage geschrieben und nie gestartet
- Chatverlauf löschbar oder abschaltbar; Bot-Verlauf abschaltbar
- Auf Linux und macOS sind die Dateien mit Schlüsseln und Notizen nur für den eigenen Benutzer lesbar

## 1.1
- Datenschutz-Modus: Anzeige LOKAL/CLOUD, Privat-Weiche, Strikt lokal

## 1.0
- Erste Version: Ollama, Claude, OpenAI-kompatibel, 7 Oberflächen
