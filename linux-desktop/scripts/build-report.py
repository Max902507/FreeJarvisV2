from pathlib import Path
import json, re, subprocess, platform
root=Path(__file__).resolve().parents[1]
files=[]
for directory in ('stage/runtime','stage/assets/desktop-voice','stage/assets/desktop-speech','dist/linux-unpacked'):
    if directory=='dist/linux-unpacked': candidates=[root/directory/'freejarvis']
    else:candidates=(root/directory).rglob('*')
    for p in candidates:
        if not p.is_file():continue
        with p.open('rb') as f:
            if f.read(4)!=b'\x7fELF':continue
        try:
            out=subprocess.run(['readelf','--version-info',str(p)],capture_output=True,text=True,check=True).stdout
            # Version requirements only, not the symbols provided by a library.
            out=out.split('Version needs section',1)[-1] if 'Version needs section' in out else ''
            v=sorted({tuple(map(int,x.split('.'))) for x in re.findall(r'Name: GLIBC_(\d+\.\d+)',out)})
            if v:files.append({'file':str(p.relative_to(root)),'glibc_required_max':'.'.join(map(str,v[-1]))})
        except (OSError,subprocess.CalledProcessError):pass
report={'builder':platform.platform(),'builder_glibc':platform.libc_ver(),'elf_glibc_requirements':files,'note':'Static ELF version scan is not a distribution compatibility test.'}
(root/'dist/build-report.json').write_text(json.dumps(report,indent=2)+'\n')
print('Buildbericht: dist/build-report.json')
