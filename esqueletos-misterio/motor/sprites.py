"""Personajes a partir de las imágenes modelo (esqueleto 3D neón): animación 2.5D.

Cada personaje se separa en cuerpo + brazo que saluda. El cuerpo tiene variantes
precalculadas de boca (4 aperturas), parpadeo (2) y latido del corazón (3).
"""
import json
import math
import os

import cairo
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../modelos")


def to_surface(im):
    a = np.asarray(im.convert("RGBA"), dtype=np.float32)
    al = a[..., 3:4] / 255.0
    bgra = np.empty_like(a)
    bgra[..., 0] = a[..., 2] * al[..., 0]
    bgra[..., 1] = a[..., 1] * al[..., 0]
    bgra[..., 2] = a[..., 0] * al[..., 0]
    bgra[..., 3] = a[..., 3]
    buf = np.ascontiguousarray(bgra.astype(np.uint8))
    h, w = buf.shape[:2]
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    stride = surf.get_stride()
    data = np.ndarray((h, stride // 4, 4), dtype=np.uint8, buffer=surf.get_data())
    data[:, :w, :] = buf
    surf.mark_dirty()
    return surf


class Personaje:
    def __init__(self, tipo, escala=0.52):
        cfg = json.load(open(os.path.join(BASE, "personajes.json")))[tipo]
        self.cfg = cfg
        s = escala
        x0, y0, x1, y1 = cfg["crop"]
        im = Image.open(os.path.join(BASE, cfg["png"])).convert("RGBA").crop((x0, y0, x1, y1))
        W, H = int((x1 - x0) * s), int((y1 - y0) * s)
        im = im.resize((W, H), Image.LANCZOS)
        # desvanecido inferior (cuerpo cortado a la cadera)
        a = np.asarray(im, dtype=np.float32).copy()
        fade = int(H * 0.16)
        ramp = np.linspace(1, 0, fade) ** 1.3
        a[H - fade:, :, 3] *= ramp[:, None]
        im = Image.fromarray(a.astype(np.uint8), "RGBA")
        P = lambda p: ((p[0] - x0) * s, (p[1] - y0) * s)  # noqa: E731
        self.W, self.H = W, H
        self.ojos = [P(o) for o in cfg["ojos"]]
        self.r_ojo = cfg["r_ojo"] * s
        b = cfg["boca"]
        self.boca = (P((b["x"], b["y"])), b["ancho"] * s, (b["menton"] - b["y"]) * s)
        hc = cfg["corazon"]
        self.corazon = (*P(hc[:2]), hc[2] * s)
        self.hombro = P(cfg["hombro"])
        # máscara del brazo
        mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mask).polygon([P(p) for p in cfg["brazo"]], fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(2))
        arm = im.copy()
        arm.putalpha(Image.fromarray((np.asarray(im.getchannel("A"), np.float32) *
                                      np.asarray(mask, np.float32) / 255).astype(np.uint8)))
        body = im.copy()
        body.putalpha(Image.fromarray((np.asarray(im.getchannel("A"), np.float32) *
                                       (1 - np.asarray(mask, np.float32) / 255)).astype(np.uint8)))
        self.arm = to_surface(arm)
        lid_col = Image.open(os.path.join(BASE, cfg["png"])).convert("RGB").getpixel(tuple(cfg["parpado_muestra"]))
        self.variantes = {}
        for m in range(4):
            bm = self._boca(body, m * 4.5 * s / 0.52)
            for hb in range(3):
                bh = self._corazon(bm, 1 + 0.045 * hb)
                for bl in range(2):
                    bb = self._parpado(bh, lid_col, cfg.get("pestanas", False)) if bl else bh
                    self.variantes[(m, hb, bl)] = to_surface(bb)

    def _boca(self, im, k):
        if k <= 0:
            return im
        (mx, my), ancho, menton = self.boca
        a = np.asarray(im).copy()
        src = a.copy()
        x0, x1 = int(mx - ancho / 2), int(mx + ancho / 2)
        y_end = int(my + menton + k + 2)
        for x in range(max(0, x0), min(self.W, x1)):
            f = math.cos((x - mx) / (ancho / 2) * math.pi / 2)
            off = k * max(0.0, f) ** 0.8
            if off < 0.5:
                continue
            gap_end = my + off
            for y in range(int(my), min(self.H, y_end)):
                if y < gap_end:
                    t = (y - my) / max(off, 1)
                    if self.cfg["boca"].get("dientes") and t < 0.32:
                        col = (240, 234, 240)
                    else:
                        col = (58, 13, 31) if t < 0.65 else (190, 70, 95)
                    a[y, x, :3] = col
                    a[y, x, 3] = 255
                else:
                    sy = int(round(y - off))
                    a[y, x] = src[sy, x]
        return Image.fromarray(a, "RGBA")

    def _corazon(self, im, k):
        if abs(k - 1) < 1e-3:
            return im
        cx, cy, r = self.corazon
        box = (int(cx - r), int(cy - r), int(cx + r), int(cy + r))
        reg = im.crop(box)
        big = reg.resize((int(reg.width * k), int(reg.height * k)), Image.LANCZOS)
        m = Image.new("L", big.size, 0)
        ImageDraw.Draw(m).ellipse((big.width * 0.12, big.height * 0.12, big.width * 0.88, big.height * 0.88), fill=255)
        m = m.filter(ImageFilter.GaussianBlur(big.width * 0.06))
        out = im.copy()
        ox, oy = int(cx - big.width / 2), int(cy - big.height / 2)
        out.paste(big, (ox, oy), m)
        return out

    def _parpado(self, im, col, pest):
        out = im.copy()
        d = ImageDraw.Draw(out)
        r = self.r_ojo
        for (ex, ey) in self.ojos:
            d.ellipse((ex - r * 1.08, ey - r * 1.08, ex + r * 1.08, ey + r * 1.04), fill=col + (255,))
            d.arc((ex - r * 0.95, ey - r * 0.55, ex + r * 0.95, ey + r * 0.45), 15, 165,
                  fill=(20, 10, 25, 255), width=max(3, int(r * 0.12)))
            if pest:
                for k in range(5):
                    a = math.radians(25 + k * 32)
                    px, py = ex + math.cos(a) * r * 0.95, ey + math.sin(a) * r * 0.45
                    d.line((px, py, px + math.cos(a) * r * 0.28, py + math.sin(a) * r * 0.32),
                           fill=(20, 10, 25, 255), width=max(2, int(r * 0.07)))
        return out

    def draw(self, c, x_centro, y_base, st, t, mirror=False, dim=0.0, talk=0.0, brazo_extra=0.0):
        """x_centro: centro horizontal del cuerpo; y_base: borde inferior."""
        ph = st.get("phase", 0.0)
        scared = st.get("scared", False)
        bob = 7 * math.sin(t * 2.0 + ph) - 5 * talk
        sway = 0.018 * math.sin(t * 1.3 + ph)
        shake = (6 * math.sin(t * 61), 3 * math.cos(t * 47)) if scared else (0, 0)
        breath = 1 + 0.008 * math.sin(t * 2.4 + ph)
        bx = self.boca[0][0]
        c.save()
        c.translate(x_centro + shake[0], y_base + bob + shake[1])
        c.rotate(sway)
        if mirror:
            c.scale(-1, 1)
        c.scale(1, breath)
        c.translate(-bx, -self.H)
        # latido
        rate = st.get("bpm", 75) / 60.0
        p = (t * rate + ph) % 1.0
        beat = max(0.0, 1 - abs(p - 0.08) / 0.08) + 0.6 * max(0.0, 1 - abs(p - 0.26) / 0.07)
        hb = 2 if beat > 0.7 else (1 if beat > 0.25 else 0)
        blink = 1 if (t + ph * 1.7) % 3.4 < 0.13 else 0
        if talk > 0:
            m = int(round(talk * 3))
        else:
            m = 2 if scared else 0
        surf = self.variantes[(max(0, min(3, m)), hb, blink)]
        # halo del corazón
        cx, cy, r = self.corazon
        g = cairo.RadialGradient(cx, cy, 2, cx, cy, r * 2.0)
        g.add_color_stop_rgba(0, 1, 0.25, 0.3, 0.45 * (0.3 + beat))
        g.add_color_stop_rgba(1, 1, 0.25, 0.3, 0)
        c.set_source_surface(surf, 0, 0)
        c.paint()
        if dim > 0:
            c.set_source_rgba(0.02, 0.01, 0.06, dim)
            c.mask_surface(surf, 0, 0)
        c.set_source(g)
        c.arc(cx, cy, r * 2.0, 0, 2 * math.pi)
        c.fill()
        # brazo que saluda
        pose = st.get("pose", "idle")
        amp, base = (0.16, 0.0) if pose in ("up", "wave") else ((0.0, 0.42) if pose == "point" else (0.05, 0.0))
        if scared:
            amp, base = 0.03, 0.12
        ang = base + brazo_extra + amp * math.sin(t * 6.5 + ph)
        hx, hy = self.hombro
        c.save()
        c.translate(hx, hy)
        c.rotate(ang)
        c.translate(-hx, -hy)
        c.set_source_surface(self.arm, 0, 0)
        c.paint()
        if dim > 0:
            c.set_source_rgba(0.02, 0.01, 0.06, dim)
            c.mask_surface(self.arm, 0, 0)
        c.restore()
        c.restore()
