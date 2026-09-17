"""
Reels Editor
============
Convierte un video horizontal en 5 clips verticales 1080x1920 listos para
Instagram Reels, con fondo desenfocado, efectos de video/audio y subtitulos
karaoke palabra por palabra quemados via libass.

Requisitos:
    pip install imageio-ffmpeg

Uso:
    python3 reels_editor.py Roger.1.mp4
"""

import json
import os
import subprocess
import sys
import wave

import numpy as np
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
INPUT = sys.argv[1] if len(sys.argv) > 1 else "Roger.1.mp4"
OUTDIR = "reels_output"
WORKDIR = "_work"

W, H = 1080, 1920          # lienzo vertical 9:16
VID_W, VID_H = 1080, 608   # bloque de video (1024x576 -> ancho completo)
VID_Y = 520                # posicion vertical del bloque
CAPTION_Y = 1270           # borde superior de los subtitulos
FONT = "Outfit"
FONT_FILE = "/mnt/skills/examples/canvas-design/canvas-fonts/Outfit-Bold.ttf"

# Paleta
CLR_BASE = "&HFFFFFF&"     # blanco (texto normal)
CLR_HOT = "&H00E5FF&"      # amarillo ambar (palabra activa, BGR)
CLR_BADGE = "&H9BE7FF&"

# -----------------------------------------------------------------------------
# Guion: cortes alineados a pausas reales del audio + texto por frase.
# Los tiempos son ABSOLUTOS respecto al video original.
# -----------------------------------------------------------------------------
PARTS = [
    {
        "name": "parte_1_cinco_minutos",
        "cut": (0.00, 17.80),
        "look": "punch",
        "phrases": [
            (0.64, 10.50, "Cuando te falten CINCO MINUTOS para llegar a una reunión, "
                          "que realmente sean los cinco minutos que te faltan. "
                          "No que estás a media hora,"),
            (11.14, 17.22, "a una hora. A ver: ya estoy saliendo, ya estoy saliendo... "
                           "¡y ni sales de tu casa y ya estás saliendo!"),
        ],
    },
    {
        "name": "parte_2_si_eres_cristiano",
        "cut": (17.80, 31.60),
        "look": "warm",
        "phrases": [
            (18.38, 30.94, "Esas cosas, si eres CRISTIANO, cristiana, ¡NO deberías hacerlo! "
                           "¿Correcto? Este SUCULENTO ají de gallina lo cocinó "
                           "mi esposo, mi esposa..."),
        ],
    },
    {
        "name": "parte_3_di_siempre_la_verdad",
        "cut": (31.60, 46.90),
        "look": "clean",
        "phrases": [
            (31.92, 34.72, "o lo mandaste a comprar al mejor restaurante."),
            (35.14, 46.78, "Tú siempre tienes que decir la VERDAD. "
                           "Hijo, dile al panadero, al gasfitero, al lechero:"),
        ],
    },
    {
        "name": "parte_4_que_le_ensenas",
        "cut": (46.90, 65.93),
        "look": "warm",
        "phrases": [
            (47.02, 62.44, "«DILE QUE NO ESTOY». ¿Qué estás ENSEÑANDO a tu hijo? "
                           "¿Cómo estamos FORMANDO en VALORES a nuestros hijos? "
                           "Que tu SÍ sea SÍ y tu NO sea NO. Si lanzas una palabra"),
            (62.64, 65.30, "con VERACIDAD, que sea tal cual lo estás"),
        ],
    },
    {
        "name": "parte_5_tu_palabra_tiene_poder",
        "cut": (65.93, 81.48),
        "look": "close",
        "phrases": [
            (66.56, 72.38, "viviendo en ese momento. Enseñemos a nuestros hijos"),
            (73.20, 79.08, "y a nuestro entorno a ser siempre EJEMPLO y TESTIMONIO "
                           "desde la palabra. ¡Tu palabra TIENE PODER!"),
            (80.08, 80.88, "¡BENDICIONES!"),
        ],
    },
]

MAX_WORDS = 4      # palabras por bloque en pantalla
MAX_CHARS = 30


# -----------------------------------------------------------------------------
# Analisis de audio: mapa de pausas para que las palabras caigan sobre voz
# -----------------------------------------------------------------------------
def speech_pauses(wav_path):
    w = wave.open(wav_path)
    sr = w.getframerate()
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    hop = int(sr * 0.02)
    rms = np.array([np.sqrt((a[i:i + hop] ** 2).mean()) + 1e-9
                    for i in range(0, len(a) - hop, hop)])
    db = 20 * np.log10(rms)
    sm = np.convolve(db, np.ones(5) / 5, mode="same")
    lo, hi = np.percentile(sm, 10), np.percentile(sm, 90)
    voiced = sm > lo + 0.42 * (hi - lo)

    pauses, i = [], 0
    while i < len(voiced):
        if not voiced[i]:
            j = i
            while j < len(voiced) and not voiced[j]:
                j += 1
            if (j - i) * 0.02 >= 0.18:
                pauses.append((i * 0.02, j * 0.02))
            i = j
        else:
            i += 1
    return pauses


def speech_spans(t0, t1, pauses):
    """Intervalos con voz dentro de [t0, t1]."""
    spans, cur = [], t0
    for ps, pe in pauses:
        if pe <= t0 or ps >= t1:
            continue
        ps, pe = max(ps, t0), min(pe, t1)
        if ps > cur:
            spans.append((cur, ps))
        cur = max(cur, pe)
    if cur < t1:
        spans.append((cur, t1))
    if not spans:
        return [(t0, t1)]
    # Si "voz detectada" cubre menos de la mitad del tramo, el umbral fue
    # demasiado agresivo (habla de bajo volumen): reparte sobre todo el tramo.
    if sum(e - s for s, e in spans) < 0.55 * (t1 - t0):
        return [(t0, t1)]
    return spans


def map_to_wall(frac, spans):
    """Convierte una posicion 0-1 del eje 'tiempo hablado' a tiempo real."""
    total = sum(e - s for s, e in spans)
    target, acc = frac * total, 0.0
    for s, e in spans:
        d = e - s
        if acc + d >= target:
            return s + (target - acc)
        acc += d
    return spans[-1][1]


# Palabras que no deben quedar colgando al final de un bloque en pantalla.
ORPHANS = {
    "a", "al", "ante", "con", "contra", "de", "del", "desde", "e", "el", "en",
    "entre", "hacia", "hasta", "la", "las", "lo", "los", "mi", "mis", "ni",
    "o", "para", "por", "que", "se", "según", "si", "sin", "sobre",
    "su", "sus", "tu", "tus", "un", "una", "unas", "unos", "y",
}
END_PUNCT = (".", "?", "!", ":", "…")


def _bare(w):
    return w.strip("¡!¿?.,;:«»\"'()-…").lower()


def _ends_sentence(w):
    return w.rstrip('"\'»)').endswith(END_PUNCT)


def chunk_words(text):
    """Agrupa el texto en bloques cortos para pantalla.

    Reglas: corta en fin de oracion, no supera MAX_WORDS/MAX_CHARS, y nunca
    deja una preposicion o articulo colgando al final de un bloque.
    """
    # 1. Separa en oraciones (conserva la puntuacion).
    sentences, cur = [], []
    for wd in text.split():
        cur.append(wd)
        if _ends_sentence(wd):
            sentences.append(cur)
            cur = []
    if cur:
        sentences.append(cur)

    chunks = []
    for sent in sentences:
        # 2. Empaqueta por longitud dentro de cada oracion.
        packed, cur = [], []
        for wd in sent:
            trial = cur + [wd]
            if cur and (len(trial) > MAX_WORDS or len(" ".join(trial)) > MAX_CHARS):
                packed.append(cur)
                cur = [wd]
            else:
                cur = trial
        if cur:
            packed.append(cur)

        # 3. Empuja las palabras huerfanas al bloque siguiente.
        for i in range(len(packed) - 1):
            while len(packed[i]) > 1 and _bare(packed[i][-1]) in ORPHANS:
                packed[i + 1].insert(0, packed[i].pop())

        # 4. Un bloque final de una sola palabra se une al anterior.
        if len(packed) > 1 and len(packed[-1]) == 1:
            merged = packed[-2] + packed[-1]
            if len(" ".join(merged)) <= MAX_CHARS + 8:
                packed[-2] = merged
                packed.pop()

        chunks.extend(packed)
    return chunks


def word_times(phrase, pauses):
    """Reparte las palabras sobre el tiempo con voz, ponderando por longitud."""
    t0, t1, text = phrase
    spans = speech_spans(t0, t1, pauses)
    chunks = chunk_words(text)
    flat = [w for c in chunks for w in c]
    weights = [len(w) + 1.6 for w in flat]
    total_w = sum(weights)

    times, acc = [], 0.0
    for wt in weights:
        s = map_to_wall(acc / total_w, spans)
        acc += wt
        e = map_to_wall(acc / total_w, spans)
        times.append((s, max(e, s + 0.12)))

    out, k = [], 0
    for c in chunks:
        out.append([(w, *times[k + i]) for i, w in enumerate(c)])
        k += len(c)
    return out


# -----------------------------------------------------------------------------
# Generacion del ASS (karaoke: una linea por palabra activa)
# -----------------------------------------------------------------------------
def ass_time(t):
    t = max(0.0, t)
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def esc(s):
    return s.replace("\\", "").replace("{", "(").replace("}", ")")


def build_ass(part, idx, pauses, path):
    cut0, cut1 = part["cut"]
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{FONT},80,{CLR_BASE},{CLR_BASE},&H000000&,&H80000000&,-1,0,0,0,100,100,0.6,0,1,6,3,8,90,90,60,1
Style: Badge,{FONT},34,{CLR_BADGE},{CLR_BADGE},&H000000&,&H00000000&,-1,0,0,0,100,100,4,0,1,3,0,8,60,60,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    # Badge de parte
    ev.append(f"Dialogue: 0,{ass_time(0)},{ass_time(min(3.2, cut1 - cut0))},Badge,,0,0,0,,"
              f"{{\\pos({W//2},150)\\an8\\fad(300,400)\\alpha&H40&}}PARTE {idx} / 5")

    for phrase in part["phrases"]:
        for chunk in word_times(phrase, pauses):
            n = len(chunk)
            for i, (_, ws, we) in enumerate(chunk):
                rs, re = ws - cut0, we - cut0
                if re <= 0 or rs >= cut1 - cut0:
                    continue
                rs, re = max(0.0, rs), min(cut1 - cut0, re)
                # Texto completo del bloque, con la palabra activa en ambar
                parts_txt = []
                for j, (wd, _, _) in enumerate(chunk):
                    if j == i:
                        parts_txt.append(f"{{\\c{CLR_HOT}\\3c&H101010&}}{esc(wd)}{{\\c{CLR_BASE}\\3c&H000000&}}")
                    else:
                        parts_txt.append(esc(wd))
                body = " ".join(parts_txt)
                fade = "\\fad(110,0)" if i == 0 else ""
                if i == n - 1:
                    fade = ("\\fad(110,90)" if n == 1 else "\\fad(0,90)")
                ev.append(f"Dialogue: 1,{ass_time(rs)},{ass_time(re)},Cap,,0,0,0,,"
                          f"{{\\pos({W//2},{CAPTION_Y})\\an8{fade}}}{body}")

    with open(path, "w", encoding="utf-8") as f:
        f.write(head + "\n".join(ev) + "\n")
    return len(ev)


# -----------------------------------------------------------------------------
# Render
# -----------------------------------------------------------------------------
LOOKS = {
    "punch": ("eq=contrast=1.10:saturation=1.14:brightness=0.012", 0.070),
    "warm":  ("eq=contrast=1.07:saturation=1.22:gamma_r=1.03:gamma_b=0.985", 0.045),
    "clean": ("eq=contrast=1.05:saturation=1.08", 0.035),
    "close": ("eq=contrast=1.08:saturation=1.12", -0.055),
}


def build_filter(part, dur, ass_path):
    eq, zoom = LOOKS[part["look"]]
    fin, fout = 0.35, 0.45

    # zoompan anima por fotograma (crop evalua w/h solo al inicializar)
    nframes = max(1, int(round(dur * 30)))
    if zoom >= 0:
        zexpr = f"1+{zoom}*on/{nframes}"          # push in
    else:
        z = abs(zoom)
        zexpr = f"{1 + z}-{z}*on/{nframes}"       # pull out

    ass = ass_path.replace("\\", "/").replace(":", r"\:")
    fonts = os.path.dirname(FONT_FILE)

    return (
        # Fondo: rellena 9:16, desenfoque fuerte y oscurecido
        f"[0:v]split=2[bg][fg];"
        f"[bg]scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},gblur=sigma=42,eq=brightness=-0.13:saturation=1.30,"
        f"setsar=1[bgv];"
        # Primer plano: pre-escalado 2x para que el zoom no tiemble
        f"[fg]scale={VID_W*2}:{VID_H*2},"
        f"zoompan=z='{zexpr}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"s={VID_W}x{VID_H}:fps=30,{eq},setsar=1[fgv];"
        # Composicion
        f"[bgv][fgv]overlay=x=0:y={VID_Y}:shortest=1,vignette=angle=PI/5[comp];"
        # Filete superior/inferior del bloque de video
        f"[comp]drawbox=x=0:y={VID_Y - 3}:w={W}:h=3:color=white@0.30:t=fill,"
        f"drawbox=x=0:y={VID_Y + VID_H}:w={W}:h=3:color=white@0.30:t=fill[framed];"
        # Barra de progreso
        f"[framed]drawbox=x=0:y={H - 12}:w='{W}*t/{dur}':h=12:"
        f"color=0xFFE500@0.95:t=fill[bar];"
        # Subtitulos karaoke
        f"[bar]ass='{ass}':fontsdir='{fonts}'[subbed];"
        # Fundidos
        f"[subbed]fade=t=in:st=0:d={fin},fade=t=out:st={dur - fout:.2f}:d={fout},"
        f"format=yuv420p[v];"
        # Audio: limpia rumor del auto, nivela y funde
        f"[0:a]highpass=f=95,afftdn=nr=10:nf=-28,"
        f"loudnorm=I=-14:TP=-1.5:LRA=11,"
        f"afade=t=in:st=0:d=0.25,afade=t=out:st={dur - 0.4:.2f}:d=0.4[a]"
    )


def main():
    if not os.path.exists(INPUT):
        raise SystemExit(f"No se encontro el video: {INPUT}")
    os.makedirs(OUTDIR, exist_ok=True)
    os.makedirs(WORKDIR, exist_ok=True)

    wav = os.path.join(WORKDIR, "audio16k.wav")
    if not os.path.exists(wav):
        subprocess.run([FFMPEG, "-y", "-v", "error", "-i", INPUT,
                        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", wav],
                       check=True)
    pauses = speech_pauses(wav)
    print(f"Pausas de voz detectadas: {len(pauses)}")

    for idx, part in enumerate(PARTS, 1):
        cut0, cut1 = part["cut"]
        dur = round(cut1 - cut0, 3)
        ass_path = os.path.abspath(os.path.join(WORKDIR, f"{idx:02d}.ass"))
        n_ev = build_ass(part, idx, pauses, ass_path)

        out = os.path.join(OUTDIR, f"{idx:02d}_{part['name']}.mp4")
        fc_path = os.path.join(WORKDIR, f"{idx:02d}.filter")
        with open(fc_path, "w", encoding="utf-8") as f:
            f.write(build_filter(part, dur, ass_path))

        print(f"[{idx}/5] {part['name']}  {cut0:.2f}s-{cut1:.2f}s ({dur:.2f}s, {n_ev} eventos)")
        subprocess.run([
            FFMPEG, "-y", "-v", "error", "-stats",
            "-ss", str(cut0), "-t", str(dur), "-i", INPUT,
            "-filter_complex_script", fc_path,
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-profile:v", "high", "-crf", "19",
            "-preset", "medium", "-r", "30", "-g", "60",
            "-pix_fmt", "yuv420p", "-colorspace", "bt709",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", out,
        ], check=True)
        print(f"      -> {out}")

    print(f"\nListo: 5 clips verticales en '{OUTDIR}/'")


if __name__ == "__main__":
    main()
