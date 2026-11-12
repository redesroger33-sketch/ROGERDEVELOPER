#!/usr/bin/env python3
"""ESQUELETOS DEL MISTERIO — motor de shorts de suspenso (1080x1920, 30 fps).

Esqueletos con cabello negro, ojos tipo Pixar, manos articuladas y corazón que late,
escenarios de ciudades del mundo, ganchos de texto cada ~4 s, subtítulos palabra por
palabra, música de tensión, latidos, golpes y cierre "CONTINUARÁ".

Uso: python3 esqueletos.py ../capitulos/<carpeta>/guion.json [--frame 3,10]
"""
import colorsys
import json
import math
import os
import random
import subprocess
import sys
import wave

import cairo
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../noticias-stickman/motor"))
import render as R  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 48000
hx = R.hx
INK = hx("1A1512")
BONE = hx("F3ECDD")
BONE_SH = hx("D9CDB5")
RED = hx("E3122C")
YEL = hx("FFD84A")
WHITE = hx("FFFFFF")
GROUND_Y = 1560

R.VOCES_NAT["narrador"] = ([("em_alex", 1.0)], 1.0)
R.VOCES_NAT["ivan"] = ([("em_santa", 1.0)], 1.03)
R.VOCES_NAT["ana"] = ([("ef_dora", 1.0)], 1.03)
R.VOCES_NAT["leo"] = ([("em_santa", 0.6), ("em_alex", 0.4)], 1.05)
R.VOCES_NAT["sofi"] = ([("ef_dora", 0.7), ("if_sara", 0.3)], 1.05)
NOMBRES = {"narrador": "NARRADOR", "ivan": "IVÁN", "ana": "ANA", "leo": "LEO", "sofi": "SOFÍA"}
COLOR_NOMBRE = {"narrador": hx("9AA4B5"), "ivan": hx("4FA3FF"), "ana": hx("FF5C9A"), "leo": hx("4FA3FF"), "sofi": hx("FF5C9A")}


def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def ease(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def back(t):
    return R.ease_out_back(t)


# ------------------------------------------------------------------ estilo NEÓN (calavera Pixar)
NEON = {"h0": 0.55, "t": 0.0, "seed": 1}
HAIR = hx("07060C")
HAIR_MID = hx("15142A")
HAIR_HI = hx("4A5C9E")


def ncol(x, y, a=1.0, sat=0.70):
    h = (NEON["h0"] + 0.00045 * x - 0.00042 * y) % 1.0
    r, g, b = colorsys.hsv_to_rgb(h, sat, 1.0)
    return (r, g, b, a)


def ngrad(x1, y1, x2, y2, a, sat=0.70):
    g = cairo.LinearGradient(x1, y1, x2 + 0.01, y2 + 0.01)
    g.add_color_stop_rgba(0, *ncol(x1, y1, a, sat))
    g.add_color_stop_rgba(1, *ncol(x2, y2, a, sat))
    return g


def _seg(c, x1, y1, x2, y2, w, src):
    c.set_source(src) if isinstance(src, cairo.Pattern) else c.set_source_rgba(*src)
    c.set_line_width(w)
    c.move_to(x1, y1)
    c.line_to(x2, y2)
    c.stroke()


def sparkle(c, x, y, r, a=1.0, col=(1, 1, 1)):
    if a <= 0.02 or r <= 0.5:
        return
    c.set_source_rgba(*col, a)
    c.move_to(x, y - r)
    for (px, py) in ((x + r * 0.18, y - r * 0.18), (x + r, y), (x + r * 0.18, y + r * 0.18), (x, y + r),
                     (x - r * 0.18, y + r * 0.18), (x - r, y), (x - r * 0.18, y - r * 0.18)):
        c.line_to(px, py)
    c.close_path()
    c.fill()
    g = cairo.RadialGradient(x, y, 0, x, y, r * 0.9)
    g.add_color_stop_rgba(0, *col, a * 0.6)
    g.add_color_stop_rgba(1, *col, 0)
    c.set_source(g)
    c.arc(x, y, r * 0.9, 0, 2 * math.pi)
    c.fill()


def bone(c, x1, y1, x2, y2, w):
    """Hueso translúcido de neón arcoíris con epífisis dobles, núcleo de cristal y destellos."""
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    for k, a in ((3.6, 0.06), (2.4, 0.12), (1.6, 0.24)):
        _seg(c, x1, y1, x2, y2, w * k, ngrad(x1, y1, x2, y2, a))
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    for (px, py, sg) in ((x1, y1, 1), (x2, y2, -1)):
        for s in (-1, 1):
            cx_, cy_ = px + nx * s * w * 0.36 + ux * sg * w * 0.1, py + ny * s * w * 0.36 + uy * sg * w * 0.1
            c.arc(cx_, cy_, w * 0.56, 0, 2 * math.pi)
            c.set_source_rgba(*ncol(px, py, 0.92))
            c.fill()
    _seg(c, x1, y1, x2, y2, w, ngrad(x1, y1, x2, y2, 0.92))
    _seg(c, x1 + ux * w * 0.3, y1 + uy * w * 0.3, x2 - ux * w * 0.3, y2 - uy * w * 0.3, w * 0.42, (1, 1, 1, 0.42))
    o = w * 0.22
    _seg(c, x1 + dx * 0.18 + nx * o, y1 + dy * 0.18 + ny * o, x1 + dx * 0.72 + nx * o, y1 + dy * 0.72 + ny * o,
         max(1.5, w * 0.12), (1, 1, 1, 0.85))
    # destellos que titilan sobre el hueso
    rnd = random.Random(int(abs(x1) * 7 + abs(y1) * 13 + abs(x2) * 3) + NEON["seed"])
    for _ in range(2):
        f = rnd.random()
        ph = rnd.random() * 6.28
        tw = 0.5 + 0.5 * math.sin(NEON["t"] * 3.2 + ph)
        sparkle(c, x1 + dx * f + nx * rnd.uniform(-w, w), y1 + dy * f + ny * rnd.uniform(-w, w),
                w * 0.55 * tw + 1, 0.9 * tw)


SKIN_L, SKIN_D, SKIN_LINE = hx("F8C9A2"), hx("E0956A"), hx("A65E3C")


def _finger(c, x, y, a, ln, w, curl, outline):
    pts = [(x, y)]
    cur = a
    for frac in (0.55, 0.45):
        x, y = x + math.sin(cur) * ln * frac, y + math.cos(cur) * ln * frac
        pts.append((x, y))
        cur += curl
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    if outline:
        c.set_source_rgba(*SKIN_LINE)
        c.set_line_width(w + 4)
    else:
        g = cairo.LinearGradient(pts[0][0] - w, 0, pts[0][0] + w, 0)
        g.add_color_stop_rgba(0, *SKIN_D)
        g.add_color_stop_rgba(0.45, *SKIN_L)
        g.add_color_stop_rgba(1, *SKIN_D)
        c.set_source(g)
        c.set_line_width(w)
    c.stroke()
    if not outline:
        tx, ty = pts[-1]
        c.save()
        c.translate(tx - math.sin(cur - curl) * w * 0.25, ty - math.cos(cur - curl) * w * 0.25)
        c.rotate(-(cur - curl))
        c.scale(1, 1.3)
        c.arc(0, 0, w * 0.3, 0, 2 * math.pi)
        c.restore()
        c.set_source_rgba(1, 0.9, 0.85, 0.85)
        c.fill()
        # pliegue del nudillo
        mx, my = pts[1]
        c.set_source_rgba(*SKIN_LINE[:3], 0.45)
        c.set_line_width(1.6)
        c.move_to(mx - w * 0.3 * math.cos(a), my + w * 0.3 * math.sin(a))
        c.line_to(mx + w * 0.3 * math.cos(a), my - w * 0.3 * math.sin(a))
        c.stroke()


def hand(c, x, y, ang, side, curl=0.0):
    """Mano humana real (piel), con palma, cuatro dedos con uñas y pulgar."""
    c.save()
    c.translate(x, y)
    c.rotate(ang)
    c.scale(side * 1.15, 1.15)
    fingers = [(-15, 34, 10.5), (-5, 41, 11.5), (5, 39, 11.5), (15, 31, 10)]
    for outline in (True, False):
        _finger(c, -21, 22, -0.95, 30, 12, curl * 0.8 + 0.25, outline)
        if outline:
            R.rrect(c, -25, 4, 50, 50, 18)
            c.set_source_rgba(*SKIN_LINE)
            c.fill()
        for i, (fx, ln, fw) in enumerate(fingers):
            _finger(c, fx, 44, (i - 1.5) * 0.11, ln, fw, curl, outline)
        if not outline:
            R.rrect(c, -23, 6, 46, 46, 16)
            g = cairo.LinearGradient(-23, 0, 23, 0)
            g.add_color_stop_rgba(0, *SKIN_D)
            g.add_color_stop_rgba(0.45, *SKIN_L)
            g.add_color_stop_rgba(1, *SKIN_D)
            c.set_source(g)
            c.fill()
            c.set_source_rgba(*SKIN_LINE[:3], 0.4)
            c.set_line_width(1.8)
            c.move_to(-14, 24)
            c.curve_to(-4, 34, 6, 30, 14, 36)
            c.stroke()
            c.move_to(-10, 38)
            c.curve_to(0, 42, 8, 40, 16, 44)
            c.stroke()
    c.restore()


def heart(c, x, y, s, beat):
    """Corazón anatómico: ventrículos, aurícula, aorta con ramas, tronco pulmonar y coronarias."""
    k = s * (1 + 0.1 * beat)
    glow = cairo.RadialGradient(x, y, 2, x, y, 95 * k)
    glow.add_color_stop_rgba(0, 1, 0.25, 0.25, 0.55 * (0.45 + beat))
    glow.add_color_stop_rgba(1, 1, 0.2, 0.3, 0)
    c.set_source(glow)
    c.arc(x, y, 95 * k, 0, 2 * math.pi)
    c.fill()
    c.save()
    c.translate(x, y)
    c.scale(k, k)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    # vena cava
    for col, lw in ((hx("5A0C22"), 17), (hx("9A3C6E"), 13)):
        _seg(c, 26, -20, 28, -62, lw, col)
    # aorta y ramas
    for col, lw in ((hx("6A0A18"), 20), (hx("E0453E"), 15)):
        c.set_source_rgba(*col)
        c.set_line_width(lw)
        c.move_to(-2, -20)
        c.curve_to(-4, -66, -40, -70, -44, -38)
        c.stroke()
        for bx in (-10, -22, -33):
            _seg(c, bx, -56, bx + 2, -80, lw * 0.42, col)
    # tronco pulmonar
    for col, lw in ((hx("6A0A18"), 16), (hx("C8323A"), 11)):
        c.set_source_rgba(*col)
        c.set_line_width(lw)
        c.move_to(-12, -14)
        c.curve_to(-26, -34, -40, -28, -52, -20)
        c.stroke()
    # aurícula derecha
    c.arc(30, -14, 15, 0, 2 * math.pi)
    c.set_source_rgba(*hx("D23A3A"))
    c.fill_preserve()
    c.set_source_rgba(*hx("6A0A18"))
    c.set_line_width(2.5)
    c.stroke()
    # ventrículos
    c.move_to(0, -28)
    c.curve_to(30, -34, 46, -6, 38, 16)
    c.curve_to(30, 40, 8, 52, -8, 60)
    c.curve_to(-28, 44, -46, 20, -42, -4)
    c.curve_to(-38, -24, -18, -30, 0, -28)
    c.close_path()
    g = cairo.LinearGradient(-30, -30, 30, 50)
    g.add_color_stop_rgba(0, *hx("FF7A66"))
    g.add_color_stop_rgba(0.5, *hx("D8283A"))
    g.add_color_stop_rgba(1, *hx("7E0A1C"))
    c.set_source(g)
    c.fill_preserve()
    c.set_source_rgba(*hx("5E0A16"))
    c.set_line_width(2.5)
    c.stroke()
    # coronarias y grasa
    c.set_source_rgba(*hx("7A0818"))
    c.set_line_width(3)
    c.move_to(-4, -24)
    c.curve_to(2, 0, -4, 30, -8, 54)
    c.stroke()
    for (a, b, cx_, cy_) in ((-2, -4, -24, 10), (0, 16, 22, 26), (-4, 30, -20, 38)):
        c.move_to(a, b)
        c.curve_to((a + cx_) / 2, b - 4, cx_, cy_ - 6, cx_, cy_)
        c.stroke()
    c.set_source_rgba(1, 0.8, 0.45, 0.45)
    c.set_line_width(2)
    c.move_to(4, -22)
    c.curve_to(18, -6, 20, 14, 12, 34)
    c.stroke()
    c.set_source_rgba(1, 1, 1, 0.55)
    c.save()
    c.translate(-20, -8)
    c.rotate(-0.5)
    c.scale(1, 0.55)
    c.arc(0, 0, 10, 0, 2 * math.pi)
    c.restore()
    c.fill()
    c.arc(18, 4, 3.5, 0, 2 * math.pi)
    c.fill()
    c.restore()


def pixar_eye(c, x, y, r, iris, look, blink, scared, female):
    rr = r * (1.08 if scared else 1.0)
    if blink:
        c.set_source_rgba(*hx("B55AD6"))
        c.arc(x, y, rr, 0, 2 * math.pi)
        c.fill()
        c.set_source_rgba(*hx("1A0F22"))
        c.set_line_width(5)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        c.arc(x, y + 2, rr * 0.8, math.radians(15), math.radians(165))
        c.stroke()
        return
    c.arc(x, y, rr, 0, 2 * math.pi)
    g = cairo.RadialGradient(x - rr * 0.2, y - rr * 0.3, rr * 0.2, x, y, rr)
    g.add_color_stop_rgba(0, 1, 1, 1, 1)
    g.add_color_stop_rgba(1, *hx("D9D2E6"))
    c.set_source(g)
    c.fill_preserve()
    c.set_source_rgba(*hx("2A1430"))
    c.set_line_width(3)
    c.stroke()
    ix, iy = x + look[0] * r * 0.22, y + look[1] * r * 0.18 + r * 0.04
    ir = rr * (0.55 if scared else 0.72)
    g = cairo.RadialGradient(ix, iy + ir * 0.3, ir * 0.1, ix, iy, ir)
    g.add_color_stop_rgba(0, *[min(1, v * 1.8 + 0.08) for v in iris[:3]], 1)
    g.add_color_stop_rgba(0.6, *iris[:3], 1)
    g.add_color_stop_rgba(1, *[v * 0.25 for v in iris[:3]], 1)
    c.set_source(g)
    c.arc(ix, iy, ir, 0, 2 * math.pi)
    c.fill()
    c.set_source_rgba(0.02, 0.02, 0.04, 1)
    c.arc(ix, iy, ir * (0.38 if scared else 0.55), 0, 2 * math.pi)
    c.fill()
    # sombra del párpado superior
    c.save()
    c.arc(x, y, rr - 1.5, 0, 2 * math.pi)
    c.clip()
    sg = cairo.LinearGradient(0, y - rr, 0, y - rr * 0.2)
    sg.add_color_stop_rgba(0, 0.25, 0.1, 0.35, 0.45)
    sg.add_color_stop_rgba(1, 0.25, 0.1, 0.35, 0)
    c.set_source(sg)
    c.paint()
    c.restore()
    c.set_source_rgba(1, 1, 1, 0.97)
    c.arc(ix - ir * 0.32, iy - ir * 0.36, ir * 0.3, 0, 2 * math.pi)
    c.fill()
    c.arc(ix + ir * 0.34, iy + ir * 0.3, ir * 0.12, 0, 2 * math.pi)
    c.fill()
    c.arc(ix + ir * 0.1, iy - ir * 0.5, ir * 0.08, 0, 2 * math.pi)
    c.fill()
    side = 1 if x > 0 else -1
    c.set_source_rgba(*hx("140A18"))
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    if female:
        # delineado con "colita" y pestañas largas
        c.set_line_width(5)
        c.arc(x, y, rr + 1, math.radians(195), math.radians(345))
        c.stroke()
        c.move_to(x + side * rr * 0.97, y - rr * 0.25)
        c.line_to(x + side * (rr + 16), y - rr * 0.55)
        c.stroke()
        for k in range(5):
            a = math.radians(-78 + k * 20) * side
            bx, by = x + math.sin(a) * rr, y - math.cos(a) * rr
            c.set_line_width(4.5 - k * 0.3)
            c.move_to(bx, by)
            c.curve_to(bx + math.sin(a) * 12, by - 10, bx + math.sin(a) * 20 + side * 6, by - 18,
                       bx + math.sin(a) * 24 + side * 12, by - 18)
            c.stroke()
    else:
        c.set_line_width(4)
        c.arc(x, y, rr + 1, math.radians(205), math.radians(335))
        c.stroke()


def _lock(c, bx, by, tx, ty, w, bend, col_a, col_b):
    dx, dy = tx - bx, ty - by
    L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L, dx / L
    c.move_to(bx + nx * w, by + ny * w)
    c.curve_to(bx + dx * 0.45 + nx * (w * 0.9 + bend), by + dy * 0.45 + ny * (w * 0.9 + bend),
               bx + dx * 0.85 + nx * (w * 0.3 + bend * 0.6), by + dy * 0.85 + ny * (w * 0.3 + bend * 0.6), tx, ty)
    c.curve_to(bx + dx * 0.8 - nx * (w * 0.2 - bend * 0.6), by + dy * 0.8 - ny * (w * 0.2 - bend * 0.6),
               bx + dx * 0.45 - nx * (w * 0.9 - bend), by + dy * 0.45 - ny * (w * 0.9 - bend),
               bx - nx * w, by - ny * w)
    c.close_path()
    g = cairo.LinearGradient(bx, by, tx, ty)
    g.add_color_stop_rgba(0, *col_a)
    g.add_color_stop_rgba(1, *col_b)
    c.set_source(g)
    c.fill()


def _hair_hi(c, x1, y1, cx_, cy_, x2, y2, a=0.55, w=3.0):
    c.set_source_rgba(*HAIR_HI[:3], a)
    c.set_line_width(w)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.move_to(x1, y1)
    c.curve_to(cx_, cy_, cx_, cy_, x2, y2)
    c.stroke()


def _cloud(c, cx, cy, R_, r, a0, a1, step, wob=0.0, t=0.0):
    a = a0
    while a <= a1:
        ar = math.radians(a)
        rr = r * (1 + 0.08 * math.sin(a * 0.37))
        c.arc(cx + math.cos(ar) * R_, cy + math.sin(ar) * R_ + wob * math.sin(t * 1.5 + a), rr, 0, 2 * math.pi)
        c.close_path()
        a += step


def _fill_hair(c, y0=-180, y1=60):
    g = cairo.LinearGradient(0, y0, 0, y1)
    g.add_color_stop_rgba(0, *HAIR_MID)
    g.add_color_stop_rgba(1, *HAIR)
    c.set_source(g)
    c.fill()


def hair_back(c, female, t, phase):
    """Volumen esponjoso de cabello detrás del cráneo, con puntas que se abren a los lados."""
    sway = 4 * math.sin(t * 1.6 + phase)
    c.new_path()
    _cloud(c, 0, -40, 112, 56, -205, 25, 15, 1.5, t)
    _fill_hair(c)
    flicks = ([(-100, -10, -178 + sway, 34, 30, -26), (100, -10, 178 + sway, 30, 30, 26),
               (-110, -70, -186, -66, 28, -18), (110, -70, 186, -70, 28, 18),
               (-70, -130, -140, -170, 26, -16), (70, -130, 140, -172, 26, 16)] if not female else
              [(-100, -20, -172 + sway, 60, 30, -22), (100, -20, 172 + sway, 60, 30, 22)])
    for (bx, by, tx, ty, w, bd) in flicks:
        _lock(c, bx, by, tx, ty, w, bd, HAIR, HAIR_MID)
    for a in (-160, -130, -100, -70, -40, -10):
        ar = math.radians(a)
        _hair_hi(c, math.cos(ar) * 80, math.sin(ar) * 80 - 40, math.cos(ar + 0.25) * 135, math.sin(ar + 0.25) * 135 - 40,
                 math.cos(ar + 0.15) * 158, math.sin(ar + 0.15) * 158 - 40, 0.35, 3.5)


def _swoop(c, top_pts, bottom_pts):
    c.move_to(*top_pts[0])
    for i in range(1, len(top_pts), 3):
        c.curve_to(*top_pts[i], *top_pts[i + 1], *top_pts[i + 2])
    prev = top_pts[-1]
    for (x, y) in bottom_pts:
        mx, my = (prev[0] + x) / 2, (prev[1] + y) / 2
        c.curve_to(prev[0] + (mx - prev[0]) * 0.3, my + 16, x + (mx - x) * 0.3, my + 16, x, y)
        prev = (x, y)
    c.close_path()


def hair_front(c, female, t, phase):
    sway = 3 * math.sin(t * 1.9 + phase)
    if female:
        # flequillo de lado con ondas + mechones largos que enmarcan la cara
        for (bx, by, tx, ty, w, b) in ((-118, -60, -138 + sway, 130, 24, -18), (122, -60, 140 + sway, 140, 22, 18)):
            _lock(c, bx, by, tx, ty, w, b, HAIR, HAIR_MID)
        _swoop(c, [(-126, -10), (-140, -150), (40, -190), (128, -70)],
               [(100, -96), (64, -100), (30, -112), (-10, -100), (-50, -96), (-86, -70), (-112, -36), (-126, -10)])
        _fill_hair(c, -190, -10)
        _hair_hi(c, -90, -120, -10, -160, 90, -110, 0.5, 4)
        _hair_hi(c, -116, -60, -128, 10, -126, 100, 0.35)
        _hair_hi(c, 116, -50, 128, 20, 128, 110, 0.35)
        # corona de flores (calavera catrina)
        for (fx, fy, r, col) in ((-92, -118, 20, hx("FF3D6E")), (-52, -142, 16, hx("FFB13B")),
                                 (-124, -80, 15, hx("B65CFF")), (-14, -152, 11, hx("4FD1FF"))):
            for k in range(2):
                a = math.radians(200 + k * 70)
                _lock(c, fx, fy, fx + math.cos(a) * r * 1.8, fy + math.sin(a) * r * 1.8, 6, 3,
                      hx("2FA35A"), hx("7BE07F"))
            for k in range(6):
                a = k * math.pi / 3 + t * 0.2
                c.arc(fx + math.cos(a) * r * 0.55, fy + math.sin(a) * r * 0.55, r * 0.55, 0, 2 * math.pi)
                c.set_source_rgba(*col[:3], 0.95)
                c.fill()
            c.arc(fx, fy, r * 0.42, 0, 2 * math.pi)
            c.set_source_rgba(*[v * 0.7 for v in col[:3]], 1)
            c.fill()
            c.set_source_rgba(1, 1, 1, 0.5)
            c.set_line_width(2)
            c.arc(fx, fy, r * 0.25, 0, 4)
            c.stroke()
    else:
        # tupé voluminoso con ondas que caen sobre la frente
        _swoop(c, [(-128, -30), (-150, -170), (60, -210), (130, -40)],
               [(108, -80), (76, -92), (44, -110), (10, -96), (-24, -112), (-58, -94), (-92, -84), (-128, -30)])
        _fill_hair(c, -210, -30)
        _lock(c, -40, -150, 40 + sway, -86, 24, 18, HAIR_MID, HAIR)
        _hair_hi(c, -100, -110, -40, -190, 80, -120, 0.55, 4.5)
        _hair_hi(c, -60, -130, 0, -170, 90, -96, 0.4, 3)
        _hair_hi(c, -116, -60, -128, -130, -60, -160, 0.35, 3)


def sugar_decor(c, female, eyes_x, eye_y, er):
    """Pintura de calavera catrina: aros de colores, diamante, gotas y puntos."""
    for sx in (-1, 1):
        ex = sx * eyes_x
        g = cairo.RadialGradient(ex, eye_y, er * 0.9, ex, eye_y, er * 1.55)
        c1, c2 = (hx("A64BFF"), hx("FF5FA2")) if female else (hx("2B5BFF"), hx("23D3FF"))
        g.add_color_stop_rgba(0, *c1[:3], 0.95)
        g.add_color_stop_rgba(0.6, *c2[:3], 0.8)
        g.add_color_stop_rgba(1, *c2[:3], 0)
        c.set_source(g)
        c.arc(ex, eye_y, er * 1.55, 0, 2 * math.pi)
        c.fill()
        cols = ((hx("FF3D6E"), hx("FFB13B"), hx("3FD9FF"), hx("7BE07F")) if female else
                (hx("FFB13B"), hx("3FD9FF"), hx("FFFFFF"), hx("7BE07F")))
        for k in range(9):
            a = math.radians(205 + k * 16.5) if sx < 0 else math.radians(335 - k * 16.5)
            c.arc(ex + math.cos(a) * er * 1.6, eye_y + math.sin(a) * er * 1.6, 5.5, 0, 2 * math.pi)
            c.set_source_rgba(*cols[k % 4])
            c.fill()
        # puntos en las mejillas
        for k in range(4):
            c.arc(sx * (72 + k * 7), 52 + k * 9, 4.5 - k * 0.6, 0, 2 * math.pi)
            c.set_source_rgba(*hx("3FD9FF"))
            c.fill()
        # gotitas en la frente
        for k, col in enumerate((hx("FFB13B"), hx("3FD9FF"), hx("FF3D6E"))):
            dx_, dy_ = sx * (26 + k * 18), -80 - k * 6
            c.move_to(dx_, dy_ - 10)
            c.curve_to(dx_ + 7, dy_, dx_ + 6, dy_ + 7, dx_, dy_ + 7)
            c.curve_to(dx_ - 6, dy_ + 7, dx_ - 7, dy_, dx_, dy_ - 10)
            c.set_source_rgba(*col)
            c.fill()
    if not female:
        # estrella en la frente (catrín) en lugar del diamante
        c.move_to(0, -66)
        for k in range(1, 11):
            a = -math.pi / 2 + k * math.pi / 5
            rr = 16 if k % 2 == 0 else 7
            c.line_to(math.cos(a) * rr, -48 + math.sin(a) * rr)
        c.close_path()
        c.set_source_rgba(*hx("23D3FF"))
        c.fill()
        c.arc(0, -48, 4, 0, 2 * math.pi)
        c.set_source_rgba(*hx("FFE15A"))
        c.fill()
        return
    # diamante central
    for (s, col) in ((1.0, hx("FF3D8B")), (0.5, hx("FFE15A"))):
        c.move_to(0, -64 * 1 - 22 * s + 22)
        c.line_to(10 * s, -42)
        c.line_to(0, -42 + 22 * s)
        c.line_to(-10 * s, -42)
        c.close_path()
        c.set_source_rgba(*col)
        c.fill()
    c.arc(0, -82, 5, 0, 2 * math.pi)
    c.set_source_rgba(*hx("A64BFF"))
    c.fill()


def skull(c, st, t):
    female = st.get("female", False)
    talking = st.get("talking", False)
    scared = st.get("scared", False)
    blink = (t + st.get("phase", 0)) % 3.3 < 0.12
    op = (6 + 16 * abs(math.sin(t * 15)) * (0.6 + 0.4 * math.sin(t * 4.7))) if talking else (18 if scared else 0)
    jd = op * 0.55
    hair_back(c, female, t, st.get("phase", 0))

    def shape():
        c.move_to(0, -128)
        c.curve_to(72, -128, 120, -82, 118, -14)
        c.curve_to(117, 28, 100, 52, 74, 64)
        if female:
            c.curve_to(64, 96 + jd, 40, 118 + jd, 0, 120 + jd)
            c.curve_to(-40, 118 + jd, -64, 96 + jd, -74, 64)
        else:
            c.curve_to(78, 104 + jd, 66, 124 + jd, 0, 126 + jd)
            c.curve_to(-66, 124 + jd, -78, 104 + jd, -74, 64)
        c.curve_to(-100, 52, -117, 28, -118, -14)
        c.curve_to(-120, -82, -72, -128, 0, -128)
        c.close_path()
    # resplandor de neón alrededor del cráneo
    for lw, a in ((26, 0.08), (14, 0.18)):
        shape()
        g = cairo.LinearGradient(-120, 0, 120, 0)
        g.add_color_stop_rgba(0, 1, 0.3, 0.75, a)
        g.add_color_stop_rgba(1, 0.25, 0.85, 1, a)
        c.set_source(g)
        c.set_line_width(lw)
        c.stroke()
    shape()
    g = cairo.RadialGradient(-20, -40, 10, 0, -10, 140)
    g.add_color_stop_rgba(0, 1, 1, 1, 1)
    g.add_color_stop_rgba(0.75, *hx("F4EEF6"))
    g.add_color_stop_rgba(1, *hx("D9CDE6"))
    c.set_source(g)
    c.fill_preserve()
    g = cairo.LinearGradient(-120, 0, 120, 0)
    g.add_color_stop_rgba(0, *hx("FF4FC3"))
    g.add_color_stop_rgba(0.5, *hx("C9B8FF"))
    g.add_color_stop_rgba(1, *hx("3FD9FF"))
    c.set_source(g)
    c.set_line_width(5)
    c.stroke()
    # rubor
    for sx in (-1, 1):
        g2 = cairo.RadialGradient(sx * 70, 40, 2, sx * 70, 40, 30)
        a = 0.6 if female else 0.3
        g2.add_color_stop_rgba(0, 1, 0.4, 0.6, a)
        g2.add_color_stop_rgba(1, 1, 0.4, 0.6, 0)
        c.set_source(g2)
        c.arc(sx * 70, 40, 30, 0, 2 * math.pi)
        c.fill()
    er = 40 if female else 38
    sugar_decor(c, female, 48, -6, er)
    # nariz en forma de corazón invertido
    c.move_to(0, 46)
    c.curve_to(-16, 36, -16, 18, -7, 18)
    c.curve_to(-3, 18, 0, 22, 0, 26)
    c.curve_to(0, 22, 3, 18, 7, 18)
    c.curve_to(16, 18, 16, 36, 0, 46)
    c.set_source_rgba(*hx("2A0F22"))
    c.fill()
    # boca: sonrisa amplia con dientes arriba y abajo
    top_y, bot_y = 62, 92 + op * 1.1
    c.move_to(-58, 60)
    c.curve_to(-30, top_y + 22, 30, top_y + 22, 58, 60)
    c.curve_to(40, bot_y + 18, -40, bot_y + 18, -58, 60)
    c.close_path()
    c.set_source_rgba(*hx("3A0D1F"))
    c.fill_preserve()
    c.save()
    c.clip()
    if op > 6:
        c.arc(0, bot_y + 30, 34, 0, 2 * math.pi)
        c.set_source_rgba(*hx("E8577A"))
        c.fill()
    for i in range(8):
        f = (i + 0.5) / 8
        tx = -58 + f * 116
        ty = 60 + 4 * f * (1 - f) * 18
        R.rrect(c, tx - 7, ty - 8, 13.5, 17, 4)
        c.set_source_rgba(1, 1, 1, 1)
        c.fill()
        by_ = 60 + 4 * f * (1 - f) * (bot_y - 48)
        R.rrect(c, tx - 6.5, by_ - 10, 13, 14, 4)
        c.set_source_rgba(*hx("F1ECF4"))
        c.fill()
    c.restore()
    c.set_source_rgba(*hx("2A0F22"))
    c.set_line_width(2.5)
    c.move_to(-58, 60)
    c.curve_to(-30, top_y + 22, 30, top_y + 22, 58, 60)
    c.stroke()
    for sx in (-1, 1):
        c.arc(sx * 64, 58, 3.5, 0, 2 * math.pi)
        c.set_source_rgba(*hx("FF3D6E"))
        c.fill()
    if not female:
        # bigote catrín de puntas rizadas
        c.set_source_rgba(*hx("120E18"))
        for sx in (-1, 1):
            c.move_to(0, 50)
            c.curve_to(sx * 18, 42, sx * 40, 46, sx * 52, 54)
            c.curve_to(sx * 62, 58, sx * 70, 50, sx * 66, 42)
            c.curve_to(sx * 74, 50, sx * 68, 66, sx * 52, 62)
            c.curve_to(sx * 38, 60, sx * 18, 60, 0, 58)
            c.close_path()
            c.fill()
        for k in range(3):
            c.arc(0, 112 + jd + k * 0.1 - k * 9 + 0 * op, 4 - k * 0.8, 0, 2 * math.pi)
            c.set_source_rgba(*hx("23D3FF"))
            c.fill()
    look = st.get("look", (0.25 * math.sin(t * 0.7), 0))
    iris = st.get("iris", hx("4A2A1A"))
    for sx in (-1, 1):
        pixar_eye(c, sx * 48, -6, er, iris, look, blink, scared, female)
    # cejas gruesas (hombre) / finas arqueadas (mujer)
    c.set_source_rgba(*hx("120E18"))
    for sx in (-1, 1):
        lift = -12 if scared else (-3 * abs(math.sin(t * 2.3)) if talking else 0)
        y0 = -64 + lift
        th = 7 if female else 13
        c.move_to(sx * 20, y0 + (8 if scared else 4))
        c.curve_to(sx * 40, y0 - 14, sx * 64, y0 - 14, sx * 82, y0 - 2)
        c.curve_to(sx * 64, y0 - 14 + th, sx * 40, y0 - 14 + th, sx * 20, y0 + (8 if scared else 4) + th * 0.6)
        c.close_path()
        c.fill()
    hair_front(c, female, t, st.get("phase", 0))


def arm_pts(sx, sy, side, a1, a2, L1=150, L2=140):
    r1, r2 = math.radians(a1), math.radians(a1 + a2)
    ex, ey = sx + side * L1 * math.sin(r1), sy + L1 * math.cos(r1)
    hx_, hy_ = ex + side * L2 * math.sin(r2), ey + L2 * math.cos(r2)
    return (ex, ey), (hx_, hy_), r2


POSES = {
    "idle": ((18, 10), (18, 10)),
    "point": ((18, 10), (95, 0)),
    "scared": ((40, 135), (40, 135)),
    "up": ((160, 10), (160, 10)),
    "talk": ((25, 55), (18, 10)),
    "think": ((18, 10), (28, 150)),
    "wave": ((18, 10), (120, 40)),
}


def _neon_path_stroke(c, build, w):
    for k, a in ((3.0, 0.07), (1.9, 0.16)):
        build()
        x1, y1, x2, y2 = c.stroke_extents() if False else (0, 0, 0, 0)
        c.set_source_rgba(*NEON["cur"], a)
        c.set_line_width(w * k)
        c.stroke()
    build()
    c.set_source_rgba(*NEON["cur"], 0.92)
    c.set_line_width(w)
    c.stroke()
    build()
    c.set_source_rgba(1, 1, 1, 0.45)
    c.set_line_width(w * 0.38)
    c.stroke()


def skeleton(c, x, st, t):
    s = st.get("scale", 0.95)
    female = st.get("female", False)
    NEON["h0"] = st.get("tono", 0.86 if female else 0.52)
    NEON["t"] = t
    NEON["seed"] = 1 if female else 2
    shake = 5 * math.sin(t * 60) if st.get("scared") else 0
    bob = 6 * math.sin(t * 2 + st.get("phase", 0))
    c.save()
    c.translate(x + shake, GROUND_Y)
    c.scale(s, s)
    # sombra / reflejo de neón en el piso
    c.save()
    c.scale(1, 0.15)
    g = cairo.RadialGradient(0, 0, 10, 0, 0, 200)
    g.add_color_stop_rgba(0, *ncol(0, 0, 0.45))
    g.add_color_stop_rgba(0.5, 0, 0, 0, 0.35)
    g.add_color_stop_rgba(1, 0, 0, 0, 0)
    c.set_source(g)
    c.arc(0, 0, 200, 0, 2 * math.pi)
    c.fill()
    c.restore()
    hip = -330 + bob * 0.3
    top = -650 + bob
    BW = 0.84 if female else 1.15          # grosor de huesos
    SW = 94 if female else 128             # ancho de hombros
    RW = 0.88 if female else 1.1           # ancho de costillas
    PW = 1.15 if female else 0.88          # ancho de cadera
    if female:
        # melena larga y voluminosa detrás del cuerpo
        sway = 8 * math.sin(t * 1.8 + st.get("phase", 0))
        hy = top - 225
        rnd = random.Random(5)
        for i in range(13):
            f = i / 12
            bx = -120 + f * 240
            tx = bx * 1.25 + sway * (0.5 + f) + rnd.uniform(-10, 10)
            ty = hy + 330 + 50 * math.sin(f * math.pi) + rnd.uniform(-20, 20)
            _lock(c, bx * 0.8, hy - 40, tx, ty, 34, rnd.uniform(-20, 20), HAIR, HAIR_MID)
        for f in (0.15, 0.35, 0.7, 0.88):
            bx = -120 + f * 240
            _hair_hi(c, bx, hy, bx * 1.2 - 10, hy + 160, bx * 1.25 + sway, hy + 320, 0.35)
    # piernas
    for sd in (-1, 1):
        knee = (sd * 55, -170)
        foot = (sd * 70, -10)
        bone(c, sd * 40 * PW, hip + 20, knee[0], knee[1], 18 * BW)
        bone(c, knee[0], knee[1], foot[0], foot[1], 15 * BW)
        bone(c, foot[0], foot[1], foot[0] + sd * 38, foot[1] + 4, 12 * BW)
    # pelvis
    def pelvis():
        c.move_to(-78 * PW, hip - 14)
        c.curve_to(-96 * PW, hip + 40, -30 * PW, hip + 72, 0, hip + 40)
        c.curve_to(30 * PW, hip + 72, 96 * PW, hip + 40, 78 * PW, hip - 14)
        c.curve_to(40 * PW, hip + 8, -40 * PW, hip + 8, -78 * PW, hip - 14)
        c.close_path()
    for lw, a in ((30, 0.08), (16, 0.18)):
        pelvis()
        c.set_source(ngrad(-80, hip, 80, hip, a))
        c.set_line_width(lw)
        c.stroke()
    pelvis()
    c.set_source(ngrad(-80, hip, 80, hip, 0.9))
    c.fill_preserve()
    c.set_source_rgba(1, 1, 1, 0.5)
    c.set_line_width(3)
    c.stroke()
    for sd in (-1, 1):
        c.save()
        c.translate(sd * 36, hip + 22)
        c.scale(1, 0.7)
        c.arc(0, 0, 14, 0, 2 * math.pi)
        c.restore()
        c.set_source_rgba(0.1, 0.05, 0.15, 0.45)
        c.fill()
    # columna
    bone(c, 0, hip - 10, 0, top + 10, 12)
    for i in range(10):
        y = hip - 20 - i * ((hip - 20 - top) / 10)
        R.rrect(c, -15, y - 12, 30, 20, 8)
        c.set_source_rgba(*ncol(0, y, 0.95))
        c.fill_preserve()
        c.set_source_rgba(1, 1, 1, 0.55)
        c.set_line_width(2)
        c.stroke()
    # corazón (detrás de costillas)
    rate = st.get("bpm", 70) / 60.0
    ph = (t * rate) % 1.0
    beat = max(0.0, 1 - abs(ph - 0.08) / 0.08) + 0.6 * max(0.0, 1 - abs(ph - 0.26) / 0.07)
    heart(c, -12, top + 150, 1.25, beat)
    # costillas de neón
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    for i in range(6):
        y = top + 60 + i * 34
        wd = (120 - abs(i - 2) * 8) * RW * ((1 - 0.05 * i) if female else 1)
        for sd in (-1, 1):
            NEON["cur"] = ncol(sd * wd * 0.8, y, 1)[:3]

            def rib(y=y, wd=wd, sd=sd):
                c.move_to(0, y)
                c.curve_to(sd * wd * 0.7, y - 18, sd * wd, y + 6, sd * wd * 0.85, y + 40)
            _neon_path_stroke(c, rib, 8 * BW)
    bone(c, 0, top + 40, 0, top + 230, 13)  # esternón
    sy = top + 20
    for sd in (-1, 1):
        bone(c, 0, sy, sd * SW, sy + 8, 11 * BW)
    # brazos + manos de piel real
    pose = st.get("pose", "idle")
    (l1, l2), (r1, r2) = POSES.get(pose, POSES["idle"])
    wig = 6 * math.sin(t * 5) if st.get("talking") else 3 * math.sin(t * 1.7 + st.get("phase", 0))
    if pose == "wave":
        r2 += 18 * math.sin(t * 7)
    for sd, (a1, a2) in ((-1, (l1 + wig, l2)), (1, (r1 - wig, r2))):
        sxp, syp = sd * SW, sy + 8
        (ex, ey), (hxp, hyp), ang = arm_pts(sxp, syp, sd, a1, a2)
        bone(c, sxp, syp, ex, ey, 16 * BW)
        bone(c, ex, ey, hxp, hyp, 12 * BW)
        bone(c, ex + 7 * sd, ey + 4, hxp + 7 * sd, hyp, 7)
        hand(c, hxp, hyp, -sd * ang, sd, curl=0.55 if pose == "scared" else 0.12)
    # cuello y cráneo
    for i in range(3):
        R.rrect(c, -16, top - 40 - i * 22, 32, 18, 7)
        c.set_source_rgba(*ncol(0, top - 40 - i * 22, 0.95))
        c.fill_preserve()
        c.set_source_rgba(1, 1, 1, 0.5)
        c.set_line_width(2)
        c.stroke()
    if st.get("bufanda"):
        R.rrect(c, -70, top - 50, 140, 36, 16)
        c.set_source_rgba(*st["bufanda"])
        c.fill_preserve()
        c.set_source_rgba(1, 1, 1, 0.35)
        c.set_line_width(3)
        c.stroke()
        R.rrect(c, 30, top - 30, 34, 110, 12)
        c.set_source_rgba(*st["bufanda"])
        c.fill_preserve()
        c.stroke()
        c.set_source_rgba(1, 1, 1, 0.55)
        for yy in (top + 10, top + 40):
            c.rectangle(32, yy, 30, 7)
            c.fill()
        for fx in range(4):
            _seg(c, 36 + fx * 8, top + 80, 36 + fx * 8, top + 96, 4, st["bufanda"])
    c.save()
    c.translate(0, top - 225)
    c.scale(1.22, 1.22)
    c.rotate(0.05 * math.sin(t * 1.3 + st.get("phase", 0)))
    skull(c, st, t)
    c.restore()
    # destellos alrededor del personaje
    rnd = random.Random(NEON["seed"] * 17)
    for _ in range(9):
        px, py = rnd.uniform(-200, 200), rnd.uniform(-1050, -150)
        ph = rnd.random() * 6.28
        tw = max(0.0, math.sin(t * 2.4 + ph))
        sparkle(c, px, py, 10 * tw + 2, 0.85 * tw, ncol(px, py, 1, 0.35)[:3])
    c.restore()


def bokeh(c, t):
    """Fondo mágico: círculos desenfocados de colores y polvo de estrellas."""
    rnd = random.Random(42)
    for _ in range(26):
        x0, y0 = rnd.uniform(0, W), rnd.uniform(150, 1600)
        r = rnd.uniform(14, 58)
        sp = rnd.uniform(4, 14)
        x = (x0 + sp * t) % (W + 120) - 60
        y = y0 - 6 * math.sin(t * 0.5 + x0)
        r_, g_, b_ = colorsys.hsv_to_rgb(rnd.random(), 0.6, 1)
        a = rnd.uniform(0.10, 0.24)
        g = cairo.RadialGradient(x, y, r * 0.2, x, y, r)
        g.add_color_stop_rgba(0, r_, g_, b_, a)
        g.add_color_stop_rgba(0.85, r_, g_, b_, a * 0.8)
        g.add_color_stop_rgba(1, r_, g_, b_, 0)
        c.set_source(g)
        c.arc(x, y, r, 0, 2 * math.pi)
        c.fill()
    for _ in range(70):
        x, y = rnd.uniform(0, W), rnd.uniform(120, 1650)
        tw = 0.5 + 0.5 * math.sin(t * rnd.uniform(1.5, 4) + rnd.random() * 6.28)
        r_, g_, b_ = colorsys.hsv_to_rgb(rnd.random(), 0.3, 1)
        c.arc(x, y, 1.2 + 1.8 * tw, 0, 2 * math.pi)
        c.set_source_rgba(r_, g_, b_, 0.25 + 0.6 * tw)
        c.fill()


# ------------------------------------------------------------------ escenarios
def sky(c, top, bot):
    g = cairo.LinearGradient(0, 0, 0, GROUND_Y)
    g.add_color_stop_rgba(0, *top)
    g.add_color_stop_rgba(1, *bot)
    c.set_source(g)
    c.paint()


def stars(c, t, n=120, seed=3, alpha=1.0):
    rnd = random.Random(seed)
    for i in range(n):
        x, y = rnd.uniform(0, W), rnd.uniform(0, 1100)
        a = alpha * (0.4 + 0.6 * abs(math.sin(t * rnd.uniform(0.5, 2) + i)))
        c.arc(x, y, rnd.uniform(1, 2.6), 0, 2 * math.pi)
        c.set_source_rgba(1, 1, 1, a)
        c.fill()


def ground(c, col):
    c.rectangle(0, GROUND_Y - 30, W, H - GROUND_Y + 30)
    c.set_source_rgba(*col)
    c.fill()


def pines(c, y, n, h, col, seed, t, sway=1.0, fallen=0.0):
    rnd = random.Random(seed)
    for i in range(n):
        x = (i + rnd.uniform(-0.3, 0.3)) * W / (n - 1)
        hh = h * rnd.uniform(0.7, 1.2)
        c.save()
        c.translate(x, y)
        ang = fallen * (1.4 if x > W / 2 else -1.4) + 0.02 * sway * math.sin(t + i)
        c.rotate(ang)
        c.move_to(-hh * 0.28, 0)
        c.line_to(0, -hh)
        c.line_to(hh * 0.28, 0)
        c.close_path()
        c.set_source_rgba(*col)
        c.fill()
        c.restore()


def big_ben(c, x, y, col, glow=None):
    c.set_source_rgba(*col)
    c.rectangle(x - 45, y - 520, 90, 520)
    c.fill()
    c.move_to(x - 55, y - 520)
    c.line_to(x, y - 660)
    c.line_to(x + 55, y - 520)
    c.close_path()
    c.fill()
    c.rectangle(x - 240, y - 220, 190, 220)
    c.rectangle(x + 50, y - 260, 260, 260)
    c.fill()
    for k in range(6):
        c.rectangle(x + 60 + k * 42, y - 300, 18, 40)
        c.fill()
    c.arc(x, y - 440, 34, 0, 2 * math.pi)
    c.set_source_rgba(*(glow or hx("FFE9A8")))
    c.fill()
    c.set_source_rgba(*col)
    c.set_line_width(4)
    c.move_to(x, y - 440)
    c.line_to(x, y - 465)
    c.move_to(x, y - 440)
    c.line_to(x + 16, y - 440)
    c.stroke()


def kremlin(c, y, col):
    c.set_source_rgba(*col)
    c.rectangle(0, y - 140, W, 140)
    c.fill()
    for k in range(14):
        c.rectangle(k * 80, y - 170, 40, 30)
        c.fill()
    # cúpulas de San Basilio
    for (x, h, r) in ((380, 360, 46), (520, 470, 60), (660, 360, 46), (780, 300, 40)):
        c.rectangle(x - r * 0.6, y - h, r * 1.2, h)
        c.fill()
        c.move_to(x - r, y - h)
        c.curve_to(x - r, y - h - r * 1.4, x, y - h - r * 1.2, x, y - h - r * 2.2)
        c.curve_to(x, y - h - r * 1.2, x + r, y - h - r * 1.4, x + r, y - h)
        c.close_path()
        c.fill()


def scene(c, kind, t, lt, ev):
    if kind == "siberia":
        sky(c, hx("1B1F45"), hx("F28A4A"))
        stars(c, t, 60, alpha=0.4)
        c.arc(820, 1100, 90, 0, 2 * math.pi)
        c.set_source_rgba(1, 0.85, 0.5, 0.8)
        c.fill()
        pines(c, 1320, 14, 300, hx("2A2238"), 2, t)
        pines(c, 1460, 11, 380, hx("17121F"), 5, t)
        ground(c, hx("15101A"))
    elif kind == "meteoro":
        sky(c, hx("2A0E2E"), hx("FF7A2E"))
        k = clamp(lt / 3.6)
        mx, my = 120 + k * 760, 260 + k * 560
        for i in range(30):
            a = 1 - i / 30
            c.arc(mx - i * 30, my - i * 24, 70 * a + 8, 0, 2 * math.pi)
            c.set_source_rgba(1, 0.6 + 0.4 * a, 0.2 * a, 0.25 * a)
            c.fill()
        g = cairo.RadialGradient(mx, my, 4, mx, my, 170)
        g.add_color_stop_rgba(0, 1, 1, 0.9, 1)
        g.add_color_stop_rgba(0.3, 1, 0.75, 0.3, 0.8)
        g.add_color_stop_rgba(1, 1, 0.4, 0.1, 0)
        c.set_source(g)
        c.arc(mx, my, 170, 0, 2 * math.pi)
        c.fill()
        pines(c, 1460, 11, 380, hx("17121F"), 5, t)
        ground(c, hx("15101A"))
    elif kind == "explosion":
        sky(c, hx("FFD3A0"), hx("FF5A1E"))
        k = clamp(lt / 2.5)
        for i in range(3):
            rr = 200 + (k + i * 0.25) % 1.0 * 1400
            c.arc(540, 1150, rr, 0, 2 * math.pi)
            c.set_source_rgba(1, 1, 0.9, 0.35 * (1 - ((k + i * 0.25) % 1.0)))
            c.set_line_width(40)
            c.stroke()
        pines(c, 1460, 12, 360, hx("3A1A0F"), 5, t, fallen=k)
        ground(c, hx("2A140C"))
    elif kind == "bosque_caido":
        sky(c, hx("3B4252"), hx("A7A9AE"))
        c.rectangle(0, 1180, W, 400)
        c.set_source_rgba(*hx("5A4E40"))
        c.fill()
        rnd = random.Random(9)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        for i in range(70):
            y = 1200 + rnd.uniform(0, 340)
            x = rnd.uniform(-50, W + 50)
            ln = 60 + (y - 1200) * 0.6
            a = math.atan2(y - 1150, x - 540)
            c.set_source_rgba(*hx("2A211A"))
            c.set_line_width(4 + (y - 1200) * 0.03)
            c.move_to(x, y)
            c.line_to(x + math.cos(a) * ln, y + math.sin(a) * ln * 0.3)
            c.stroke()
        for x in (180, 420, 650, 900):
            c.set_source_rgba(*hx("2A211A"))
            c.set_line_width(10)
            c.move_to(x, 1220)
            c.line_to(x + 4, 1100)
            c.stroke()
        ground(c, hx("4A3E33"))
        if ev.get("carpa"):
            c.move_to(820, 1520)
            c.line_to(900, 1400)
            c.line_to(980, 1520)
            c.close_path()
            c.set_source_rgba(*hx("C9B48A"))
            c.fill()
    elif kind == "londres":
        sky(c, hx("1C2A5A"), hx("F2C27A"))
        stars(c, t, 50, alpha=0.3)
        big_ben(c, 760, 1440, hx("141824"))
        ground(c, hx("10131C"))
    elif kind == "moscu":
        sky(c, hx("0E1430"), hx("4A3C7A"))
        stars(c, t, 100)
        kremlin(c, 1440, hx("0A0C18"))
        ground(c, hx("0A0C18"))
    elif kind == "noche":
        sky(c, hx("05060E"), hx("1A1530"))
        stars(c, t, 140)
        ground(c, hx("07070C"))


# ------------------------------------------------------------------ texto
def font(c, size, fam=R.F_BLACK):
    R.font(c, size, fam)


def gancho(c, txt, lt, color):
    if lt < 0 or lt > 3.4:
        return
    k = back(lt / 0.25)
    fade = 1 if lt < 2.8 else clamp((3.4 - lt) / 0.6)
    jit = 4 * math.sin(lt * 80) if lt < 0.4 else 0
    lines = txt.split("|")
    c.save()
    c.translate(540 + jit, 380)
    c.scale(k, k)
    for i, ln in enumerate(lines):
        size = 96 if i == 0 else 70
        font(c, size)
        while R.tw(c, ln) > 980:
            size -= 4
            font(c, size)
        x = -R.tw(c, ln) / 2
        y = i * (size + 16)
        c.move_to(x, y)
        c.text_path(ln)
        c.set_source_rgba(0, 0, 0, 0.85 * fade)
        c.set_line_width(18)
        c.set_line_join(cairo.LINE_JOIN_ROUND)
        c.stroke()
        c.move_to(x, y)
        col = color if i == 0 else WHITE
        c.set_source_rgba(*col[:3], fade)
        c.show_text(ln)
    c.restore()


def subtitulos(c, who, texto, lt, habla):
    words = [w.replace("*", "") for w in texto.split()]
    hl = ["*" in w for w in texto.split()]
    size = 54
    font(c, size)
    sp = R.tw(c, " ")
    lines, cur, cw = [], [], 0
    for i, wd in enumerate(words):
        ww = R.tw(c, wd)
        if cur and cw + sp + ww > 960:
            lines.append(cur)
            cur, cw = [], 0
        cur.append((i, wd, ww))
        cw += (sp if len(cur) > 1 else 0) + ww
    lines.append(cur)
    lines = lines[-2:] if len(lines) > 2 else lines
    n = len(words)
    idx = min(n - 1, int(clamp((lt - 0.1) / max(habla, 0.4)) * n))
    y0 = 1690
    font(c, 28)
    lbl = NOMBRES.get(who, who.upper())
    w_ = R.tw(c, lbl) + 36
    R.rrect(c, 540 - w_ / 2, y0 - 92, w_, 44, 22)
    c.set_source_rgba(*COLOR_NOMBRE.get(who, WHITE))
    c.fill()
    c.set_source_rgba(0, 0, 0, 1)
    c.move_to(540 - R.tw(c, lbl) / 2, y0 - 60)
    c.show_text(lbl)
    font(c, size)
    for li, line in enumerate(lines):
        lw = sum(x[2] for x in line) + sp * (len(line) - 1)
        x = 540 - lw / 2
        y = y0 + li * (size + 14)
        for (i, wd, ww) in line:
            col = YEL if i == idx else (hx("FF6B6B") if hl[i] else WHITE)
            c.move_to(x, y)
            c.text_path(wd)
            c.set_source_rgba(0, 0, 0, 0.9)
            c.set_line_width(10)
            c.stroke()
            c.move_to(x, y)
            c.set_source_rgba(*col)
            c.show_text(wd)
            x += ww + sp


def badge(c, txt, t, total):
    c.set_source_rgba(1, 1, 1, 0.15)
    c.rectangle(0, 0, W, 10)
    c.fill()
    c.set_source_rgba(*RED)
    c.rectangle(0, 0, W * clamp(t / total), 10)
    c.fill()
    font(c, 30)
    w = R.tw(c, txt) + 60
    R.rrect(c, 540 - w / 2, 50, w, 58, 29)
    c.set_source_rgba(0, 0, 0, 0.65)
    c.fill_preserve()
    c.set_source_rgba(*RED)
    c.set_line_width(3)
    c.stroke()
    c.set_source_rgba(1, 1, 1, 1)
    c.move_to(540 - R.tw(c, txt) / 2, 90)
    c.show_text(txt)


_GRAIN = []


def post(c, t, flash, shake_amt):
    # viñeta
    g = cairo.RadialGradient(540, 960, 500, 540, 960, 1250)
    g.add_color_stop_rgba(0, 0, 0, 0, 0)
    g.add_color_stop_rgba(1, 0, 0, 0, 0.75)
    c.set_source(g)
    c.paint()
    # grano
    if not _GRAIN:
        rnd = np.random.default_rng(1)
        for _ in range(4):
            a = (rnd.random((H // 4, W // 4)) * 40).astype(np.uint8)
            buf = np.zeros((H // 4, W // 4, 4), np.uint8)
            buf[..., 0] = buf[..., 1] = buf[..., 2] = 255
            buf[..., 3] = a
            s = cairo.ImageSurface.create_for_data(memoryview(buf), cairo.FORMAT_ARGB32, W // 4, H // 4)
            _GRAIN.append((s, buf))
    s, _ = _GRAIN[int(t * 24) % 4]
    c.save()
    c.scale(4, 4)
    c.set_source_surface(s, 0, 0)
    c.paint_with_alpha(0.18)
    c.restore()
    if flash > 0:
        c.set_source_rgba(1, 1, 1, flash)
        c.paint()


def cierre(c, ep, lt):
    k = ease(lt / 0.4)
    c.set_source_rgba(0, 0, 0, 0.72 * k)
    c.paint()
    if lt > 0.2:
        kk = back((lt - 0.2) / 0.35)
        c.save()
        c.translate(540, 520)
        c.scale(kk, kk)
        R.text_center(c, "CONTINUARÁ...", 0, 0, 104, RED, outline=hx("000000"), ow=14)
        for i, ln in enumerate(ep["siguiente"].split("|")):
            R.text_center(c, ln, 0, 90 + i * 64, 50 if i == 0 else 42, WHITE, R.F_XBOLD)
        c.restore()
    if lt > 0.6:
        kk = back((lt - 0.6) / 0.35)
        c.save()
        c.translate(540, 1240)
        c.scale(kk, kk)
        R.rrect(c, -470, -120, 940, 240, 36)
        c.set_source_rgba(0.08, 0.06, 0.08, 0.95)
        c.fill_preserve()
        c.set_source_rgba(*RED)
        c.set_line_width(5)
        c.stroke()
        taps = (1.2, 1.9, 2.6)
        on = [lt > tp for tp in taps]
        for i, (lbl, bx, col) in enumerate((("LIKE", -440, hx("2B6BE0")), ("❤", -140, hx("3A1F2B")), ("SÍGUEME", 160, RED))):
            R.rrect(c, bx, -55, 280, 110, 55)
            c.set_source_rgba(*(col if (on[i] if i < 2 else not on[i]) else hx("2A2A33")))
            c.fill()
            if i == 0:
                R.draw_thumb_icon(c, bx + 70, 0, 1.15, WHITE)
                R.text_center(c, "LIKE", bx + 185, 18, 44, WHITE)
            elif i == 1:
                R.draw_heart(c, bx + 80, 6, 1.1, RED if on[1] else hx("2A2A33"), None if on[1] else WHITE)
                R.text_center(c, "¡GRACIAS!" if on[1] else "ME GUSTA", bx + 190, 16, 30, WHITE)
            else:
                R.draw_user_plus(c, bx + 55, 2, 1.0, WHITE)
                R.text_center(c, "SIGUIENDO" if on[2] else "SÍGUEME", bx + 175, 14, 36, WHITE)
        targets = [(-300, 30), (40, 30), (300, 30)]
        pos, press = (0, 260), 0
        for i, tp in enumerate(taps):
            if lt >= tp - 0.4:
                prev = targets[i - 1] if i else (0, 260)
                m = ease((lt - (tp - 0.4)) / 0.35)
                pos = (prev[0] + (targets[i][0] - prev[0]) * m, prev[1] + (targets[i][1] - prev[1]) * m)
                press = max(0, 1 - abs(lt - tp) / 0.12)
        R.draw_hand(c, pos[0], pos[1], press)
        c.restore()


# ------------------------------------------------------------------ audio
def audio(lineas, total, outro_at, path):
    n = int(total * SR) + SR
    tt = np.arange(n) / SR
    rng = np.random.default_rng(2)
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * tt)
    drone = (0.20 * np.sin(2 * np.pi * 55 * tt) + 0.12 * np.sin(2 * np.pi * 82.4 * tt + 0.5)
             + 0.07 * np.sin(2 * np.pi * 110 * tt) * lfo + 0.05 * np.sin(2 * np.pi * 116.5 * tt))
    wind = np.convolve(rng.standard_normal(n), np.ones(400) / 400, "same") * 1.6
    music = drone * lfo + wind * 0.35
    # pulso de tensión (bajo) cada beat a 96 bpm
    beat = 60 / 96
    for b in range(int(total / beat)):
        i0 = int(b * beat * SR)
        L = min(int(0.25 * SR), n - i0)
        x = np.arange(L) / SR
        music[i0:i0 + L] += 0.18 * np.sin(2 * np.pi * (60 * np.exp(-x * 8) + 38) * x) * np.exp(-x * 9)
    voice = np.zeros(n)
    sfx = np.zeros(n)

    def add(sig, at, amp):
        i0 = int(at * SR)
        m = min(len(sig), n - i0)
        if m > 0 and i0 >= 0:
            sfx[i0:i0 + m] += amp * sig[:m]

    def thump(at, amp=0.9):
        for d in (0.0, 0.2):
            L = int(0.18 * SR)
            x = np.arange(L) / SR
            add(np.sin(2 * np.pi * (70 * np.exp(-x * 12) + 40) * x) * np.exp(-x * 18), at + d, amp * (1 if d == 0 else 0.7))

    def whoosh(at, amp=0.4):
        L = int(0.5 * SR)
        x = np.arange(L) / SR
        nz = np.convolve(rng.standard_normal(L), np.ones(25) / 25, "same") * 5
        add(nz * np.sin(np.pi * x / 0.5) ** 2, at, amp)

    def boom(at):
        L = int(2.5 * SR)
        x = np.arange(L) / SR
        s_ = np.sin(2 * np.pi * (90 * np.exp(-x * 3) + 28) * x) * np.exp(-x * 1.4)
        nz = np.convolve(rng.standard_normal(L), np.ones(60) / 60, "same") * 6 * np.exp(-x * 2)
        add(s_ + nz, at, 0.9)

    def riser(at, dur=2.0):
        L = int(dur * SR)
        x = np.arange(L) / SR
        f = 200 + 1400 * (x / dur) ** 2
        add(np.sin(2 * np.pi * np.cumsum(f) / SR) * (x / dur) ** 2 * 0.5, at, 0.35)

    for (a, b, ln) in lineas:
        vo = ln["_audio"] / (np.abs(ln["_audio"]).max() + 1e-9)
        i0 = int((a + 0.12) * SR)
        m = min(len(vo), n - i0)
        voice[i0:i0 + m] += vo[:m]
        if ln.get("gancho"):
            whoosh(a, 0.35)
            thump(a + 0.05, 0.6)
        for sx in ln.get("sfx", []):
            if sx == "boom":
                boom(a + 0.2)
            elif sx == "riser":
                riser(max(0, a + (b - a) - 2.0), 2.0)
            elif sx == "latidos":
                for k in range(int((b - a) / 0.8)):
                    thump(a + k * 0.8, 0.8)
    whoosh(outro_at, 0.5)
    for tp in (1.2, 1.9, 2.6):
        L = int(0.3 * SR)
        x = np.arange(L) / SR
        add(np.sin(2 * np.pi * 1400 * x) * np.exp(-x * 14), outro_at + tp, 0.25)
    env = np.convolve(np.abs(voice), np.ones(4800) / 4800, "same")
    duck = 1 - 0.55 * np.clip(env * 12, 0, 1)
    mix = music * 0.5 * duck + sfx * 0.7 + voice
    mix = mix[:int(total * SR)]
    f = int(0.6 * SR)
    mix[-f:] *= np.linspace(1, 0, f)
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.92
    pcm = (np.stack([mix, mix], 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ------------------------------------------------------------------ main
def main():
    gp = sys.argv[1]
    ep = json.load(open(gp, encoding="utf-8"))
    outdir = os.path.dirname(os.path.abspath(gp))
    total = ep.get("duracion", 45.0)
    outro = ep.get("cierre", 3.6)
    pausa = ep.get("pausa", 0.25)
    preview = "--frame" in sys.argv
    lineas = []
    tcur = 0.0
    for i, ln in enumerate(ep["lineas"]):
        if preview:
            fw = f"/tmp/esq_{i}.wav"
            if os.path.exists(fw):
                wf = wave.open(fw)
                n = int(wf.getnframes() * SR / wf.getframerate())
            else:
                n = int(SR * 2.5)
            ln["_audio"] = np.zeros(n)
        else:
            ln["_audio"] = R.tts_line(ln["quien"], ln.get("voz", ln["texto"].replace("*", "")), f"/tmp/esq_{i}.wav", 1.0)
        ln["habla"] = len(ln["_audio"]) / SR
        d = ln["habla"] + 0.12 + ln.get("pausa", pausa)
        lineas.append([tcur, tcur + d, ln])
        tcur += d
    speech_end = tcur
    outro_at = max(speech_end, total - outro)
    if speech_end > total - outro + 0.5:
        print(f"AVISO: el habla dura {speech_end:.1f}s; total {total}s")
    if ep.get("duracion_max"):
        total = min(ep["duracion_max"], math.ceil(speech_end + outro))
    total = max(total, speech_end + outro)
    # estira levemente para encajar
    if speech_end < total - outro:
        k = (total - outro) / speech_end
        for L in lineas:
            L[0] *= k
            L[1] *= k
    print(f"Duración: {total:.2f} s (habla {speech_end:.1f} s)")
    if not preview:
        audio(lineas, total, outro_at, "/tmp/esq_audio.wav")

    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    elenco = ep["elenco"]
    MODELOS = {}
    for name, cfg in elenco.items():
        if cfg.get("modelo"):
            import sprites
            MODELOS[name] = {"close": sprites.Personaje(cfg["modelo"], cfg.get("escala_primer_plano", 0.72)),
                             "two": sprites.Personaje(cfg["modelo"], cfg.get("escala", 0.42))}

    def frame(t):
        cur = None
        for (a, b, ln) in lineas:
            if a <= t < b:
                cur = (a, b, ln)
        if cur is None:
            cur = lineas[-1] if t >= lineas[-1][0] else lineas[0]
        a, b, ln = cur
        lt = t - a
        sk = ln.get("escena", "noche")
        shake = 0
        if "boom" in ln.get("sfx", []) and lt < 1.2:
            shake = 18 * (1 - lt / 1.2)
        if PLANOS:
            dibujar_plano(c, t, ln, lt, shake)
        else:
            escena_clasica(c, t, ln, lt, a, b, shake)
        if ln.get("gancho"):
            gancho(c, ln["gancho"], lt, RED if ln.get("rojo", True) else YEL)
        if t < outro_at and lt < ln["habla"] + 0.25:
            subtitulos(c, ln["quien"], ln["texto"], lt, ln["habla"])
        flash = 0
        if "boom" in ln.get("sfx", []) and lt < 0.6:
            flash = 0.9 * (1 - lt / 0.6)
        if ln.get("gancho") and lt < 0.08:
            flash = max(flash, 0.25)
        post(c, t, flash, shake)
        if t >= outro_at:
            cierre(c, ep, t - outro_at)
        badge(c, ep["badge"], t, total)

    # --------------------------------------------------------- modo cine (planos)
    PLANOS = []
    for pl in ep.get("planos", []):
        a_, b_, _ = lineas[pl["linea"]]
        PLANOS.append((a_ + pl.get("desde", 0.0) * (b_ - a_), pl))
    PLANOS.sort(key=lambda x: x[0])
    if PLANOS:
        import cine
        import sprites as SP
        cine.registrar_reales(ep.get("escenas_reales", {}))
        for _, pl in PLANOS:
            cine.escena(pl["escena"])
    _PJ = {}

    def pj(tipo, esc):
        key = (tipo, round(esc, 2))
        if key not in _PJ:
            _PJ[key] = SP.Personaje(tipo, esc)
        return _PJ[key]

    def dibujar_plano(c, t, ln, lt_line, shake):
        idx = max(i for i, (ts, _) in enumerate(PLANOS) if ts <= t + 1e-6) if t >= PLANOS[0][0] else 0
        t0, pl = PLANOS[idx]
        t1 = PLANOS[idx + 1][0] if idx + 1 < len(PLANOS) else total
        lt = t - t0
        k = clamp(lt / max(0.1, t1 - t0))
        E = cine.escena(pl["escena"])
        cam = pl.get("cam", {})
        z, x, y, r = cine.camara(cam, k)
        dx, dy, dz = cine.desplazamiento_transicion(pl.get("trans", ""), lt)
        hmx, hmy, hmr = cine.mano(t, idx * 1.7, pl.get("mano", 1.0))
        sh = (shake * math.sin(t * 70) + hmx, shake * math.cos(t * 55) + hmy)
        r += hmr
        barrido = pl.get("trans") == "barrido" and lt < 0.26
        if barrido:
            c.push_group()
        c.save()
        c.translate(dx, dy)
        c.translate(W / 2, H / 2)
        c.scale(dz, dz)
        c.translate(-W / 2, -H / 2)
        c.save()
        cine.aplicar_camara(c, z, x, y, r, sh, (E.bw, E.bh))
        E.fondo(c, t, lt, k, blur=pl.get("fondo_desenfocado", False))
        E.dyn(c, t, lt, k)
        cine.fx_real(c, pl.get("fx", E.fx), t, lt, k, E.bw, E.bh)
        c.restore()
        # personajes (pantalla) con paralaje respecto a la cámara
        z0, x0, y0, _ = cine.camara(cam, 0)
        par = pl.get("paralaje", 0.45)
        px, py = -(x - x0) * z * par + hmx * 1.15, -(y - y0) * z * par + hmy * 1.15
        pz = (z / z0) ** 0.5
        pers = pl.get("pj", [])
        pers = sorted(pers, key=lambda q: q["q"] == ln["quien"])
        for q in pers:
            cfg = elenco[q["q"]]
            st = dict(cfg)
            st.update(ln.get("estado", {}).get(q["q"], {}))
            st.update(q.get("estado", {}))
            st["talking"] = (ln["quien"] == q["q"] and lt_line < ln["habla"] + 0.1)
            talk = (0.35 + 0.65 * abs(math.sin(t * 13)) * (0.5 + 0.5 * math.sin(t * 4.3))) if st["talking"] else 0.0
            P = pj(cfg["modelo"], q.get("esc", 0.6))
            ex = q["x"] * 1.0
            ey = q.get("y", 1640) * 1.0
            ent = q.get("entra")
            ke = cine.ease_out(lt / 0.7)
            if ent == "abajo":
                ey += 520 * (1 - ke)
            elif ent == "izq":
                ex -= 700 * (1 - ke)
            elif ent == "der":
                ex += 700 * (1 - ke)
            walk = q.get("camina", 0.0)
            ex += walk * lt
            bob_w = 10 * abs(math.sin(lt * 6)) if walk else 0
            sx_ = (ex - W / 2) * pz + W / 2 + px
            sy_ = (ey - H / 2) * pz + H / 2 + py - bob_w + sh[1] * 0.5
            c.save()
            c.translate(sx_, sy_)
            c.rotate(hmr)
            c.scale(pz, pz)
            c.translate(-sx_, -sy_)
            if q.get("sombra", True) and not q.get("reflejo"):
                # sombra de contacto: ancla al personaje en el suelo real
                c.save()
                c.translate(sx_, sy_ - 6)
                c.scale(1, 0.16)
                gsh = cairo.RadialGradient(0, 0, 10, 0, 0, P.W * 0.5)
                gsh.add_color_stop_rgba(0, 0, 0, 0, 0.55)
                gsh.add_color_stop_rgba(1, 0, 0, 0, 0)
                c.set_source(gsh)
                c.arc(0, 0, P.W * 0.5, 0, 2 * math.pi)
                c.fill()
                c.restore()
            if E.agua and q.get("reflejo"):
                c.save()
                c.rectangle(0, E.agua, W, H - E.agua)
                c.clip()
                c.translate(0, 2 * E.agua)
                c.scale(1, -1)
                c.push_group()
                P.draw(c, sx_, E.agua, st, t, mirror=q.get("espejo", False), talk=talk,
                       brazo_extra=q.get("brazo", 0.0), tinte=E.luz, lean=q.get("lean", 0.0))
                c.pop_group_to_source()
                c.paint_with_alpha(0.32)
                c.restore()
            P.draw(c, sx_, sy_, st, t, mirror=q.get("espejo", False), talk=talk,
                   brazo_extra=q.get("brazo", 0.0), tinte=E.luz, lean=q.get("lean", 0.0))
            c.restore()
        # primer plano con más paralaje
        c.save()
        c.translate(px * 1.6, py * 1.2)
        E.fg(c, t, lt, k)
        c.restore()
        if E.sepia:
            cine.sepia_overlay(c, t)
        c.restore()
        if barrido:
            # barrido de cámara con desenfoque de movimiento real (estelas horizontales)
            pat = c.pop_group()
            f = 1 - cine.ease_out(lt / 0.26)
            n = 9
            for i in range(n):
                c.save()
                c.translate((i - n / 2) * 42 * f, 0)
                c.set_source(pat)
                c.paint_with_alpha(1.0 if i == 0 else 1.0 / (i + 1))
                c.restore()
        cine.transicion(c, pl.get("trans", ""), lt)
        if pl.get("rotulo") and lt < 2.4:
            a = min(1.0, lt / 0.3, (2.4 - lt) / 0.4)
            font(c, 34, R.F_XBOLD)
            txt = pl["rotulo"].replace("📍", "").strip()
            ext = c.text_extents(txt)
            slide = 40 * (1 - cine.ease_out(lt / 0.4))
            x0r = 40 - slide
            R.rrect(c, x0r, 1420, ext.width + 92, 62, 12)
            c.set_source_rgba(0.05, 0.03, 0.08, 0.7 * a)
            c.fill()
            c.set_source_rgba(0.89, 0.07, 0.17, a)
            c.arc(x0r + 32, 1446, 12, math.pi, 0)
            c.line_to(x0r + 32, 1468)
            c.close_path()
            c.fill()
            c.set_source_rgba(1, 1, 1, a)
            c.arc(x0r + 32, 1446, 5, 0, 6.3)
            c.fill()
            c.move_to(x0r + 60, 1463)
            c.show_text(txt)

    def escena_clasica(c, t, ln, lt, a, b, shake):
        c.save()
        if shake:
            c.translate(shake * math.sin(t * 70), shake * math.cos(t * 55))
        zoom = 1 + 0.04 * clamp(lt / max(b - a, 0.1)) + 0.07 * max(0.0, 1 - lt / 0.18)
        c.translate(540, 960)
        c.scale(zoom, zoom)
        c.translate(-540, -960)
        scene(c, sk, t, lt, ln)
        c.set_source_rgba(0.04, 0.03, 0.10, 0.38)
        c.paint()
        bokeh(c, t)
        orden = sorted(elenco.items(), key=lambda kv: kv[0] == ln["quien"])
        primer_plano = MODELOS and ln["quien"] in elenco and ln.get("plano") != "dos"
        for name, cfg in orden:
            if primer_plano and name != ln["quien"]:
                continue
            st = dict(cfg)
            st["talking"] = (ln["quien"] == name and lt < ln["habla"] + 0.1)
            st.update(ln.get("estado", {}).get(name, {}))
            if cfg.get("modelo"):
                talk = (0.35 + 0.65 * abs(math.sin(t * 13)) * (0.5 + 0.5 * math.sin(t * 4.3))) if st["talking"] else 0.0
                dim = 0.28 if (ln["quien"] in elenco and ln["quien"] != name) else 0.0
                if primer_plano:
                    MODELOS[name]["close"].draw(c, cfg.get("x_primer_plano", 540), 1610, st, t,
                                                mirror=cfg.get("espejo", False), talk=talk)
                else:
                    MODELOS[name]["two"].draw(c, cfg["x"], cfg.get("y", 1600), st, t,
                                              mirror=cfg.get("espejo", False), dim=dim, talk=talk,
                                              brazo_extra=-0.42)
            else:
                skeleton(c, cfg["x"], st, t)
        c.restore()

    if preview:
        for ts in sys.argv[sys.argv.index("--frame") + 1].split(","):
            frame(float(ts))
            p = os.path.join(os.environ.get("PREV_DIR", "/tmp/claude-0/-home-user-ROGERDEVELOPER/0e37c101-6eae-5a11-b822-1ce6fbc4f785/scratchpad"), f"esq_{float(ts):05.1f}.png")
            surf.write_to_png(p)
            print(p)
        return
    out = os.path.join(outdir, ep["archivo"])
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-i", "/tmp/esq_audio.wav", "-c:v", "libx264", "-preset", "medium",
                          "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
                          "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for fi in range(int(total * FPS)):
        frame(fi / FPS)
        surf.flush()
        p.stdin.write(bytes(surf.get_data()))
    p.stdin.close()
    p.wait()
    frame(1.0)
    surf.write_to_png(os.path.join(outdir, "miniatura.png"))
    print("Listo:", out)


if __name__ == "__main__":
    main()
