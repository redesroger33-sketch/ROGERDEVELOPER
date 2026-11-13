#!/usr/bin/env bash
# Importa uno o más lotes de fotos descargados con el conector Google_Drive (download_file_content).
# Acepta el .txt (JSON base64) o el .zip que guarda el conector.
# Uso: bash importar_fotos.sh /root/.claude/projects/.../tool-results/mcp-Google_Drive-download_file_content-XXXX.txt [...]
# Une creditos.json del lote con el existente (no borra créditos anteriores).
set -e
DEST="$(cd "$(dirname "$0")/.." && pwd)/fotos"
mkdir -p "$DEST"
for f in "$@"; do
  tmp=$(mktemp -d)
  if [[ "$f" == *.zip ]]; then cp "$f" "$tmp/lote.zip"; else jq -r .content "$f" | base64 -d > "$tmp/lote.zip"; fi
  (cd "$tmp" && unzip -oq lote.zip && rm lote.zip)
  if [ -f "$tmp/creditos.json" ]; then
    python3 - "$DEST/creditos.json" "$tmp/creditos.json" <<'EOF'
import json, os, sys
dst, src = sys.argv[1], sys.argv[2]
a = json.load(open(dst)) if os.path.exists(dst) else {}
a.update(json.load(open(src)))
json.dump(a, open(dst, "w"), ensure_ascii=False, indent=1)
EOF
    rm "$tmp/creditos.json"
  fi
  mv -f "$tmp"/*.jpg "$DEST"/ 2>/dev/null || true
  rm -rf "$tmp"
done
ls "$DEST" | wc -l
