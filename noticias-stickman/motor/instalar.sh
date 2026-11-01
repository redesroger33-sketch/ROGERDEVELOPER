#!/usr/bin/env bash
# Prepara el entorno de Noticias Stickman (voces + librerías). Idempotente.
set -e
pip install -q piper-tts pycairo numpy pillow 2>/dev/null
cd /tmp
for m in es_MX-ald-medium es_MX-claude-high es_AR-daniela-high; do
  if [ ! -f "/tmp/vits-piper-$m/$m.onnx" ]; then
    curl -sSL -o "vits-piper-$m.tar.bz2" "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-$m.tar.bz2"
    tar xjf "vits-piper-$m.tar.bz2" && rm -f "vits-piper-$m.tar.bz2"
  fi
done
echo "Entorno listo"
