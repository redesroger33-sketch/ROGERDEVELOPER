#!/usr/bin/env python3
"""ESQUELETOS DEL MISTERIO — motor de shorts de suspenso (1080x1920, 30 fps).

Esqueletos con cabello negro, ojos tipo Pixar, manos articuladas y corazón que late,
escenarios de ciudades del mundo, ganchos de texto cada ~4 s, subtítulos palabra por
palabra, música de tensión, latidos, golpes y cierre "CONTINUARÁ".

Uso: python3 esqueletos.py ../capitulos/<carpeta>/guion.json [--frame 3,10]
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

R.VOCES_NAT["narrador"] = ([("em_alex", 1.0)], 1.1)
R.VOCES_NAT["ivan"] = ([("em_santa", 1.0)], 1.12)
R.VOCES_NAT["ana"] = ([("ef_dora", 1.0)], 1.12)
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


# ------------------------------------------------------------------ huesos
def bone(c, x1, y1, x2, y2, w):
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    for col, ww in ((INK, w + 7), (BONE, w)):
        c.set_source_rgba(*col)
        c.set_line_width(ww)
        c.move_to(x1, y1)
        c.line_to(x2, y2)
        c.stroke()
        for (px, py) in ((x1, y1), (x2, y2)):
            c.arc(px, py, (ww / 2) * 1.35, 0, 2 * math.pi)
            c.fill()
    # brillo
    c.set_source_rgba(1, 1, 1, 0.5)
    c.set_line_width(max(2, w * 0.18))
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L * w * 0.18, dx / L * w * 0.18
    c.move_to(x1 + dx * 0.2 + nx, y1 + dy * 0.2 + ny)
    c.line_to(x1 + dx * 0.8 + nx, y1 + dy * 0.8 + ny)
    c.stroke()


def hand(c, x, y, ang, side, curl=0.0):
    """Mano esquelética articulada: carpos, 5 dedos con falanges."""
    c.save()
    c.translate(x, y)
    c.rotate(ang)
    c.scale(side, 1)
    # palma (carpos)
    c.save()
    c.scale(1, 0.8)
    c.arc(0, 12, 17, 0, 2 * math.pi)
    c.restore()
    c.set_source_rgba(*INK)
    c.fill_preserve()
    c.set_source_rgba(*BONE)
    c.set_line_width(2)
    c.save()
    c.scale(1, 0.8)
    c.arc(0, 12, 13, 0, 2 * math.pi)
    c.restore()
    c.fill()
    fingers = [(-14, 1.0, 0.55), (-6, 1.0, 1.0), (2, 1.0, 1.1), (10, 1.0, 1.0), (17, 1.0, 0.8)]
    for i, (fx, _, ln) in enumerate(fingers):
        a = math.radians(-35 if i == 0 else (i - 2) * 9)
        px, py = fx * 0.9, 20
        segs = [14 * ln, 11 * ln, 8 * ln] if i else [12, 10]
        cur = a
        for s in segs:
            nx_, ny_ = px + math.sin(cur) * s, py + math.cos(cur) * s
            bone(c, px, py, nx_, ny_, 5)
            px, py = nx_, ny_
            cur += curl * 0.5
    c.restore()


def heart(c, x, y, s, beat):
    k = s * (1 + 0.12 * beat)
    glow = cairo.RadialGradient(x, y, 2, x, y, 70 * k)
    glow.add_color_stop_rgba(0, 1, 0.1, 0.2, 0.55 * (0.5 + beat))
    glow.add_color_stop_rgba(1, 1, 0.1, 0.2, 0)
    c.set_source(glow)
    c.arc(x, y, 70 * k, 0, 2 * math.pi)
    c.fill()
    c.save()
    c.translate(x, y)
    c.scale(k, k)
    c.move_to(0, 32)
    c.curve_to(-48, 2, -34, -38, 0, -16)
    c.curve_to(34, -38, 48, 2, 0, 32)
    c.close_path()
    g = cairo.LinearGradient(-30, -30, 30, 30)
    g.add_color_stop_rgba(0, *hx("FF4A5E"))
    g.add_color_stop_rgba(1, *hx("A0001C"))
    c.set_source(g)
    c.fill_preserve()
    c.set_source_rgba(*hx("5A0010"))
    c.set_line_width(3)
    c.stroke()
    c.arc(-14, -14, 7, 0, 2 * math.pi)
    c.set_source_rgba(1, 1, 1, 0.55)
    c.fill()
    # arteria
    c.set_source_rgba(*hx("C21A35"))
    c.set_line_width(7)
    c.move_to(4, -20)
    c.curve_to(6, -36, 18, -40, 22, -48)
    c.stroke()
    c.restore()


def pixar_eye(c, x, y, r, iris, look, blink, scared, female):
    # cuenca
    c.save()
    c.translate(x, y)
    c.scale(1, 1.08)
    c.arc(0, 0, r * 1.18, 0, 2 * math.pi)
    c.restore()
    c.set_source_rgba(0.12, 0.08, 0.07, 1)
    c.fill()
    rr = r * (1.08 if scared else 1.0)
    if blink:
        c.set_source_rgba(*BONE_SH)
        c.arc(x, y, rr, 0, 2 * math.pi)
        c.fill()
        c.set_source_rgba(*INK)
        c.set_line_width(4)
        c.arc(x, y + 2, rr * 0.8, math.radians(20), math.radians(160))
        c.stroke()
        return
    c.arc(x, y, rr, 0, 2 * math.pi)
    c.set_source_rgba(1, 1, 1, 1)
    c.fill_preserve()
    c.set_source_rgba(*INK)
    c.set_line_width(3)
    c.stroke()
    ix, iy = x + look[0] * r * 0.25, y + look[1] * r * 0.2
    ir = rr * (0.48 if scared else 0.62)
    g = cairo.RadialGradient(ix - ir * 0.2, iy - ir * 0.3, ir * 0.1, ix, iy, ir)
    g.add_color_stop_rgba(0, *[min(1, v * 1.5) for v in iris[:3]], 1)
    g.add_color_stop_rgba(0.7, *iris[:3], 1)
    g.add_color_stop_rgba(1, *[v * 0.4 for v in iris[:3]], 1)
    c.set_source(g)
    c.arc(ix, iy, ir, 0, 2 * math.pi)
    c.fill()
    c.set_source_rgba(0.03, 0.03, 0.05, 1)
    c.arc(ix, iy, ir * (0.32 if scared else 0.45), 0, 2 * math.pi)
    c.fill()
    c.set_source_rgba(1, 1, 1, 0.95)
    c.arc(ix - ir * 0.35, iy - ir * 0.38, ir * 0.28, 0, 2 * math.pi)
    c.fill()
    c.arc(ix + ir * 0.3, iy + ir * 0.3, ir * 0.12, 0, 2 * math.pi)
    c.fill()
    if female:
        c.set_source_rgba(*INK)
        c.set_line_width(4)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        side = 1 if x > 0 else -1
        for k in range(4):
            a = math.radians(-70 + k * 22) * side
            bx, by = x + math.sin(a) * rr, y - math.cos(a) * rr
            c.move_to(bx, by)
            c.curve_to(bx + math.sin(a) * 10, by - 8, bx + math.sin(a) * 18 + side * 4, by - 14,
                       bx + math.sin(a) * 22 + side * 8, by - 16)
            c.stroke()


def skull(c, st, t):
    female = st.get("female", False)
    talking = st.get("talking", False)
    scared = st.get("scared", False)
    blink = (t + st.get("phase", 0)) % 3.3 < 0.12
    # cráneo
    c.save()
    c.scale(1, 1.05)
    c.arc(0, -10, 112, 0, 2 * math.pi)
    c.restore()
    g = cairo.RadialGradient(-30, -50, 10, 0, -10, 130)
    g.add_color_stop_rgba(0, *hx("FFFBF2"))
    g.add_color_stop_rgba(1, *BONE_SH)
    c.set_source(g)
    c.fill_preserve()
    c.set_source_rgba(*INK)
    c.set_line_width(6)
    c.stroke()
    # mandíbula
    op = (8 + 16 * abs(math.sin(t * 15)) * (0.6 + 0.4 * math.sin(t * 4.7))) if talking else (14 if scared else 0)
    c.save()
    c.translate(0, op)
    R.rrect(c, -62, 62, 124, 60, 26)
    c.set_source_rgba(*BONE_SH)
    c.fill_preserve()
    c.set_source_rgba(*INK)
    c.set_line_width(5)
    c.stroke()
    c.set_source_rgba(1, 1, 1, 1)
    for i in range(6):
        R.rrect(c, -46 + i * 16, 64, 13, 15, 4)
        c.fill()
    c.restore()
    if op > 2:
        c.set_source_rgba(0.1, 0.05, 0.05, 1)
        c.rectangle(-50, 72, 100, op)
        c.fill()
    c.set_source_rgba(1, 1, 1, 1)
    for i in range(6):
        R.rrect(c, -46 + i * 16, 60, 13, 14, 4)
        c.fill()
    # nariz
    c.move_to(0, 18)
    c.line_to(-12, 42)
    c.line_to(12, 42)
    c.close_path()
    c.set_source_rgba(0.15, 0.1, 0.08, 1)
    c.fill()
    # pómulos rosados (mujer) / sombra
    if female:
        for sx in (-1, 1):
            g2 = cairo.RadialGradient(sx * 62, 26, 2, sx * 62, 26, 26)
            g2.add_color_stop_rgba(0, 1, 0.45, 0.6, 0.6)
            g2.add_color_stop_rgba(1, 1, 0.45, 0.6, 0)
            c.set_source(g2)
            c.arc(sx * 62, 26, 26, 0, 2 * math.pi)
            c.fill()
    look = st.get("look", (0.2 * math.sin(t * 0.7), 0))
    iris = st.get("iris", hx("6B3E1F"))
    for sx in (-1, 1):
        pixar_eye(c, sx * 44, -12, 36 if female else 34, iris, look, blink, scared, female)
    # cejas
    c.set_source_rgba(*hx("140F12"))
    c.set_line_width(7)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    for sx in (-1, 1):
        lift = -12 if scared else 0
        c.move_to(sx * 18, -62 + lift + (6 if scared else 0))
        c.line_to(sx * 66, -66 + lift)
        c.stroke()
    # cabello frontal
    c.set_source_rgba(*hx("140F12"))
    if female:
        c.move_to(-118, -10)
        c.curve_to(-120, -150, 110, -165, 120, -20)
        c.curve_to(90, -80, 30, -96, 10, -70)
        c.curve_to(-20, -100, -80, -90, -118, -10)
        c.close_path()
        c.fill()
        c.arc(96, 10, 12, 0, 2 * math.pi)
        c.set_source_rgba(*YEL)
        c.fill()
    else:
        c.move_to(-112, -30)
        c.curve_to(-110, -150, 100, -175, 116, -40)
        c.curve_to(80, -95, 30, -100, -10, -78)
        c.curve_to(-40, -100, -90, -80, -112, -30)
        c.close_path()
        c.fill()
        c.set_source_rgba(1, 1, 1, 0.18)
        c.set_line_width(5)
        c.arc(10, -40, 90, math.radians(220), math.radians(290))
        c.stroke()


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
}


def skeleton(c, x, st, t):
    s = st.get("scale", 0.95)
    shake = 5 * math.sin(t * 60) if st.get("scared") else 0
    bob = 6 * math.sin(t * 2 + st.get("phase", 0))
    c.save()
    c.translate(x + shake, GROUND_Y)
    c.scale(s, s)
    # sombra
    c.save()
    c.scale(1, 0.15)
    c.arc(0, 0, 170, 0, 2 * math.pi)
    c.restore()
    c.set_source_rgba(0, 0, 0, 0.35)
    c.fill()
    hip = -330 + bob * 0.3
    top = -650 + bob
    if st.get("female"):
        # melena larga detrás del cuerpo
        sway = 8 * math.sin(t * 1.8 + st.get("phase", 0))
        hy = top - 210
        c.move_to(-128, hy - 40)
        c.curve_to(-175, hy + 120, -150 + sway, hy + 300, -110 + sway, hy + 360)
        c.curve_to(-60, hy + 380, 60, hy + 380, 110 + sway, hy + 360)
        c.curve_to(150 + sway, hy + 300, 175, hy + 120, 128, hy - 40)
        c.close_path()
        c.set_source_rgba(*hx("140F12"))
        c.fill()
    # piernas
    for sd in (-1, 1):
        knee = (sd * 55, -170)
        foot = (sd * 70, -10)
        bone(c, sd * 40, hip + 20, knee[0], knee[1], 18)
        bone(c, knee[0], knee[1], foot[0], foot[1], 15)
        bone(c, foot[0], foot[1], foot[0] + sd * 38, foot[1] + 4, 12)
    # pelvis
    c.move_to(-75, hip - 10)
    c.curve_to(-90, hip + 40, -30, hip + 70, 0, hip + 40)
    c.curve_to(30, hip + 70, 90, hip + 40, 75, hip - 10)
    c.curve_to(40, hip + 10, -40, hip + 10, -75, hip - 10)
    c.close_path()
    c.set_source_rgba(*BONE)
    c.fill_preserve()
    c.set_source_rgba(*INK)
    c.set_line_width(5)
    c.stroke()
    # columna
    for i in range(10):
        y = hip - 20 - i * ((hip - 20 - top) / 10)
        R.rrect(c, -14, y - 13, 28, 22, 7)
        c.set_source_rgba(*BONE)
        c.fill_preserve()
        c.set_source_rgba(*INK)
        c.set_line_width(3)
        c.stroke()
    # corazón (detrás de costillas)
    rate = st.get("bpm", 70) / 60.0
    ph = (t * rate) % 1.0
    beat = max(0.0, 1 - abs(ph - 0.08) / 0.08) + 0.6 * max(0.0, 1 - abs(ph - 0.26) / 0.07)
    heart(c, -16, top + 150, 1.3, beat)
    # costillas
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    for i in range(6):
        y = top + 60 + i * 34
        wd = 120 - abs(i - 2) * 8
        for sd in (-1, 1):
            for col, lw in ((INK, 13), (BONE, 7)):
                c.set_source_rgba(*col)
                c.set_line_width(lw)
                c.move_to(0, y)
                c.curve_to(sd * wd * 0.7, y - 18, sd * wd, y + 6, sd * wd * 0.85, y + 40)
                c.stroke()
    bone(c, 0, top + 40, 0, top + 230, 14)  # esternón
    # clavículas
    sy = top + 20
    for sd in (-1, 1):
        bone(c, 0, sy, sd * 110, sy + 8, 11)
    # brazos + manos
    pose = st.get("pose", "idle")
    (l1, l2), (r1, r2) = POSES.get(pose, POSES["idle"])
    wig = 6 * math.sin(t * 5) if st.get("talking") else 3 * math.sin(t * 1.7 + st.get("phase", 0))
    for sd, (a1, a2) in ((-1, (l1 + wig, l2)), (1, (r1 - wig, r2))):
        sxp, syp = sd * 110, sy + 8
        (ex, ey), (hxp, hyp), ang = arm_pts(sxp, syp, sd, a1, a2)
        bone(c, sxp, syp, ex, ey, 16)
        bone(c, ex, ey, hxp, hyp, 13)
        bone(c, ex + 6 * sd, ey + 4, hxp + 6 * sd, hyp, 7)
        hand(c, hxp, hyp, -sd * ang, sd, curl=0.5 if pose == "scared" else 0.1)
    # cuello y cráneo
    for i in range(3):
        R.rrect(c, -16, top - 40 - i * 22, 32, 18, 6)
        c.set_source_rgba(*BONE)
        c.fill_preserve()
        c.set_source_rgba(*INK)
        c.set_line_width(3)
        c.stroke()
    c.save()
    c.translate(0, top - 225)
    c.scale(1.22, 1.22)
    tilt = 0.05 * math.sin(t * 1.3 + st.get("phase", 0))
    c.rotate(tilt)
    skull(c, st, t)
    c.restore()
    # bufanda
    if st.get("bufanda"):
        R.rrect(c, -70, top - 50, 140, 36, 16)
        c.set_source_rgba(*st["bufanda"])
        c.fill_preserve()
        c.set_source_rgba(*INK)
        c.set_line_width(4)
        c.stroke()
        R.rrect(c, 30, top - 30, 34, 110, 12)
        c.set_source_rgba(*st["bufanda"])
        c.fill_preserve()
        c.set_source_rgba(*INK)
        c.stroke()
    c.restore()


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
            ln["_audio"] = np.zeros(int(SR * 2.5))
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
        c.save()
        if shake:
            c.translate(shake * math.sin(t * 70), shake * math.cos(t * 55))
        zoom = 1 + 0.04 * clamp(lt / max(b - a, 0.1))
        c.translate(540, 960)
        c.scale(zoom, zoom)
        c.translate(-540, -960)
        scene(c, sk, t, lt, ln)
        for name, cfg in elenco.items():
            st = dict(cfg)
            st["talking"] = (ln["quien"] == name and lt < ln["habla"] + 0.1)
            st.update(ln.get("estado", {}).get(name, {}))
            skeleton(c, cfg["x"], st, t)
        c.restore()
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

    if preview:
        for ts in sys.argv[sys.argv.index("--frame") + 1].split(","):
            frame(float(ts))
            p = f"/tmp/claude-0/-home-user-ROGERDEVELOPER/0e37c101-6eae-5a11-b822-1ce6fbc4f785/scratchpad/esq_{float(ts):05.1f}.png"
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
