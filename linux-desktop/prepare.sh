#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
commit=6f3b9839d79f36c131c29832ebe42538521290ae
if [[ ! -d upstream/.git ]]; then
  git clone https://github.com/Max902507/FreeJarvisV2.git upstream
fi
[[ $(git -C upstream remote get-url origin) == https://github.com/Max902507/FreeJarvisV2.git ]] || { echo 'Unerwartetes Original-Repository'; exit 1; }
# Export the exact original commit without changing or checking out the working tree.
git -C upstream cat-file -e "$commit^{commit}"
rm -rf stage/assets
mkdir -p stage/assets
git -C upstream archive "$commit" | tar -x -C stage/assets
cp desktop/{desktop_server.py,desktop_speech.py,linux_integration.py,speech-adapter.js} stage/assets/
printf '%s\n' "$commit" > stage/assets/UPSTREAM_COMMIT
# Verify the original source and every theme, sound and shared asset byte for byte.
python3 - "$commit" <<'PY'
import hashlib, pathlib, subprocess, sys
commit=sys.argv[1]
paths=subprocess.check_output(['git','-C','upstream','ls-tree','-r','--name-only',commit],text=True).splitlines()
for p in paths:
    expected=subprocess.check_output(['git','-C','upstream','show',f'{commit}:{p}'])
    actual=(pathlib.Path('stage/assets')/p).read_bytes()
    assert hashlib.sha256(expected).digest()==hashlib.sha256(actual).digest(),p
print(f'Originaldateien unverändert: {len(paths)} Dateien geprüft.')
PY
if [[ ! -f package-lock.json ]]; then
  npm install
else
  npm ci
fi
python3 -m venv .build-venv
.build-venv/bin/python scripts/prepare-speech.py
python3 scripts/bundle-voice.py
npm test
