#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
python3 tools/validate_assets.py --stage "$stage/game"
godot --headless --path "$stage/game" --editor --import --quit
godot --headless --path "$stage/game" --export-release Web "$stage/index.html"
cp web/{index.html,styles.css,app.js,GODOT-NOTICES.txt} "$stage"
python3 tools/verify_web.py "$stage"
mkdir -p build
for file in index.html index.js index.wasm index.pck index.audio.worklet.js index.audio.position.worklet.js styles.css app.js GODOT-NOTICES.txt; do
    cp "$stage/$file" build/
done
python3 tools/verify_web.py build --strict
