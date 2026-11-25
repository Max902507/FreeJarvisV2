#!/usr/bin/env python3
"""Download fixed-version Vosk speech assets from PyPI and Alpha Cephei.
No model is downloaded during the finished application runtime.
"""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import zipfile
ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'.speech-cache'; CACHE.mkdir(exist_ok=True)
OUT=ROOT/'stage/assets/desktop-speech';OUT.mkdir(parents=True,exist_ok=True)
models=['vosk-model-small-de-0.15','vosk-model-small-en-us-0.15']
wheel=next(CACHE.glob('vosk-0.3.45-*-manylinux*x86_64*.whl'),None)
if wheel is None:
    subprocess.run([sys.executable,'-m','pip','download','--no-deps','--only-binary=:all:','--dest',str(CACHE),'vosk==0.3.45'],check=True)
    wheel=next(CACHE.glob('vosk-0.3.45-*-manylinux*x86_64*.whl'))
with zipfile.ZipFile(wheel) as z:
    for n in z.namelist():
        if n=='vosk/libvosk.so':
            with z.open(n) as src,(OUT/'libvosk.so').open('wb') as dest:shutil.copyfileobj(src,dest)
        elif '.dist-info/' in n and ('LICENSE' in n.upper() or 'NOTICE' in n.upper()):
            (OUT/('Vosk-'+Path(n).name)).write_bytes(z.read(n))
if not (OUT/'libvosk.so').is_file(): raise RuntimeError('libvosk.so fehlt')
for model in models:
    target=OUT/model
    archive=CACHE/(model+'.zip')
    if not archive.exists():
        print('Lade kostenloses Sprachpaket:',model,flush=True)
        temp=archive.with_suffix('.part')
        with urllib.request.urlopen('https://alphacephei.com/vosk/models/'+model+'.zip',timeout=120) as src,temp.open('wb') as dst:shutil.copyfileobj(src,dst)
        temp.replace(archive)
    if not (target/'conf/model.conf').exists():
        if target.exists(): shutil.rmtree(target)
        with zipfile.ZipFile(archive) as z:
            for member in z.infolist():
                dest=(OUT/member.filename).resolve()
                if not dest.is_relative_to(target.resolve()):raise RuntimeError('Unerwarteter Pfad im Sprachpaket')
                if member.is_dir():dest.mkdir(parents=True,exist_ok=True)
                else:
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    with z.open(member) as src,dest.open('wb') as dst:shutil.copyfileobj(src,dst)
    if not (target/'conf/model.conf').exists():raise RuntimeError('Modell unvollständig: '+model)
(OUT/'THIRD-PARTY-NOTICES.txt').write_text('Vosk API 0.3.45, Alpha Cephei, https://github.com/alphacep/vosk-api\nGerman and English models: https://alphacephei.com/vosk/models\nApache License 2.0; see Apache-2.0.txt.\n',encoding='utf-8')
shutil.copyfile(ROOT/'scripts/Apache-2.0.txt',OUT/'Apache-2.0.txt')
with (OUT/'DOWNLOAD-SHA256.txt').open('w') as f:
    for p in [wheel]+[CACHE/(m+'.zip') for m in models]:
        h=hashlib.sha256()
        with p.open('rb') as src:
            for b in iter(lambda:src.read(1024*1024),b''):h.update(b)
        f.write(f'{h.hexdigest()}  {p.name}\n')
print('Lokale Spracherkennung: Deutsch und Englisch vorbereitet.')
