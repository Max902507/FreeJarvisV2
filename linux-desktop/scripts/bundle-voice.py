#!/usr/bin/env python3
"""Package the builder's installed eSpeak as a separate offline WAV generator.
The target machine does not need eSpeak. Never bundle glibc or the ELF loader.
"""
import json, os, re, shutil, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'stage/assets/desktop-voice'

def run(args, **kw): return subprocess.run(args,check=True,capture_output=True,**kw)

def library_dependencies(deps):
    for line in deps.splitlines():
        m=re.search(r'^\s*(\S+)\s+=>\s+(/\S+)',line)
        if not m: continue
        soname,src=m.groups()
        # Some ldd versions report absolute loader paths on both sides of =>.
        soname=Path(soname).name
        source_name=Path(src).name
        if any(n.startswith(('ld-linux','ld-musl')) for n in (soname,source_name)): continue
        if not soname or soname in ('.','..'): raise RuntimeError('Ungültiger Bibliotheksname')
        if re.fullmatch(r'lib(?:c|m|pthread|rt|dl|resolv|util|anl|nss_[\w]+)\.so(?:\.\d+)*',soname): continue
        yield soname,src

def main():
    executable=shutil.which('espeak-ng') or shutil.which('espeak')
    if not executable: sys.exit('Auf dem BUILD-System fehlt eSpeak(-NG). Nutze build-portable.sh oder installiere es dort.')
    version=run([executable,'--version'],text=True).stdout.strip()
    match=re.search(r'Data at:\s*(.+)',version)
    if not match: raise RuntimeError('eSpeak-Datenverzeichnis nicht ermittelbar: '+version)
    data=Path(match.group(1).strip())
    if not data.is_dir(): raise RuntimeError('Sprachdaten fehlen: '+str(data))
    if OUT.exists(): shutil.rmtree(OUT)
    for name in ('bin','lib','licenses'): (OUT/name).mkdir(parents=True)
    binary=OUT/'bin'/Path(executable).name
    shutil.copy2(executable,binary)
    shutil.copytree(data,OUT/data.name)
    deps=run(['ldd',executable],text=True).stdout
    if 'not found' in deps: raise RuntimeError(deps)
    copied=[Path(executable),data]
    for soname,src in library_dependencies(deps):
        shutil.copy2(src,OUT/'lib'/soname);copied.append(Path(src))
    packages={}
    for src in copied:
        if shutil.which('dpkg-query'):
            for lookup in dict.fromkeys([str(src),str(src.resolve())]):
                r=subprocess.run(['dpkg-query','-S',lookup],capture_output=True,text=True)
                if r.returncode==0:
                    for line in r.stdout.splitlines():
                        pkg=line.split(': ',1)[0].split(', ')[0]
                        v=subprocess.run(['dpkg-query','-W','-f=${binary:Package}\t${Version}\t${source:Package}\t${source:Version}',pkg],capture_output=True,text=True)
                        if v.returncode==0:
                            packages[pkg]=v.stdout; doc=Path('/usr/share/doc')/pkg.split(':')[0]/'copyright'
                            if doc.is_file():shutil.copyfile(doc,OUT/'licenses'/(pkg.replace(':','_')+'.txt'))
                    break
        elif shutil.which('pacman'):
            r=subprocess.run(['pacman','-Qoq',str(src)],capture_output=True,text=True)
            if r.returncode==0:
                for pkg in r.stdout.splitlines():
                    v=subprocess.run(['pacman','-Q',pkg],capture_output=True,text=True);packages[pkg]=v.stdout.strip()
                    loc=Path('/usr/share/licenses')/pkg
                    if loc.is_dir():shutil.copytree(loc,OUT/'licenses'/pkg,dirs_exist_ok=True)
    for name in ('GPL-2','GPL-3','LGPL-2.1','LGPL-3'):
        p=Path('/usr/share/common-licenses')/name
        if p.is_file():shutil.copyfile(p,OUT/'licenses'/name)
    (OUT/'PACKAGE-SOURCES.txt').write_text(version+'\n'+ '\n'.join(sorted(packages.values()))+'\n\nSource locations: https://sources.debian.org/ ; https://archlinux.org/packages/ ; https://github.com/espeak-ng/espeak-ng\nPublic redistribution requires corresponding source and notice review.\n')
    env=dict(os.environ,LD_LIBRARY_PATH=str(OUT/'lib'))
    # eSpeak variants differ in how --path is interpreted; test both without using host data.
    for rel in ('.',data.name):
        args=[str(binary),'--path='+str(OUT/rel),'--stdout','--stdin','-v','de']
        r=subprocess.run(args,input=b'Guten Morgen.',capture_output=True,env=env,timeout=20)
        if r.returncode==0 and r.stdout.startswith(b'RIFF') and len(r.stdout)>1000:
            (OUT/'voice.json').write_text(json.dumps({'executable':'bin/'+binary.name,'data_path':rel,'version':version},ensure_ascii=False));break
    else: raise RuntimeError('Gebündelte Sprachausgabe fehlgeschlagen')
    print('Gebündelte eSpeak-Stimme getestet:',version)
if __name__=='__main__':main()
