"""Arma un video de Curious Stories a partir de imágenes, la voz y la línea de tiempo.

Uso:
    python3 armar_video.py <carpeta-del-video> <audio.mp3> <salida.mp4> [musica.mp3]

La carpeta del video debe tener:
    - imagenes/       las escenas (NN-nombre.png)
    - voz-narracion.txt   el texto narrado, un párrafo por bloque
    - escenas.json    la línea de tiempo (qué imagen, movimiento y textos por párrafo)

Los tiempos se ajustan a las pausas reales del audio: se detectan los silencios
y cada cambio de párrafo se pega al silencio más cercano a su tiempo estimado.
"""
import json
import os
import re
import subprocess
import sys

W, H, FPS = 1920, 1080, 30
FUENTE = "DejaVu Sans"
FUENTE_MONO = "DejaVu Sans Mono"


def correr(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"Falló: {' '.join(cmd[:6])}...\n{r.stderr[-2000:]}")
    return r


def duracion(audio):
    r = correr(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "csv=p=0", audio])
    return float(r.stdout.strip())


def silencios(audio):
    r = subprocess.run(["ffmpeg", "-i", audio, "-af",
                        "silencedetect=noise=-35dB:d=0.3", "-f", "null", "-"],
                       capture_output=True, text=True)
    ini = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    fin = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    return [(a + b) / 2 for a, b in zip(ini, fin)]


def tiempos_parrafos(parrafos, total, pausas):
    """Inicio de cada párrafo: estimado por cantidad de palabras y pegado a una pausa real."""
    palabras = [max(1, len(p.split())) for p in parrafos]
    suma = sum(palabras)
    inicios, t = [0.0], 0.0
    for n in palabras[:-1]:
        t += n / suma * total
        inicios.append(t)
    usadas = set()
    for i in range(1, len(inicios)):
        cerca = [p for p in pausas if abs(p - inicios[i]) < 4 and p > inicios[i - 1] + 0.5 and p not in usadas]
        if cerca:
            mejor = min(cerca, key=lambda p: abs(p - inicios[i]))
            usadas.add(mejor)
            inicios[i] = mejor
    return inicios


def clip_imagen(img, dur, mov, salida):
    """Una escena: imagen con movimiento de cámara (efecto Ken Burns)."""
    n = max(1, round(dur * FPS))
    z = {
        "zoom_in": f"1+0.10*on/{n}",
        "zoom_rapido": f"1+0.15*min(on/{FPS * 1.5},1)",
        "zoom_out": f"1.10-0.10*on/{n}",
        "zoom_lento": f"1+0.06*on/{n}",
        "paneo_der": "1.12",
        "subir": "1.15",
    }[mov]
    x = {"paneo_der": f"(iw-iw/zoom)*on/{n}"}.get(mov, "iw/2-(iw/zoom/2)")
    y = {"subir": f"(ih-ih/zoom)*(1-on/{n})"}.get(mov, "ih/2-(ih/zoom/2)")
    filtro = (f"scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,"
              f"crop={W * 2}:{H * 2},"
              f"zoompan=z='{z}':x='{x}':y='{y}':d={n}:s={W}x{H}:fps={FPS},"
              f"format=yuv420p")
    correr(["ffmpeg", "-y", "-loop", "1", "-i", img, "-vf", filtro,
            "-frames:v", str(n), "-c:v", "libx264", "-preset", "medium",
            "-crf", "18", salida])


def tc(s):
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def ass(parrafos, inicios, total, escenas, salida):
    """Subtítulos (abajo) y textos estilo terminal del robot (arriba)."""
    cab = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{FUENTE},62,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,5,2,2,120,120,90,1
Style: Terminal,{FUENTE_MONO},66,&H0066FF33,&H00FFFFFF,&H00000000,&HB4000000,-1,0,0,0,100,100,2,0,3,14,0,8,80,80,70,1
Style: Alerta,{FUENTE_MONO},70,&H003333FF,&H00FFFFFF,&H00000000,&HB4000000,-1,0,0,0,100,100,2,0,3,14,0,8,80,80,70,1
Style: Grande,{FUENTE},88,&H0033DDFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,7,3,5,120,120,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    fines = inicios[1:] + [total]
    for p, a, b in zip(parrafos, inicios, fines):
        # Subtítulos de 6 a 8 palabras, repartidos según el largo de cada trozo.
        pal = p.split()
        trozos, act = [], []
        for w in pal:
            act.append(w)
            if len(act) >= 8 or (len(act) >= 4 and re.search(r"[.?!:…]$", w)):
                trozos.append(" ".join(act)); act = []
        if act:
            trozos.append(" ".join(act))
        t, largo = a, sum(len(x) for x in trozos)
        for tr in trozos:
            d = (b - a) * len(tr) / largo
            ev.append(f"Dialogue: 0,{tc(t)},{tc(t + d - 0.05)},Sub,,0,0,0,,{tr}")
            t += d
    for e in escenas:
        a = inicios[e["parrafo"] - 1] + e.get("retraso", 0)
        for txt in e.get("textos", []):
            ini = a + txt.get("en", 0)
            fin = min(ini + txt.get("dura", 3.5), total)
            estilo = txt.get("estilo", "Terminal")
            # Efecto de máquina de escribir: las letras aparecen una a una.
            letras = txt["texto"]
            paso = max(2, int(60 / max(1, len(letras))))
            maq = "".join(f"{{\\alpha&HFF&\\t({i * paso},{i * paso + 1},\\alpha&H00&)}}{c}"
                          for i, c in enumerate(letras)) if estilo != "Grande" else \
                "{\\fad(300,300)}" + letras
            ev.append(f"Dialogue: 1,{tc(ini)},{tc(fin)},{estilo},,0,0,0,,{maq}")
    open(salida, "w").write(cab + "\n".join(ev) + "\n")


def main():
    carpeta, audio, salida = sys.argv[1:4]
    musica = sys.argv[4] if len(sys.argv) > 4 else None
    parrafos = [p.strip() for p in open(os.path.join(carpeta, "voz-narracion.txt")).read().split("\n\n") if p.strip()]
    escenas = json.load(open(os.path.join(carpeta, "escenas.json")))
    total = duracion(audio)
    fin_video = total + escenas_final(carpeta)
    inicios = tiempos_parrafos(parrafos, total, silencios(audio))
    # Las escenas ya armadas se reutilizan; borra la carpeta "trabajo" si cambias imágenes o tiempos.
    tmp = os.path.join(os.path.dirname(os.path.abspath(salida)), "trabajo")
    os.makedirs(tmp, exist_ok=True)
    clips = []
    for i, e in enumerate(escenas):
        a = inicios[e["parrafo"] - 1] + e.get("retraso", 0)
        sig = escenas[i + 1] if i + 1 < len(escenas) else None
        b = inicios[sig["parrafo"] - 1] + sig.get("retraso", 0) if sig else fin_video
        c = os.path.join(tmp, f"{i:02d}.mp4")
        if not os.path.exists(c):
            clip_imagen(os.path.join(carpeta, "imagenes", e["imagen"]), b - a, e["mov"], c)
        clips.append((c, e))
        print(f"  escena {i + 1}/{len(escenas)}: {e['imagen']} {tc(a)} → {tc(b)}")
    lista = os.path.join(tmp, "lista.txt")
    open(lista, "w").write("".join(f"file '{c}'\n" for c, _ in clips))
    base = os.path.join(tmp, "base.mp4")
    correr(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lista, "-c", "copy", base])
    subs = os.path.join(tmp, "subs.ass")
    ass(parrafos, inicios, total, escenas, subs)

    # Efectos puntuales: destellos y sacudidas de cámara en los momentos marcados.
    efectos = []
    for e in escenas:
        a = inicios[e["parrafo"] - 1] + e.get("retraso", 0)
        for fx in e.get("efectos", []):
            t = a + fx.get("en", 0)
            if fx["tipo"] == "destello":
                efectos.append(f"eq=brightness='if(between(t,{t:.2f},{t + 0.25:.2f}),0.5*(1-(t-{t:.2f})/0.25),0)':eval=frame")
            elif fx["tipo"] == "glitch":
                efectos.append(f"rgbashift=rh=18:bh=-18:enable='between(t,{t:.2f},{t + 0.4:.2f})'")
            elif fx["tipo"] == "oscurecer":
                efectos.append(f"eq=brightness='if(gte(t,{t:.2f}),-0.18,0)':eval=frame")
    sacudidas = [inicios[e["parrafo"] - 1] + e.get("retraso", 0) + fx.get("en", 0)
                 for e in escenas for fx in e.get("efectos", []) if fx["tipo"] == "sacudida"]
    if sacudidas:
        cond = "+".join(f"between(t,{t:.2f},{t + 0.5:.2f})" for t in sacudidas)
        efectos.append(f"scale={W + 40}:{H + 40},crop={W}:{H}:x='20+if({cond},15*sin(t*80),0)':y='20+if({cond},12*cos(t*95),0)'")
    vf = ",".join(efectos + [f"ass={subs}"]) if efectos else f"ass={subs}"

    # Audio: voz + sonidos sintetizados + música opcional.
    entradas = ["-i", base, "-i", audio]
    mezcla, n = ["[1:a]apad[voz]"], 2
    etiquetas = ["[voz]"]
    for e in escenas:
        a = inicios[e["parrafo"] - 1] + e.get("retraso", 0)
        for s in e.get("sonidos", []):
            t = a + s.get("en", 0)
            ms = int(t * 1000)
            if s["tipo"] == "ding":
                entradas += ["-f", "lavfi", "-i", "sine=frequency=1760:duration=0.9"]
                mezcla.append(f"[{n}:a]afade=t=out:st=0.05:d=0.85,volume=0.35,adelay={ms}|{ms}[s{n}]")
            elif s["tipo"] == "error":
                entradas += ["-f", "lavfi", "-i", "aevalsrc='0.4*sgn(sin(2*PI*180*t))':d=0.35"]
                mezcla.append(f"[{n}:a]volume=0.25,adelay={ms}|{ms}[s{n}]")
            elif s["tipo"] == "pop":
                entradas += ["-f", "lavfi", "-i", "anoisesrc=d=1.2:c=white:a=0.6"]
                mezcla.append(f"[{n}:a]volume='if(lt(mod(t,0.13),0.025),1,0)':eval=frame,highpass=f=900,volume=0.5,adelay={ms}|{ms}[s{n}]")
            else:
                continue
            etiquetas.append(f"[s{n}]")
            n += 1
    if musica:
        entradas += ["-stream_loop", "-1", "-i", musica]
        mezcla.append(f"[{n}:a]volume=0.12,afade=t=out:st={fin_video - 3:.2f}:d=3[mus]")
        etiquetas.append("[mus]")
    mezcla.append(f"{''.join(etiquetas)}amix=inputs={len(etiquetas)}:normalize=0:duration=first,"
                  f"atrim=0:{fin_video:.2f}[aout]")
    correr(["ffmpeg", "-y", *entradas, "-filter_complex", ";".join(mezcla),
            "-map", "0:v", "-map", "[aout]", "-vf", vf,
            "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-t", f"{fin_video:.2f}", "-movflags", "+faststart", salida])
    print(f"Listo: {salida} ({tc(fin_video)})")


def escenas_final(carpeta):
    """Segundos extra al final, para la pantalla final de YouTube."""
    return json.load(open(os.path.join(carpeta, "escenas.json")))[-1].get("extra_final", 0)


if __name__ == "__main__":
    main()
