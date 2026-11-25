#!/usr/bin/env python3
"""Desktop entry point; original FreeJarvis server.py and themes are not modified."""
import hmac
import json
import urllib.parse
import sys
from desktop_speech import Speech, SpeechError
from linux_integration import install, suggestions
import os
import shutil
import subprocess
from pathlib import Path

import server as jarvis

DATA_FILES = {
    'SETTINGS_FILE': 'einstellungen.json', 'MEMORY_FILE': 'gedaechtnis.json',
    'BOTSTAT_FILE': 'bot_statistik.json', 'KOSTEN_FILE': 'kosten.json',
    'CLOUD_VERLAUF_FILE': 'cloud_verlauf.json', 'FEHLER_FILE': 'fehler.log',
}


def main():
    os.umask(0o077)
    token = os.environ.pop('JARVIS_DESKTOP_TOKEN')
    if len(token) != 64:
        raise RuntimeError('Ungültige Desktop-Sitzung')
    asset_dir = Path(os.environ['JARVIS_ASSET_DIR']).resolve(strict=True)
    data_dir = Path(os.environ['JARVIS_DATA_DIR']).resolve()
    data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    data_dir.chmod(0o700)
    jarvis.BASE = str(asset_dir)
    for key, filename in DATA_FILES.items():
        setattr(jarvis, key, str(data_dir / filename))
    speech = Speech(asset_dir)
    install(jarvis, data_dir)
    class DesktopHandler(jarvis.Handler):
        def eigen(self, post=False):
            return (super().eigen(post) and hmac.compare_digest(
                self.headers.get('X-FreeJarvis-Desktop', '').encode(), token.encode()))
        def do_GET(self):
            path = urllib.parse.urlparse(self.path).path
            if path == '/api/desktop/speech/status':
                if not self.local() or not self.eigen(): return self.send_json(403, {'error':'Nicht erlaubt.'})
                return self.send_json(200,speech.caps())
            return super().do_GET()

        def do_POST(self):
            path = urllib.parse.urlparse(self.path).path
            if not path.startswith('/api/desktop/speech/'):
                return super().do_POST()
            if not self.local() or not self.eigen(post=True): return self.send_json(403, {'error':'Nicht erlaubt.'})
            if 'json' not in (self.headers.get('Content-Type') or '').lower(): return self.send_json(415, {'error':'Nur JSON.'})
            data=self.body(); op=path.rsplit('/',1)[1]
            try:
                if op=='start': result=speech.start(data.get('lang','de-DE'))
                elif op=='chunk': result=speech.chunk(str(data.get('id','')),data.get('pcm',''))
                elif op=='stop': result=speech.close(str(data.get('id','')))
                elif op=='tts':
                    audio=speech.synth(data)
                    self.send_response(200);self.send_header('Content-Type','audio/wav');self.send_header('Content-Length',str(len(audio)));self.send_header('Cache-Control','no-store');self.schutz();self.end_headers();self.wfile.write(audio);return
                else:return self.send_json(404,{'error':'Unbekannte Sprachfunktion.'})
                return self.send_json(200,result)
            except (SpeechError,OSError,ValueError,subprocess.TimeoutExpired) as e:
                return self.send_json(422,{'error':str(e)})

        def static(self,path):
            if path not in ('/core/core.js','/core/pc.js'):
                return super().static(path)
            source=(asset_dir/path.lstrip('/')).read_text(encoding='utf-8')
            if path=='/core/core.js':
                caps=speech.caps()
                # Keep original UI, route its existing file picker to the narrowly scoped Electron bridge.
                needle='async function api(path, body) {'
                if source.count(needle)!=1: raise RuntimeError('Unbekannte Upstream-API-Funktion')
                source=source.replace(needle,needle+"\n    if (path === '/api/pc/waehlen' && window.freejarvisDesktop) return window.freejarvisDesktop.pickPath(body?.art);",1)
                # Same UI, accurate desktop-specific help and local microphone behavior.
                if caps['stt']:
                    source=source.replace(' || J.settings.strikt_lokal) return false;', ') return false;',1)
                    source=source.replace('if (J.settings.strikt_lokal) { toast("Strikt lokal ist an: Die Spracheingabe des Browsers läuft über einen Online-Dienst und ist deshalb aus. Bitte tippen.", true, 6000); return; }','')
                    source=source.replace('Bereit · strikt lokal · bitte tippen','Bereit · strikt lokal')
                    source=source.replace('Die Spracherkennung läuft im Browser (Chrome oder Edge) und braucht Internet.','Die Spracherkennung läuft lokal auf deinem PC und braucht kein Internet.')
                    source=source.replace('st.strikt_lokal ? "aus (bitte tippen)" : "läuft über einen Online-Dienst des Browsers (Chrome: Google, Edge: Microsoft)" + (st.mikro === "aus" ? ", aber nur, wenn du den Mikro-Knopf drückst" : ""), !st.strikt_lokal','"lokal auf deinem PC" + (st.mikro === "aus" ? ", nur per Mikro-Knopf" : ""), false')
                    source=source.replace(' und die Spracheingabe des Browsers.','; lokale Spracheingabe bleibt verfügbar.')
                source=source.replace('toast("Kein Mikrofon gefunden.", true, 5000)','toast(e.message || "Kein Mikrofon gefunden.", true, 5000)')
                if caps['tts']:
                    source=source.replace('Die Browser-Stimme ist kostenlos. In Microsoft Edge gibt es besonders natürliche Stimmen (Name enthält „Natural“).','Die lokale Systemstimme ist kostenlos und benötigt kein Internet.')
                    source=source.replace('Browser-Stimme','Lokale Stimme')
                    source=source.replace('Lokale Stimme. Achtung: Stimmen mit „Online“ oder „Natural“ im Namen laufen über Server von Microsoft bzw. Google','Lokale Stimme auf deinem PC')
                    source=source.replace('!st.strikt_lokal && st.stimme !== "aus"','!st.strikt_lokal && st.stimme === "elevenlabs"')
                prefix='window.__freejarvisSpeechCaps='+json.dumps(caps)+';\n'+(asset_dir/'speech-adapter.js').read_text(encoding='utf-8')+'\n'
                source=prefix+source
            else:
                # Use only installed programs as suggestions, preserving manual entry and permission rules.
                import re
                source=re.sub(r'linux: \[\[.*?\]\]', lambda m:'linux: '+json.dumps(suggestions(),ensure_ascii=False),source,count=1)
                source=source.replace('sysname = "windows"','sysname = "linux"')
                source=source.replace(r'C:\\Users\\Du\\Documents','/home/du/Dokumente').replace('z.B. notepad.exe','z.B. firefox').replace('(notepad.exe)','(firefox)')
                source=source.replace('oder der volle Pfad zur .exe oder Verknüpfung','oder der volle Pfad zur ausführbaren Datei bzw. installierten .desktop-Datei')
                source=source.replace('Nicht gefunden. Windows-Programme wie calc.exe starten oft trotzdem.','Programm nicht gefunden.')
            data=source.encode('utf-8');self.send_response(200);self.send_header('Content-Type','text/javascript; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.schutz();self.end_headers();self.wfile.write(data)
    jarvis.pc_waehlen = lambda art: {"ok":False,"pfad":"","fehler":"Bitte den Desktop-Auswahldialog verwenden oder den Pfad eintippen."}
    jarvis.load_settings()
    jarvis.botstat_load()
    jarvis.kosten_load()
    jarvis.cloud_verlauf_load()
    port = int(os.environ.get('JARVIS_DESKTOP_PORT', '5051'))
    # Do not attach to an existing service or silently change the localStorage origin.
    with jarvis.Server(('127.0.0.1', port), DesktopHandler) as srv:
        jarvis.AKTIV_PORT[0] = srv.server_port
        print(f'FREEJARVIS_READY {srv.server_port}', flush=True)
        srv.serve_forever()

if __name__ == '__main__':
    main()
