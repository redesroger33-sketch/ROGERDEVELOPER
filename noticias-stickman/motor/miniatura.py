"""Miniatura vertical 1080x1920 para Noticias Stickman (episodio 01 NOV 2026)."""
import math
import sys
import cairo
import render as R
from PIL import Image

out = sys.argv[1]
s = cairo.ImageSurface(cairo.FORMAT_ARGB32, R.W, R.H)
c = cairo.Context(s)
R.draw_sunburst(c, 0.3, R.hx("FFF4C9"), R.hx("FFE27A"))
c.save(); c.translate(540, 190)
R.rrect(c, -300, -62, 600, 124, 32); R.fill_stroke(c, R.NAVY, R.TEAL, 8)
R.text_center(c, "NOTICIAS", 0, -4, 54, R.WHITE); R.text_center(c, "STICKMAN", 0, 46, 46, R.TEAL)
c.restore()
c.save(); c.translate(540, 320); R.rrect(c, -250, -34, 500, 68, 34); c.set_source_rgba(*R.RED); c.fill()
R.text_center(c, "FERIADO 1 DE NOVIEMBRE", 0, 13, 36, R.WHITE); c.restore()
c.save(); c.translate(540, 520); c.rotate(-0.04)
R.text_center(c, "¿TE PAGAN", 0, 0, 130, R.NAVY, outline=R.WHITE, ow=22)
R.text_center(c, "TRIPLE?", 0, 150, 190, R.PINK, outline=R.WHITE, ow=24)
c.restore()
R.CAST["chato"]["x"], R.CAST["paco"]["x"], R.CAST["lucha"]["x"] = 200, 540, 880
c.save(); c.translate(0, -20)
c.new_path(); R.draw_character(c, "paco", 1.0, {"pose": "rest", "expr": "laugh"})
c.new_path(); R.draw_character(c, "lucha", 1.0, {"pose": "up", "expr": "happy"})
c.new_path(); hy = R.draw_character(c, "chato", 1.0, {"pose": "up", "expr": "alert"})
c.new_path(); R.fx_alert(c, 200, hy, 1.0, 0.5)
c.new_path(); R.fx_money(c, 200, hy, 1.0, 1.3)
c.restore()
c.new_path()
c.save(); c.translate(860, 1450); c.rotate(0.18)
c.arc(0, 0, 140, 0, 2 * math.pi); R.fill_stroke(c, R.TEAL, R.INK, 10)
R.text_center(c, "x3", 0, 52, 160, R.WHITE, outline=R.INK, ow=12)
c.restore()
c.new_path()
R.rrect(c, 60, 1700, 960, 150, 40); R.fill_stroke(c, R.NAVY, R.TEAL, 8)
R.text_center(c, "S/ 60  →  S/ 180", 540, 1800, 88, R.YELLOW)
s.write_to_png("/tmp/mini.png")
Image.open("/tmp/mini.png").convert("RGB").save(out, quality=92)
