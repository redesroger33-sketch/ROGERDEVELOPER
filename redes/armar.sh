#!/usr/bin/env bash
# Uso: armar.sh entrada.mp4 salida.mp4
# Detecta cada lámina, le aplica zoom-in (Ken Burns 1.00→1.12), une con fundido y pone música original.
set -euo pipefail
IN="$1"; OUT="$2"; DIR="$(dirname "$0")"; W=$(mktemp -d)
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$IN")
if [ -n "${CORTES:-}" ]; then read -ra CUTS <<< "$CORTES"; else mapfile -t CUTS < <(ffmpeg -v info -i "$IN" -vf "select='gt(scene,0.05)',showinfo" -an -f null - 2>&1 | grep -o "pts_time:[0-9.]*" | cut -d: -f2); fi
if [ ${#CUTS[@]} -eq 0 ]; then echo "ERROR: no se detectaron cortes; usa CORTES=\"4 9 14\"" >&2; exit 1; fi
STARTS=(0 "${CUTS[@]}"); ENDS=("${CUTS[@]}" "$DUR")
XF=0.4; FPS=30; N=${#STARTS[@]}
for i in $(seq 0 $((N-1))); do
  S=${STARTS[$i]}; E=${ENDS[$i]}
  L=$(python3 -c "print(round($E-$S+($XF if $i<$N-1 else 0),3))")
  FR=$(python3 -c "print(int($L*$FPS))")
  ffmpeg -v error -y -ss "$(python3 -c "print($S+1.2)")" -i "$IN" -frames:v 1 "$W/s$i.png"
  ffmpeg -v error -y -loop 1 -i "$W/s$i.png" -vf "scale=2160:3840,zoompan=z='1+0.10*on/$FR':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=$FR:s=1080x1920:fps=$FPS,format=yuv420p" -frames:v $FR -c:v libx264 -crf 18 -preset medium "$W/c$i.mp4"
  echo "$L" > "$W/l$i"
done
# encadenar con xfade
ARGS=(); for i in $(seq 0 $((N-1))); do ARGS+=(-i "$W/c$i.mp4"); done
FILT=""; PREV="0:v"; ACC=0
for i in $(seq 1 $((N-1))); do
  L=$(cat "$W/l$((i-1))"); ACC=$(python3 -c "print(round($ACC+$L-$XF,3))")
  FILT+="[$PREV][$i:v]xfade=transition=fade:duration=$XF:offset=$ACC[v$i];"; PREV="v$i"
done
FILT="${FILT%;}"
ffmpeg -v error -y "${ARGS[@]}" -filter_complex "$FILT" -map "[$PREV]" -c:v libx264 -crf 18 -preset medium -r $FPS "$W/video.mp4"
VD=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$W/video.mp4")
python3 "$DIR/musica.py" "$W/musica.wav" "$VD" >/dev/null
ffmpeg -v error -y -i "$W/video.mp4" -i "$W/musica.wav" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$OUT"
rm -rf "$W"
echo "listo: $OUT ($N láminas, ${VD}s)"
