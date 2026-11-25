"""Integration tests against the actual pinned upstream, once prepare.sh has fetched it."""
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'stage' / 'assets'

@unittest.skipUnless((ASSETS / 'server.py').exists(), 'Originalquellcode noch nicht geladen')
class UpstreamIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.token = secrets.token_hex(32)
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0)); cls.port = s.getsockname()[1]
        cls.origin = f'http://127.0.0.1:{cls.port}'
        env = dict(os.environ, JARVIS_DESKTOP_TOKEN=cls.token,
                   JARVIS_ASSET_DIR=str(ASSETS), JARVIS_DATA_DIR=cls.temp.name,
                   JARVIS_DESKTOP_PORT=str(cls.port), PYTHONUNBUFFERED='1')
        cmd = [os.environ['JARVIS_TEST_FROZEN']] if os.environ.get('JARVIS_TEST_FROZEN') else [sys.executable, str(ASSETS/'desktop_server.py')]
        cls.proc = subprocess.Popen(cmd, env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        def stop():
            cls.proc.terminate()
            try: cls.proc.communicate(timeout=5)
            except subprocess.TimeoutExpired: cls.proc.kill(); cls.proc.communicate()
        cls.addClassCleanup(stop)
        import select
        ready, _, _ = select.select([cls.proc.stdout], [], [], 10)
        if not ready: raise RuntimeError('Backend-Start hat Zeitlimit überschritten')
        line = cls.proc.stdout.readline().strip()
        if line != f'FREEJARVIS_READY {cls.port}': raise RuntimeError('Backend nicht gestartet: '+line)

    def request(self, path, token=True, payload=None, extra=None):
        headers = {'X-FreeJarvis-Desktop':self.token} if token else {}
        body = None
        if payload is not None:
            body=json.dumps(payload).encode(); headers.update({'Content-Type':'application/json','X-Jarvis':'1','Origin':self.origin})
        headers.update(extra or {})
        req=urllib.request.Request(self.origin+path,data=body,headers=headers)
        return urllib.request.urlopen(req,timeout=5)

    def test_all_25_themes(self):
        with self.request('/api/status') as r: status=json.load(r)
        self.assertEqual(status['version'],'2.1')
        self.assertEqual(len(status['themes']),25)
        for name, path in status['themes'].items():
            with self.subTest(theme=name), self.request(path) as r:
                self.assertEqual(r.status,200); self.assertIn(b'<html',r.read().lower())

    def test_system_values(self):
        with self.request('/api/system') as r: info=json.load(r)
        self.assertIsInstance(info['cpu'],int)
        self.assertGreater(info['ram_gesamt'],0)
        self.assertGreaterEqual(info['platte_frei'],0)

    def test_speech_adapter_and_security(self):
        with self.request('/core/core.js') as r:
            js=r.read();self.assertIn(b'LocalRecognition',js);self.assertIn(b'window.freejarvisDesktop.pickPath',js)
        with self.request('/api/desktop/speech/status') as r: caps=json.load(r)
        self.assertEqual(set(caps['stt']),{'de','en'})
        self.assertTrue(caps['bundled_tts'])
        with self.request('/api/desktop/speech/tts',payload={'text':'Guten Morgen.','lang':'de-DE'}) as r:
            self.assertTrue(r.read().startswith(b'RIFF'))
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.request('/api/desktop/speech/start',token=False,payload={'lang':'de-DE'})
        self.assertEqual(e.exception.code,403)
        e.exception.close()

    def test_mock_ki_provider_streams(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import threading
        class Provider(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def respond(self, data, content_type):
                self.send_response(200);self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
            def do_GET(self):
                if self.path=='/api/tags': self.respond(b'{"models":[{"name":"testmodel"}]}','application/json')
                elif self.path=='/v1/models': self.respond(b'{"data":[{"id":"testmodel"}]}','application/json')
                else:self.send_error(404)
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                if self.path=='/api/chat':
                    self.respond(b'{"message":{"content":"Desktop-Testantwort"},"done":false}\n{"done":true,"prompt_eval_count":5,"eval_count":3}\n','application/x-ndjson')
                elif self.path=='/v1/chat/completions':
                    self.respond(b'data: {"choices":[{"delta":{"content":"Desktop-Testantwort"}}]}\n\ndata: [DONE]\n\n','text/event-stream')
                else:self.send_error(404)
        with ThreadingHTTPServer(('127.0.0.1',0),Provider) as srv:
            thread=threading.Thread(target=srv.serve_forever,daemon=True);thread.start()
            url=f'http://127.0.0.1:{srv.server_port}'
            try:
                for provider in ('ollama','openai'):
                    with self.subTest(provider=provider):
                        with self.request('/api/settings',payload={'anbieter':provider,'modell':'testmodel','ollama_url':url,'openai_url':url+'/v1','strikt_lokal':True,'auto_merken':False}) as r: json.load(r)
                        with self.request('/api/chat',payload={'messages':[{'role':'user','content':'Erkläre Quantenphysik in einem Satz.'}]}) as r: events=[json.loads(line) for line in r if line.strip()]
                        self.assertTrue(any(e.get('t')=='done' and 'Desktop-Testantwort' in e.get('text','') for e in events),events)
            finally:srv.shutdown();thread.join()

    def test_offline_timer_without_ai(self):
        with self.request('/api/settings',payload={'anbieter':'ollama','modell':'','ollama_url':'http://127.0.0.1:1','strikt_lokal':True}) as r: json.load(r)
        with self.request('/api/chat',payload={'messages':[{'role':'user','content':'Timer für 10 Sekunden'}]}) as r:
            events=[json.loads(line) for line in r if line.strip()]
        self.assertTrue(any(e.get('t')=='action' and e.get('typ')=='timer' for e in events),events)
        self.assertTrue(any(e.get('t')=='done' for e in events),events)

    def test_security(self):
        for path, kwargs in [('/api/settings',{'token':False}),('/api/settings',{'payload':{'name':'bad'},'extra':{'Origin':'http://example.com'}}),('/server.py',{}),('/einstellungen.json',{})]:
            with self.subTest(path=path,kwargs=kwargs), self.assertRaises(urllib.error.HTTPError) as e:
                self.request(path,**kwargs)
            self.assertIn(e.exception.code,(403,404));e.exception.close()

    def test_settings_external_storage(self):
        with self.request('/api/settings',payload={'name':'Desktop-Test'}) as r: self.assertEqual(json.load(r)['name'],'Desktop-Test')
        self.assertTrue((Path(self.temp.name)/'einstellungen.json').exists())
        self.assertFalse((ASSETS/'einstellungen.json').exists())
        with self.request('/api/settings') as r: self.assertEqual(json.load(r)['name'],'Desktop-Test')

if __name__=='__main__': unittest.main()
