#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
[[ $(uname -m) == x86_64 ]] || { echo 'x86_64 erforderlich'; exit 1; }
if command -v podman >/dev/null 2>&1; then engine=podman; userargs=(--userns=keep-id --user "$(id -u):$(id -g)");
elif command -v docker >/dev/null 2>&1; then engine=docker; userargs=(--user "$(id -u):$(id -g)");
else echo 'Portable Build-Umgebung: Podman oder Docker erforderlich. Alternativ ./build-appimage.sh für einen lokalen Testbuild.'; exit 1; fi
"$engine" build -t freejarvis-build-alpha1 -f Dockerfile.portable .
# Separate copy inside container: no mixing Arch venv/native modules with Debian.
mkdir -p dist-portable
"$engine" run --rm "${userargs[@]}" -e HOME=/tmp/freejarvis-home -e CI=true \
  -v "$PWD:/input:ro" -v "$PWD/dist-portable:/output:rw" freejarvis-build-alpha1 bash -c '
  set -euo pipefail
  mkdir -p "$HOME" /tmp/build; cd /tmp/build
  cp /input/{prepare.sh,build-appimage.sh,package.json} .
  cp -r /input/{desktop,scripts,tests} .
  if [[ -f /input/package-lock.json ]]; then cp /input/package-lock.json .; fi
  if [[ -d /input/.speech-cache ]]; then cp -r /input/.speech-cache .; fi
  ./build-appimage.sh
  cp dist/{*.AppImage,SHA256SUMS.txt,build-report.json,npm-audit-*.json} /output/
  cp package-lock.json /output/package-lock.json
  cp stage/assets/desktop-speech/DOWNLOAD-SHA256.txt /output/speech-downloads-sha256.txt
  cp stage/assets/desktop-voice/PACKAGE-SOURCES.txt /output/voice-package-sources.txt
  '
echo 'Portabler Build: dist-portable/'
