"""Local speech adapters. No microphone data leaves the loopback server."""
import base64
import ctypes as C
import json
import os
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path

MODELS = {'de': 'vosk-model-small-de-0.15', 'en': 'vosk-model-small-en-us-0.15'}


def host_env():
    env = dict(os.environ)
    if 'LD_LIBRARY_PATH_ORIG' in env:
        env['LD_LIBRARY_PATH'] = env.pop('LD_LIBRARY_PATH_ORIG')
    elif getattr(__import__('sys'), 'frozen', False):
        env.pop('LD_LIBRARY_PATH', None)
    return env


class SpeechError(Exception):
    pass


class Speech:
    def __init__(self, assets):
        self.root = Path(assets) / 'desktop-speech'
        self.lock = threading.RLock()
        self.lib = None
        self.models = {}
        self.sessions = {}
        voice_root = Path(assets) / 'desktop-voice'
        self.voice_root = None
        self.voice_args = []
        self.tts = None
        if (voice_root/'voice.json').is_file():
            config=json.loads((voice_root/'voice.json').read_text(encoding='utf-8'))
            candidate=voice_root/config['executable']
            if candidate.is_file():
                self.tts=str(candidate)
                self.voice_root=voice_root
                self.voice_args=['--path='+str(voice_root/config['data_path'])]
        elif not getattr(__import__('sys'),'frozen',False):
            self.tts=shutil.which('espeak-ng') or shutil.which('espeak')

    def caps(self):
        return {'stt': [lang for lang, model in MODELS.items() if (self.root/'libvosk.so').is_file() and (self.root/model/'conf'/'model.conf').is_file()], 'tts': bool(self.tts), 'bundled_tts': bool(self.voice_root)}

    def _load(self):
        if self.lib is not None:
            return self.lib
        lib = C.CDLL(str(self.root/'libvosk.so'))
        specs = {
            'vosk_set_log_level': ([C.c_int], None),
            'vosk_model_new': ([C.c_char_p], C.c_void_p),
            'vosk_recognizer_new': ([C.c_void_p,C.c_float], C.c_void_p),
            'vosk_recognizer_accept_waveform': ([C.c_void_p,C.c_char_p,C.c_int], C.c_int),
            'vosk_recognizer_result': ([C.c_void_p], C.c_char_p),
            'vosk_recognizer_partial_result': ([C.c_void_p], C.c_char_p),
            'vosk_recognizer_free': ([C.c_void_p], None),
        }
        for name, (args, ret) in specs.items():
            f = getattr(lib,name); f.argtypes = args; f.restype = ret
        lib.vosk_set_log_level(-1)
        self.lib = lib
        return lib

    def _prune(self):
        now = time.monotonic()
        for key, (_,last) in list(self.sessions.items()):
            if now-last > 60:
                self.close(key)

    def start(self, lang):
        lang = str(lang).split('-')[0].lower()
        if lang not in self.caps()['stt']:
            raise SpeechError('Lokales Sprachpaket nicht vorhanden: '+lang)
        with self.lock:
            self._prune()
            if len(self.sessions) >= 4:
                raise SpeechError('Zu viele aktive Mikrofon-Sitzungen.')
            lib = self._load()
            if lang not in self.models:
                model = lib.vosk_model_new(os.fsencode(self.root/MODELS[lang]))
                if not model: raise SpeechError('Sprachmodell konnte nicht geladen werden.')
                self.models[lang] = model
            rec = lib.vosk_recognizer_new(self.models[lang], 16000.0)
            if not rec: raise SpeechError('Spracherkennung konnte nicht gestartet werden.')
            key = uuid.uuid4().hex
            self.sessions[key] = (rec,time.monotonic())
            return {'id':key}

    def chunk(self, key, encoded):
        if not isinstance(encoded,str) or len(encoded)>180000:
            raise SpeechError('Ungültiger Audioblock.')
        try: pcm=base64.b64decode(encoded,validate=True)
        except (ValueError,TypeError): raise SpeechError('Ungültiger Audioblock.')
        if not pcm or len(pcm)%2 or len(pcm)>128000:
            raise SpeechError('Ungültiger PCM-Audioblock.')
        with self.lock:
            self._prune()
            if key not in self.sessions: raise SpeechError('Mikrofon-Sitzung abgelaufen.')
            rec,_=self.sessions[key]; self.sessions[key]=(rec,time.monotonic())
            status=self.lib.vosk_recognizer_accept_waveform(rec,pcm,len(pcm))
            if status<0: raise SpeechError('Audio konnte nicht verarbeitet werden.')
            data=json.loads((self.lib.vosk_recognizer_result(rec) if status else self.lib.vosk_recognizer_partial_result(rec)).decode('utf-8'))
            return {'final':bool(status), 'text':data.get('text' if status else 'partial','')}

    def close(self,key):
        with self.lock:
            entry=self.sessions.pop(key,None)
            if entry: self.lib.vosk_recognizer_free(entry[0])
            return {'ok':True}

    def synth(self,data):
        if not self.tts: raise SpeechError('Keine lokale Stimme: Sprachpaket fehlt.')
        text=data.get('text','')
        if not isinstance(text,str) or len(text)>4000: raise SpeechError('Ungültiger Vorlesetext.')
        lang='en-us' if str(data.get('lang','')).lower().startswith('en') else 'de'
        def number(key,default,low,high):
            try: return max(low,min(high,float(data.get(key,default))))
            except (TypeError,ValueError): return default
        rate=int(175*number('rate',1,.4,2.5)); pitch=int(50*number('pitch',1,.2,1.9))
        env=host_env()
        if self.voice_root: env['LD_LIBRARY_PATH']=str(self.voice_root/'lib')
        result=subprocess.run([self.tts,*self.voice_args,'--stdout','--stdin','-v',lang,'-s',str(rate),'-p',str(pitch)],input=text.encode('utf-8'),capture_output=True,timeout=25,env=env)
        if result.returncode or not result.stdout.startswith(b'RIFF'):
            raise SpeechError('Lokale Stimme konnte nicht erzeugt werden.')
        return result.stdout
