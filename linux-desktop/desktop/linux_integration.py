"""Linux-only adapters for the original backend; no changes to browser edition."""
import os
import configparser
import shutil
import stat
import subprocess
import uuid
from pathlib import Path
from desktop_speech import host_env


def open_host(pfad):
    opener=shutil.which('xdg-open')
    args=[opener,str(pfad)] if opener else [shutil.which('gio'),'open',str(pfad)]
    if not args[0]: raise OSError('Kein XDG-Dateiöffner verfügbar.')
    subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=host_env())


def application_dirs():
    home=Path(os.environ.get('XDG_DATA_HOME') or Path.home()/'.local/share')
    system=os.environ.get('XDG_DATA_DIRS') or '/usr/local/share:/usr/share'
    return [p/'applications' for p in [home]+[Path(x) for x in system.split(':') if x.startswith('/')]]


def desktop_entries():
    """Follow XDG precedence, desktop visibility and TryExec; never execute during discovery."""
    seen=set(); desktop=set(os.environ.get('XDG_CURRENT_DESKTOP','').split(':'))
    for root in application_dirs():
        if not root.is_dir():continue
        for p in sorted(root.rglob('*.desktop')):
            ident=str(p.relative_to(root)).replace('/','-')
            if ident in seen:continue
            seen.add(ident)
            cfg=configparser.ConfigParser(interpolation=None,strict=False);cfg.optionxform=str
            try:
                if p.stat().st_size>256000:continue
                cfg.read(p,encoding='utf-8');d=cfg['Desktop Entry']
                if d.get('Type')!='Application' or any(d.get(k,'false').lower()=='true' for k in ('Hidden','NoDisplay','Terminal')):continue
                only=set(d.get('OnlyShowIn','').strip(';').split(';'))- {''}
                notshow=set(d.get('NotShowIn','').strip(';').split(';'))- {''}
                if (only and not desktop & only) or desktop & notshow:continue
                if d.get('TryExec') and not shutil.which(d['TryExec']):continue
                if not d.get('Name') or not d.get('Exec'):continue
                yield p,d
            except (OSError,UnicodeError,ValueError,KeyError,configparser.Error):continue


def suggestions():
    groups=[('Dateien','FileManager',['dolphin','nautilus','thunar','nemo','pcmanfm-qt','pcmanfm','caja','cosmic-files','dde-file-manager']),('Rechner','Calculator',['kcalc','gnome-calculator','galculator','mate-calc','qalculate-gtk','cosmic-calculator']),('Editor','TextEditor',['kate','kwrite','gedit','mousepad','xed','pluma','featherpad','cosmic-edit']),('Browser','WebBrowser',['firefox','chromium','brave','vivaldi','falkon'])]
    entries=list(desktop_entries()) if shutil.which('gio') else []
    result=[]
    for name,category,commands in groups:
        matches=[p for p,d in entries if category in d.get('Categories','').split(';')]
        if matches: result.append([name,str(matches[0])]);continue
        for command in commands:
            if shutil.which(command):result.append([name,command]);break
    return result


def desktop_launch_args(pfad):
    p=Path(pfad)
    if p.suffix!='.desktop':return [pfad]
    # Only installed applications explicitly selected by the user; no arbitrary project desktop files.
    if not p.is_absolute() or not p.is_file():raise OSError('Keine installierte Desktop-Anwendung.')
    if not any(Path(os.path.abspath(p)).is_relative_to(Path(os.path.abspath(root))) for root in application_dirs()):raise OSError('Desktop-Datei liegt außerhalb der Anwendungsverzeichnisse.')
    gio=shutil.which('gio')
    if not gio:raise OSError('GIO fehlt; bitte den ausführbaren Programmpfad verwenden.')
    return [gio,'launch',str(p)]


def install(jarvis,data_dir):
    original_info=jarvis.system_info
    def info():
        d=original_info()
        d['auffaellig']=[x for x in d.get('auffaellig',[]) if not x.startswith('Festplatte ')]
        try:
            du=shutil.disk_usage(data_dir)
            d['platte']=round(100*(du.total-du.free)/du.total)
            d['platte_frei']=round(du.free/1e9)
            if d['platte']>=95:d['auffaellig'].append(f"Festplatte {d['platte']} Prozent")
        except (OSError,ZeroDivisionError):d['platte']=d['platte_frei']=None
        return d
    jarvis.system_info=info
    jarvis._oeffnen=open_host
    orig=jarvis.pc_ausfuehren
    def pc(s,aktion,ziel,inhalt=''):
        if aktion.lower().strip()=='programm':
            progs=s.get('pc_programme') or []
            pr=next((x for x in progs if x['name'].lower()==ziel.lower()),None) or next((x for x in progs if ziel.lower() in x['name'].lower()),None)
            if not pr: return orig(s,aktion,ziel,inhalt)
            pfad=os.path.expanduser(pr['pfad'])
            try:subprocess.Popen(desktop_launch_args(pfad),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=host_env())
            except OSError as e:raise jarvis.PCError(f"'{pr['name']}' konnte nicht gestartet werden: {e.strerror or e}")
            return f"{pr['name']} gestartet",f"Das Programm {pr['name']} wurde gestartet."
        if aktion.lower().strip()=='schreiben':
            if not s.get('pc_schreiben'):return orig(s,aktion,ziel,inhalt)
            p=jarvis.pc_pfad(s,ziel,muss_existieren=False)
            if os.path.splitext(p)[1].lower() not in jarvis.PC_SCHREIBBAR: return orig(s,aktion,ziel,inhalt)
            try: gab=write_with_backup(p,jarvis.pc_inhalt(inhalt))
            except OSError as e:raise jarvis.PCError('Datei konnte nicht sicher geschrieben werden: '+str(e))
            return ('Datei geändert (alte Fassung als .bak gesichert)' if gab else 'Datei angelegt'), f"Die Datei {p} wurde {'überschrieben, die alte Fassung liegt daneben als .bak' if gab else 'neu angelegt'}."
        return orig(s,aktion,ziel,inhalt)
    jarvis.pc_ausfuehren=pc


def write_with_backup(path,text):
    """Never follow backup symlinks, never modify a hardlinked inode in place."""
    path=Path(path)
    if not path.is_absolute():raise OSError('Absoluter Pfad erforderlich')
    fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
    temps=[]
    try:
        for part in path.parent.parts[1:]:
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=child
        name=path.name; backup=name+'.bak'
        def check(n):
            try: info=os.stat(n,dir_fd=fd,follow_symlinks=False)
            except FileNotFoundError:return None
            if not stat.S_ISREG(info.st_mode):raise OSError('Keine reguläre Datei: '+n)
            return info
        old=check(name);check(backup)
        def tmpfile():
            n='.freejarvis-'+uuid.uuid4().hex
            f=os.open(n,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd);temps.append(n);return n,f
        if old:
            n,out=tmpfile()
            with os.fdopen(out,'wb') as target:
                source=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
                with os.fdopen(source,'rb') as src:
                    if not stat.S_ISREG(os.fstat(src.fileno()).st_mode):raise OSError('Keine reguläre Quelldatei')
                    shutil.copyfileobj(src,target)
                os.fchmod(target.fileno(),stat.S_IMODE(old.st_mode)&0o777);target.flush();os.fsync(target.fileno())
            os.replace(n,backup,src_dir_fd=fd,dst_dir_fd=fd);temps.remove(n)
        n,out=tmpfile()
        with os.fdopen(out,'w',encoding='utf-8',newline='\n') as target:
            target.write(text)
            if old:os.fchmod(target.fileno(),stat.S_IMODE(old.st_mode)&0o777)
            target.flush();os.fsync(target.fileno())
        os.replace(n,name,src_dir_fd=fd,dst_dir_fd=fd);temps.remove(n)
        return old is not None
    finally:
        for n in temps:
            try:os.unlink(n,dir_fd=fd)
            except OSError:pass
        os.close(fd)
