"""Identidad de canal para YouTube: banner, perfil, marca de agua y miniatura.

Uso: python3 branding.py   (desde stickman-canales/herramientas)
Salida: stickman-canales/<canal>/branding/
Medidas oficiales de YouTube:
  banner 2560x1440 (zona segura 1546x423 al centro), perfil 800x800 (se ve en círculo),
  marca de agua 150x150 PNG transparente, miniatura 1280x720.
"""
import math
import os
import sys

import cairo
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "..", "noticias-stickman", "motor"))
import render as R  # noqa: E402

CANALES = {
    "doctor": {
        "nombre": ("DOCTOR", "STICKMAN"),
        "lema": "Salud natural con ciencia",
        "sub": "Hábitos · Alimentos · Plantas · Estudios reales",
        "dia": "NUEVO VIDEO CADA DÍA",
        "c1": "E3F7F9", "c2": "BFE9EE", "acento": "0FA3B1", "acento2": "FF4F9A", "oscuro": "123A4A",
        "elenco": ["bruno", "vita"], "locutor": "bruno",
        "fotos": ["menestras_mix", "malecon_miraflores_4", "lentejas_rojas", "parque_kennedy_3"],
    },
    "cocina": {
        "nombre": ("COCINA", "STICKMAN"),
        "lema": "Recetas peruanas de verdad",
        "sub": "Paso a paso · Con cantidades · Trucos de grandes cocineros",
        "dia": "NUEVA RECETA CADA DÍA",
        "c1": "FFF1DC", "c2": "FFD7A8", "acento": "E63946", "acento2": "FF9F1C", "oscuro": "3B2A20",
        "elenco": ["rosita", "tito", "beto"], "locutor": "tito",
        "fotos": ["lomo_saltado_0", "aji_de_gallina", "aji_amarillo_0", "wok_fuego_0"],
    },
}


def hx(h, a=1.0):
    return R.hx(h, a)


def sunburst(c, w, h, cx, cy, c1, c2, n=28):
    c.set_source_rgba(*hx(c1))
    c.paint()
    c.save()
    c.translate(cx, cy)
    c.set_source_rgba(*hx(c2))
    big = math.hypot(w, h)
    for i in range(n):
        a0 = i * 2 * math.pi / n
        c.move_to(0, 0)
        c.arc(0, 0, big, a0, a0 + math.pi / n)
        c.close_path()
        c.fill()
    c.restore()


def personaje(c, who, cx, cy_cabeza, escala, st, t=1.0):
    """Dibuja el personaje con su cabeza centrada en (cx, cy_cabeza)."""
    c.save()
    c.translate(cx, cy_cabeza)
    c.scale(escala, escala)
    c.translate(-R.CAST[who]["x"], -R.HEAD_Y)
    c.new_path()
    R.draw_character(c, who, t, st)
    c.restore()
    c.new_path()


def texto(c, s, cx, y, size, color, fam=None, outline=None, ow=0, maxw=None):
    fam = fam or R.F_BLACK
    R.font(c, size, fam)
    while maxw and R.tw(c, s) > maxw:
        size -= 2
        R.font(c, size, fam)
    R.text_center(c, s, cx, y, size, hx(color) if isinstance(color, str) else color, fam,
                  outline=hx(outline) if isinstance(outline, str) else outline, ow=ow)
    return size


def logo(c, cfg, cx, cy, escala=1.0):
    """Placa del nombre: DOCTOR / STICKMAN."""
    c.save()
    c.translate(cx, cy)
    c.scale(escala, escala)
    R.rrect(c, -360, -95, 720, 190, 48)
    R.fill_stroke(c, hx(cfg["oscuro"]), hx(cfg["acento"]), 12)
    texto(c, cfg["nombre"][0], 0, -8, 92, R.WHITE, maxw=660)
    texto(c, cfg["nombre"][1], 0, 70, 66, cfg["acento2"], maxw=660)
    c.restore()


def estados(cfg):
    base = {"bruno": {"pose": "up", "expr": "happy"}, "vita": {"pose": "wave", "expr": "happy"},
            "tito": {"pose": "rest", "expr": "happy"}, "rosita": {"pose": "wave", "expr": "laugh"},
            "beto": {"pose": "up", "expr": "laugh"}}
    return {w: base[w] for w in cfg["elenco"]}


def guardar(s, ruta, jpg=True):
    tmp = ruta + ".png"
    s.write_to_png(tmp)
    if jpg:
        Image.open(tmp).convert("RGB").save(ruta, quality=93)
        os.remove(tmp)
    else:
        os.replace(tmp, ruta)


def banner(cfg, out):
    W, H = 2560, 1440
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(s)
    sunburst(c, W, H, W / 2, H / 2, cfg["c1"], cfg["c2"], 36)
    # fotos reales a los costados (fuera de la zona segura: se ven en TV y escritorio)
    for i, key in enumerate(cfg["fotos"]):
        x = 60 if i < 2 else W - 60 - 420
        y = 120 + (i % 2) * 640
        c.save()
        c.translate(x + 210, y + 280)
        c.rotate(-0.06 if i % 2 == 0 else 0.05)
        R.rrect(c, -222, -292, 444, 584, 30)
        R.fill_stroke(c, hx("FFFFFF"), hx(cfg["oscuro"]), 8)
        R.draw_foto(c, key, -206, -276, 412, 552, credito=False, radio=22)
        c.restore()
    # zona segura: logo + lema + personajes (cabezas) a los lados
    logo(c, cfg, W / 2, 640, 1.05)
    texto(c, cfg["lema"].upper(), W / 2, 820, 64, cfg["oscuro"], outline="FFFFFF", ow=14, maxw=1000)
    c.save()
    R.rrect(c, W / 2 - 330, 850, 660, 70, 35)
    c.set_source_rgba(*hx(cfg["acento"]))
    c.fill()
    c.restore()
    texto(c, cfg["dia"], W / 2, 900, 36, R.WHITE, R.F_XBOLD)
    st = estados(cfg)
    lados = [cfg["locutor"], [w for w in cfg["elenco"] if w != cfg["locutor"]][0]]
    for who, x in zip(lados, (W / 2 - 640, W / 2 + 640)):
        personaje(c, who, x, 660 if who == "tito" else 640, 0.85, st[who])
    texto(c, cfg["sub"], W / 2, 1390, 34, cfg["oscuro"], R.F_XBOLD, maxw=1500)
    guardar(s, os.path.join(out, "banner_2560x1440.jpg"))


def perfil(cfg, out):
    S = 800
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, S, S)
    c = cairo.Context(s)
    sunburst(c, S, S, S / 2, S / 2, cfg["c1"], cfg["c2"], 24)
    c.arc(S / 2, S / 2, S / 2 - 18, 0, 2 * math.pi)
    c.set_source_rgba(*hx(cfg["acento"]))
    c.set_line_width(36)
    c.stroke()
    who = cfg["locutor"]
    personaje(c, who, S / 2, 400 if who == "tito" else 345, 1.45, {"pose": "rest", "expr": "happy"})
    # banda con el nombre en la parte baja del círculo
    c.save()
    c.arc(S / 2, S / 2, S / 2 - 36, 0, 2 * math.pi)
    c.clip()
    c.set_source_rgba(*hx(cfg["oscuro"]))
    c.rectangle(0, 560, S, 260)
    c.fill()
    texto(c, cfg["nombre"][0], S / 2, 640, 74, R.WHITE, maxw=520)
    texto(c, cfg["nombre"][1], S / 2, 700, 46, cfg["acento2"], maxw=440)
    c.restore()
    guardar(s, os.path.join(out, "perfil_800x800.jpg"))


def marca_agua(cfg, out):
    S = 600  # se dibuja grande y se reduce a 150 para que quede nítido
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, S, S)
    c = cairo.Context(s)
    c.arc(S / 2, S / 2, S / 2 - 6, 0, 2 * math.pi)
    c.set_source_rgba(*hx(cfg["acento"]))
    c.fill()
    c.arc(S / 2, S / 2, S / 2 - 40, 0, 2 * math.pi)
    c.set_source_rgba(*hx("FFFFFF"))
    c.fill()
    c.save()
    c.arc(S / 2, S / 2, S / 2 - 40, 0, 2 * math.pi)
    c.clip()
    who = cfg["locutor"]
    personaje(c, who, S / 2, 300 if who == "tito" else 255, 1.15, {"pose": "rest", "expr": "happy"})
    c.restore()
    # botón SUSCRÍBETE abajo
    R.rrect(c, 60, 440, 480, 110, 55)
    R.fill_stroke(c, R.RED, R.WHITE, 10)
    texto(c, "SUSCRÍBETE", S / 2, 515, 62, R.WHITE, maxw=420)
    tmp = os.path.join(out, "_wm.png")
    s.write_to_png(tmp)
    Image.open(tmp).resize((150, 150), Image.LANCZOS).save(os.path.join(out, "marca_de_agua_150x150.png"))
    os.remove(tmp)


def miniatura(cfg, out):
    W, H = 1280, 720
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(s)
    sunburst(c, W, H, 900, 360, cfg["c1"], cfg["c2"], 28)
    c.save()
    c.translate(950, 360)
    c.rotate(0.04)
    R.rrect(c, -300, -230, 600, 460, 34)
    R.fill_stroke(c, hx("FFFFFF"), hx(cfg["acento"]), 12)
    R.draw_foto(c, cfg["fotos"][0], -284, -214, 568, 428, credito=False, radio=24)
    c.restore()
    logo(c, cfg, 330, 150, 0.8)
    texto(c, cfg["lema"].upper(), 330, 300, 52, cfg["oscuro"], outline="FFFFFF", ow=12, maxw=600)
    st = estados(cfg)
    xs = [180, 470] if len(cfg["elenco"]) == 2 else [130, 330, 530]
    for who, x in zip(cfg["elenco"], xs):
        personaje(c, who, x, 470, 0.62, st[who])
    R.rrect(c, 40, 640, 560, 60, 30)
    c.set_source_rgba(*hx(cfg["acento"]))
    c.fill()
    texto(c, cfg["dia"], 320, 681, 32, R.WHITE, R.F_XBOLD)
    guardar(s, os.path.join(out, "miniatura_1280x720.jpg"))


def main():
    for canal, cfg in CANALES.items():
        out = os.path.join(AQUI, "..", canal, "branding")
        os.makedirs(out, exist_ok=True)
        R.CANAL = R.CANALES[canal]
        R.LOCUTOR = cfg["locutor"]
        banner(cfg, out)
        perfil(cfg, out)
        marca_agua(cfg, out)
        miniatura(cfg, out)
        print(canal, sorted(os.listdir(out)))


if __name__ == "__main__":
    main()
