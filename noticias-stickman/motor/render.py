#!/usr/bin/env python3
"""Motor de render de NOTICIAS STICKMAN.

Lee un guion.json y produce un short vertical 1080x1920 a 30 fps:
intro con titular, 3 stickmans (Paco el locutor, Lucha la reportera,
Chato el vecino), globos con texto karaoke, tarjetas de datos, efectos,
cierre con botones LIKE / corazón / SÍGUEME, música y efectos de sonido
sintetizados (libres de derechos).

Uso:
    python3 render.py ../episodios/<carpeta>/guion.json
    python3 render.py ../episodios/<carpeta>/guion.json --frame 12.5   # PNG de prueba
"""
import json
import math
import os
import random
import subprocess
import sys
import wave

import cairo
import numpy as np

W, H, FPS = 1080, 1920, 30
F_BLACK, F_XBOLD, F_SEMI = "Inter Black", "Inter ExtraBold", "Inter SemiBold"


def hx(h, a=1.0):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)) + (a,)


NAVY = hx("1C2130")
INK = hx("1E2230")
TEAL = hx("19BDAD")
PINK = hx("F0287A")
WHITE = hx("FFFFFF")
GRAY_TXT = hx("C3C7CF")
WALL = hx("E3F1EE")
FLOOR = hx("9A6B4F")
METAL = hx("AEB5C0")
SKIN = hx("D49A6A")
RED = hx("F2283C")
YELLOW = hx("FFD23F")

INTRO = 2.0
LOCUTOR = "paco"
ELENCO = ["chato", "paco", "lucha"]
PROGRAMA = ["NOTICIAS", "STICKMAN"]
VOICE_DIR = os.environ.get("NS_VOCES", "/tmp")
VOCES = {"maskaly": "es_MX-ald-medium", "paco": "es_MX-ald-medium", "chato": "es_MX-claude-high", "lucha": "es_AR-daniela-high",
         # Stickman Doctor
         "bruno": "es_MX-ald-medium", "vita": "es_AR-daniela-high",
         # Stickman Cocina
         "tito": "es_MX-ald-medium", "rosita": "es_AR-daniela-high", "beto": "es_MX-claude-high"}
VOZ_OFFSET = 0.15
# Tono: semitonos por personaje (positivo = más aguda, negativo = más gruesa)
TONO = {"maskaly": "mezcla", "paco": 3.0, "chato": 4.0, "lucha": 3.0,
        "bruno": -2.5, "vita": 5.0, "tito": 1.0, "rosita": 3.0, "beto": 2.5}
OUTRO = 4.5

CAST = {
    "chato": {"x": 190, "body": hx("FF7A1A"), "led": hx("2BE07A"), "name": "CHATO", "iris": hx("6B3E1F")},
    "maskaly": {"x": 540, "body": hx("E8175D"), "led": hx("FF2E63"), "name": "MASKALY", "iris": hx("5B3A29")},
    "paco": {"x": 540, "body": hx("2B6BE0"), "led": hx("FFD23F"), "name": "PACO", "iris": hx("3A6FB0")},
    "lucha": {"x": 890, "body": hx("9B4DFF"), "led": hx("FF4FA3"), "name": "LUCHA", "iris": hx("2E8B57")},
    # Stickman Doctor: dos médicos coloridos con bata, espejo frontal y estetoscopio
    "bruno": {"x": 300, "body": hx("0FA3B1"), "led": hx("3DFF9A"), "name": "DR. BRUNO", "iris": hx("2F4F7F")},
    "vita": {"x": 780, "body": hx("FF4F9A"), "led": hx("FFD23F"), "name": "DRA. VITA", "iris": hx("2E8B57")},
    # Stickman Cocina: el chef y dos comensales que preguntan
    "tito": {"x": 540, "body": hx("E63946"), "led": hx("FFD23F"), "name": "CHEF TITO", "iris": hx("5B3A29")},
    "rosita": {"x": 190, "body": hx("FF9F1C"), "led": hx("FF4FA3"), "name": "ROSITA", "iris": hx("6B3E1F")},
    "beto": {"x": 890, "body": hx("2EC4B6"), "led": hx("2B6BE0"), "name": "BETO", "iris": hx("3A6FB0")},
}

# Ajustes por canal (el guion elige con "canal": "noticias" | "doctor" | "cocina")
CANALES = {
    "noticias": {"fondo": "noticias", "gracias": "¡GRACIAS, STICKMATAS!", "campana": "Activa la campana para la noticia de mañana",
                 "bpm": 124, "aviso": None},
    "doctor": {"fondo": "consultorio", "gracias": "¡GRACIAS, FAMILIA SANA!", "campana": "Activa la campana: mañana otro consejo natural",
               "bpm": 104, "aviso": "Información educativa · No reemplaza tu consulta médica"},
    "cocina": {"fondo": "cocina", "gracias": "¡GRACIAS, COCINEROS!", "campana": "Activa la campana: mañana otra receta peruana",
               "bpm": 116, "aviso": None},
}
CANAL = CANALES["noticias"]
SCREEN = (52, 458, 560, 372)          # x, y, ancho, alto de la pantalla grande
FOTOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "stickman-canales", "fotos")
_FOTO_CACHE = {}
_CREDITOS = None
HEAD_Y, HEAD_R = 1010, 118
SHOULDER_Y, HIP_Y, FOOT_Y = 1175, 1430, 1700


# ---------------------------------------------------------------- utilidades
def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def ease_out_back(t):
    t = clamp(t)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def rrect(c, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    c.new_sub_path()
    c.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    c.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    c.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    c.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    c.close_path()


def font(c, size, fam=F_BLACK):
    c.select_font_face(fam, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    c.set_font_size(size)


def tw(c, s):
    return c.text_extents(s).x_advance


def text_center(c, s, cx, y, size, color, fam=F_BLACK, outline=None, ow=0):
    font(c, size, fam)
    x = cx - tw(c, s) / 2
    if outline:
        c.move_to(x, y)
        c.text_path(s)
        c.set_source_rgba(*outline)
        c.set_line_width(ow)
        c.set_line_join(cairo.LINE_JOIN_ROUND)
        c.stroke()
    c.move_to(x, y)
    c.set_source_rgba(*color)
    c.show_text(s)


def fill_stroke(c, fill, stroke=INK, lw=7):
    c.set_source_rgba(*fill)
    c.fill_preserve()
    c.set_source_rgba(*stroke)
    c.set_line_width(lw)
    c.stroke()


def parse_words(texto):
    """'Hola *mundo* hoy' -> [('Hola',False),('mundo',True),('hoy',False)]"""
    out = []
    for raw in texto.split():
        hl = "*" in raw
        out.append((raw.replace("*", ""), hl))
    return out


# ---------------------------------------------------------------- fondo
def build_background():
    if CANAL["fondo"] == "consultorio":
        return build_consultorio()
    if CANAL["fondo"] == "cocina":
        return build_cocina()
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(s)
    c.set_source_rgba(*WALL)
    c.paint()
    c.set_source_rgba(1, 1, 1, 0.85)
    for yy in range(30, 1390, 46):
        off = 23 if (yy // 46) % 2 else 0
        for xx in range(20 + off, W, 46):
            c.arc(xx, yy, 4.2, 0, 2 * math.pi)
            c.fill()
    # zócalo + piso de madera
    c.set_source_rgba(*FLOOR)
    c.rectangle(0, 1390, W, H - 1390)
    c.fill()
    c.set_source_rgba(1, 1, 1, 0.18)
    c.set_line_width(3)
    for xx in range(-900, W + 200, 95):
        c.move_to(xx, H)
        c.line_to(xx + 420, 1390)
        c.stroke()
    c.set_source_rgba(*INK)
    c.rectangle(0, 1380, W, 18)
    c.fill()
    # pantalla grande (marco)
    rrect(c, 52, 458, 560, 372, 26)
    fill_stroke(c, NAVY, TEAL, 9)
    # cartel EN VIVO
    rrect(c, 680, 466, 340, 92, 22)
    fill_stroke(c, hx("2A2F3F"), INK, 6)
    # panel logo
    rrect(c, 680, 586, 340, 244, 26)
    fill_stroke(c, WHITE, INK, 7)
    text_center(c, PROGRAMA[0], 850, 670, 50 if len(PROGRAMA[0]) < 9 else 44, NAVY)
    text_center(c, PROGRAMA[1], 850, 730, 54, TEAL)
    rrect(c, 735, 758, 230, 44, 22)
    c.set_source_rgba(*NAVY)
    c.fill()
    text_center(c, "PERÚ · MUNDO", 850, 790, 28, WHITE, F_XBOLD)
    return s


# ---------------------------------------------------------------- fotos reales (Wikimedia Commons, licencias libres)
def creditos():
    global _CREDITOS
    if _CREDITOS is None:
        p = os.path.join(FOTOS_DIR, "creditos.json")
        _CREDITOS = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    return _CREDITOS


def foto_surface(key):
    """Carga fotos/<key>.jpg como superficie cairo (cacheada)."""
    if key in _FOTO_CACHE:
        return _FOTO_CACHE[key]
    from PIL import Image
    path = os.path.join(FOTOS_DIR, key + ".jpg")
    if not os.path.exists(path):
        print("AVISO: falta la foto", path)
        _FOTO_CACHE[key] = None
        return None
    im = Image.open(path).convert("RGBA")
    r, g, b, a = im.split()
    data = bytearray(Image.merge("RGBA", (b, g, r, a)).tobytes())
    surf = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, im.width, im.height, im.width * 4)
    _FOTO_CACHE[key] = (surf, data)
    return _FOTO_CACHE[key]


def credito_corto(key):
    cr = creditos().get(key)
    if not cr:
        return ""
    autor = (cr.get("autor") or "").strip() or "Wikimedia Commons"
    if len(autor) > 34:
        autor = autor[:32] + "…"
    return f"Foto: {autor} · {cr.get('lic', '')}"


def draw_foto(c, key, x, y, w, h, t=0.0, zoom=0.0, credito=True, radio=18):
    """Dibuja la foto recortada (cover) en el rectángulo, con zoom lento opcional."""
    fs = foto_surface(key)
    c.save()
    rrect(c, x, y, w, h, radio)
    c.clip()
    if fs is None:
        c.set_source_rgba(*hx("2A2F3F"))
        c.paint()
        text_center(c, key.upper(), x + w / 2, y + h / 2, 34, WHITE)
    else:
        surf = fs[0]
        iw, ih = surf.get_width(), surf.get_height()
        s = max(w / iw, h / ih) * (1.0 + zoom)
        c.translate(x + w / 2, y + h / 2)
        c.scale(s, s)
        c.translate(-iw / 2, -ih / 2)
        c.set_source_surface(surf, 0, 0)
        c.paint()
    c.restore()
    if credito and fs is not None:
        txt = credito_corto(key)
        if txt:
            font(c, 17, F_SEMI)
            tw_ = tw(c, txt) + 18
            rrect(c, x + w - tw_ - 8, y + h - 34, tw_, 26, 8)
            c.set_source_rgba(0, 0, 0, 0.55)
            c.fill()
            c.set_source_rgba(1, 1, 1, 0.92)
            c.move_to(x + w - tw_ + 1, y + h - 15)
            c.show_text(txt)


def build_consultorio():
    """Consultorio luminoso: pared menta con azulejos, cruz verde, planta y camilla."""
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(s)
    g = cairo.LinearGradient(0, 0, 0, 1390)
    g.add_color_stop_rgba(0, *hx("DDF4F7"))
    g.add_color_stop_rgba(1, *hx("BFE7EC"))
    c.set_source(g)
    c.paint()
    c.set_source_rgba(1, 1, 1, 0.55)
    c.set_line_width(2)
    for yy in range(900, 1390, 70):
        c.move_to(0, yy)
        c.line_to(W, yy)
        c.stroke()
    for xx in range(0, W, 70):
        c.move_to(xx, 900)
        c.line_to(xx, 1390)
        c.stroke()
    # piso vinílico
    c.set_source_rgba(*hx("8FB8C9"))
    c.rectangle(0, 1390, W, H - 1390)
    c.fill()
    c.set_source_rgba(1, 1, 1, 0.25)
    for xx in range(-900, W + 200, 120):
        c.move_to(xx, H)
        c.line_to(xx + 420, 1390)
        c.stroke()
    c.set_source_rgba(*INK)
    c.rectangle(0, 1380, W, 16)
    c.fill()
    # planta
    rrect(c, 20, 1250, 110, 140, 14)
    fill_stroke(c, hx("F2C14E"), INK, 6)
    for (dx, dy, a) in ((-30, -60, -0.5), (10, -90, 0.0), (45, -55, 0.55), (-5, -40, -0.2)):
        c.save()
        c.translate(75 + dx, 1250 + dy)
        c.rotate(a)
        c.scale(0.45, 1)
        c.arc(0, 0, 55, 0, 2 * math.pi)
        c.restore()
        fill_stroke(c, hx("2FBF71"), INK, 5)
    # botiquín con cruz
    rrect(c, 950, 1120, 110, 100, 14)
    fill_stroke(c, WHITE, INK, 6)
    c.set_source_rgba(*hx("2FBF71"))
    c.rectangle(992, 1135, 26, 70)
    c.rectangle(970, 1157, 70, 26)
    c.fill()
    # marco de la pantalla (monitor del consultorio)
    x0, y0, w, h = SCREEN
    rrect(c, x0 - 10, y0 - 10, w + 20, h + 20, 30)
    fill_stroke(c, NAVY, hx("0FA3B1"), 10)
    return s


def build_cocina():
    """Cocina de verdad: foto real de cocina (si existe) + azulejos y repisas."""
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(s)
    c.set_source_rgba(*hx("F6EBDD"))
    c.paint()
    fondo = foto_surface("cocina_fondo")
    if fondo is not None:
        draw_foto(c, "cocina_fondo", 0, 0, W, 1450, credito=False, radio=0)
        c.set_source_rgba(1, 0.97, 0.92, 0.35)
        c.rectangle(0, 0, W, 1450)
        c.fill()
    else:
        # azulejos tipo metro
        c.set_source_rgba(1, 1, 1, 0.9)
        for yy in range(0, 1450, 44):
            off = 45 if (yy // 44) % 2 else 0
            for xx in range(-off, W, 90):
                rrect(c, xx + 3, yy + 3, 84, 38, 6)
                c.fill()
        # repisa con frascos
        c.set_source_rgba(*hx("8A5A3C"))
        c.rectangle(0, 920, W, 20)
        c.fill()
        cols = [hx("FFD23F"), hx("E63946"), hx("2FBF71"), hx("FF9F1C"), hx("9B4DFF")]
        for i, xx in enumerate(range(40, W, 150)):
            rrect(c, xx, 840, 70, 80, 12)
            fill_stroke(c, cols[i % 5], INK, 4)
            rrect(c, xx + 8, 826, 54, 18, 5)
            fill_stroke(c, hx("C9CED6"), INK, 3)
    # mesón de acero y madera (los personajes cocinan detrás)
    c.set_source_rgba(*hx("B9C2CC"))
    c.rectangle(0, 1450, W, 50)
    c.fill()
    c.set_source_rgba(*INK)
    c.rectangle(0, 1445, W, 8)
    c.fill()
    c.set_source_rgba(*hx("9A6B4F"))
    c.rectangle(0, 1500, W, H - 1500)
    c.fill()
    c.set_source_rgba(1, 1, 1, 0.12)
    c.set_line_width(4)
    for yy in range(1530, H, 60):
        c.move_to(0, yy)
        c.line_to(W, yy)
        c.stroke()
    # marco de la pantalla (pizarra del chef)
    x0, y0, w, h = SCREEN
    rrect(c, x0 - 10, y0 - 10, w + 20, h + 20, 30)
    fill_stroke(c, hx("3B2A20"), hx("E63946"), 10)
    return s


def draw_meson(c, t, fuego):
    """Primer plano de la cocina: wok sobre la hornilla, tabla con cebolla y ají."""
    # tabla de picar
    rrect(c, 640, 1462, 300, 46, 12)
    fill_stroke(c, hx("D9A066"), INK, 5)
    for i in range(5):
        c.save()
        c.translate(680 + i * 26, 1474)
        c.scale(1, 0.5)
        c.arc(0, 0, 14, math.pi, 2 * math.pi)
        c.restore()
        c.set_source_rgba(*hx("9B3D8F"))
        c.set_line_width(5)
        c.stroke()
    for i in range(3):
        rrect(c, 830 + i * 24, 1468, 16, 30, 6)
        fill_stroke(c, hx("FFC300"), INK, 3)
    # hornilla
    rrect(c, 330, 1466, 300, 36, 10)
    fill_stroke(c, hx("2A2F3F"), INK, 5)
    if fuego:
        rnd = random.Random(int(t * 12))
        for i in range(9):
            fx_ = 360 + i * 30
            fh = 60 + 50 * abs(math.sin(t * 9 + i * 1.7)) + rnd.uniform(0, 25)
            c.move_to(fx_ - 16, 1466)
            c.curve_to(fx_ - 18, 1466 - fh * 0.5, fx_ - 2, 1466 - fh * 0.7, fx_, 1466 - fh)
            c.curve_to(fx_ + 2, 1466 - fh * 0.7, fx_ + 18, 1466 - fh * 0.5, fx_ + 16, 1466)
            c.close_path()
            g = cairo.LinearGradient(0, 1466, 0, 1466 - fh)
            g.add_color_stop_rgba(0, *hx("FFD23F"))
            g.add_color_stop_rgba(1, *hx("FF3D00", 0.85))
            c.set_source(g)
            c.fill()
    # wok
    wy = 1440 + (4 * math.sin(t * 14) if fuego else 0)
    c.save()
    c.translate(480, wy)
    c.scale(1, 0.42)
    c.arc(0, 0, 150, 0, math.pi)
    c.restore()
    fill_stroke(c, hx("3A3F4B"), INK, 6)
    c.save()
    c.translate(480, wy)
    c.scale(1, 0.12)
    c.arc(0, 0, 150, 0, 2 * math.pi)
    c.restore()
    fill_stroke(c, hx("5A3A22"), INK, 5)
    rrect(c, 625, wy - 12, 120, 20, 10)
    fill_stroke(c, hx("8A5A3C"), INK, 4)
    # vapor
    c.set_source_rgba(1, 1, 1, 0.55)
    c.set_line_width(7)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    for i in range(3):
        ph = (t * 0.8 + i * 0.33) % 1.0
        sx = 430 + i * 50
        c.move_to(sx, wy - 30 - ph * 160)
        c.curve_to(sx + 20, wy - 60 - ph * 160, sx - 20, wy - 90 - ph * 160, sx, wy - 120 - ph * 160)
        c.set_source_rgba(1, 1, 1, 0.5 * (1 - ph))
        c.stroke()


def draw_aviso(c):
    if not CANAL.get("aviso"):
        return
    font(c, 24, F_XBOLD)
    s = CANAL["aviso"]
    w = tw(c, s) + 40
    rrect(c, 540 - w / 2, H - 70, w, 44, 22)
    c.set_source_rgba(*hx("1C2130", 0.82))
    c.fill()
    c.set_source_rgba(1, 1, 1, 0.95)
    c.move_to(540 - w / 2 + 20, H - 40)
    c.show_text(s)


def draw_etiqueta(c, txt, x, y, size=34, fondo=None, color=WHITE):
    font(c, size)
    w = tw(c, txt) + 36
    rrect(c, x, y, w, size + 22, (size + 22) / 2)
    c.set_source_rgba(*(fondo or hx("1C2130", 0.85)))
    c.fill()
    c.set_source_rgba(*color)
    c.move_to(x + 18, y + size + 4)
    c.show_text(txt)
    return w


def draw_screen_fotos(c, kind, t, local):
    x0, y0, w, h = SCREEN
    tipo, _, resto = kind.partition(":")
    partes = resto.split("|")
    if tipo == "foto":
        key = partes[0]
        k = ease_out_back(local / 0.35)
        c.save()
        cx, cy = x0 + w / 2, y0 + h / 2
        c.translate(cx, cy)
        c.scale(0.85 + 0.15 * k, 0.85 + 0.15 * k)
        c.translate(-cx, -cy)
        draw_foto(c, key, x0, y0, w, h, t, zoom=0.07 * clamp(local / 6.0))
        if len(partes) > 1 and partes[1]:
            size = 44
            font(c, size)
            while tw(c, partes[1]) > w - 80:
                size -= 3
                font(c, size)
            draw_etiqueta(c, partes[1], x0 + 22, y0 + 20, size, hx("E63946" if CANAL["fondo"] == "cocina" else "0FA3B1"))
        c.restore()
    elif tipo == "fotos":
        keys = partes[0].split(",")
        labels = partes[1:] + [""] * len(keys)
        n = len(keys)
        cols = 2 if n == 4 else n
        rows = 2 if n == 4 else 1
        gap = 16
        cw = (w - gap * (cols + 1)) / cols
        ch = (h - gap * (rows + 1)) / rows
        c.save()
        rrect(c, x0, y0, w, h, 18)
        c.set_source_rgba(*hx("1C2130"))
        c.fill()
        c.restore()
        for i, key in enumerate(keys):
            st = i * 0.35
            if local < st:
                continue
            k = ease_out_back((local - st) / 0.3)
            col, row = i % cols, i // cols
            x = x0 + gap + col * (cw + gap)
            y = y0 + gap + row * (ch + gap)
            c.save()
            c.translate(x + cw / 2, y + ch / 2)
            c.scale(k, k)
            c.translate(-(x + cw / 2), -(y + ch / 2))
            draw_foto(c, key, x, y, cw, ch, t, zoom=0.04 * clamp((local - st) / 5), credito=False, radio=14)
            if labels[i]:
                size = 30 if n >= 3 else 36
                font(c, size)
                while tw(c, labels[i]) > cw - 50:
                    size -= 2
                    font(c, size)
                lw = tw(c, labels[i]) + 30
                rrect(c, x + (cw - lw) / 2, y + ch - size - 30, lw, size + 18, (size + 18) / 2)
                c.set_source_rgba(*hx("FFD23F"))
                c.fill()
                c.set_source_rgba(*NAVY)
                c.move_to(x + (cw - lw) / 2 + 15, y + ch - 22)
                c.show_text(labels[i])
            c.restore()
        # créditos de todas las fotos en una línea
        txt = "Fotos: Wikimedia Commons (licencias libres, créditos en la descripción)"
        font(c, 16, F_SEMI)
        c.set_source_rgba(1, 1, 1, 0.75)
        c.move_to(x0 + w - tw(c, txt) - 20, y0 + h - 4)
        c.show_text(txt)
    else:  # lista: TITULO|item|item...
        titulo, items = partes[0], partes[1:]
        rrect(c, x0, y0, w, h, 18)
        c.set_source_rgba(*hx("FFF8EC"))
        c.fill()
        acento = hx("E63946") if CANAL["fondo"] == "cocina" else hx("0FA3B1")
        rrect(c, x0, y0, w, 74, 18)
        c.set_source_rgba(*acento)
        c.fill()
        text_center(c, titulo, x0 + w / 2, y0 + 52, 40, WHITE)
        n = max(1, len(items))
        lh = min(70, (h - 100) / n)
        size = min(38, int(lh * 0.62))
        for i, it in enumerate(items):
            st = 0.2 + i * 0.45
            if local < st:
                continue
            k = ease_out_back((local - st) / 0.25)
            y = y0 + 96 + i * lh
            c.save()
            c.translate(x0 + 40, y + lh / 2)
            c.scale(k, k)
            c.arc(0, 0, lh * 0.36, 0, 2 * math.pi)
            c.set_source_rgba(*acento)
            c.fill()
            text_center(c, str(i + 1), 0, lh * 0.15, int(lh * 0.42), WHITE)
            c.restore()
            fs = size
            font(c, fs, F_XBOLD)
            while tw(c, it) > w - 120:
                fs -= 2
                font(c, fs, F_XBOLD)
            c.set_source_rgba(*NAVY)
            c.move_to(x0 + 82, y + lh / 2 + fs * 0.35)
            c.show_text(it)


# ---------------------------------------------------------------- pantalla
def draw_screen(c, kind, t, local):
    x0, y0, w, h = SCREEN
    if kind.startswith(("foto:", "fotos:", "lista:")):
        draw_screen_fotos(c, kind, t, local)
        return
    c.save()
    rrect(c, x0 + 10, y0 + 10, w - 20, h - 20, 18)
    c.clip()
    grad = cairo.LinearGradient(0, y0, 0, y0 + h)
    grad.add_color_stop_rgba(0, *hx("23314F"))
    grad.add_color_stop_rgba(1, *hx("141A29"))
    c.set_source(grad)
    c.paint()
    cx, cy = x0 + w / 2, y0 + h / 2
    k = ease_out_back(local / 0.35)
    c.translate(cx, cy)
    c.scale(0.6 + 0.4 * k, 0.6 + 0.4 * k)
    c.translate(-cx, -cy)
    if kind.startswith("texto:"):
        partes = kind[6:].split("|")
        cols = [YELLOW, WHITE, TEAL]
        for i, ln in enumerate(partes):
            size = 120 if i == 0 else 54
            font(c, size)
            while tw(c, ln) > w - 60:
                size -= 4
                font(c, size)
            text_center(c, ln, cx, cy - 20 + (i * 90 if i else 0) - (40 if len(partes) > 1 else -40), size, cols[i % 3])
    elif kind.startswith("fecha:"):
        num, dia, cinta = (kind[6:].split(":") + ["", "", ""])[:3]
        rrect(c, cx - 150, cy - 160, 300, 320, 22)
        fill_stroke(c, WHITE, INK, 7)
        c.save()
        rrect(c, cx - 150, cy - 160, 300, 82, 22)
        c.clip()
        c.set_source_rgba(*RED)
        c.paint()
        c.restore()
        text_center(c, "NOVIEMBRE", cx, cy - 104, 34, WHITE)
        text_center(c, num, cx, cy + 70, 150, NAVY)
        text_center(c, dia, cx, cy + 128, 34, hx("5A6070"), F_XBOLD)
        if cinta:
            c.save()
            c.translate(cx + 165, cy - 150)
            c.rotate(0.3)
            font(c, 26)
            wv = tw(c, cinta) + 40
            rrect(c, -wv / 2, -26, wv, 52, 12)
            fill_stroke(c, TEAL, INK, 5)
            c.set_source_rgba(*NAVY)
            c.move_to(-tw(c, cinta) / 2, 10)
            c.show_text(cinta)
            c.restore()
    elif kind == "colegio":
        c.move_to(cx - 200, cy - 20)
        c.line_to(cx, cy - 150)
        c.line_to(cx + 200, cy - 20)
        c.close_path()
        fill_stroke(c, RED, INK, 6)
        c.rectangle(cx - 180, cy - 20, 360, 180)
        fill_stroke(c, hx("F4E3C1"), INK, 6)
        for k in (-1, 1):
            for j in (0, 1):
                c.rectangle(cx + k * 110 - 30, cy + 10 + j * 70, 60, 45)
                fill_stroke(c, hx("6EC8FF"), INK, 4)
        rrect(c, cx - 35, cy + 70, 70, 90, 6)
        fill_stroke(c, hx("8A5A3C"), INK, 4)
        text_center(c, "COAR", cx, cy - 45, 46, WHITE)
        c.set_source_rgba(*INK)
        c.set_line_width(5)
        c.move_to(cx, cy - 150)
        c.line_to(cx, cy - 210)
        c.stroke()
        c.rectangle(cx, cy - 210, 60, 36)
        c.set_source_rgba(*RED)
        c.fill()
        c.rectangle(cx + 20, cy - 210, 20, 36)
        c.set_source_rgba(*WHITE)
        c.fill()
    elif kind == "calabaza":
        for dx in (-70, 0, 70):
            c.save()
            c.translate(cx + dx * 0.9, cy + 10)
            c.scale(0.75, 1)
            c.arc(0, 0, 120, 0, 2 * math.pi)
            c.restore()
            fill_stroke(c, hx("FF8A1F"), INK, 6)
        rrect(c, cx - 14, cy - 140, 28, 40, 6)
        fill_stroke(c, hx("3E8E41"), INK, 4)
        for k in (-1, 1):
            c.move_to(cx + k * 55 - 25, cy - 10)
            c.line_to(cx + k * 55 + 25, cy - 10)
            c.line_to(cx + k * 55, cy - 50)
            c.close_path()
            c.set_source_rgba(*YELLOW)
            c.fill()
        text_center(c, "25", cx, cy + 90, 90, YELLOW, outline=INK, ow=8)
    elif kind == "mano":
        # mano gigante caricaturesca (sin gore realista)
        sh = 6 * math.sin(t * 4)
        c.save()
        c.translate(cx, cy + 30 + sh)
        rrect(c, -110, -60, 220, 200, 60)
        fill_stroke(c, hx("F2C29B"), INK, 6)
        for i, (fx_, fh) in enumerate(((-90, 150), (-35, 190), (20, 200), (75, 170))):
            rrect(c, fx_ - 24, -60 - fh, 48, fh + 30, 24)
            fill_stroke(c, hx("F2C29B"), INK, 6)
            rrect(c, fx_ - 16, -60 - fh + 4, 32, 30, 14)
            fill_stroke(c, PINK, INK, 3)
            if i in (1, 3):
                c.rectangle(fx_ - 26, -60 - fh * 0.45, 52, 14)
                fill_stroke(c, YELLOW, INK, 3)
        rrect(c, -150, 10, 80, 44, 22)
        fill_stroke(c, hx("F2C29B"), INK, 6)
        rrect(c, -100, 130, 200, 40, 10)
        fill_stroke(c, RED, INK, 5)
        c.restore()
    elif kind in ("calendario", "lunes"):
        num, dia, cinta = ("1", "DOMINGO", "FERIADO") if kind == "calendario" else ("2", "LUNES", "SE TRABAJA")
        rrect(c, cx - 150, cy - 160, 300, 320, 22)
        fill_stroke(c, WHITE, INK, 7)
        c.save()
        rrect(c, cx - 150, cy - 160, 300, 82, 22)
        c.clip()
        c.set_source_rgba(*RED)
        c.paint()
        c.restore()
        text_center(c, "NOVIEMBRE", cx, cy - 104, 34, WHITE)
        text_center(c, num, cx, cy + 70, 150, NAVY)
        text_center(c, dia, cx, cy + 128, 34, hx("5A6070"), F_XBOLD)
        c.save()
        c.translate(cx + 165, cy - 150)
        c.rotate(0.3)
        rrect(c, -105, -26, 210, 52, 12)
        fill_stroke(c, TEAL if kind == "calendario" else YELLOW, INK, 5)
        font(c, 26)
        c.set_source_rgba(*NAVY)
        c.move_to(-tw(c, cinta) / 2, 10)
        c.show_text(cinta)
        c.restore()
    elif kind in ("ley", "contrato"):
        rrect(c, cx - 130, cy - 165, 260, 330, 16)
        fill_stroke(c, WHITE, INK, 7)
        titulo = "D. LEG. 713" if kind == "ley" else "CONTRATO"
        text_center(c, titulo, cx, cy - 105, 38, NAVY)
        c.set_source_rgba(*GRAY_TXT)
        for i in range(6):
            rrect(c, cx - 95, cy - 70 + i * 34, 190 - (50 if i == 5 else 0), 14, 7)
            c.fill()
        if kind == "ley":
            c.arc(cx + 80, cy + 120, 44, 0, 2 * math.pi)
            fill_stroke(c, RED, INK, 5)
            text_center(c, "LEY", cx + 80, cy + 132, 30, WHITE)
        else:
            mx, my = cx + 70 + 10 * math.sin(t * 3), cy + 60
            c.arc(mx, my, 60, 0, 2 * math.pi)
            c.set_source_rgba(0.6, 0.9, 1, 0.35)
            c.fill_preserve()
            c.set_source_rgba(*INK)
            c.set_line_width(10)
            c.stroke()
            c.move_to(mx + 42, my + 42)
            c.line_to(mx + 105, my + 105)
            c.set_line_width(22)
            c.set_line_cap(cairo.LINE_CAP_ROUND)
            c.stroke()
    elif kind == "x3":
        for i in range(5):
            yy = cy + 110 - i * 40
            c.save()
            c.translate(cx - 120, yy)
            c.scale(1, 0.42)
            c.arc(0, 0, 80, 0, 2 * math.pi)
            c.restore()
            fill_stroke(c, YELLOW, INK, 5)
        text_center(c, "S/", cx - 120, cy - 45, 46, hx("8A6A00"))
        text_center(c, "x3", cx + 110, cy + 55, 170, TEAL, outline=INK, ow=10)
    elif kind == "compartir":
        pts = [(cx - 110, cy), (cx + 100, cy - 100), (cx + 100, cy + 100)]
        c.set_source_rgba(*TEAL)
        c.set_line_width(16)
        c.move_to(*pts[1])
        c.line_to(*pts[0])
        c.line_to(*pts[2])
        c.stroke()
        for (px, py) in pts:
            c.arc(px, py, 52, 0, 2 * math.pi)
            fill_stroke(c, WHITE, TEAL, 12)
    else:  # logo
        c.arc(cx, cy - 30, 110, 0, 2 * math.pi)
        fill_stroke(c, TEAL, WHITE, 8)
        c.set_source_rgba(1, 1, 1, 0.9)
        c.set_line_width(6)
        c.save()
        c.translate(cx, cy - 30)
        c.scale(0.45 + 0.1 * math.sin(t * 2), 1)
        c.arc(0, 0, 110, 0, 2 * math.pi)
        c.restore()
        c.stroke()
        c.move_to(cx - 110, cy - 30)
        c.line_to(cx + 110, cy - 30)
        c.stroke()
        text_center(c, "ÚLTIMA HORA", cx, cy + 150, 40, YELLOW)
    c.restore()


def draw_live(c, t):
    on = (t % 1.0) < 0.6
    c.arc(728, 512, 18, 0, 2 * math.pi)
    c.set_source_rgba(*(RED if on else hx("5A2830")))
    c.fill()
    font(c, 44)
    c.set_source_rgba(*WHITE)
    c.move_to(762, 528)
    c.show_text("EN VIVO")


# ---------------------------------------------------------------- personajes
def limb(c, pts, color, lw=10):
    c.set_source_rgba(*color)
    c.set_line_width(lw)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.stroke()


def arm_points(sx, sy, side, a1, a2, L1=118, L2=110):
    r1, r2 = math.radians(a1), math.radians(a1 + a2)
    ex, ey = sx + side * L1 * math.sin(r1), sy + L1 * math.cos(r1)
    hx_, hy = ex + side * L2 * math.sin(r2), ey + L2 * math.cos(r2)
    return (sx, sy), (ex, ey), (hx_, hy)


POSES = {
    "rest": ((22, 8), (22, 8)),
    "hip": ((42, -115), (42, -115)),
    "up": ((150, 15), (150, 15)),
    "wave": ((22, 8), (140, 25)),
    "point": ((22, 8), (85, 5)),
    "talk": ((30, 60), (25, 10)),
    "think": ((22, 8), (25, 150)),
    "shrug": ((60, -80), (60, -80)),
}


def draw_mic(c, x, y, ang):
    c.save()
    c.translate(x, y)
    c.rotate(ang)
    rrect(c, -11, -10, 22, 110, 9)
    fill_stroke(c, hx("2A2F3F"), INK, 4)
    rrect(c, -26, -34, 52, 38, 8)
    fill_stroke(c, TEAL, INK, 4)
    font(c, 22)
    c.set_source_rgba(*NAVY)
    c.move_to(-tw(c, "NS") / 2, -6)
    c.show_text("NS")
    c.arc(0, -62, 34, 0, 2 * math.pi)
    fill_stroke(c, hx("C9CED6"), INK, 5)
    c.set_source_rgba(*hx("7E8694"))
    c.set_line_width(2.5)
    for k in range(-2, 3):
        c.move_to(-30, -62 + k * 11)
        c.line_to(30, -62 + k * 11)
        c.stroke()
    c.restore()


PROPS = {"paco": "mic", "maskaly": "mic", "tito": "cucharon"}


def draw_bata(c, who, x, sy, bob):
    """Bata blanca de doctor o chaqueta de chef, con el color del personaje en el cuello."""
    col = CAST[who]["body"]
    hip = HIP_Y + bob * 0.3 + 40
    c.move_to(x - 70, sy - 8)
    c.line_to(x + 70, sy - 8)
    c.line_to(x + 95, hip)
    c.line_to(x - 95, hip)
    c.close_path()
    fill_stroke(c, WHITE, INK, 6)
    if who == "tito":
        for k in range(3):
            for side in (-1, 1):
                c.arc(x + side * 26, sy + 50 + k * 60, 8, 0, 2 * math.pi)
                fill_stroke(c, hx("C9CED6"), INK, 3)
        rrect(c, x - 95, hip - 20, 190, 20, 6)
        fill_stroke(c, col, INK, 4)
        return
    # cuello en V con el color del uniforme (scrubs)
    c.move_to(x - 34, sy - 8)
    c.line_to(x, sy + 60)
    c.line_to(x + 34, sy - 8)
    c.close_path()
    fill_stroke(c, col, INK, 4)
    # solapas
    c.set_source_rgba(*INK)
    c.set_line_width(4)
    for side in (-1, 1):
        c.move_to(x + side * 34, sy - 8)
        c.line_to(x + side * 10, sy + 120)
        c.stroke()
    # bolsillo con lapiceros
    rrect(c, x + 30, sy + 110, 46, 40, 6)
    fill_stroke(c, WHITE, INK, 4)
    for k, cc in enumerate((hx("2B6BE0"), RED)):
        c.rectangle(x + 38 + k * 14, sy + 96, 7, 22)
        c.set_source_rgba(*cc)
        c.fill()
    # credencial
    rrect(c, x - 82, sy + 100, 56, 40, 6)
    fill_stroke(c, col, INK, 3)
    rrect(c, x - 76, sy + 106, 18, 18, 3)
    c.set_source_rgba(1, 1, 1, 0.9)
    c.fill()


def draw_mandil(c, who, x, sy, bob):
    col = hx("FFFFFF") if who == "rosita" else hx("F4E3C1")
    hip = HIP_Y + bob * 0.3 + 30
    c.move_to(x - 45, sy + 30)
    c.line_to(x + 45, sy + 30)
    c.line_to(x + 75, hip)
    c.line_to(x - 75, hip)
    c.close_path()
    fill_stroke(c, col, INK, 5)
    rrect(c, x - 30, sy + 120, 60, 40, 8)
    fill_stroke(c, CAST[who]["body"], INK, 3)
    c.set_source_rgba(*INK)
    c.set_line_width(3)
    c.move_to(x - 45, sy + 30)
    c.line_to(x - 20, sy - 12)
    c.move_to(x + 45, sy + 30)
    c.line_to(x + 20, sy - 12)
    c.stroke()


def draw_estetoscopio(c, who, x, sy, t):
    """Estetoscopio colgado del cuello (aparato del cuello)."""
    tubo = hx("1E2230")
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_source_rgba(*tubo)
    c.set_line_width(9)
    c.move_to(x - 48, sy - 14)
    c.curve_to(x - 70, sy + 70, x - 30, sy + 130, x + 4, sy + 140)
    c.stroke()
    c.move_to(x + 48, sy - 14)
    c.curve_to(x + 62, sy + 50, x + 30, sy + 110, x + 4, sy + 140)
    c.stroke()
    c.set_source_rgba(*METAL)
    c.set_line_width(6)
    for side in (-1, 1):
        c.move_to(x + side * 48, sy - 14)
        c.line_to(x + side * 40, sy - 40)
        c.stroke()
    c.set_source_rgba(*tubo)
    c.set_line_width(8)
    sw = 4 * math.sin(t * 2.3)
    c.move_to(x + 4, sy + 140)
    c.line_to(x + 4 + sw, sy + 190)
    c.stroke()
    c.arc(x + 4 + sw, sy + 210, 24, 0, 2 * math.pi)
    fill_stroke(c, hx("C9CED6"), INK, 5)
    c.arc(x + 4 + sw, sy + 210, 12, 0, 2 * math.pi)
    c.set_source_rgba(*CAST[who]["body"])
    c.fill()


def draw_cucharon(c, x, y, ang):
    c.save()
    c.translate(x, y)
    c.rotate(ang)
    rrect(c, -8, -150, 16, 170, 8)
    fill_stroke(c, hx("C68B59"), INK, 4)
    c.save()
    c.translate(0, -170)
    c.scale(1, 1.3)
    c.arc(0, 0, 30, 0, 2 * math.pi)
    c.restore()
    fill_stroke(c, hx("D9A066"), INK, 5)
    c.restore()


def draw_face(c, cx, cy, r, who, expr, talking, t):
    cfg = CAST[who]
    # base
    c.save()
    c.arc(cx, cy, r, 0, 2 * math.pi)
    c.clip()
    g = cairo.LinearGradient(cx - r, cy - r, cx, cy + r)
    g.add_color_stop_rgba(0, *hx("C7CDD6"))
    g.add_color_stop_rgba(1, *METAL)
    c.set_source(g)
    c.rectangle(cx - r, cy - r, r, 2 * r)
    c.fill()
    c.set_source_rgba(*SKIN)
    c.rectangle(cx, cy - r, r, 2 * r)
    c.fill()
    c.set_source_rgba(*hx("7E8694"))
    c.set_line_width(3)
    for yy in (cy - 0.42 * r, cy + 0.36 * r):
        c.move_to(cx - r, yy)
        c.line_to(cx, yy)
        c.stroke()
    for (dx, dy) in ((-0.75, -0.6), (-0.3, -0.72), (-0.82, 0.15), (-0.62, 0.62), (-0.25, 0.78)):
        c.arc(cx + dx * r, cy + dy * r, 5.5, 0, 2 * math.pi)
        c.set_source_rgba(*hx("5D6573"))
        c.fill()
    # costura central
    c.set_source_rgba(*hx("5D6573"))
    c.set_line_width(4)
    c.move_to(cx, cy - r)
    c.line_to(cx, cy + r)
    c.stroke()
    c.set_line_width(2.5)
    for k in range(-4, 5):
        c.move_to(cx - 6, cy + k * r * 0.22)
        c.line_to(cx + 6, cy + k * r * 0.22)
        c.stroke()
    # rubor
    c.arc(cx + 0.55 * r, cy + 0.32 * r, 0.16 * r, 0, 2 * math.pi)
    c.set_source_rgba(*hx("F07A7A", 0.45))
    c.fill()
    c.restore()

    # ojo robot (LED)
    ex, ey = cx - 0.47 * r, cy - 0.05 * r
    glow = cairo.RadialGradient(ex, ey, 2, ex, ey, 0.55 * r)
    glow.add_color_stop_rgba(0, *cfg["led"][:3], 0.55)
    glow.add_color_stop_rgba(1, *cfg["led"][:3], 0.0)
    c.set_source(glow)
    c.arc(ex, ey, 0.55 * r, 0, 2 * math.pi)
    c.fill()
    rrect(c, ex - 0.25 * r, ey - 0.17 * r, 0.5 * r, 0.34 * r, 9)
    c.set_source_rgba(*hx("1A1D27"))
    c.fill()
    led_r = 0.11 * r * (0.25 if expr == "wink" else 1.0)
    c.arc(ex, ey, max(led_r, 3), 0, 2 * math.pi)
    c.set_source_rgba(*cfg["led"])
    c.fill()

    # ojo humano
    hx0, hy0, er = cx + 0.42 * r, cy - 0.08 * r, 0.27 * r
    blink = (t % 3.7) < 0.12
    if blink:
        c.set_source_rgba(*INK)
        c.set_line_width(6)
        c.move_to(hx0 - er, hy0)
        c.line_to(hx0 + er, hy0)
        c.stroke()
    else:
        scale_e = 1.15 if expr in ("surprised", "alert") else 1.0
        c.arc(hx0, hy0, er * scale_e, 0, 2 * math.pi)
        fill_stroke(c, WHITE, INK, 5)
        lx = 0.05 * r * math.sin(t * 0.9)
        c.arc(hx0 - 0.05 * r + lx, hy0 + 0.02 * r, er * 0.58, 0, 2 * math.pi)
        c.set_source_rgba(*cfg["iris"])
        c.fill()
        c.arc(hx0 - 0.05 * r + lx, hy0 + 0.02 * r, er * 0.3, 0, 2 * math.pi)
        c.set_source_rgba(*hx("111111"))
        c.fill()
        c.arc(hx0 + 0.03 * r + lx, hy0 - 0.07 * r, er * 0.16, 0, 2 * math.pi)
        c.set_source_rgba(*WHITE)
        c.fill()
    # cejas
    c.set_source_rgba(*INK)
    c.set_line_width(7)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    by = hy0 - er - 0.14 * r
    if expr in ("surprised", "alert"):
        c.move_to(hx0 - er, by - 12)
        c.curve_to(hx0 - 0.3 * er, by - 30, hx0 + 0.3 * er, by - 30, hx0 + er, by - 12)
        c.stroke()
    elif expr == "worried":
        c.move_to(hx0 - er, by + 2)
        c.line_to(hx0 + er, by - 16)
        c.stroke()
    elif expr == "serious":
        c.move_to(hx0 - er, by - 8)
        c.line_to(hx0 + er, by + 6)
        c.stroke()

    # boca
    mx, my, mw = cx, cy + 0.47 * r, 0.42 * r
    c.set_line_width(9 if who == "maskaly" else 7)
    c.set_source_rgba(*(hx("D3123E") if who == "maskaly" else INK))
    if talking:
        op = (0.06 + 0.14 * abs(math.sin(t * 17)) * (0.6 + 0.4 * math.sin(t * 5.3))) * r
        c.save()
        c.translate(mx, my)
        c.scale(1, max(op, 4) / (0.22 * r))
        c.arc(0, 0, 0.22 * r, 0, 2 * math.pi)
        c.restore()
        fill_stroke(c, hx("6B1424"), INK, 6)
        rrect(c, mx - 0.13 * r, my - op + 2, 0.26 * r, min(op * 0.45, 12), 3)
        c.set_source_rgba(*WHITE)
        c.fill()
    elif expr in ("happy", "laugh"):
        c.arc(mx, my - 0.18 * r, mw * 0.85, math.radians(25), math.radians(155))
        c.stroke()
    elif expr in ("surprised", "alert"):
        c.save()
        c.translate(mx, my + 4)
        c.scale(0.7, 1)
        c.arc(0, 0, 0.13 * r, 0, 2 * math.pi)
        c.restore()
        fill_stroke(c, hx("6B1424"), INK, 6)
    elif expr == "worried":
        c.move_to(mx - mw * 0.7, my + 6)
        for i in range(1, 7):
            c.line_to(mx - mw * 0.7 + i * mw * 1.4 / 6, my + (6 if i % 2 == 0 else -6))
        c.stroke()
    else:
        c.move_to(mx - mw * 0.6, my)
        c.line_to(mx + mw * 0.6, my)
        c.stroke()

    # contorno
    c.arc(cx, cy, r, 0, 2 * math.pi)
    c.set_source_rgba(*INK)
    c.set_line_width(8)
    c.stroke()


def draw_hair(c, who, cx, cy, r, t):
    if who == "paco":
        # antena
        c.set_source_rgba(*hx("5D6573"))
        c.set_line_width(5)
        c.move_to(cx - 0.55 * r, cy - 0.8 * r)
        c.line_to(cx - 0.75 * r, cy - 1.25 * r)
        c.stroke()
        c.arc(cx - 0.75 * r, cy - 1.25 * r, 13, 0, 2 * math.pi)
        c.set_source_rgba(*CAST["paco"]["led"])
        c.fill()
        # pelo engominado con jopo
        c.move_to(cx, cy - r - 6)
        c.curve_to(cx + 0.3 * r, cy - 1.35 * r, cx + 1.0 * r, cy - 1.2 * r, cx + 1.02 * r, cy - 0.35 * r)
        c.curve_to(cx + 0.85 * r, cy - 0.7 * r, cx + 0.4 * r, cy - 0.78 * r, cx, cy - 0.72 * r)
        c.close_path()
        fill_stroke(c, hx("2E1F1A"), INK, 5)
        c.set_source_rgba(1, 1, 1, 0.35)
        c.set_line_width(5)
        c.arc(cx + 0.45 * r, cy - 0.7 * r, 0.32 * r, math.radians(200), math.radians(290))
        c.stroke()
    elif who == "lucha":
        c.set_source_rgba(*hx("5D6573"))
        c.set_line_width(5)
        c.move_to(cx - 0.5 * r, cy - 0.85 * r)
        c.line_to(cx - 0.62 * r, cy - 1.28 * r)
        c.stroke()
        c.arc(cx - 0.62 * r, cy - 1.28 * r, 13, 0, 2 * math.pi)
        c.set_source_rgba(*CAST["lucha"]["led"])
        c.fill()
        # cola de caballo
        sway = 10 * math.sin(t * 2.2)
        c.move_to(cx + 0.85 * r, cy - 0.55 * r)
        c.curve_to(cx + 1.55 * r, cy - 0.6 * r, cx + 1.45 * r + sway, cy + 0.4 * r, cx + 1.25 * r + sway, cy + 0.85 * r)
        c.curve_to(cx + 1.1 * r, cy + 0.3 * r, cx + 1.05 * r, cy - 0.2 * r, cx + 0.8 * r, cy - 0.3 * r)
        c.close_path()
        fill_stroke(c, hx("4A2370"), INK, 5)
        c.arc(cx + 0.9 * r, cy - 0.5 * r, 14, 0, 2 * math.pi)
        fill_stroke(c, YELLOW, INK, 4)
        # flequillo
        c.move_to(cx, cy - r - 4)
        c.curve_to(cx + 0.5 * r, cy - 1.1 * r, cx + 1.05 * r, cy - 0.7 * r, cx + 0.95 * r, cy - 0.3 * r)
        c.curve_to(cx + 0.7 * r, cy - 0.55 * r, cx + 0.3 * r, cy - 0.45 * r, cx + 0.05 * r, cy - 0.62 * r)
        c.close_path()
        fill_stroke(c, hx("4A2370"), INK, 5)
        # arete
        c.arc(cx + 0.98 * r, cy + 0.32 * r, 9, 0, 2 * math.pi)
        fill_stroke(c, YELLOW, INK, 3)
    elif who == "maskaly":
        c.set_source_rgba(*hx("5D6573"))
        c.set_line_width(5)
        c.move_to(cx - 0.45 * r, cy - 0.85 * r)
        c.line_to(cx - 0.55 * r, cy - 1.45 * r)
        c.stroke()
        c.arc(cx - 0.55 * r, cy - 1.45 * r, 13, 0, 2 * math.pi)
        c.set_source_rgba(*CAST["maskaly"]["led"])
        c.fill()
        # flequillo de lado
        c.move_to(cx - 0.9 * r, cy - 0.45 * r)
        c.curve_to(cx - 0.7 * r, cy - 1.25 * r, cx + 0.9 * r, cy - 1.2 * r, cx + 1.0 * r, cy - 0.2 * r)
        c.curve_to(cx + 0.6 * r, cy - 0.75 * r, cx - 0.2 * r, cy - 0.7 * r, cx - 0.9 * r, cy - 0.45 * r)
        c.close_path()
        fill_stroke(c, hx("8E1B3A"), INK, 5)
        # lentes de sol sobre la cabeza
        for k in (-1, 1):
            rrect(c, cx + k * 0.32 * r - 0.26 * r, cy - 1.02 * r, 0.52 * r, 0.26 * r, 10)
            fill_stroke(c, hx("1A1D27"), YELLOW, 4)
        # pestañas y labios
        ex, ey, er = cx + 0.42 * r, cy - 0.08 * r, 0.27 * r
        c.set_source_rgba(*INK)
        c.set_line_width(4)
        for k in range(3):
            a = math.radians(-60 + k * 30)
            c.move_to(ex + er * math.sin(a), ey - er * math.cos(a))
            c.line_to(ex + (er + 14) * math.sin(a), ey - (er + 14) * math.cos(a))
            c.stroke()
        # aretes grandes
        c.arc(cx + 1.0 * r, cy + 0.45 * r, 20, 0, 2 * math.pi)
        c.set_source_rgba(*YELLOW)
        c.set_line_width(7)
        c.stroke()
        c.arc(cx - 1.0 * r, cy + 0.45 * r, 20, 0, 2 * math.pi)
        c.stroke()
    elif who in ("bruno", "vita"):
        # pelo
        if who == "bruno":
            c.move_to(cx - 0.95 * r, cy - 0.35 * r)
            c.curve_to(cx - 0.9 * r, cy - 1.2 * r, cx + 0.9 * r, cy - 1.2 * r, cx + 0.98 * r, cy - 0.35 * r)
            c.curve_to(cx + 0.6 * r, cy - 0.75 * r, cx - 0.6 * r, cy - 0.75 * r, cx - 0.95 * r, cy - 0.35 * r)
            c.close_path()
            fill_stroke(c, hx("6B6F7A"), INK, 5)     # canas de doctor experimentado
        else:
            sway = 6 * math.sin(t * 2.4)
            for side in (-1, 1):
                c.move_to(cx + side * 0.8 * r, cy - 0.6 * r)
                c.curve_to(cx + side * 1.35 * r, cy - 0.2 * r, cx + side * 1.25 * r + sway, cy + 0.7 * r, cx + side * 1.05 * r + sway, cy + 0.95 * r)
                c.curve_to(cx + side * 0.95 * r, cy + 0.4 * r, cx + side * 0.95 * r, cy - 0.1 * r, cx + side * 0.75 * r, cy - 0.35 * r)
                c.close_path()
                fill_stroke(c, hx("3A1F14"), INK, 5)
            c.move_to(cx - 0.95 * r, cy - 0.4 * r)
            c.curve_to(cx - 0.9 * r, cy - 1.25 * r, cx + 0.9 * r, cy - 1.25 * r, cx + 0.98 * r, cy - 0.4 * r)
            c.curve_to(cx + 0.5 * r, cy - 0.85 * r, cx - 0.5 * r, cy - 0.6 * r, cx - 0.95 * r, cy - 0.4 * r)
            c.close_path()
            fill_stroke(c, hx("3A1F14"), INK, 5)
        # vincha con espejo frontal (aparato de la cabeza)
        col = CAST[who]["body"]
        c.set_source_rgba(*col)
        c.set_line_width(14)
        c.arc(cx, cy + 0.15 * r, 1.0 * r, math.radians(200), math.radians(340))
        c.stroke()
        c.set_source_rgba(*INK)
        c.set_line_width(3)
        c.arc(cx, cy + 0.15 * r, 1.0 * r + 7, math.radians(200), math.radians(340))
        c.stroke()
        mxr, myr = cx + 0.05 * r, cy - 0.98 * r
        c.arc(mxr, myr, 0.36 * r, 0, 2 * math.pi)
        fill_stroke(c, hx("C9CED6"), INK, 6)
        gl = cairo.RadialGradient(mxr - 12, myr - 12, 2, mxr, myr, 0.3 * r)
        gl.add_color_stop_rgba(0, 1, 1, 1, 1)
        gl.add_color_stop_rgba(1, *hx("8FD3FF", 0.9))
        c.arc(mxr, myr, 0.27 * r, 0, 2 * math.pi)
        c.set_source(gl)
        c.fill()
        c.arc(mxr, myr, 6, 0, 2 * math.pi)
        c.set_source_rgba(*INK)
        c.fill()
        # destello del espejo
        if (t % 2.6) < 0.25:
            c.set_source_rgba(1, 1, 0.8, 0.9)
            c.set_line_width(4)
            for a in range(0, 360, 60):
                ra = math.radians(a + 20)
                c.move_to(mxr + math.cos(ra) * 0.45 * r, myr + math.sin(ra) * 0.45 * r)
                c.line_to(mxr + math.cos(ra) * 0.62 * r, myr + math.sin(ra) * 0.62 * r)
                c.stroke()
        if who == "vita":
            c.arc(cx + 0.98 * r, cy + 0.32 * r, 10, 0, 2 * math.pi)
            fill_stroke(c, YELLOW, INK, 3)
    elif who == "tito":
        # pañuelo rojo bajo el mentón se dibuja en el cuerpo; aquí el gorro de chef alto
        c.save()
        c.translate(cx, cy - 0.78 * r)
        rrect(c, -0.78 * r, -0.12 * r, 1.56 * r, 0.36 * r, 10)
        fill_stroke(c, WHITE, INK, 6)
        c.new_path()
        for (dx, dy, rr) in ((-0.55, -0.55, 0.42), (0.0, -0.75, 0.5), (0.55, -0.55, 0.42), (-0.28, -1.05, 0.4), (0.3, -1.05, 0.4)):
            c.new_sub_path()
            c.arc(dx * r, dy * r + 2 * math.sin(t * 2 + dx), rr * r, 0, 2 * math.pi)
        c.set_source_rgba(*WHITE)
        c.fill_preserve()
        c.set_source_rgba(*INK)
        c.set_line_width(5)
        c.stroke()
        rrect(c, -0.6 * r, -0.4 * r, 1.2 * r, 0.36 * r, 6)
        c.set_source_rgba(*WHITE)
        c.fill()
        c.restore()
        # bigote
        c.save()
        c.translate(cx + 0.02 * r, cy + 0.28 * r)
        for side in (-1, 1):
            c.move_to(0, 0)
            c.curve_to(side * 0.2 * r, -0.12 * r, side * 0.42 * r, -0.05 * r, side * 0.46 * r, 0.1 * r)
            c.curve_to(side * 0.3 * r, 0.02 * r, side * 0.15 * r, 0.08 * r, 0, 0.05 * r)
            c.close_path()
            fill_stroke(c, hx("2E1F1A"), INK, 3)
        c.restore()
    elif who == "rosita":
        # moño alto y flequillo, flor en el pelo
        c.arc(cx + 0.1 * r, cy - 1.12 * r, 0.38 * r, 0, 2 * math.pi)
        fill_stroke(c, hx("1E1A33"), INK, 5)
        c.move_to(cx - 0.95 * r, cy - 0.3 * r)
        c.curve_to(cx - 0.95 * r, cy - 1.3 * r, cx + 0.95 * r, cy - 1.3 * r, cx + 0.98 * r, cy - 0.3 * r)
        c.curve_to(cx + 0.55 * r, cy - 0.8 * r, cx - 0.2 * r, cy - 0.55 * r, cx - 0.95 * r, cy - 0.3 * r)
        c.close_path()
        fill_stroke(c, hx("1E1A33"), INK, 5)
        for a in range(0, 360, 72):
            ra = math.radians(a + 10 * math.sin(t))
            c.arc(cx + 0.62 * r + math.cos(ra) * 15, cy - 0.85 * r + math.sin(ra) * 15, 11, 0, 2 * math.pi)
            fill_stroke(c, hx("FF4FA3"), INK, 2)
        c.arc(cx + 0.62 * r, cy - 0.85 * r, 8, 0, 2 * math.pi)
        fill_stroke(c, YELLOW, INK, 2)
        c.arc(cx + 0.98 * r, cy + 0.32 * r, 12, 0, 2 * math.pi)
        fill_stroke(c, hx("FF4FA3"), INK, 3)
        ex, ey, er = cx + 0.42 * r, cy - 0.08 * r, 0.27 * r
        c.set_source_rgba(*INK)
        c.set_line_width(4)
        for k in range(3):
            a = math.radians(-60 + k * 30)
            c.move_to(ex + er * math.sin(a), ey - er * math.cos(a))
            c.line_to(ex + (er + 12) * math.sin(a), ey - (er + 12) * math.cos(a))
            c.stroke()
    elif who == "beto":
        # gorra hacia atrás
        c.move_to(cx - 1.0 * r, cy - 0.3 * r)
        c.curve_to(cx - 0.98 * r, cy - 1.35 * r, cx + 0.98 * r, cy - 1.35 * r, cx + 1.0 * r, cy - 0.3 * r)
        c.close_path()
        fill_stroke(c, hx("2B6BE0"), INK, 6)
        rrect(c, cx - 1.45 * r, cy - 0.42 * r, 0.6 * r, 0.2 * r, 8)
        fill_stroke(c, hx("1F4FA8"), INK, 5)
        c.arc(cx, cy - 1.0 * r, 12, 0, 2 * math.pi)
        fill_stroke(c, YELLOW, INK, 3)
        # barba corta
        c.set_source_rgba(*hx("2E1F1A", 0.55))
        c.arc(cx + 0.45 * r, cy + 0.55 * r, 0.35 * r, math.radians(10), math.radians(170))
        c.set_line_width(10)
        c.stroke()
    elif who == "chato":
        # chullo andino
        c.save()
        c.move_to(cx - 1.0 * r, cy - 0.32 * r)
        c.curve_to(cx - 0.98 * r, cy - 1.45 * r, cx + 0.98 * r, cy - 1.45 * r, cx + 1.0 * r, cy - 0.32 * r)
        c.close_path()
        c.clip_preserve()
        c.set_source_rgba(*RED)
        c.fill()
        bands = [(hx("FFD23F"), -1.05), (hx("19BDAD"), -0.82), (WHITE, -0.6)]
        for col, yy in bands:
            c.set_source_rgba(*col)
            c.move_to(cx - 1.1 * r, cy + yy * r)
            for i in range(12):
                xx = cx - 1.1 * r + (i + 1) * 2.2 * r / 12
                c.line_to(xx, cy + (yy + (0.08 if i % 2 == 0 else 0)) * r)
            c.line_to(cx + 1.1 * r, cy + (yy + 0.14) * r)
            c.line_to(cx - 1.1 * r, cy + (yy + 0.14) * r)
            c.close_path()
            c.fill()
        c.restore()
        c.move_to(cx - 1.0 * r, cy - 0.32 * r)
        c.curve_to(cx - 0.98 * r, cy - 1.45 * r, cx + 0.98 * r, cy - 1.45 * r, cx + 1.0 * r, cy - 0.32 * r)
        c.close_path()
        c.set_source_rgba(*INK)
        c.set_line_width(6)
        c.stroke()
        # orejeras y tiras
        for side in (-1, 1):
            c.move_to(cx + side * 1.0 * r, cy - 0.32 * r)
            c.line_to(cx + side * 1.02 * r, cy + 0.42 * r)
            c.line_to(cx + side * 0.86 * r, cy - 0.3 * r)
            c.close_path()
            fill_stroke(c, RED, INK, 5)
            sw = 6 * math.sin(t * 3 + side)
            c.set_source_rgba(*YELLOW)
            c.set_line_width(6)
            c.move_to(cx + side * 1.02 * r, cy + 0.42 * r)
            c.line_to(cx + side * 1.0 * r + sw, cy + 0.85 * r)
            c.stroke()
            c.arc(cx + side * 1.0 * r + sw, cy + 0.88 * r, 11, 0, 2 * math.pi)
            fill_stroke(c, YELLOW, INK, 3)
        # pompón
        c.arc(cx, cy - 1.18 * r, 24, 0, 2 * math.pi)
        fill_stroke(c, YELLOW, INK, 5)


def draw_maskaly_back(c, cx, cy, r, t):
    # melena voluminosa de diva
    col = hx("8E1B3A")
    c.new_path()
    for (dx, dy, rr) in ((-0.95, -0.55, 0.55), (-1.05, 0.1, 0.5), (-0.95, 0.65, 0.45), (0.95, -0.55, 0.55),
                         (1.05, 0.1, 0.5), (0.95, 0.65, 0.45), (-0.5, -1.0, 0.55), (0.5, -1.0, 0.55), (0, -1.12, 0.5)):
        c.new_sub_path()
        c.arc(cx + dx * r, cy + dy * r + 3 * math.sin(t * 2 + dx), rr * r, 0, 2 * math.pi)
    c.set_source_rgba(*col)
    c.fill_preserve()
    c.set_source_rgba(*INK)
    c.set_line_width(5)
    c.stroke()


def draw_character(c, who, t, st):
    """st: dict con pose, expr, talking, bounce"""
    cfg = CAST[who]
    x = cfg["x"]
    talking = st.get("talking", False)
    bob = 4 * math.sin(t * 3.1 + x) - (16 * abs(math.sin(t * 7 + x)) if st.get("jump") else 0)
    hy = HEAD_Y + bob
    col = cfg["body"]
    # sombra
    c.save()
    c.translate(x, FOOT_Y + 22)
    c.scale(1, 0.18)
    c.arc(0, 0, 150, 0, 2 * math.pi)
    c.restore()
    c.set_source_rgba(0, 0, 0, 0.18)
    c.fill()
    # piernas y torso
    limb(c, [(x - 70, FOOT_Y), (x, HIP_Y + bob * 0.3), (x + 70, FOOT_Y)], col, 11)
    for fx_ in (x - 70, x + 70):
        c.save()
        c.translate(fx_ + (-8 if fx_ < x else 8), FOOT_Y + 4)
        c.scale(1.6, 1)
        c.arc(0, 0, 14, 0, 2 * math.pi)
        c.restore()
        fill_stroke(c, col, INK, 3)
    limb(c, [(x, HIP_Y + bob * 0.3), (x, hy + HEAD_R - 10)], col, 11)
    sy0 = SHOULDER_Y + bob * 0.6
    if who in ("bruno", "vita", "tito"):
        draw_bata(c, who, x, sy0, bob)
    elif who in ("rosita", "beto"):
        draw_mandil(c, who, x, sy0, bob)
    # brazos
    pose = st.get("pose", "rest")
    (l1, l2), (r1, r2) = POSES.get(pose, POSES["rest"])
    wig = 8 * math.sin(t * 6.5) if talking else 3 * math.sin(t * 2 + x)
    sy = SHOULDER_Y + bob * 0.6
    if pose in ("wave", "up"):
        r2 += 18 * math.sin(t * 9)
        if pose == "up":
            l2 += 18 * math.sin(t * 9 + 1)
    # side: -1 = izquierda de pantalla
    left = arm_points(x, sy, -1, l1 + wig, l2)
    if who == LOCUTOR and st.get("mic", True) and who in PROPS:
        right = arm_points(x, sy, 1, 32, 128)
    else:
        right = arm_points(x, sy, 1, r1 - wig, r2)
    for pts in (left, right):
        limb(c, list(pts), col, 10)
        c.arc(pts[2][0], pts[2][1], 13, 0, 2 * math.pi)
        fill_stroke(c, col, INK, 3)
    if who == "paco":
        # moño
        c.move_to(x, sy - 8)
        c.line_to(x - 30, sy - 26)
        c.line_to(x - 30, sy + 10)
        c.close_path()
        c.move_to(x, sy - 8)
        c.line_to(x + 30, sy - 26)
        c.line_to(x + 30, sy + 10)
        c.close_path()
        fill_stroke(c, RED, INK, 4)
    if who == "maskaly":
        # collar de perlas
        for k in range(-3, 4):
            c.arc(x + k * 13, sy - 2 + abs(k) * -3 + 10, 7, 0, 2 * math.pi)
            fill_stroke(c, WHITE, INK, 2)
    if who == LOCUTOR and st.get("mic", True) and who in PROPS:
        hxp, hyp = right[2]
        if PROPS[who] == "mic":
            draw_mic(c, hxp - 4, hyp - 6, math.radians(-28))
        else:
            draw_cucharon(c, hxp - 4, hyp - 6, math.radians(-28 + 8 * math.sin(t * 3)))
    if who in ("bruno", "vita"):
        draw_estetoscopio(c, who, x, sy, t)
    if who == "tito":
        # pañuelo rojo al cuello
        c.move_to(x - 40, sy - 16)
        c.line_to(x + 40, sy - 16)
        c.line_to(x, sy + 40)
        c.close_path()
        fill_stroke(c, RED, INK, 4)
    if who == "lucha":
        # credencial de prensa
        c.set_source_rgba(*INK)
        c.set_line_width(3)
        c.move_to(x - 14, sy - 10)
        c.line_to(x, sy + 60)
        c.line_to(x + 14, sy - 10)
        c.stroke()
        rrect(c, x - 34, sy + 52, 68, 46, 7)
        fill_stroke(c, WHITE, INK, 4)
        font(c, 15)
        c.set_source_rgba(*PINK)
        c.move_to(x - tw(c, "PRENSA") / 2, sy + 81)
        c.show_text("PRENSA")
    # cabeza
    if who == "maskaly":
        draw_maskaly_back(c, x, hy, HEAD_R, t)
    draw_face(c, x, hy, HEAD_R, who, st.get("expr", "neutral"), talking, t)
    draw_hair(c, who, x, hy, HEAD_R, t)
    return hy


# ---------------------------------------------------------------- efectos
def fx_ja(c, x, hy, t, local):
    for i, (dx, dy, s) in enumerate(((-120, -90, 60), (60, -150, 66), (110, -40, 56))):
        if local < i * 0.15:
            continue
        j = 4 * math.sin(t * 30 + i)
        text_center(c, "JA", x + dx + j, hy + dy, s, TEAL, outline=INK, ow=9)


def fx_alert(c, x, hy, t, local):
    text_center(c, "!!", x + 110, hy - 110 + 3 * math.sin(t * 25), 80, RED, outline=INK, ow=8)
    c.set_source_rgba(*INK)
    c.set_line_width(5)
    for a in range(0, 360, 45):
        ra = math.radians(a)
        c.move_to(x + math.cos(ra) * 150, hy + math.sin(ra) * 150)
        c.line_to(x + math.cos(ra) * 185, hy + math.sin(ra) * 185)
        c.stroke()


def fx_plop(c, x, hy, t, local):
    k = ease_out_back(local / 0.3)
    cx, cy = x + 95, hy - 120
    c.save()
    c.translate(cx, cy)
    c.scale(k, k)
    c.rotate(-0.15)
    c.move_to(95, 0)
    for i in range(1, 25):
        a = i * math.pi / 12
        rr = 95 if i % 2 == 0 else 58
        c.line_to(rr * math.cos(a), rr * 0.7 * math.sin(a))
    c.close_path()
    fill_stroke(c, YELLOW, INK, 5)
    font(c, 36)
    c.set_source_rgba(*RED)
    c.move_to(-tw(c, "¡PLOP!") / 2, 13)
    c.show_text("¡PLOP!")
    c.restore()


def fx_sweat(c, x, hy, t, local):
    for i, (dx, dy) in enumerate(((105, -60), (125, 5))):
        yy = hy + dy + ((local * 60 + i * 20) % 40)
        c.move_to(x + dx, yy - 20)
        c.curve_to(x + dx + 14, yy, x + dx + 12, yy + 14, x + dx, yy + 14)
        c.curve_to(x + dx - 12, yy + 14, x + dx - 14, yy, x + dx, yy - 20)
        fill_stroke(c, hx("6EC8FF"), INK, 3)


def fx_money(c, x, hy, t, local):
    rnd = random.Random(7)
    for i in range(7):
        dx = rnd.uniform(-170, 170)
        sp = rnd.uniform(70, 130)
        yy = hy - 40 - ((local * sp + i * 60) % 260)
        text_center(c, "S/", x + dx, yy, 46, hx("1FB24A"), outline=INK, ow=6)


def fx_stars(c, x, hy, t, local):
    for i in range(5):
        a = t * 2 + i * 1.256
        px, py = x + math.cos(a) * 170, hy - 40 + math.sin(a) * 90
        s = 14 + 6 * math.sin(t * 8 + i)
        c.move_to(px, py - s)
        c.line_to(px + s * 0.3, py - s * 0.3)
        c.line_to(px + s, py)
        c.line_to(px + s * 0.3, py + s * 0.3)
        c.line_to(px, py + s)
        c.line_to(px - s * 0.3, py + s * 0.3)
        c.line_to(px - s, py)
        c.line_to(px - s * 0.3, py - s * 0.3)
        c.close_path()
        fill_stroke(c, YELLOW, INK, 3)


def confetti(c, t, start, n=70, seed=3):
    rnd = random.Random(seed)
    cols = [TEAL, PINK, YELLOW, hx("2B6BE0"), hx("FF7A1A"), hx("9B4DFF")]
    lt = t - start
    if lt < 0 or lt > 3.5:
        return
    for i in range(n):
        x0 = rnd.uniform(0, W)
        vy = rnd.uniform(380, 700)
        y = -40 + vy * lt - rnd.uniform(0, 300)
        x = x0 + 40 * math.sin(lt * rnd.uniform(2, 5) + i)
        if y < -40 or y > H:
            continue
        c.save()
        c.translate(x, y)
        c.rotate(lt * rnd.uniform(3, 9) + i)
        c.rectangle(-11, -6, 22, 12)
        c.set_source_rgba(*rnd.choice(cols))
        c.fill()
        c.restore()


def fx_confeti(c, x, hy, t, local):
    confetti(c, t, t - local, 60, 11)


FX = {"confeti": fx_confeti, "ja": fx_ja, "alert": fx_alert, "plop": fx_plop, "sweat": fx_sweat, "money": fx_money, "stars": fx_stars}


# ---------------------------------------------------------------- globo y tarjetas
def layout_words(c, words, maxw, size):
    font(c, size)
    sp = tw(c, " ")
    lines, cur, curw = [], [], 0
    for wd, hl in words:
        ww = tw(c, wd)
        if cur and curw + sp + ww > maxw:
            lines.append(cur)
            cur, curw = [], 0
        cur.append((wd, hl, ww))
        curw += (sp if len(cur) > 1 else 0) + ww
    if cur:
        lines.append(cur)
    return lines, sp


def draw_bubble(c, scene, local, dur):
    who = scene["quien"]
    cfg = CAST[who]
    words = parse_words(scene["texto"])
    size = 50
    lines, sp = layout_words(c, words, 850, size)
    while len(lines) > 2 and size > 42:
        size -= 4
        lines, sp = layout_words(c, words, 850, size)
    while len(lines) > 3 and size > 40:
        size -= 4
        lines, sp = layout_words(c, words, 850, size)
    while len(lines) > (4 if CANAL["fondo"] != "noticias" else 3):
        size -= 4
        lines, sp = layout_words(c, words, 850, size)
    lh = size * 1.2
    bx, by, bw = 50, 145, 980
    bh = 86 + lh * len(lines)
    k = ease_out_back(local / 0.22)
    c.save()
    tail_x = cfg["x"]
    c.translate(tail_x, by + bh)
    c.scale(0.85 + 0.15 * k, 0.85 + 0.15 * k)
    c.translate(-tail_x, -(by + bh))
    # sombra
    rrect(c, bx + 8, by + 10, bw, bh, 34)
    c.set_source_rgba(0, 0, 0, 0.12)
    c.fill()
    rrect(c, bx, by, bw, bh, 34)
    fill_stroke(c, WHITE, INK, 7)
    # cola
    tx = clamp(tail_x, bx + 90, bx + bw - 90)
    c.move_to(tx - 30, by + bh - 4)
    c.line_to(tx + (tail_x - tx) * 0.5, by + bh + 46)
    c.line_to(tx + 26, by + bh - 4)
    c.set_source_rgba(*WHITE)
    c.fill_preserve()
    c.set_source_rgba(*INK)
    c.set_line_width(7)
    c.stroke()
    c.rectangle(tx - 24, by + bh - 14, 46, 12)
    c.set_source_rgba(*WHITE)
    c.fill()
    # etiqueta
    font(c, 30)
    lw_ = tw(c, cfg["name"]) + 40
    rrect(c, bx + 34, by + 20, lw_, 46, 23)
    c.set_source_rgba(*cfg["body"])
    c.fill()
    c.set_source_rgba(*WHITE)
    c.move_to(bx + 54, by + 54)
    c.show_text(cfg["name"])
    # karaoke
    total = sum(len(l) for l in lines)
    prog = clamp((local - VOZ_OFFSET) / max(scene.get("habla", dur * 0.78) * 0.95, 0.5))
    shown = math.ceil(prog * total)
    n = 0
    font(c, size)
    y = by + 78 + size * 0.95
    for line in lines:
        x = bx + 44
        for wd, hl, ww in line:
            n += 1
            if n <= shown:
                col = PINK if hl else NAVY
            else:
                col = GRAY_TXT
            c.set_source_rgba(*col)
            c.move_to(x, y)
            c.show_text(wd)
            x += ww + sp
        y += lh
    c.restore()


def draw_card(c, card, local):
    k = ease_out_back(local / 0.3)
    if k <= 0:
        return
    cx, cy = 540, 655
    label, valor = card["label"], card["valor"]
    nota = card.get("nota", "")
    font(c, 84)
    vw = tw(c, valor)
    w = max(560, vw + 110)
    w = min(w, 1000)
    h = 220 if nota else 190
    c.save()
    c.translate(cx, cy)
    c.scale(k, k)
    rrect(c, -w / 2 + 8, -h / 2 + 10, w, h, 26)
    c.set_source_rgba(0, 0, 0, 0.25)
    c.fill()
    rrect(c, -w / 2, -h / 2, w, h, 26)
    fill_stroke(c, NAVY, TEAL, 7)
    text_center(c, label, 0, -h / 2 + 52, 30, TEAL, F_XBOLD)
    size = 84
    font(c, size)
    while tw(c, valor) > w - 60:
        size -= 4
        font(c, size)
    text_center(c, valor, 0, -h / 2 + 140, size, WHITE)
    if nota:
        text_center(c, nota, 0, h / 2 - 20, 22, GRAY_TXT, F_SEMI)
    c.restore()


def draw_top(c, ep, t, total):
    c.set_source_rgba(1, 1, 1, 0.9)
    c.rectangle(0, 0, W, 14)
    c.fill()
    c.set_source_rgba(*TEAL)
    c.rectangle(0, 0, W * clamp(t / total), 14)
    c.fill()
    s = " ".join(PROGRAMA) + " · " + ep["fecha"]
    font(c, 34)
    w = tw(c, s) + 64
    rrect(c, 540 - w / 2, 58, w, 64, 32)
    c.set_source_rgba(*NAVY)
    c.fill()
    text_center(c, s, 540, 103, 34, TEAL)


# ---------------------------------------------------------------- intro / cierre
def draw_sunburst(c, t, col_a, col_b):
    c.set_source_rgba(*col_a)
    c.paint()
    c.save()
    c.translate(540, 980)
    c.rotate(t * 0.25)
    c.set_source_rgba(*col_b)
    for i in range(24):
        a0 = i * 2 * math.pi / 24
        c.move_to(0, 0)
        c.arc(0, 0, 2400, a0, a0 + math.pi / 24)
        c.close_path()
        c.fill()
    c.restore()


def draw_intro(c, ep, t):
    draw_sunburst(c, t, hx("EAF8F6"), hx("CDEFEA"))
    k = ease_out_back(t / 0.35)
    c.save()
    c.translate(540, 300)
    c.scale(k, k)
    rrect(c, -330, -70, 660, 140, 36)
    fill_stroke(c, NAVY, TEAL, 8)
    text_center(c, PROGRAMA[0], 0, -6, 60, WHITE)
    text_center(c, PROGRAMA[1], 0, 52, 52, TEAL)
    c.restore()
    if t > 0.15:
        k2 = ease_out_back((t - 0.15) / 0.3)
        c.save()
        c.translate(540, 440)
        c.scale(k2, k2)
        s = ep["fecha"] + " · " + ep.get("seccion", "PERÚ")
        font(c, 34, F_XBOLD)
        w = tw(c, s) + 60
        rrect(c, -w / 2, -32, w, 64, 32)
        c.set_source_rgba(*RED)
        c.fill()
        text_center(c, s, 0, 12, 34, WHITE, F_XBOLD)
        c.restore()
    for i, line in enumerate(ep["titular"]):
        st = 0.3 + i * 0.18
        if t < st:
            continue
        k3 = ease_out_back((t - st) / 0.3)
        c.save()
        c.translate(540, 600 + i * 120)
        c.scale(k3, k3)
        c.rotate(-0.03)
        col = PINK if i == len(ep["titular"]) - 1 else NAVY
        size = 104
        font(c, size)
        while tw(c, line) > 980:
            size -= 4
            font(c, size)
        text_center(c, line, 0, 36, size, col, outline=WHITE, ow=18)
        c.restore()
    draw_character(c, LOCUTOR, t, {"pose": "rest", "expr": "happy", "talking": t > 0.6, "mic": True, "jump": True})
    confetti(c, t, 0.2, 80, 5)


def draw_thumb_icon(c, x, y, s, col):
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    rrect(c, -30, -2, 16, 34, 4)
    c.set_source_rgba(*col)
    c.fill()
    c.move_to(-10, 0)
    c.line_to(2, -26)
    c.curve_to(6, -36, 18, -34, 16, -22)
    c.line_to(12, -6)
    c.line_to(28, -6)
    c.curve_to(38, -6, 40, 4, 34, 10)
    c.line_to(28, 30)
    c.curve_to(26, 34, 22, 34, 18, 34)
    c.line_to(-10, 34)
    c.close_path()
    c.fill()
    c.restore()


def draw_heart(c, x, y, s, col, outline=None):
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    c.move_to(0, 30)
    c.curve_to(-50, -2, -30, -42, 0, -18)
    c.curve_to(30, -42, 50, -2, 0, 30)
    c.close_path()
    c.restore()
    c.set_source_rgba(*col)
    if outline:
        c.fill_preserve()
        c.set_source_rgba(*outline)
        c.set_line_width(4)
        c.stroke()
    else:
        c.fill()


def draw_user_plus(c, x, y, s, col):
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    c.set_source_rgba(*col)
    c.arc(-8, -14, 13, 0, 2 * math.pi)
    c.fill()
    c.arc(-8, 26, 26, math.pi, 2 * math.pi)
    c.fill()
    c.rectangle(18, -6, 22, 7)
    c.fill()
    c.rectangle(25.5, -14, 7, 22)
    c.fill()
    c.restore()


def draw_hand(c, x, y, press):
    c.save()
    c.translate(x, y)
    s = 1.0 - 0.12 * press
    c.scale(s, s)
    c.rotate(-0.25)
    rrect(c, -12, -5, 24, 80, 12)          # índice
    fill_stroke(c, YELLOW, INK, 4)
    rrect(c, -28, 45, 74, 82, 24)          # palma
    fill_stroke(c, YELLOW, INK, 4)
    for i in range(3):
        rrect(c, 8 + i * 0 + i * 12, 40 + i * 6, 22, 30, 10)
    c.restore()


def draw_outro(c, ep, t, local):
    # banda superior
    k = ease_out(local / 0.3)
    c.save()
    c.set_source_rgba(*hx("1C2130", 0.93))
    c.rectangle(0, 170, W, 560 * k)
    c.fill()
    c.restore()
    if local > 0.15:
        k2 = ease_out_back((local - 0.15) / 0.3)
        c.save()
        c.translate(540, 300)
        c.scale(k2, k2)
        text_center(c, CANAL["gracias"], 0, 0, 70 if len(CANAL["gracias"]) < 22 else 62, TEAL)
        text_center(c, ep.get("cierre_sub", "Mañana, otra noticia calientita"), 0, 80, 44, WHITE, F_SEMI)
        rrect(c, -450, 150, 900, 104, 52)
        fill_stroke(c, TEAL, WHITE, 5)
        text_center(c, "SÍGUEME PARA NO PERDÉRTELO", 0, 220, 48, NAVY)
        c.restore()
    # panel de botones
    if local > 0.35:
        k3 = ease_out_back((local - 0.35) / 0.35)
        c.save()
        c.translate(540, 1395)
        c.scale(k3, k3)
        rrect(c, -470, -165, 940, 330, 36)
        c.set_source_rgba(*hx("1C2130", 0.96))
        c.fill_preserve()
        c.set_source_rgba(*TEAL)
        c.set_line_width(7)
        c.stroke()
        text_center(c, "¿TE SIRVIÓ? APÓYAME", 0, -98, 46, WHITE)
        taps = (1.1, 2.0, 2.9)
        on = [local > tp + 0.1 for tp in taps]
        # LIKE
        rrect(c, -440, -50, 280, 110, 55)
        c.set_source_rgba(*(hx("2B6BE0") if on[0] else hx("343A4C")))
        c.fill()
        draw_thumb_icon(c, -370, 4, 1.2, WHITE)
        text_center(c, "LIKE", -250, 22, 46, WHITE)
        # CORAZÓN
        rrect(c, -140, -50, 280, 110, 55)
        c.set_source_rgba(*(hx("3A1F2B") if on[1] else hx("343A4C")))
        c.fill()
        hk = 1.0 + (0.35 * math.sin(clamp((local - taps[1] - 0.1) / 0.35) * math.pi) if on[1] else 0)
        draw_heart(c, -60, 6, 1.15 * hk, RED if on[1] else hx("343A4C"), outline=None if on[1] else WHITE)
        text_center(c, "ME GUSTA" if not on[1] else "¡GRACIAS!", 50, 20, 30, WHITE)
        if on[1]:
            for i in range(6):
                lt = local - taps[1] - 0.1
                if lt < 1.2:
                    a = i * math.pi / 3
                    draw_heart(c, -60 + math.cos(a) * 90 * ease_out(lt / 0.6),
                               6 + math.sin(a) * 70 * ease_out(lt / 0.6) - lt * 40, 0.35, hx("FF5A7A", 1 - lt / 1.2))
        # SÍGUEME
        rrect(c, 160, -50, 280, 110, 55)
        c.set_source_rgba(*(hx("343A4C") if on[2] else RED))
        c.fill()
        draw_user_plus(c, 215, 4, 1.05, WHITE)
        text_center(c, "SIGUIENDO" if on[2] else "SÍGUEME", 330, 18, 36 if on[2] else 40, WHITE)
        text_center(c, CANAL["campana"], 0, 125, 30, TEAL, F_XBOLD)
        # mano
        targets = [(-300, 30), (-60, 40), (300, 30)]
        pos = targets[0]
        press = 0.0
        for i, tp in enumerate(taps):
            if local >= tp - 0.45:
                prev = targets[i - 1] if i > 0 else (0, 220)
                m = ease_out((local - (tp - 0.45)) / 0.4)
                pos = (prev[0] + (targets[i][0] - prev[0]) * m, prev[1] + (targets[i][1] - prev[1]) * m)
                press = max(0.0, 1 - abs(local - tp) / 0.12)
        if local < taps[0] - 0.45:
            pos = (0, 220)
        draw_hand(c, pos[0] + 20, pos[1] + 10, press)
        c.restore()


# ---------------------------------------------------------------- timeline
def build_timeline(ep):
    t = INTRO
    out = []
    for sc in ep["escenas"]:
        sc.setdefault("dur", 4.0)
        out.append((t, t + sc["dur"], sc))
        t += sc["dur"]
    return out, t + OUTRO


def state_for(ep, timeline, t):
    """Devuelve escena actual, tiempo local y estados de cada personaje."""
    cur, local = None, 0
    for (a, b, sc) in timeline:
        if a <= t < b:
            cur, local = (a, b, sc), t - a
    states = {w: {"pose": "rest", "expr": "neutral", "talking": False} for w in CAST}
    if cur:
        sc = cur[2]
        for w, e in sc.get("expr", {}).items():
            states[w]["expr"] = e
        for w, p in sc.get("pose", {}).items():
            states[w]["pose"] = p
        speaking_until = cur[0] + VOZ_OFFSET + sc.get("habla", (cur[1] - cur[0]) * 0.82)
        states[sc["quien"]]["talking"] = t < speaking_until
        for w_ in states:
            if states[w_]["expr"] in ("happy", "laugh"):
                states[w_]["jump"] = True
        if states[sc["quien"]]["pose"] == "rest" and sc["quien"] != LOCUTOR:
            states[sc["quien"]]["pose"] = "talk"
    return cur, local, states


def render_frame(ctx, bg, ep, timeline, total, t):
    c = ctx
    if t < INTRO:
        draw_intro(c, ep, t)
        if t > INTRO - 0.18:
            a = (t - (INTRO - 0.18)) / 0.18
            c.set_source_rgba(1, 1, 1, a)
            c.paint()
        return
    c.set_source_surface(bg, 0, 0)
    c.paint()
    if CANAL["fondo"] == "noticias":
        draw_live(c, t)
    cur, local, states = state_for(ep, timeline, t)
    in_outro = t >= total - OUTRO
    if in_outro:
        for w in states:
            states[w] = {"pose": "wave" if w != LOCUTOR else "rest", "expr": "happy", "talking": False, "jump": True}
    # pantalla: última pantalla declarada hasta ahora
    screen, s_start = ep.get("pantalla_inicial", "logo"), INTRO
    for (a, b, sc) in timeline:
        if a <= t and "pantalla" in sc:
            screen, s_start = sc["pantalla"], a
    draw_screen(c, screen, t, t - s_start)
    heads = {}
    for w in ELENCO:
        heads[w] = draw_character(c, w, t, states[w])
    if CANAL["fondo"] == "cocina":
        c.set_source_surface(FRENTE, 0, 0)
        c.paint()
        fuego = bool(cur and cur[2].get("fuego")) and not in_outro
        draw_meson(c, t, fuego)
    if cur and not in_outro:
        sc = cur[2]
        for f in sc.get("fx", []):
            name, who = f.split(":")
            FX[name](c, CAST[who]["x"], heads[who], t, local)
        if "tarjeta" in sc:
            draw_card(c, sc["tarjeta"], local - sc["tarjeta"].get("delay", 0.5))
        draw_bubble(c, sc, local, cur[1] - cur[0])
    if in_outro:
        draw_outro(c, ep, t, t - (total - OUTRO))
        for w in [e for e in ELENCO if e != LOCUTOR]:
            fx_stars(c, CAST[w]["x"], heads[w], t, 0)
        confetti(c, t, total - OUTRO + 1.0, 90, 9)
    if t < INTRO + 0.15:
        c.set_source_rgba(1, 1, 1, 1 - (t - INTRO) / 0.15)
        c.paint()
    draw_top(c, ep, t, total)
    if not in_outro:
        draw_aviso(c)


# ---------------------------------------------------------------- audio
SR = 48000


def synth_audio(ep, timeline, total, path):
    n = int(total * SR) + SR
    music = np.zeros(n)
    bpm = CANAL["bpm"]
    beat = 60 / bpm
    tt = np.arange(n) / SR

    def note(f, start, dur, amp, kind="pluck"):
        i0 = int(start * SR)
        m = int(dur * SR)
        if i0 >= n:
            return
        m = min(m, n - i0)
        x = np.arange(m) / SR
        if kind == "pluck":
            env = np.exp(-x * 6) * np.minimum(1, x * 200)
            sig = np.sin(2 * np.pi * f * x) + 0.4 * np.sin(4 * np.pi * f * x) + 0.15 * np.sin(6 * np.pi * f * x)
        elif kind == "bass":
            env = np.exp(-x * 4) * np.minimum(1, x * 300)
            sig = np.sin(2 * np.pi * f * x) + 0.3 * np.sign(np.sin(2 * np.pi * f * x)) * 0.3
        else:
            env = np.exp(-x * 3)
            sig = np.sin(2 * np.pi * f * x)
        music[i0:i0 + m] += amp * env * sig

    rng = np.random.default_rng(1)
    chords = [[261.6, 329.6, 392.0], [196.0, 246.9, 293.7], [220.0, 261.6, 329.6], [174.6, 220.0, 261.6]]
    roots = [65.4, 49.0, 55.0, 43.65]
    nb = int(total / beat) + 2
    for b in range(nb):
        st = b * beat
        bar = (b // 4) % 4
        # kick
        if b % 2 == 0:
            i0 = int(st * SR)
            m = min(int(0.25 * SR), n - i0)
            if m > 0:
                x = np.arange(m) / SR
                f = 120 * np.exp(-x * 25) + 45
                music[i0:i0 + m] += 0.55 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 14)
        else:  # clap
            i0 = int(st * SR)
            m = min(int(0.15 * SR), n - i0)
            if m > 0:
                x = np.arange(m) / SR
                music[i0:i0 + m] += 0.18 * rng.standard_normal(m) * np.exp(-x * 30)
        for h in (0, 0.5):
            i0 = int((st + h * beat) * SR)
            m = min(int(0.04 * SR), n - i0)
            if m > 0:
                noise = rng.standard_normal(m)
                noise = np.diff(np.concatenate([[0], noise]))
                music[i0:i0 + m] += 0.07 * noise * np.exp(-np.arange(m) / SR * 90)
        note(roots[bar], st, beat * 0.9, 0.35, "bass")
        note(roots[bar] * 2, st + beat / 2, beat * 0.4, 0.15, "bass")
        if b % 2 == 0:
            for k_, f in enumerate(chords[bar]):
                note(f * 2, st + k_ * 0.03, beat * 1.5, 0.07, "pluck")
        mel = [4, 2, 0, 2, 4, 4, 5, 4]
        scale = [523.3, 587.3, 659.3, 698.5, 784.0, 880.0]
        if (b // 16) % 2 == 1:
            for h, deg in enumerate(mel[(b % 4) * 2:(b % 4) * 2 + 2]):
                note(scale[deg] * (1 if bar != 2 else 0.89), st + h * beat / 2, beat * 0.45, 0.06, "pluck")
    music *= 0.5

    sfx = np.zeros(n)
    voice = np.zeros(n)

    def add(sig, at, amp=1.0):
        i0 = int(at * SR)
        m = min(len(sig), n - i0)
        if m > 0:
            sfx[i0:i0 + m] += amp * sig[:m]

    def pop():
        x = np.arange(int(0.09 * SR)) / SR
        f = 500 + 2200 * x / 0.09
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 35)

    def whoosh():
        m = int(0.35 * SR)
        x = np.arange(m) / SR
        nz = rng.standard_normal(m)
        k = np.ones(40) / 40
        nz = np.convolve(nz, k, mode="same") * 6
        return nz * np.sin(np.pi * x / 0.35) ** 2

    def ding(f=1320):
        x = np.arange(int(0.6 * SR)) / SR
        return (np.sin(2 * np.pi * f * x) + 0.5 * np.sin(2 * np.pi * f * 2.01 * x)) * np.exp(-x * 7)

    def boing():
        x = np.arange(int(0.4 * SR)) / SR
        f = 180 + 120 * np.sin(2 * np.pi * 9 * x) * np.exp(-x * 4)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 6)

    def blip_talk(dur):
        # "voz" de stickman: sílabas tipo blip para dar ritmo al karaoke
        m = int(dur * SR)
        out = np.zeros(m)
        r = np.random.default_rng(int(dur * 1000))
        tcur = 0.0
        while tcur < dur - 0.08:
            f = r.uniform(380, 620)
            L = int(0.055 * SR)
            x = np.arange(L) / SR
            s = np.sign(np.sin(2 * np.pi * f * x)) * 0.5 + np.sin(2 * np.pi * f * x)
            s *= np.sin(np.pi * x / 0.055)
            i0 = int(tcur * SR)
            out[i0:i0 + L] += s[: max(0, min(L, m - i0))]
            tcur += r.uniform(0.11, 0.16)
        return out

    def rimshot(at):
        for j, d in enumerate((0.0, 0.13)):
            x = np.arange(int(0.12 * SR)) / SR
            add(np.sin(2 * np.pi * (180 - 60 * x / 0.12) * x) * np.exp(-x * 25), at + d, 0.5)
            add(rng.standard_normal(len(x)) * np.exp(-x * 40), at + d, 0.15)
        m = int(0.9 * SR)
        x = np.arange(m) / SR
        nz = rng.standard_normal(m)
        nz = np.diff(np.concatenate([[0], nz]))
        add(nz * np.exp(-x * 4) * (0.6 + 0.4 * np.sin(2 * np.pi * 6000 * x)), at + 0.3, 0.22)

    def aplausos(at, dur=2.0):
        m = int(dur * SR)
        out = np.zeros(m)
        r = np.random.default_rng(5)
        for _ in range(int(dur * 60)):
            i0 = r.integers(0, m - 3000)
            L = 2400
            out[i0:i0 + L] += r.standard_normal(L) * np.exp(-np.arange(L) / SR * 120) * r.uniform(0.3, 1)
        out *= np.minimum(1, np.linspace(3, 0, m))
        add(np.diff(np.concatenate([[0], out])), at, 0.5)

    # intro sting
    for i, f in enumerate((523.3, 659.3, 784.0, 1046.5)):
        add(ding(f), 0.05 + i * 0.09, 0.22)
    add(whoosh(), INTRO - 0.2, 0.25)
    for (a, b, sc) in timeline:
        add(pop(), a, 0.35)
        if "_audio" in sc:
            vo = sc["_audio"] / (np.max(np.abs(sc["_audio"])) + 1e-9)
            i0 = int((a + VOZ_OFFSET) * SR)
            m = min(len(vo), n - i0)
            voice[i0:i0 + m] += vo[:m]
        else:
            add(blip_talk((b - a) * 0.8), a + 0.1, 0.035)
        if "tarjeta" in sc:
            add(whoosh(), a + sc["tarjeta"].get("delay", 0.5), 0.3)
            add(ding(1568), a + sc["tarjeta"].get("delay", 0.5) + 0.15, 0.12)
        for snd in sc.get("sonido", []):
            if snd == "rimshot":
                add_t = a + VOZ_OFFSET + sc.get("habla", 1.5) + 0.02
                rimshot(add_t)
            if snd == "aplausos":
                aplausos(a + 0.3, 1.8)
        for f in sc.get("fx", []):
            if f.startswith("plop"):
                add(boing(), a + 0.05, 0.4)
            if f.startswith("ja"):
                for j in range(3):
                    add(pop(), a + 0.15 * j, 0.2)
            if f.startswith("money"):
                for j in range(4):
                    add(ding(2093), a + 0.3 + j * 0.25, 0.08)
    o = total - OUTRO
    add(whoosh(), o, 0.3)
    aplausos(o + 0.2, 2.5)
    for i, tp in enumerate((1.1, 2.0, 2.9)):
        add(pop(), o + tp, 0.4)
        add(ding(1318 + i * 220), o + tp + 0.03, 0.18)
    # ducking: baja la música cuando alguien habla
    env = np.convolve(np.abs(voice), np.ones(4800) / 4800, mode="same")
    duck = 1 - 0.55 * np.clip(env * 12, 0, 1)
    mix = music * 0.55 * duck + sfx * 0.6 + voice * 0.95
    fade = int(0.6 * SR)
    end = int(total * SR)
    mix = mix[:end]
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix = mix / (np.max(np.abs(mix)) + 1e-9) * 0.85
    stereo = np.stack([mix, mix], axis=1)
    pcm = (stereo * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ---------------------------------------------------------------- voces
def tts_line(who, texto, path, length_scale, tono=None):
    name = VOCES[who]
    d = os.path.join(VOICE_DIR, "vits-piper-" + name)
    subprocess.run(["python3", "-m", "piper", "-m", f"{d}/{name}.onnx", "-c", f"{d}/{name}.onnx.json",
                    "--length-scale", str(length_scale), "--noise-scale", "0.8", "--noise-w-scale", "0.95", "-f", path],
                   input=texto.encode("utf-8"), check=True, capture_output=True)
    semis = TONO.get(who, 0)
    if semis == "mezcla":
        # voz gruesa y delgada a la vez: capa aguda (+7 st) sobre la voz grave original
        with wave.open(path) as w:
            sr0 = w.getframerate()
        f = 2 ** (7 / 12)
        mezcla = path.replace(".wav", "_mezcla.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-filter_complex",
                        f"[0]asplit[a][b];[a]asetrate={int(sr0 * f)},aresample={sr0},atempo={1 / f:.5f},volume=0.85[hi];"
                        f"[b]volume=0.5,lowpass=f=1800[lo];[hi][lo]amix=inputs=2:normalize=0,"
                        "equalizer=f=2500:t=q:w=1:g=2", mezcla], check=True)
        path = mezcla
    elif semis:
        with wave.open(path) as w:
            sr0 = w.getframerate()
        f = 2 ** (semis / 12)
        shifted = path.replace(".wav", "_tono.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-af",
                        f"asetrate={int(sr0 * f)},aresample={sr0},atempo={1 / f:.5f},"
                        "equalizer=f=3000:t=q:w=1:g=3,volume=1.1", shifted], check=True)
        path = shifted
    with wave.open(path) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32767
        sr = w.getframerate()
    # recorta silencios de bordes
    idx = np.where(np.abs(x) > 0.02)[0]
    if len(idx):
        x = x[max(0, idx[0] - int(0.02 * sr)): idx[-1] + int(0.05 * sr)]
    if sr != SR:
        tt = np.arange(int(len(x) * SR / sr)) / SR
        x = np.interp(tt, np.arange(len(x)) / sr, x)
    return x


def build_voices(ep, tmp):
    escala = {w: 1.0 for w in VOCES}
    escala.update(ep.get("velocidad_voz", {}))
    target = ep.get("duracion_max", 38.8)
    factor = 1.0
    for _ in range(4):
        total = INTRO + OUTRO
        for i, sc in enumerate(ep["escenas"]):
            texto = sc.get("voz", sc["texto"].replace("*", ""))
            x = tts_line(sc["quien"], texto, os.path.join(tmp, f"v{i}.wav"), escala[sc["quien"]] * factor)
            sc["_audio"] = x
            sc["habla"] = len(x) / SR
            sc["dur"] = sc["habla"] + VOZ_OFFSET + sc.get("pausa", 0.3)
            total += sc["dur"]
        if total <= target:
            break
        factor *= max(0.8, (target - INTRO - OUTRO - 0.4 * len(ep["escenas"])) /
                      (total - INTRO - OUTRO - 0.4 * len(ep["escenas"])))
    print(f"Voces listas (velocidad x{1 / factor:.2f})")


def camera(timeline, t):
    for (a, b, sc) in timeline:
        if a <= t < b:
            local = t - a
            z, dx, dy = 1.0, 0.0, 0.0
            zx = 540 + (CAST[sc["quien"]]["x"] - 540) * 0.5
            if sc.get("zoom"):
                k = ease_out(local / 0.25) if local < b - a - 0.25 else ease_out((b - a - local) / 0.25)
                z = 1.0 + 0.1 * k
            if sc.get("temblor") and local < 0.6:
                amp = 14 * (1 - local / 0.6)
                dx, dy = amp * math.sin(local * 90), amp * math.cos(local * 77)
            return z, dx, dy, zx
    return 1.0, 0.0, 0.0, 540


# ---------------------------------------------------------------- main
FRENTE = None


def configurar(ep):
    """Aplica canal, elenco y posiciones del guion (lo usan render y miniaturas)."""
    global LOCUTOR, ELENCO, PROGRAMA, CANAL, SCREEN, FRENTE
    CANAL = CANALES[ep.get("canal", "noticias")]
    LOCUTOR = ep.get("locutor", "paco")
    ELENCO = ep.get("elenco", ["chato", "paco", "lucha"])
    PROGRAMA = ep.get("programa", ["NOTICIAS", "STICKMAN"])
    xs = (300, 780) if len(ELENCO) == 2 else (190, 540, 890)
    for w, x in zip(ELENCO, xs):
        CAST[w]["x"] = x
    if CANAL["fondo"] != "noticias":
        SCREEN = (40, 440, 1000, 450)
    if CANAL["fondo"] == "cocina":
        FRENTE = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        fc = cairo.Context(FRENTE)
        bg = build_cocina()
        fc.set_source_surface(bg, 0, 0)
        fc.rectangle(0, 1445, W, H - 1445)
        fc.fill()


def main():
    gpath = sys.argv[1]
    ep = json.load(open(gpath, encoding="utf-8"))
    outdir = os.path.dirname(os.path.abspath(gpath))
    configurar(ep)
    if "--sin-voz" not in sys.argv:
        build_voices(ep, "/tmp")
    timeline, total = build_timeline(ep)
    bg = build_background()
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)

    if "--frame" in sys.argv:
        ts = [float(x) for x in sys.argv[sys.argv.index("--frame") + 1].split(",")]
        for tt in ts:
            render_frame(ctx, bg, ep, timeline, total, tt)
            p = os.path.join("/tmp", f"frame_{tt:05.2f}.png")
            surf.write_to_png(p)
            print(p)
        return

    print(f"Duración total: {total:.2f} s")
    wav = os.path.join("/tmp", ep["id"] + ".wav")
    synth_audio(ep, timeline, total, wav)
    out = os.path.join(outdir, ep["archivo"])
    cmd = ["ffmpeg", "-v", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav,
           "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nframes = int(round(total * FPS))
    out_s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    octx = cairo.Context(out_s)
    for i in range(nframes):
        tt = i / FPS
        render_frame(ctx, bg, ep, timeline, total, tt)
        surf.flush()
        z, dx, dy, zx = camera(timeline, tt)
        if z == 1.0 and dx == 0 and dy == 0:
            p.stdin.write(bytes(surf.get_data()))
            continue
        octx.save()
        octx.translate(zx + dx, 900 + dy)
        octx.scale(z, z)
        octx.translate(-zx, -900)
        octx.set_source_surface(surf, 0, 0)
        octx.paint()
        octx.restore()
        out_s.flush()
        p.stdin.write(bytes(out_s.get_data()))
    p.stdin.close()
    p.wait()
    # miniatura = frame del titular
    render_frame(ctx, bg, ep, timeline, total, 1.4)
    surf.write_to_png(os.path.join(outdir, "miniatura.png"))
    print("Listo:", out)


if __name__ == "__main__":
    main()
