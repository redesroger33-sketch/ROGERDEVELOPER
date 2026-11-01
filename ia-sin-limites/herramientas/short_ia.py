#!/usr/bin/env python3
"""Render del short de muestra de IA SIN LÍMITES (#23: ¿Es buena inversión este depa?).

Estilo: tecnológico oscuro con neón, celular con prompt que se escribe solo,
ecuaciones animadas, barras de gastos, medidor, subtítulos palabra por palabra
estilo CapCut, dos voces (narrador y "la IA") y cierre con LIKE / ❤ / SÍGUEME.

Uso: python3 short_ia.py <salida.mp4>
"""
import math
import os
import random
import subprocess
import sys
import wave

import cairo
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../noticias-stickman/motor"))
import render as R  # noqa: E402  (voces, utilidades de dibujo)

W, H, FPS, SR = 1080, 1920, 30, 48000
BG1, BG2 = R.hx("070B18"), R.hx("121A36")
CYAN, MAG, LIME, WHITE = R.hx("00E5FF"), R.hx("FF2E93"), R.hx("B6FF3B"), R.hx("FFFFFF")
DIM = R.hx("8A93B2")
F = R.F_BLACK

R.VOCES["narrador"] = "es_MX-claude-high"
R.VOCES["ia"] = "es_AR-daniela-high"
R.TONO["narrador"] = 1.5
R.TONO["ia"] = 2.0

GUION = [
    ("narrador", "hook", "¿Un depa de *S/ 350,000* que se alquila en *S/ 1,800?* ¿Conviene o no?",
     "¿Un depa de trescientos cincuenta mil soles, que se alquila en mil ochocientos? ¿Conviene, o no?"),
    ("narrador", "phone", "Antes de firmar, pregúntale a la *inteligencia artificial.* Copia este prompt.",
     "Antes de firmar, pregúntale a la inteligencia artificial. Copia este prompt."),
    ("ia", "bruta", "Rentabilidad bruta: *S/ 1,800* por 12 meses son *S/ 21,600* al año. Eso es *6.2%.*",
     "Rentabilidad bruta: mil ochocientos por doce meses, son veintiún mil seiscientos soles al año. Eso es seis punto dos por ciento."),
    ("narrador", "bruta2", "Suena bien… pero la IA *no se queda ahí.*",
     "Suena bien... pero la IA no se queda ahí."),
    ("ia", "gastos", "Resta los gastos reales: *impuesto,* arbitrios y predial, *un mes vacío* y reparaciones.",
     "Resta los gastos reales: impuesto, arbitrios y predial, un mes vacío, y reparaciones."),
    ("ia", "neta", "Te quedan *S/ 16,520.* Rentabilidad neta: *4.7%.*",
     "Te quedan dieciséis mil quinientos veinte soles. Rentabilidad neta: cuatro punto siete por ciento."),
    ("narrador", "veredicto", "La clave: si tu *crédito* cuesta más que eso, el alquiler *no paga el depa solo.*",
     "La clave: si tu crédito cuesta más que eso, el alquiler no paga el depa solo."),
    ("narrador", "cta", "La IA no compra por ti, pero te *salva de comprar mal.* Comenta *NÚMEROS.*",
     "La IA no compra por ti, pero te salva de comprar mal. Comenta números, y te paso el prompt."),
]
PROMPT = ("Eres analista inmobiliario en Lima. Depa: precio S/ 350,000, alquiler S/ 1,800 al mes. "
          "Calcula la rentabilidad bruta y neta (impuesto 5%, arbitrios, vacancia, reparaciones) y dime si conviene.")
GASTOS = [("Impuesto a la renta (5%)", 1080), ("Arbitrios y predial (est.)", 1200),
          ("1 mes sin inquilino", 1800), ("Reparaciones (est.)", 1000)]
PAUSA = 0.35
OUTRO = 3.2


# ----------------------------------------------------------------- dibujo base
def fondo(c, t):
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgba(0, *BG1)
    g.add_color_stop_rgba(1, *BG2)
    c.set_source(g)
    c.paint()
    # rejilla en perspectiva
    c.set_line_width(2)
    hor = 1250
    for i in range(-12, 13):
        c.set_source_rgba(0, 0.9, 1, 0.10)
        c.move_to(540 + i * 40, hor)
        c.line_to(540 + i * 260, H)
        c.stroke()
    off = (t * 120) % 80
    for k in range(10):
        y = hor + (k * 80 + off) ** 1.25 / 4.2
        if y > H:
            break
        c.set_source_rgba(0, 0.9, 1, 0.08 + 0.02 * k)
        c.move_to(0, y)
        c.line_to(W, y)
        c.stroke()
    # partículas
    rnd = random.Random(4)
    for i in range(45):
        x = rnd.uniform(0, W)
        y = (rnd.uniform(0, H) - t * rnd.uniform(15, 40)) % H
        a = 0.25 + 0.25 * math.sin(t * 2 + i)
        c.arc(x, y, rnd.uniform(1.5, 3.5), 0, 2 * math.pi)
        c.set_source_rgba(*(CYAN[:3] if i % 3 else MAG[:3]), a)
        c.fill()


def glow_text(c, s, cx, y, size, col, glow=None, fam=F):
    R.font(c, size, fam)
    x = cx - R.tw(c, s) / 2
    if glow:
        for k, a in ((14, 0.10), (8, 0.18), (4, 0.3)):
            c.move_to(x, y)
            c.text_path(s)
            c.set_source_rgba(*glow[:3], a)
            c.set_line_width(k)
            c.set_line_join(cairo.LINE_JOIN_ROUND)
            c.stroke()
    c.move_to(x, y)
    c.set_source_rgba(*col)
    c.show_text(s)


def infinito(c, cx, cy, s, t):
    c.save()
    c.translate(cx, cy)
    c.scale(s, s)
    c.new_path()
    for i in range(121):
        a = i / 120 * 2 * math.pi
        x = 40 * math.cos(a) / (1 + math.sin(a) ** 2)
        y = 40 * math.sin(a) * math.cos(a) / (1 + math.sin(a) ** 2)
        (c.move_to if i == 0 else c.line_to)(x, y)
    c.restore()
    g = cairo.LinearGradient(cx - 40 * s, 0, cx + 40 * s, 0)
    g.add_color_stop_rgba(0, *CYAN)
    g.add_color_stop_rgba(1, *MAG)
    c.set_source(g)
    c.set_line_width(7)
    c.stroke()
    a = t * 2.5
    px = cx + s * 40 * math.cos(a) / (1 + math.sin(a) ** 2)
    py = cy + s * 40 * math.sin(a) * math.cos(a) / (1 + math.sin(a) ** 2)
    c.arc(px, py, 7, 0, 2 * math.pi)
    c.set_source_rgba(*WHITE)
    c.fill()


def marca(c, t, total):
    c.set_source_rgba(1, 1, 1, 0.12)
    c.rectangle(0, 0, W, 10)
    c.fill()
    g = cairo.LinearGradient(0, 0, W, 0)
    g.add_color_stop_rgba(0, *CYAN)
    g.add_color_stop_rgba(1, *MAG)
    c.set_source(g)
    c.rectangle(0, 0, W * min(1, t / total), 10)
    c.fill()
    R.rrect(c, 300, 52, 480, 76, 38)
    c.set_source_rgba(1, 1, 1, 0.06)
    c.fill_preserve()
    c.set_source_rgba(*CYAN[:3], 0.6)
    c.set_line_width(3)
    c.stroke()
    infinito(c, 372, 90, 0.75, t)
    R.font(c, 36)
    c.set_source_rgba(*WHITE)
    c.move_to(420, 103)
    c.show_text("IA SIN LÍMITES")


def panel(c, x, y, w, h, col=CYAN, a=0.07):
    R.rrect(c, x, y, w, h, 28)
    c.set_source_rgba(1, 1, 1, a)
    c.fill_preserve()
    c.set_source_rgba(*col[:3], 0.75)
    c.set_line_width(4)
    c.stroke()


# ----------------------------------------------------------------- escenas
def esc_hook(c, t, lt, d):
    k = R.ease_out_back(lt / 0.35)
    c.save()
    c.translate(540, 560)
    c.scale(k, k)
    # casa neón
    c.set_line_width(12)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    c.move_to(-170, 0)
    c.line_to(0, -150)
    c.line_to(170, 0)
    c.move_to(-130, -30)
    c.line_to(-130, 160)
    c.line_to(130, 160)
    c.line_to(130, -30)
    for k_, a in ((26, 0.12), (12, 1.0)):
        c.set_source_rgba(*CYAN[:3], a)
        c.set_line_width(k_)
        c.stroke_preserve()
    c.new_path()
    R.rrect(c, -35, 60, 70, 100, 8)
    c.set_source_rgba(*MAG)
    c.fill()
    c.restore()
    if lt > 0.3:
        glow_text(c, "S/ 350,000", 540, 900, 120, WHITE, CYAN)
    if lt > 1.6:
        glow_text(c, "ALQUILER S/ 1,800", 540, 1010, 70, LIME, LIME)
    if lt > 3.0:
        s = 1 + 0.06 * math.sin(lt * 10)
        c.save()
        c.translate(540, 1140)
        c.scale(s, s)
        glow_text(c, "¿CONVIENE?", 0, 0, 110, MAG, MAG)
        c.restore()


def esc_phone(c, t, lt, d):
    k = R.ease_out(lt / 0.4)
    x0, y0, w, h = 190, 250 + (1 - k) * 600, 700, 1080
    R.rrect(c, x0 - 14, y0 - 14, w + 28, h + 28, 70)
    c.set_source_rgba(*R.hx("1B2340"))
    c.fill_preserve()
    c.set_source_rgba(*CYAN[:3], 0.8)
    c.set_line_width(4)
    c.stroke()
    R.rrect(c, x0, y0, w, h, 58)
    c.set_source_rgba(*R.hx("0D1226"))
    c.fill()
    R.rrect(c, x0 + w / 2 - 80, y0 + 20, 160, 34, 17)
    c.set_source_rgba(0, 0, 0, 1)
    c.fill()
    glow_text(c, "Asistente IA", 540, y0 + 115, 40, WHITE, None, R.F_XBOLD)
    c.arc(540 - 150, y0 + 101, 12, 0, 2 * math.pi)
    c.set_source_rgba(*LIME)
    c.fill()
    # burbuja de prompt que se escribe
    n = int(len(PROMPT) * R.clamp((lt - 0.5) / (d * 0.75)))
    txt = PROMPT[:n] + ("▌" if int(t * 3) % 2 == 0 else "")
    R.font(c, 34, R.F_SEMI)
    lines, cur = [], ""
    for wd in txt.split(" "):
        test = (cur + " " + wd).strip()
        if R.tw(c, test) > w - 130:
            lines.append(cur)
            cur = wd
        else:
            cur = test
    lines.append(cur)
    bh = 50 + 46 * len(lines)
    R.rrect(c, x0 + 40, y0 + 170, w - 80, bh, 30)
    g = cairo.LinearGradient(x0, 0, x0 + w, 0)
    g.add_color_stop_rgba(0, *R.hx("0E6F86"))
    g.add_color_stop_rgba(1, *R.hx("6A1E5C"))
    c.set_source(g)
    c.fill()
    c.set_source_rgba(*WHITE)
    for i, ln in enumerate(lines):
        c.move_to(x0 + 70, y0 + 225 + i * 46)
        c.show_text(ln)
    # puntos de "pensando"
    if n >= len(PROMPT):
        for i in range(3):
            a = 0.3 + 0.7 * abs(math.sin(t * 5 + i))
            c.arc(x0 + 90 + i * 34, y0 + 220 + bh + 40, 10, 0, 2 * math.pi)
            c.set_source_rgba(*CYAN[:3], a)
            c.fill()


def esc_bruta(c, t, lt, d, fase2=False):
    panel(c, 70, 300, 940, 760)
    glow_text(c, "RENTABILIDAD BRUTA", 540, 390, 46, CYAN, None, R.F_XBOLD)
    pasos = [(0.4, "S/ 1,800  ×  12", WHITE), (2.2, "=  S/ 21,600 al año", LIME), (4.4, "÷  S/ 350,000", WHITE)]
    for i, (st, s, col) in enumerate(pasos):
        if lt >= st or fase2:
            kk = 1 if fase2 else R.ease_out_back((lt - st) / 0.3)
            c.save()
            c.translate(540, 500 + i * 110)
            c.scale(kk, kk)
            glow_text(c, s, 0, 0, 74, col)
            c.restore()
    if lt >= 5.6 or fase2:
        kk = 1 if fase2 else R.ease_out_back((lt - 5.6) / 0.35)
        c.save()
        c.translate(540, 930)
        c.scale(kk, kk)
        glow_text(c, "6.2%", 0, 40, 190, LIME, LIME)
        c.restore()
    if fase2:
        # sello "¿y los gastos?"
        k = R.ease_out_back(lt / 0.3)
        c.save()
        c.translate(780, 1160)
        c.rotate(-0.12)
        c.scale(k, k)
        R.rrect(c, -230, -60, 460, 110, 24)
        c.set_source_rgba(*MAG)
        c.fill()
        glow_text(c, "¿Y LOS GASTOS?", 0, 18, 52, WHITE)
        c.restore()


def esc_gastos(c, t, lt, d):
    panel(c, 70, 260, 940, 900, MAG)
    glow_text(c, "GASTOS REALES AL AÑO", 540, 350, 46, MAG, None, R.F_XBOLD)
    base = 21600
    restado = 0
    for i, (nom, v) in enumerate(GASTOS):
        st = 0.5 + i * (d - 1.2) / 4
        if lt < st:
            continue
        kk = R.ease_out(R.clamp((lt - st) / 0.3))
        y = 450 + i * 105
        c.save()
        c.translate((1 - kk) * 200, 0)
        R.font(c, 38, R.F_XBOLD)
        c.set_source_rgba(*WHITE[:3], kk)
        c.move_to(120, y)
        c.show_text(nom)
        R.font(c, 44)
        s = f"- S/ {v:,}"
        c.set_source_rgba(*MAG[:3], kk)
        c.move_to(960 - R.tw(c, s), y)
        c.show_text(s)
        c.restore()
        restado += v * kk
    # barra que se encoge
    actual = base - restado
    bw = 840 * actual / base
    R.rrect(c, 120, 900, 840, 80, 40)
    c.set_source_rgba(1, 1, 1, 0.08)
    c.fill()
    R.rrect(c, 120, 900, max(bw, 80), 80, 40)
    g = cairo.LinearGradient(120, 0, 960, 0)
    g.add_color_stop_rgba(0, *LIME)
    g.add_color_stop_rgba(1, *CYAN)
    c.set_source(g)
    c.fill()
    glow_text(c, f"S/ {int(round(actual)):,}", 540, 1080, 80, WHITE, CYAN)


def medidor(c, cx, cy, r, val, maxv, col, lbl):
    c.new_path()
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_line_width(34)
    c.set_source_rgba(1, 1, 1, 0.1)
    c.arc(cx, cy, r, math.pi, 2 * math.pi)
    c.stroke()
    c.set_source_rgba(*col)
    c.new_path()
    c.arc(cx, cy, r, math.pi, math.pi + math.pi * max(0.01, min(1, val / maxv)))
    c.stroke()
    c.new_path()
    glow_text(c, f"{val:.1f}%", cx, cy - 20, 110, WHITE, col)
    glow_text(c, lbl, cx, cy + 60, 40, col, None, R.F_XBOLD)


def esc_neta(c, t, lt, d):
    panel(c, 70, 300, 940, 860, LIME)
    k = R.ease_out(R.clamp((lt - 0.3) / 1.6))
    glow_text(c, "S/ 16,520 al año", 540, 420, 70, WHITE, LIME)
    medidor(c, 330, 860, 200, 6.2, 10, DIM, "BRUTA")
    medidor(c, 750, 860, 200, 6.2 - 1.5 * k, 10, LIME, "NETA")


def esc_veredicto(c, t, lt, d):
    panel(c, 70, 300, 940, 860)
    glow_text(c, "TU DEPA RINDE vs TU CRÉDITO", 540, 390, 44, CYAN, None, R.F_XBOLD)
    k = R.ease_out(R.clamp((lt - 0.4) / 1.2))
    k2 = R.ease_out(R.clamp((lt - 1.4) / 1.2))
    for i, (lbl, v, col, kk) in enumerate((("Rentabilidad neta", 4.7, LIME, k),
                                           ("Crédito hipotecario (ej.)", 9.0, MAG, k2))):
        y = 520 + i * 230
        R.font(c, 40, R.F_XBOLD)
        c.set_source_rgba(*WHITE)
        c.move_to(120, y)
        c.show_text(lbl)
        R.rrect(c, 120, y + 30, 840 * (v / 10) * kk + 1, 90, 45)
        c.set_source_rgba(*col)
        c.fill()
        glow_text(c, f"{v * kk:.1f}%", 120 + 840 * (v / 10) * kk - 100 if kk > 0.3 else 220, y + 95, 56, BG1)
    if lt > 3.0:
        kk = R.ease_out_back((lt - 3.0) / 0.3)
        c.save()
        c.translate(540, 1050)
        c.scale(kk, kk)
        glow_text(c, "EL ALQUILER NO LO PAGA SOLO", 0, 0, 52, WHITE, MAG)
        c.restore()


def esc_cta(c, t, lt, d):
    infinito(c, 540, 470, 4.0, t)
    glow_text(c, "IA SIN LÍMITES", 540, 700, 96, WHITE, CYAN)
    glow_text(c, "Comenta NÚMEROS y te paso el prompt", 540, 790, 40, LIME, None, R.F_XBOLD)
    botones(c, t, lt)


def botones(c, t, lt):
    taps = (1.0, 1.8, 2.6)
    on = [lt > tp for tp in taps]
    y = 960
    specs = [("LIKE", 120, R.hx("2B6BE0")), ("ME GUSTA", 400, R.hx("3A1F2B")), ("SÍGUEME", 680, R.hx("D3123E"))]
    for i, (lbl, x, col) in enumerate(specs):
        kk = R.ease_out_back(R.clamp((lt - 0.2 - i * 0.12) / 0.3))
        if kk <= 0:
            continue
        c.save()
        c.translate(x + 140, y + 55)
        c.scale(kk, kk)
        R.rrect(c, -140, -55, 280, 110, 55)
        c.set_source_rgba(*(col if on[i] else R.hx("1E2748")))
        c.fill_preserve()
        c.set_source_rgba(*CYAN[:3], 0.7)
        c.set_line_width(3)
        c.stroke()
        if i == 0:
            R.draw_thumb_icon(c, -80, 0, 1.1, WHITE)
            glow_text(c, "LIKE", 30, 18, 42, WHITE)
        elif i == 1:
            R.draw_heart(c, -70, 4, 1.05, R.RED if on[1] else R.hx("1E2748"), None if on[1] else WHITE)
            glow_text(c, "¡GRACIAS!" if on[1] else "ME GUSTA", 40, 14, 28, WHITE)
        else:
            R.draw_user_plus(c, -85, 2, 1.0, WHITE)
            glow_text(c, "SIGUIENDO" if on[2] else "SÍGUEME", 30, 14, 34, WHITE)
        c.restore()
    # mano
    pos = (540, 1250)
    targets = [(260, 1010), (540, 1010), (820, 1010)]
    press = 0
    for i, tp in enumerate(taps):
        if lt >= tp - 0.4:
            prev = targets[i - 1] if i else (540, 1250)
            m = R.ease_out((lt - (tp - 0.4)) / 0.35)
            pos = (prev[0] + (targets[i][0] - prev[0]) * m, prev[1] + (targets[i][1] - prev[1]) * m)
            press = max(0, 1 - abs(lt - tp) / 0.12)
    R.draw_hand(c, pos[0], pos[1], press)


ESCENAS = {"hook": esc_hook, "phone": esc_phone, "bruta": esc_bruta,
           "bruta2": lambda c, t, lt, d: esc_bruta(c, t, lt, d, True),
           "gastos": esc_gastos, "neta": esc_neta, "veredicto": esc_veredicto, "cta": esc_cta}


# ----------------------------------------------------------------- subtítulos
def subtitulos(c, texto, lt, habla, who):
    words = R.parse_words(texto)
    size = 58
    lines, sp = R.layout_words(c, words, 940, size)
    while len(lines) > 2 and size > 44:
        size -= 4
        lines, sp = R.layout_words(c, words, 940, size)
    total = sum(len(l) for l in lines)
    cur = min(total - 1, int(R.clamp((lt - 0.12) / max(habla, 0.5)) * total))
    y0 = 1430
    # etiqueta de quién habla
    lbl, col = ("NARRADOR", CYAN) if who == "narrador" else ("IA", MAG)
    R.font(c, 28)
    w = R.tw(c, lbl) + 40
    R.rrect(c, 540 - w / 2, y0 - 80, w, 46, 23)
    c.set_source_rgba(*col)
    c.fill()
    glow_text(c, lbl, 540, y0 - 47, 28, BG1)
    n = 0
    for i, line in enumerate(lines):
        R.font(c, size)
        lw = sum(x[2] for x in line) + sp * (len(line) - 1)
        x = 540 - lw / 2
        y = y0 + i * size * 1.25
        for wd, hl, ww in line:
            col_t = (R.hx("FFE14D") if n == cur else (LIME if hl else WHITE))
            c.move_to(x, y)
            c.text_path(wd)
            c.set_source_rgba(0, 0, 0, 0.8)
            c.set_line_width(8)
            c.stroke()
            c.move_to(x, y)
            c.set_source_rgba(*col_t)
            c.show_text(wd)
            x += ww + sp
            n += 1


# ----------------------------------------------------------------- audio
def audio(lineas, total, path):
    n = int(total * SR) + SR
    voz = np.zeros(n)
    sfx = np.zeros(n)
    music = np.zeros(n)
    rng = np.random.default_rng(3)
    for (a, b, who, vis, txt, x) in lineas:
        i0 = int((a + 0.12) * SR)
        m = min(len(x), n - i0)
        voz[i0:i0 + m] += x[:m] / (np.abs(x).max() + 1e-9)
        L = int(0.25 * SR)
        tt = np.arange(L) / SR
        sw = np.sin(2 * np.pi * np.cumsum(300 + 2500 * tt / 0.25) / SR) * np.exp(-tt * 12)
        nz = np.convolve(rng.standard_normal(L), np.ones(30) / 30, "same") * 4 * np.sin(np.pi * tt / 0.25)
        sfx[int(a * SR):int(a * SR) + L] += 0.12 * sw + 0.25 * nz
    # música electrónica suave: pad + pulso
    tt = np.arange(n) / SR
    bpm = 100
    beat = 60 / bpm
    chords = [(220.0, 261.6, 329.6), (174.6, 220.0, 261.6), (196.0, 246.9, 293.7), (164.8, 196.0, 246.9)]
    for b in range(int(total / beat) + 1):
        st = b * beat
        ch = chords[(b // 4) % 4]
        i0 = int(st * SR)
        L = min(int(beat * SR), n - i0)
        x = np.arange(L) / SR
        env = np.exp(-x * 2.5)
        for f in ch:
            music[i0:i0 + L] += 0.05 * env * np.sin(2 * np.pi * f * x) * (1 + 0.3 * np.sin(2 * np.pi * 5 * x))
        music[i0:i0 + L] += 0.12 * np.sin(2 * np.pi * ch[0] / 4 * x) * np.exp(-x * 6)
        k = min(int(0.2 * SR), n - i0)
        xk = np.arange(k) / SR
        music[i0:i0 + k] += 0.35 * np.sin(2 * np.pi * np.cumsum(110 * np.exp(-xk * 20) + 40) / SR) * np.exp(-xk * 15)
        for h in (0.5,):
            j0 = int((st + h * beat) * SR)
            kk = min(int(0.03 * SR), n - j0)
            if kk > 0:
                music[j0:j0 + kk] += 0.05 * np.diff(np.concatenate([[0], rng.standard_normal(kk)]))
    env = np.convolve(np.abs(voz), np.ones(4800) / 4800, "same")
    duck = 1 - 0.6 * np.clip(env * 12, 0, 1)
    mix = music * 0.6 * duck + sfx * 0.5 + voz
    # clics finales
    o = total - OUTRO
    for tp in (1.0, 1.8, 2.6):
        L = int(0.3 * SR)
        x = np.arange(L) / SR
        i0 = int((o + tp) * SR)
        mix[i0:i0 + L] += 0.3 * np.sin(2 * np.pi * 1500 * x) * np.exp(-x * 14)
    mix = mix[:int(total * SR)]
    f = int(0.5 * SR)
    mix[-f:] *= np.linspace(1, 0, f)
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.9
    pcm = (np.stack([mix, mix], 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ----------------------------------------------------------------- main
def main():
    out = sys.argv[1]
    lineas = []
    t = 0.0
    for i, (who, vis, txt, voz) in enumerate(GUION):
        x = R.tts_line(who, voz, f"/tmp/ia_{i}.wav", 0.95)
        d = len(x) / SR
        lineas.append([t, t + d + 0.12 + PAUSA, who, vis, txt, x])
        t += d + 0.12 + PAUSA
    lineas[-1][1] += OUTRO
    total = lineas[-1][1]
    print(f"Duración: {total:.2f} s")
    audio(lineas, total, "/tmp/ia_audio.wav")
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(s)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-i", "/tmp/ia_audio.wav", "-c:v", "libx264", "-preset", "medium",
                          "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
                          "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    frames = int(total * FPS)
    preview = "--preview" in sys.argv
    for fi in range(frames):
        tt = fi / FPS
        fondo(c, tt)
        for (a, b, who, vis, txt, x) in lineas:
            if a <= tt < b:
                lt, d = tt - a, b - a
                habla = len(x) / SR
                c.save()
                if lt < 0.2:  # zoom de entrada en cada escena
                    z = 1.04 - 0.04 * R.ease_out(lt / 0.2)
                    c.translate(540, 760)
                    c.scale(z, z)
                    c.translate(-540, -760)
                ESCENAS[vis](c, tt, lt, d)
                c.restore()
                if lt < habla + 0.3:
                    subtitulos(c, txt, lt, habla, who)
                if lt < 0.12 and a > 0:
                    c.set_source_rgba(1, 1, 1, 0.35 * (1 - lt / 0.12))
                    c.paint()
        marca(c, tt, total)
        s.flush()
        if preview and fi % 45 == 0:
            s.write_to_png(f"/tmp/ia_prev_{fi:04d}.png")
        p.stdin.write(bytes(s.get_data()))
    p.stdin.close()
    p.wait()
    print("Listo:", out)


if __name__ == "__main__":
    main()
