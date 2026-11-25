#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
[[ $(uname -m) == x86_64 ]] || { echo 'Dieser Entwicklungsbuild ist für x86_64.'; exit 1; }
./prepare.sh
.build-venv/bin/python -m pip install pyinstaller==6.22.3
.build-venv/bin/python -m PyInstaller --noconfirm --clean --onedir --name freejarvis-backend --distpath "$PWD/stage/runtime" --workpath "$PWD/stage/pyinstaller-work" --specpath "$PWD/stage" "$PWD/stage/assets/desktop_server.py"
JARVIS_TEST_FROZEN="$PWD/stage/runtime/freejarvis-backend/freejarvis-backend" python3 -m unittest discover -s tests -p test_integration.py
npm run dist:linux
version=$(node -p 'require("./package.json").version')
(cd dist && sha256sum "FreeJarvis-Linux-x86_64-${version}.AppImage" | tee SHA256SUMS.txt)
npm audit --omit=dev --json > dist/npm-audit-runtime.json || true
npm audit --json > dist/npm-audit-all.json || true
python3 scripts/build-report.py
