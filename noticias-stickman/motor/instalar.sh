#!/usr/bin/env bash
# Prepara el entorno de Noticias Stickman (voces + librerías). Idempotente.
set -e
pip install -q --break-system-packages piper-tts pycairo numpy pillow kokoro-onnx soundfile 2>/dev/null || pip install -q piper-tts pycairo numpy pillow kokoro-onnx soundfile 2>/dev/null
# Voces naturales (Kokoro) — motor por defecto
mkdir -p /tmp/kok && cd /tmp/kok
[ -f kokoro-v1.0.onnx ] || curl -sSL -o kokoro-v1.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
[ -f voices-v1.0.bin ] || curl -sSL -o voices-v1.0.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
# Voces Piper (respaldo: NS_MOTOR_VOZ=piper)
cd /tmp
for m in es_MX-ald-medium es_MX-claude-high es_AR-daniela-high; do
  if [ ! -f "/tmp/vits-piper-$m/$m.onnx" ]; then
    curl -sSL -o "vits-piper-$m.tar.bz2" "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-$m.tar.bz2"
    tar xjf "vits-piper-$m.tar.bz2" && rm -f "vits-piper-$m.tar.bz2"
  fi
done
echo "Entorno listo"
