"""
Video Processing Script
=======================
Divide el video 'Roger.1.mp4' en 5 partes, aplica efectos de video/audio
y agrega subtitulos estilizados.

Requisitos:
    pip install "moviepy>=2.0" imageio-ffmpeg

Uso:
    python3 process_video.py [ruta_del_video]
"""

import os
import re
import sys

from moviepy import (
    VideoFileClip, TextClip, CompositeVideoClip, afx, vfx
)

INPUT_VIDEO = sys.argv[1] if len(sys.argv) > 1 else "Roger.1.mp4"
OUTPUT_DIR = "output_segments"

# Fuentes candidatas (la primera que exista es la que se usa).
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]

# -----------------------------------------------------------------------------
# Definicion de los 5 segmentos con cortes, efectos y subtitulos
# -----------------------------------------------------------------------------
segments = [
    {
        "name": "parte_1_5_minutos_antes",
        "start": 0.0,
        "end": 13.0,
        "zoom_effect": True,
        "subtitles": [
            {"start": 0.0, "end": 4.5, "text": "Cuando te faltan 5 MINUTOS para llegar..."},
            {"start": 4.5, "end": 8.5, "text": "no cuando estas a media hora o una hora,"},
            {"start": 8.5, "end": 13.0, "text": "dices: !Ya estoy saliendo! y ni sales de tu casa."},
        ],
    },
    {
        "name": "parte_2_compromiso_moral",
        "start": 13.0,
        "end": 30.0,
        "color_boost": True,
        "subtitles": [
            {"start": 13.0, "end": 18.0, "text": "Esas cosas, si eres CRISTIANO, !NO deberias hacerlas!"},
            {"start": 18.0, "end": 24.0, "text": "Este SUCULENTO aji de gallina..."},
            {"start": 24.0, "end": 30.0, "text": "lo cocino mi esposo o lo mandaste a comprar."},
        ],
    },
    {
        "name": "parte_3_mensaje_hijos",
        "start": 30.0,
        "end": 49.0,
        "subtitles": [
            {"start": 30.0, "end": 38.0, "text": "Tu siempre tienes que decir la VERDAD."},
            {"start": 38.0, "end": 45.0, "text": "Hijo, dile al cobrador/gasfitero: !DILE QUE NO ESTOY!"},
            {"start": 45.0, "end": 49.0, "text": "Que le estas ENSENANDO a tu hijo?"},
        ],
    },
    {
        "name": "parte_4_formando_valores",
        "start": 49.0,
        "end": 65.0,
        "color_boost": True,
        "subtitles": [
            {"start": 49.0, "end": 55.0, "text": "Como estamos FORMANDO en VALORES a nuestros hijos?"},
            {"start": 55.0, "end": 60.0, "text": "Que tu SI sea SI y tu NO sea NO."},
            {"start": 60.0, "end": 65.0, "text": "Lanzas una palabra con VERACIDAD y VELOCIDAD."},
        ],
    },
    {
        "name": "parte_5_palabra_con_poder",
        "start": 65.0,
        "end": 81.47,
        "fade_out": True,
        "subtitles": [
            {"start": 65.0, "end": 72.0, "text": "Ensenemos a nuestro entorno a ser EJEMPLO y TESTIMONIO."},
            {"start": 72.0, "end": 78.0, "text": "!Tu palabra TIENE PODER!"},
            {"start": 78.0, "end": 81.47, "text": "!BENDICIONES!"},
        ],
    },
]

EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF]+",
    flags=re.UNICODE,
)


def pick_font():
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    raise SystemExit(
        "No se encontro una fuente TrueType. Instala fuentes DejaVu "
        "o agrega la ruta de tu fuente a FONT_CANDIDATES."
    )


FONT = pick_font()


def create_subtitle_clip(txt, start, end, video_w, video_h):
    """Genera subtitulos estilizados (fondo semi-transparente y texto amarillo)."""
    # Las fuentes del sistema no traen glifos de emoji: se descartan.
    txt = EMOJI_RE.sub("", txt).strip()
    duration = end - start
    txt_clip = TextClip(
        font=FONT,
        text=txt,
        font_size=42,
        color="yellow",
        bg_color=(0, 0, 0, 166),   # negro al 65% de opacidad
        transparent=True,
        method="caption",
        size=(int(video_w * 0.85), None),
        margin=(12, 10),
    )
    txt_clip = txt_clip.with_start(start).with_duration(duration)
    txt_clip = txt_clip.with_position(("center", video_h * 0.75))
    return txt_clip


def apply_zoom(clip, rate=0.03):
    """Zoom in progresivo, recortado al tamano original para no romper el codec."""
    w, h = clip.size
    zoomed = clip.with_effects([vfx.Resize(lambda t: 1 + rate * t)])
    return zoomed.with_effects(
        [vfx.Crop(width=w, height=h, x_center=None, y_center=None)]
    )


def process_video():
    if not os.path.exists(INPUT_VIDEO):
        raise SystemExit(f"No se encontro el archivo de video: {INPUT_VIDEO}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    base_clip = VideoFileClip(INPUT_VIDEO)
    total = base_clip.duration
    print(f"Video de entrada: {INPUT_VIDEO} ({total:.2f}s, {base_clip.size[0]}x{base_clip.size[1]})")

    written = []
    for idx, seg in enumerate(segments, 1):
        start = min(seg["start"], total)
        end = min(seg["end"], total)
        if end - start <= 0:
            print(f"Parte {idx} ({seg['name']}) omitida: fuera de la duracion del video.")
            continue

        print(f"Procesando Parte {idx}: {seg['name']} [{start:.2f}s - {end:.2f}s]...")

        subclip = base_clip.subclipped(start, end)

        # --- Efectos de video ---
        if seg.get("zoom_effect"):
            subclip = apply_zoom(subclip)

        if seg.get("color_boost"):
            subclip = subclip.with_effects([vfx.MultiplyColor(1.15)])

        if seg.get("fade_out"):
            subclip = subclip.with_effects([vfx.FadeOut(1.5)])

        # --- Efectos de audio ---
        if subclip.audio is not None:
            audio = subclip.audio.with_effects(
                [afx.AudioFadeIn(0.3), afx.AudioFadeOut(0.3)]
            )
            subclip = subclip.with_audio(audio)

        # --- Subtitulos ---
        subtitle_clips = []
        w, h = subclip.size
        seg_duration = end - start
        for sub in seg["subtitles"]:
            rel_start = max(0.0, sub["start"] - seg["start"])
            rel_end = min(seg_duration, sub["end"] - seg["start"])
            if rel_end > rel_start:
                subtitle_clips.append(
                    create_subtitle_clip(sub["text"], rel_start, rel_end, w, h)
                )

        final_seg = CompositeVideoClip([subclip] + subtitle_clips)

        out_path = os.path.join(OUTPUT_DIR, f"{idx:02d}_{seg['name']}.mp4")
        final_seg.write_videofile(
            out_path,
            codec="libx264",
            audio_codec="aac",
            fps=30,
            preset="medium",
        )
        final_seg.close()
        written.append(out_path)
        print(f"Guardado: {out_path}")

    base_clip.close()
    print(f"\nListo. {len(written)} archivos en '{OUTPUT_DIR}/'.")


if __name__ == "__main__":
    process_video()
