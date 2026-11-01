"""Miniatura vertical genérica: python3 miniatura_gen.py config.json salida.jpg"""
import json, math, sys
import cairo
import render as R
from PIL import Image

cfg = json.load(open(sys.argv[1], encoding="utf-8"))
s = cairo.ImageSurface(cairo.FORMAT_ARGB32, R.W, R.H)
c = cairo.Context(s)
R.draw_sunburst(c, 0.3, R.hx(cfg.get("fondo1", "FFF4C9")), R.hx(cfg.get("fondo2", "FFE27A")))
prog = cfg.get("programa", ["NOTICIAS", "STICKMAN"])
c.save(); c.translate(540, 190)
R.rrect(c, -300, -62, 600, 124, 32); R.fill_stroke(c, R.NAVY, R.TEAL, 8)
R.text_center(c, prog[0], 0, -4, 54, R.WHITE); R.text_center(c, prog[1], 0, 46, 46, R.TEAL)
c.restore()
c.save(); c.translate(540, 320)
R.font(c, 36); w = R.tw(c, cfg["banda"]) + 60
R.rrect(c, -w / 2, -34, w, 68, 34); c.set_source_rgba(*R.RED); c.fill()
R.text_center(c, cfg["banda"], 0, 13, 36, R.WHITE); c.restore()
c.save(); c.translate(540, 520); c.rotate(-0.04)
for i, (ln, sz) in enumerate(zip(cfg["titulo"], (120, 150))):
    R.font(c, sz)
    while R.tw(c, ln) > 1000:
        sz -= 6; R.font(c, sz)
    R.text_center(c, ln, 0, i * 150, sz, R.PINK if i else R.NAVY, outline=R.WHITE, ow=22)
c.restore()
elenco = cfg.get("elenco", ["chato", "paco", "lucha"])
for w_, x in zip(elenco, (200, 540, 880)):
    R.CAST[w_]["x"] = x
R.LOCUTOR = cfg.get("locutor", "paco")
c.save(); c.translate(0, -20)
heads = {}
for w_ in elenco:
    c.new_path()
    st = cfg["estados"].get(w_, {"pose": "rest", "expr": "happy"})
    if w_ == "maskaly":
        pass
    heads[w_] = R.draw_character(c, w_, 1.0, st)
for f in cfg.get("fx", []):
    n, who = f.split(":"); c.new_path()
    R.FX[n](c, R.CAST[who]["x"], heads[who], 1.0, 0.6)
c.restore(); c.new_path()
b = cfg["sello"]
c.save(); c.translate(b.get("x", 860), b.get("y", 1450)); c.rotate(0.18)
c.arc(0, 0, 140, 0, 2 * math.pi); R.fill_stroke(c, R.TEAL, R.INK, 10)
sz = b.get("size", 110)
R.font(c, sz)
while R.tw(c, b["texto"]) > 240:
    sz -= 6; R.font(c, sz)
R.text_center(c, b["texto"], 0, sz * 0.35, sz, R.WHITE, outline=R.INK, ow=10)
c.restore(); c.new_path()
R.rrect(c, 60, 1700, 960, 150, 40); R.fill_stroke(c, R.NAVY, R.TEAL, 8)
sz = 80; R.font(c, sz)
while R.tw(c, cfg["franja"]) > 900:
    sz -= 4; R.font(c, sz)
R.text_center(c, cfg["franja"], 540, 1800, sz, R.YELLOW)
s.write_to_png("/tmp/mini.png")
Image.open("/tmp/mini.png").convert("RGB").save(sys.argv[2], quality=92)
