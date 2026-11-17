#!/usr/bin/env bash
# Uso: reel_desde_laminas.sh salida.mp4 lamina_1.png lamina_2.png ... [ -- semitonos ]
# Arma un reel 1080x1920 desde láminas 1080x1350: cada lámina centrada sobre la misma lámina
# ampliada, desenfocada y oscurecida; zoom 1.00→1.10 por lámina, fundido entre láminas y
# música original (portada 4 s, láminas intermedias 5 s, cierre 4 s).
# Opcional: TRANSPONER=<semitonos> para variar la tonalidad de la música cada semana.
set -euo pipefail
OUT="$1"; shift
DIR="$(cd "$(dirname "$0")" && pwd)"; W=$(mktemp -d)
N=$#; [ "$N" -ge 2 ] || { echo "ERROR: se necesitan al menos 2 láminas" >&2; exit 1; }
i=0; LISTA="$W/lista.txt"; : > "$LISTA"; CORTES=""; T=0
for L in "$@"; do
  ffmpeg -v error -y -i "$L" -filter_complex \
    "[0:v]scale=1080:1350:force_original_aspect_ratio=decrease,pad=1080:1350:(ow-iw)/2:(oh-ih)/2[fg];\
     [0:v]scale=1440:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=40,eq=brightness=-0.25[bg];\
     [bg][fg]overlay=(W-w)/2:(H-h)/2" -frames:v 1 "$W/f$i.png"
  if [ $i -eq 0 ] || [ $i -eq $((N-1)) ]; then D=4; else D=5; fi
  printf "file '%s'\nduration %s\n" "$W/f$i.png" "$D" >> "$LISTA"
  T=$((T+D)); [ $i -lt $((N-1)) ] && CORTES="$CORTES $T"
  i=$((i+1))
done
printf "file '%s'\n" "$W/f$((N-1)).png" >> "$LISTA"
ffmpeg -v error -y -f concat -safe 0 -i "$LISTA" -vf "fps=30,format=yuv420p" -c:v libx264 -crf 18 -t $T "$W/base.mp4"
CORTES="${CORTES# }" "$DIR/armar.sh" "$W/base.mp4" "$OUT"
rm -rf "$W"
