"""CINE — escenarios cinematográficos por capas para ESQUELETOS DEL MISTERIO.

Cada escena tiene: fondo estático grande (se construye una vez, con niebla,
perspectiva atmosférica y luz), una capa dinámica (partículas, meteoros, ondas)
y un primer plano (rocas, troncos, nieve, barandas) que tapa a los personajes
para que parezcan DENTRO del paisaje. La cámara se mueve como en cine:
dolly, grúa, paneo, giro; y los planos cambian cada 3-4 s con transiciones.
"""
import math
import random

import cairo
import numpy as np
from PIL import Image, ImageFilter

W, H = 1080, 1920
BW, BH = 1400, 2300          # lienzo del fondo (margen para mover la cámara)


def hx(s, a=1.0):
    s = s.lstrip("#")
    return (int(s[0:2], 16) / 255, int(s[2:4], 16) / 255, int(s[4:6], 16) / 255, a)


def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def smooth(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return tuple(lerp(a, b, t) for a, b in zip(c1, c2))


# ---------------------------------------------------------------- utilidades de imagen
def surf_to_pil(s):
    w, h = s.get_width(), s.get_height()
    a = np.ndarray((h, s.get_stride() // 4, 4), np.uint8, s.get_data())[:, :w]
    return Image.fromarray(a[..., [2, 1, 0, 3]].copy(), "RGBA")


def pil_to_surf(im):
    a = np.asarray(im.convert("RGBA"))
    w, h = im.size
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    d = np.ndarray((h, s.get_stride() // 4, 4), np.uint8, s.get_data())
    d[:, :w] = a[..., [2, 1, 0, 3]]
    s.mark_dirty()
    return s


def blurred(s, r):
    return pil_to_surf(surf_to_pil(s).filter(ImageFilter.GaussianBlur(r)))


def new_layer(w=BW, h=BH):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    return s, cairo.Context(s)


def paint_blur(c, draw_fn, r, w=BW, h=BH):
    """Dibuja algo en una capa aparte, la desenfoca y la pega (niebla, brillos)."""
    s, cc = new_layer(w, h)
    draw_fn(cc)
    c.set_source_surface(blurred(s, r), 0, 0)
    c.paint()


def vgrad(c, y0, y1, stops, x0=0, x1=BW):
    g = cairo.LinearGradient(0, y0, 0, y1)
    for p, col in stops:
        g.add_color_stop_rgba(p, *col)
    c.set_source(g)
    c.rectangle(x0, y0, x1 - x0, y1 - y0)
    c.fill()


def ridge(rnd, y, amp, rough=0.55, n=7, x0=-50, x1=BW + 50):
    pts = [y + rnd.uniform(-amp, amp), y + rnd.uniform(-amp, amp)]
    a = amp
    for _ in range(n):
        new = []
        for i in range(len(pts) - 1):
            new += [pts[i], (pts[i] + pts[i + 1]) / 2 + rnd.uniform(-a, a)]
        new.append(pts[-1])
        pts = new
        a *= rough
    xs = np.linspace(x0, x1, len(pts))
    return list(zip(xs, pts))


def fill_ridge(c, pts, bottom, col):
    c.move_to(pts[0][0], bottom)
    for p in pts:
        c.line_to(*p)
    c.line_to(pts[-1][0], bottom)
    c.close_path()
    if isinstance(col, cairo.Pattern):
        c.set_source(col)
    else:
        c.set_source_rgba(*col)
    c.fill()


def pine(c, x, y, h, col, rnd=None, lean=0.0, snow=None):
    """Pino de taiga: tronco + pisos dentados."""
    rnd = rnd or random.Random(int(x * 7 + y))
    c.save()
    c.translate(x, y)
    c.rotate(lean)
    w = h * 0.22
    c.set_source_rgba(*col)
    c.rectangle(-h * 0.012, -h * 0.25, h * 0.024, h * 0.25)
    c.fill()
    tiers = 7
    for i in range(tiers):
        f = i / tiers
        ty = -h * (0.18 + f * 0.82)
        tw = w * (1 - f * 0.85) * rnd.uniform(0.85, 1.15)
        th = h * 0.2
        c.move_to(0, ty - th)
        steps = 5
        for k in range(steps + 1):
            u = k / steps
            c.line_to(tw * u, ty - th * (1 - u) + (h * 0.02 if k % 2 else 0))
        for k in range(steps, -1, -1):
            u = k / steps
            c.line_to(-tw * u, ty - th * (1 - u) + (h * 0.02 if k % 2 else 0))
        c.close_path()
        c.set_source_rgba(*col)
        c.fill()
        if snow:
            c.set_source_rgba(*snow)
            c.move_to(-tw * 0.7, ty - th * 0.25)
            c.curve_to(-tw * 0.2, ty - th * 0.45, tw * 0.2, ty - th * 0.45, tw * 0.7, ty - th * 0.25)
            c.line_to(tw * 0.5, ty - th * 0.18)
            c.curve_to(0, ty - th * 0.32, 0, ty - th * 0.32, -tw * 0.5, ty - th * 0.18)
            c.fill()
    c.restore()


def forest_on(c, pts, rnd, hmin, hmax, col, dens=1.0, snow=None, lean=0.0, fallen=0.0, cx=None):
    for (x, y) in pts[:: max(1, int(3 / dens))]:
        for _ in range(int(2 * dens)):
            xx = x + rnd.uniform(-12, 12)
            h = rnd.uniform(hmin, hmax)
            ln = lean
            if fallen > 0 and cx is not None:
                ln += math.copysign(fallen * 1.45, xx - cx)
            pine(c, xx, y + rnd.uniform(0, 14), h, col, rnd, ln, snow)


def cloud(c, x, y, w, h, top, bot, rnd, n=14):
    for _ in range(n):
        cx = x + rnd.uniform(-w / 2, w / 2)
        cy = y + rnd.uniform(-h / 2, h / 2)
        r = rnd.uniform(h * 0.35, h * 0.8)
        g = cairo.LinearGradient(0, cy - r, 0, cy + r)
        g.add_color_stop_rgba(0, *top)
        g.add_color_stop_rgba(1, *bot)
        c.set_source(g)
        c.arc(cx, cy, r, 0, 2 * math.pi)
        c.fill()


def sun_rays(c, x, y, n, length, col, rnd, spread=math.pi):
    for i in range(n):
        a = -math.pi / 2 + rnd.uniform(-spread / 2, spread / 2)
        w = rnd.uniform(0.02, 0.06)
        g = cairo.RadialGradient(x, y, 0, x, y, length)
        g.add_color_stop_rgba(0, *col)
        g.add_color_stop_rgba(1, *col[:3], 0)
        c.set_source(g)
        c.move_to(x, y)
        c.arc(x, y, length, a - w, a + w)
        c.close_path()
        c.fill()


def glow(c, x, y, r, col, a=1.0):
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(0, *col[:3], a)
    g.add_color_stop_rgba(0.35, *col[:3], a * 0.35)
    g.add_color_stop_rgba(1, *col[:3], 0)
    c.set_source(g)
    c.arc(x, y, r, 0, 2 * math.pi)
    c.fill()


def noise_tex(w, h, scale, seed, c0, c1, blur=2.0, alpha=255):
    rng = np.random.default_rng(seed)
    small = rng.random((max(2, h // scale), max(2, w // scale)))
    im = Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    n = np.asarray(im, np.float32)[..., None] / 255
    col = np.array(c0[:3]) * (1 - n) + np.array(c1[:3]) * n
    rgba = np.concatenate([col * 255, np.full((h, w, 1), alpha)], 2).astype(np.uint8)
    return pil_to_surf(Image.fromarray(rgba, "RGBA"))


# ---------------------------------------------------------------- partículas
class Particulas:
    def __init__(self, n, seed, kind):
        r = random.Random(seed)
        self.p = [(r.random(), r.random(), r.uniform(0.4, 1.0), r.random() * 6.28) for _ in range(n)]
        self.kind = kind

    def draw(self, c, t, w=W, h=H, strength=1.0, wind=0.0):
        k = self.kind
        for (x0, y0, z, ph) in self.p:
            if k == "nieve":
                x = (x0 * w + math.sin(t * 0.8 + ph) * 30 * z + wind * t * 80 * z) % (w + 40) - 20
                y = (y0 * h + t * 110 * z) % (h + 40) - 20
                r = 2.2 + 5 * z ** 2
                c.set_source_rgba(1, 1, 1, 0.55 * z * strength)
                c.arc(x, y, r, 0, 2 * math.pi)
                c.fill()
            elif k == "brasas":
                x = (x0 * w + math.sin(t * 2 + ph) * 25 + wind * t * 60) % w
                y = h - ((y0 * h + t * 160 * z) % (h + 60))
                tw = 0.5 + 0.5 * math.sin(t * 9 + ph)
                glow(c, x, y, 10 * z + 6, hx("FF8A2A"), 0.9 * tw * strength)
                c.set_source_rgba(1, 0.9, 0.5, 0.9 * tw * strength)
                c.arc(x, y, 1.8 * z + 0.8, 0, 2 * math.pi)
                c.fill()
            elif k == "polvo":
                x = (x0 * w + t * 18 * z + math.sin(t * 0.6 + ph) * 20) % w
                y = (y0 * h + math.cos(t * 0.5 + ph) * 25) % h
                tw = 0.5 + 0.5 * math.sin(t * 2 + ph)
                c.set_source_rgba(1, 0.92, 0.75, 0.35 * tw * z * strength)
                c.arc(x, y, 1.2 + 2.2 * z, 0, 2 * math.pi)
                c.fill()
            elif k == "cenizas":
                x = (x0 * w + t * 70 * z + wind * t * 90) % (w + 40) - 20
                y = (y0 * h + t * 40 * z + math.sin(t + ph) * 20) % h
                c.set_source_rgba(0.25, 0.22, 0.22, 0.6 * z * strength)
                c.save()
                c.translate(x, y)
                c.rotate(t * 2 + ph)
                c.rectangle(-3 * z, -1.5 * z, 6 * z, 3 * z)
                c.fill()
                c.restore()
            elif k == "luciernagas":
                x = x0 * w + math.sin(t * 0.7 + ph) * 40
                y = y0 * h * 0.8 + math.cos(t * 0.9 + ph) * 30
                tw = max(0.0, math.sin(t * 2.2 + ph))
                glow(c, x, y, 14 * z, hx("BFE8FF"), 0.8 * tw * strength)


# ---------------------------------------------------------------- escenas
class Escena:
    """bg: superficie BWxBH. dyn(c, t, lt, k): capa animada en coordenadas del fondo.
    fg(c, t, lt): primer plano en coordenadas de pantalla. luz: tinte para personajes."""
    agua = None          # y de la línea de agua (pantalla) para reflejos
    luz = None
    particulas = None
    sepia = False

    def dyn(self, c, t, lt, k):
        pass

    def fg(self, c, t, lt, k):
        pass


def _taiga_ridges(c, rnd, sky_hor, layers, base_y, snow=None):
    for i, (dy, amp, col, tree_h, dens) in enumerate(layers):
        pts = ridge(rnd, base_y + dy, amp)
        fill_ridge(c, pts, BH, col)
        forest_on(c, pts, rnd, tree_h * 0.7, tree_h * 1.2, col, dens, snow)
        # bruma entre capas
        def fog(cc, y=base_y + dy, colr=sky_hor):
            g = cairo.LinearGradient(0, y - 60, 0, y + 140)
            g.add_color_stop_rgba(0, *colr[:3], 0)
            g.add_color_stop_rgba(0.5, *colr[:3], 0.55 - i * 0.08)
            g.add_color_stop_rgba(1, *colr[:3], 0)
            cc.set_source(g)
            cc.rectangle(0, y - 60, BW, 200)
            cc.fill()
        paint_blur(c, fog, 18)


class TaigaAmanecer(Escena):
    """Plano aéreo: taiga siberiana al amanecer con río dorado y niebla."""
    def __init__(self):
        rnd = random.Random(1908)
        s, c = new_layer()
        vgrad(c, 0, 1250, [(0, hx("0E1838")), (0.45, hx("3A3D6E")), (0.75, hx("D98A5E")), (1, hx("FFD39A"))])
        sun = (820, 1150)
        paint_blur(c, lambda cc: sun_rays(cc, *sun, 26, 1300, hx("FFE2A8", 0.22), rnd), 6)
        glow(c, *sun, 520, hx("FFC77A"), 0.9)
        glow(c, *sun, 90, hx("FFF6DD"), 1.0)
        def clouds(cc):
            r2 = random.Random(3)
            for (x, y, w_, h_) in ((300, 520, 700, 90), (1000, 640, 600, 70), (500, 860, 900, 60), (1150, 380, 500, 80)):
                cloud(cc, x, y, w_, h_, hx("FFB98A", 0.85), hx("6A4A78", 0.8), r2)
        paint_blur(c, clouds, 28)
        layers = [(0, 40, hx("8A6F8E"), 46, 1.6), (90, 50, hx("5E4E72"), 60, 1.6), (210, 60, hx("3A3352"), 80, 1.3),
                  (380, 70, hx("221E33"), 110, 1.1)]
        # río serpenteante con reflejo del cielo
        _taiga_ridges(c, rnd, hx("F2B585"), layers[:2], 1180)
        c.move_to(-50, 2300)
        c.curve_to(300, 1900, 1100, 1700, 760, 1460)
        c.curve_to(560, 1330, 900, 1300, 840, 1250)
        c.line_to(880, 1250)
        c.curve_to(980, 1310, 650, 1360, 860, 1470)
        c.curve_to(1250, 1720, 600, 2000, 300, 2300)
        c.close_path()
        g = cairo.LinearGradient(0, 1250, 0, 2300)
        g.add_color_stop_rgba(0, *hx("FFE3B0"))
        g.add_color_stop_rgba(1, *hx("C0705A"))
        c.set_source(g)
        c.fill()
        _taiga_ridges(c, rnd, hx("D99A7A"), layers[2:3], 1180)
        # río en primer término reflejando el amanecer
        c.move_to(300, BH)
        c.curve_to(520, 2000, 980, 1800, 820, 1560)
        c.curve_to(760, 1470, 900, 1440, 860, 1400)
        c.line_to(900, 1400)
        c.curve_to(1000, 1460, 900, 1520, 980, 1600)
        c.curve_to(1180, 1850, 900, 2050, 1000, BH)
        c.close_path()
        g = cairo.LinearGradient(0, 1400, 0, BH)
        g.add_color_stop_rgba(0, *hx("FFE6B8"))
        g.add_color_stop_rgba(1, *hx("E09A6A"))
        c.set_source(g)
        c.fill()
        for side in (-1, 1):
            for i in range(9):
                x = (rnd.uniform(-80, 260) if side < 0 else rnd.uniform(1140, 1480))
                pine(c, x, BH + 40, rnd.uniform(700, 1200), hx("15111E"), rnd)
        self.bg = s
        self.birds = random.Random(5)
        self.part = Particulas(60, 2, "polvo")

    def dyn(self, c, t, lt, k):
        # bandada de aves cruzando
        for i in range(9):
            x = 200 + lt * 120 + (i % 3) * 40 + i * 18
            y = 760 + (i // 3) * 26 + math.sin(lt * 2 + i) * 6
            w = 12 + 3 * math.sin(lt * 12 + i)
            c.set_source_rgba(0.1, 0.08, 0.12, 0.8)
            c.set_line_width(3)
            c.move_to(x - 14, y - w * 0.4)
            c.curve_to(x - 7, y - w, x - 3, y - 2, x, y)
            c.curve_to(x + 3, y - 2, x + 7, y - w, x + 14, y - w * 0.4)
            c.stroke()

    def fg(self, c, t, lt, k):
        self.part.draw(c, t)


class RioTaiga(Escena):
    """Orilla del río: pinos altos, rayos de luz entre los árboles, agua espejo."""
    agua = 1560
    luz = (1.0, 0.75, 0.45, 0.35, "soft")

    def __init__(self):
        rnd = random.Random(77)
        s, c = new_layer()
        vgrad(c, 0, 1300, [(0, hx("3D4A7A")), (0.6, hx("E8A77A")), (1, hx("FFE0B0"))])
        glow(c, 700, 1000, 600, hx("FFD7A0"), 0.9)
        _taiga_ridges(c, rnd, hx("F0C090"), [(0, 30, hx("9B8296"), 50, 1.5), (110, 40, hx("6E5C78"), 80, 1.4)], 1050)
        # agua
        vgrad(c, 1420, BH, [(0, hx("F6D2A2")), (0.4, hx("8E6E80")), (1, hx("2A2638"))])
        # bosque cercano a ambos lados
        for side in (0, 1):
            for i in range(10):
                x = (rnd.uniform(-60, 380) if side == 0 else rnd.uniform(1020, 1460))
                pine(c, x, 1430 + rnd.uniform(-10, 10), rnd.uniform(500, 900), hx("1E1A28"), rnd)
        # reflejo: la parte superior volteada, desenfocada y oscurecida sobre el agua
        im = surf_to_pil(s)
        top = im.crop((0, 1420 - 880, BW, 1420)).transpose(Image.FLIP_TOP_BOTTOM).filter(ImageFilter.GaussianBlur(5))
        refl = pil_to_surf(top)
        c.save()
        c.rectangle(0, 1420, BW, 880)
        c.clip()
        c.set_source_surface(refl, 0, 1420)
        c.paint_with_alpha(0.75)
        vgrad(c, 1420, BH, [(0, hx("2A2A40", 0.15)), (1, hx("141222", 0.85))])
        for i in range(70):
            y = rnd.uniform(1425, 2200)
            c.set_source_rgba(1, 0.95, 0.85, rnd.uniform(0.05, 0.22))
            c.rectangle(rnd.uniform(0, BW), y, rnd.uniform(40, 220), 2.5)
            c.fill()
        c.restore()
        self.bg = s
        rays, rc = new_layer()
        sun_rays(rc, 700, 900, 18, 1500, hx("FFE9C2", 0.16), rnd, math.pi * 0.9)
        self.rays = blurred(rays, 8)
        self.part = Particulas(70, 4, "polvo")

    def dyn(self, c, t, lt, k):
        c.save()
        c.translate(700, 900)
        c.rotate(0.03 * math.sin(t * 0.4))
        c.translate(-700, -900)
        c.set_source_surface(self.rays, 0, 0)
        c.paint_with_alpha(0.8 + 0.2 * math.sin(t * 0.9))
        c.restore()

    def fg(self, c, t, lt, k):
        # juncos en primer plano
        r = random.Random(9)
        for i in range(46):
            x = r.uniform(-20, W + 20)
            if 200 < x < 880 and r.random() < 0.6:
                continue
            h = r.uniform(120, 300)
            sw = 10 * math.sin(t * 1.4 + i)
            c.set_source_rgba(0.08, 0.07, 0.06, 0.95)
            c.set_line_width(r.uniform(3, 6))
            c.move_to(x, H)
            c.curve_to(x, H - h * 0.5, x + sw * 0.5, H - h * 0.8, x + sw, H - h)
            c.stroke()
        self.part.draw(c, t)


class CieloMeteoro(Escena):
    """Contrapicado: copas de pinos enmarcando un cielo que se enciende con el bólido."""
    luz = (1.0, 0.65, 0.3, 0.5, "soft")

    def __init__(self):
        rnd = random.Random(31)
        s, c = new_layer()
        vgrad(c, 0, BH, [(0, hx("0B1030")), (0.5, hx("2C2552")), (0.85, hx("A25A55")), (1, hx("E89A62"))])
        for i in range(200):
            c.set_source_rgba(1, 1, 1, rnd.uniform(0.2, 0.8))
            c.arc(rnd.uniform(0, BW), rnd.uniform(0, 1300), rnd.uniform(0.6, 1.8), 0, 6.3)
            c.fill()
        # copas de pinos desde abajo (marco)
        for i in range(16):
            x = rnd.choice([rnd.uniform(-100, 260), rnd.uniform(1140, 1500)])
            pine(c, x, BH + 100, rnd.uniform(1100, 1800), hx("0A0812"), rnd, lean=(0.2 if x < 700 else -0.2))
        self.bg = s

    def dyn(self, c, t, lt, k):
        p = clamp(lt / 2.6)
        mx, my = lerp(1300, 380, p), lerp(150, 900, p)
        # resplandor del cielo
        glow(c, mx, my, 900, hx("FF8A3A"), 0.55 * p + 0.15)
        for i in range(40):
            f = i / 40
            x, y = mx + (1 - f) * 0 + f * 520, my - f * 470
            glow(c, x, y, 80 * (1 - f) + 10, hx("FFB25A"), 0.35 * (1 - f))
        r = random.Random(int(t * 30))
        for i in range(20):
            a = r.uniform(0.3, 1.2)
            d = r.uniform(30, 260)
            c.set_source_rgba(1, 0.85, 0.5, r.uniform(0.4, 1))
            c.arc(mx + math.cos(a) * d, my - math.sin(a) * d * 0.9, r.uniform(1.5, 4), 0, 6.3)
            c.fill()
        glow(c, mx, my, 260, hx("FFF2C8"), 1.0)
        glow(c, mx, my, 70, hx("FFFFFF"), 1.0)
        # destello anamórfico
        g = cairo.LinearGradient(mx - 380, 0, mx + 380, 0)
        g.add_color_stop_rgba(0, 1, 0.85, 0.6, 0)
        g.add_color_stop_rgba(0.5, 1, 0.9, 0.7, 0.45)
        g.add_color_stop_rgba(1, 1, 0.85, 0.6, 0)
        c.set_source(g)
        c.rectangle(mx - 380, my - 2.5, 760, 5)
        c.fill()


class Explosion(Escena):
    """La explosión: destello, bola de fuego en el horizonte, onda que tumba el bosque."""
    luz = (1.0, 0.55, 0.25, 0.6, "soft")

    def __init__(self):
        self.rnd_seed = 12
        self.part = Particulas(90, 6, "brasas")
        self.dust = Particulas(60, 8, "cenizas")
        s, c = new_layer()
        vgrad(c, 0, BH, [(0, hx("3A1E3A")), (0.55, hx("E06A3A")), (0.72, hx("FFD08A")), (1, hx("3A1A12"))])
        self.bg = s
        self.ridge = ridge(random.Random(4), 1500, 30)
        col, cc = new_layer(1000, 1200)
        r = random.Random(3)
        for i in range(60):
            f = i / 60
            yy = 1150 - f * 950
            rad = 70 + f * 240 + r.uniform(-20, 20)
            cl = mix(hx("FFD27A"), hx("3A2228"), min(1, f * 1.3))
            cc.set_source_rgba(*cl[:3], 0.5)
            cc.arc(500 + r.uniform(-60, 60) * f, yy, rad, 0, 6.3)
            cc.fill()
        self.column = blurred(col, 22)

    def dyn(self, c, t, lt, k):
        cx = 700
        fb = ease_out(lt / 1.2)
        glow(c, cx, 1450, 300 + 1200 * fb, hx("FFE7B0"), 0.95)
        glow(c, cx, 1450, 180 + 300 * fb, hx("FFFFFF"), 1.0)
        # columna de humo y fuego (crece)
        c.save()
        c.translate(cx, 1500)
        c.scale(0.4 + 0.8 * fb, 0.2 + 0.9 * fb)
        c.translate(-500, -1150)
        c.set_source_surface(self.column, 0, 0)
        c.paint_with_alpha(0.95)
        c.restore()
        # onda expansiva
        wave = lt * 900
        c.set_source_rgba(1, 0.95, 0.85, 0.5 * max(0.0, 1 - lt / 3))
        c.set_line_width(26)
        c.save()
        c.translate(cx, 1560)
        c.scale(1, 0.18)
        c.arc(0, 0, wave, 0, 6.3)
        c.restore()
        c.stroke()
        # bosque que cae cuando pasa la onda
        rr = random.Random(5)
        pts = self.ridge
        fill_ridge(c, pts, BH, hx("1E0E0A"))
        for (x, y) in pts[::2]:
            for _ in range(2):
                xx = x + rr.uniform(-10, 10)
                d = abs(xx - cx)
                fall = clamp((wave - d) / 160) if d < 1600 else 0
                pine(c, xx, y + 6, rr.uniform(120, 220), hx("1E0E0A"), rr,
                     lean=math.copysign(fall * 1.45, xx - cx))

    def fg(self, c, t, lt, k):
        self.dust.draw(c, t, wind=2.5)
        self.part.draw(c, t, strength=1.0, wind=1.5)
        # rocas de primer plano
        c.set_source_rgba(*hx("140806"))
        c.move_to(-20, H)
        c.curve_to(80, 1480, 260, 1500, 420, 1600)
        c.curve_to(520, 1640, 600, 1560, 760, 1600)
        c.curve_to(900, 1540, 1000, 1500, 1100, 1560)
        c.line_to(1100, H)
        c.close_path()
        c.fill()
        c.set_source_rgba(1, 0.6, 0.3, 0.6)
        c.set_line_width(4)
        c.move_to(80, 1488)
        c.curve_to(200, 1490, 300, 1520, 420, 1600)
        c.stroke()


class Calor(Escena):
    """Primer plano en el infierno: brasas, humo naranja y calor."""
    luz = (1.0, 0.45, 0.2, 0.55, "soft")

    def __init__(self):
        s, c = new_layer()
        vgrad(c, 0, BH, [(0, hx("2A0A12")), (0.5, hx("8A2A18")), (0.8, hx("E86A2A")), (1, hx("FFB050"))])
        rnd = random.Random(8)
        def smoke(cc):
            for i in range(40):
                cc.set_source_rgba(0.15, 0.06, 0.06, 0.5)
                cc.arc(rnd.uniform(0, BW), rnd.uniform(0, 1500), rnd.uniform(80, 220), 0, 6.3)
                cc.fill()
        paint_blur(c, smoke, 40)
        for i in range(12):
            x = rnd.uniform(0, BW)
            pine(c, x, 1900, rnd.uniform(600, 900), hx("1A0806"), rnd, lean=rnd.uniform(-0.9, 0.9))
        self.bg = s
        self.part = Particulas(130, 11, "brasas")

    def dyn(self, c, t, lt, k):
        for i in range(5):
            glow(c, 200 + i * 260, 1900 - 40 * math.sin(t * 3 + i), 380, hx("FF6A20"), 0.5 + 0.2 * math.sin(t * 7 + i))

    def fg(self, c, t, lt, k):
        self.part.draw(c, t, wind=0.6)
        g = cairo.LinearGradient(0, H - 380, 0, H)
        g.add_color_stop_rgba(0, 1, 0.4, 0.1, 0)
        g.add_color_stop_rgba(1, 1, 0.35, 0.1, 0.55)
        c.set_source(g)
        c.rectangle(0, H - 380, W, 380)
        c.fill()


class BosqueAereo(Escena):
    """Vista de dron: el patrón en "mariposa" de 80 millones de árboles caídos."""
    def __init__(self):
        s, c = new_layer()
        c.set_source_surface(noise_tex(BW, BH, 40, 3, hx("4A4436"), hx("6E6650"), 6), 0, 0)
        c.paint()
        c.set_source_surface(noise_tex(BW, BH, 8, 4, hx("3A3428", 0.0), hx("8A8068", 0.0), 1, 90), 0, 0)
        c.paint_with_alpha(0.5)
        cx, cy = BW / 2, BH / 2
        rnd = random.Random(80)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        for i in range(2600):
            a = rnd.uniform(0, 2 * math.pi)
            d = rnd.uniform(60, 1300) ** 1.0
            sx = 1.0 + 0.35 * math.cos(a) ** 2       # forma de mariposa
            x, y = cx + math.cos(a) * d * sx, cy + math.sin(a) * d
            ln = rnd.uniform(16, 34)
            c.set_source_rgba(*mix(hx("2A2018"), hx("6A5A44"), rnd.random())[:3], 0.95)
            c.set_line_width(rnd.uniform(2.5, 5))
            c.move_to(x, y)
            c.line_to(x + math.cos(a) * ln, y + math.sin(a) * ln)
            c.stroke()
        # epicentro: árboles quemados en pie ("bosque de postes telegráficos")
        for i in range(120):
            x, y = cx + rnd.gauss(0, 60), cy + rnd.gauss(0, 60)
            c.set_source_rgba(0.08, 0.07, 0.06, 1)
            c.arc(x, y, 3, 0, 6.3)
            c.fill()
        # ríos y pantanos
        c.set_source_rgba(*hx("6E7E8A", 0.8))
        c.set_line_width(14)
        c.move_to(0, 300)
        c.curve_to(400, 600, 900, 200, BW, 700)
        c.stroke()
        self.bg = s
        smoke, sc = new_layer()
        r2 = random.Random(2)
        for i in range(30):
            sc.set_source_rgba(0.85, 0.82, 0.78, 0.35)
            sc.arc(r2.uniform(0, BW), r2.uniform(0, BH), r2.uniform(60, 180), 0, 6.3)
            sc.fill()
        self.smoke = blurred(smoke, 40)

    def dyn(self, c, t, lt, k):
        c.save()
        c.translate(lt * 30, -lt * 20)
        c.set_source_surface(self.smoke, 0, 0)
        c.paint_with_alpha(0.8)
        c.restore()


class BosqueCaido(Escena):
    """A ras de suelo: troncos tumbados en abanico, humo, cielo gris."""
    luz = (0.8, 0.8, 0.9, 0.25, "soft")

    def __init__(self):
        rnd = random.Random(27)
        s, c = new_layer()
        vgrad(c, 0, BH, [(0, hx("4A5060")), (0.55, hx("A8A6A2")), (0.7, hx("8A8070")), (1, hx("3A3228"))])
        for i in range(3):
            pts = ridge(rnd, 1250 + i * 70, 20)
            fill_ridge(c, pts, BH, mix(hx("8C8A86"), hx("4A4236"), i / 2))
            for (x, y) in pts[::3]:
                c.set_source_rgba(0.15 + i * 0.03, 0.13, 0.11, 1)
                c.set_line_width(2 + i)
                ln = 30 + i * 20
                a = rnd.uniform(-0.25, 0.25)
                c.move_to(x, y + 6)
                c.line_to(x + math.cos(a) * ln, y + 6 + math.sin(a) * ln * 0.2)
                c.stroke()
        glow(c, 980, 900, 420, hx("F4EEE0"), 0.55)
        glow(c, 980, 900, 70, hx("FFFDF4"), 0.9)
        # troncos pelados aún de pie
        for i in range(26):
            x = rnd.uniform(0, BW)
            c.set_source_rgba(0.12, 0.1, 0.09, 1)
            c.set_line_width(rnd.uniform(6, 12))
            c.move_to(x, 1460)
            c.line_to(x + rnd.uniform(-6, 6), 1460 - rnd.uniform(200, 420))
            c.stroke()
        def fog(cc):
            vgrad(cc, 1150, 1600, [(0, hx("D8D4CC", 0)), (0.5, hx("D8D4CC", 0.7)), (1, hx("D8D4CC", 0))])
        paint_blur(c, fog, 30)
        self.bg = s
        self.ash = Particulas(70, 13, "cenizas")

    def fg(self, c, t, lt, k):
        self.ash.draw(c, t, wind=1.0)
        # gran tronco caído en primer plano (tapa a los personajes)
        c.save()
        c.translate(0, 1490)
        c.rotate(-0.06)
        g = cairo.LinearGradient(0, 0, 0, 120)
        g.add_color_stop_rgba(0, *hx("6A5A48"))
        g.add_color_stop_rgba(0.35, *hx("3A3026"))
        g.add_color_stop_rgba(1, *hx("17120E"))
        c.set_source(g)
        R = 70
        c.move_to(-60, 0)
        c.line_to(1180, -30)
        c.arc(1180, -30 + R, R, -math.pi / 2, math.pi / 2)
        c.line_to(-60, 2 * R)
        c.close_path()
        c.fill()
        c.set_source_rgba(0.1, 0.08, 0.06, 0.8)
        c.set_line_width(3)
        r = random.Random(4)
        for i in range(30):
            x = r.uniform(0, 1150)
            c.move_to(x, r.uniform(20, 120))
            c.line_to(x + r.uniform(40, 120), r.uniform(20, 120))
            c.stroke()
        # anillos del corte
        for i in range(6):
            c.set_source_rgba(0.75 - i * 0.08, 0.6 - i * 0.07, 0.45 - i * 0.06, 1)
            c.arc(1180 + 8, -30 + R, R * (1 - i / 6), 0, 6.3)
            c.fill()
        c.restore()
        c.rectangle(0, 1620, W, 300)
        c.set_source_rgba(*hx("17120E"))
        c.fill()


class Expedicion1927(Escena):
    """Película de archivo: nieve, carpa de la expedición, huellas de trineo. Sepia."""
    sepia = True
    luz = (0.75, 0.6, 0.42, 0.95, "color")

    def __init__(self):
        rnd = random.Random(1927)
        s, c = new_layer()
        vgrad(c, 0, BH, [(0, hx("BDB6A8")), (0.55, hx("E8E2D4")), (1, hx("F4F0E6"))])
        _taiga_ridges(c, rnd, hx("E8E2D4"), [(0, 30, hx("8A8478"), 60, 1.3), (120, 40, hx("5E584E"), 100, 1.2)], 1150,
                      snow=hx("F4F0E6"))
        # campo nevado + troncos caídos asomando
        vgrad(c, 1400, BH, [(0, hx("EDE8DC")), (1, hx("CFC8B8"))])
        for i in range(60):
            x, y = rnd.uniform(0, BW), rnd.uniform(1420, 1900)
            a = rnd.uniform(-0.3, 0.3)
            c.set_source_rgba(0.3, 0.27, 0.22, 0.85)
            c.set_line_width(3 + (y - 1400) / 100)
            c.move_to(x, y)
            c.line_to(x + math.cos(a) * 80, y + math.sin(a) * 15)
            c.stroke()
        # carpa y trineo
        c.set_source_rgba(*hx("9A8E78"))
        c.move_to(980, 1500)
        c.line_to(1080, 1340)
        c.line_to(1180, 1500)
        c.close_path()
        c.fill()
        c.set_source_rgba(*hx("4A4236"))
        c.move_to(1080, 1340)
        c.line_to(1060, 1500)
        c.line_to(1100, 1500)
        c.close_path()
        c.fill()
        c.set_source_rgba(0.45, 0.4, 0.33, 0.7)
        c.set_line_width(4)
        for dx in (0, 26):
            c.move_to(200 + dx, BH)
            c.curve_to(400 + dx, 1800, 800 + dx, 1650, 1000 + dx, 1510)
            c.stroke()
        self.bg = s
        self.snow = Particulas(110, 21, "nieve")

    def fg(self, c, t, lt, k):
        self.snow.draw(c, t, strength=0.9)
        # banco de nieve en primer plano
        c.move_to(-20, H)
        c.curve_to(100, 1520, 400, 1560, 560, 1600)
        c.curve_to(720, 1560, 900, 1500, 1100, 1560)
        c.line_to(1100, H)
        c.close_path()
        c.set_source_rgba(*hx("E6E0D2"))
        c.fill()


class Pantano(Escena):
    """Pantano con charcas espejo: el 'cráter' que nunca existió."""
    agua = 1600
    luz = (0.75, 0.85, 1.0, 0.3, "soft")

    def __init__(self):
        rnd = random.Random(55)
        s, c = new_layer()
        vgrad(c, 0, 1350, [(0, hx("2E3A55")), (0.7, hx("8A97A8")), (1, hx("C8C8C0"))])
        _taiga_ridges(c, rnd, hx("B8BCC0"), [(0, 25, hx("6E7480"), 50, 1.2), (80, 30, hx("4A5060"), 70, 1.2)], 1230)
        vgrad(c, 1360, BH, [(0, hx("4A4A3A")), (1, hx("2A2A20"))])
        # charcas que reflejan el cielo
        for i in range(14):
            x, y = rnd.uniform(0, BW), rnd.uniform(1400, 2100)
            w_, h_ = rnd.uniform(80, 300), rnd.uniform(14, 40)
            c.save()
            c.translate(x, y)
            c.scale(1, h_ / w_)
            c.arc(0, 0, w_, 0, 6.3)
            c.restore()
            c.set_source_rgba(*hx("A8B4C4", 0.85))
            c.fill()
        # árboles muertos
        for i in range(10):
            x = rnd.uniform(0, BW)
            y = rnd.uniform(1380, 1500)
            c.set_source_rgba(0.13, 0.12, 0.1, 1)
            c.set_line_width(rnd.uniform(4, 9))
            top = y - rnd.uniform(150, 380)
            c.move_to(x, y)
            c.line_to(x + rnd.uniform(-10, 10), top)
            c.stroke()
            for j in range(3):
                yy = lerp(y, top, rnd.uniform(0.4, 0.9))
                c.set_line_width(2.5)
                c.move_to(x, yy)
                c.line_to(x + rnd.uniform(-60, 60), yy - rnd.uniform(20, 60))
                c.stroke()
        def fog(cc):
            vgrad(cc, 1250, 1650, [(0, hx("D0D8E0", 0)), (0.5, hx("D0D8E0", 0.6)), (1, hx("D0D8E0", 0))])
        paint_blur(c, fog, 30)
        self.bg = s
        self.part = Particulas(30, 3, "luciernagas")

    def fg(self, c, t, lt, k):
        vgrad(c, self.agua, H, [(0, hx("6E7A8A", 0.55)), (1, hx("1A1E26", 0.95))], 0, W)
        for i in range(10):
            y = self.agua + 18 + i * 28
            c.set_source_rgba(1, 1, 1, 0.08)
            c.set_line_width(2)
            c.move_to(0, y + 3 * math.sin(t * 2 + i))
            for x in range(0, W + 40, 40):
                c.line_to(x, y + 3 * math.sin(t * 2 + i + x * 0.02))
            c.stroke()
        self.part.draw(c, t, strength=0.8)


def big_ben(c, x, y, s, col, lit):
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    c.set_source_rgba(*col)
    c.rectangle(-40, -520, 80, 520)
    c.fill()
    c.rectangle(-50, -600, 100, 90)
    c.fill()
    c.move_to(-50, -600)
    c.line_to(0, -760)
    c.line_to(50, -600)
    c.close_path()
    c.fill()
    c.rectangle(-3, -820, 6, 70)
    c.fill()
    glow(c, 0, -555, 70, lit, 0.8)
    c.set_source_rgba(*lit[:3], 1)
    c.arc(0, -555, 30, 0, 6.3)
    c.fill()
    c.set_source_rgba(*col)
    c.set_line_width(3)
    c.move_to(0, -555)
    c.line_to(0, -578)
    c.move_to(0, -555)
    c.line_to(16, -555)
    c.stroke()
    for i in range(6):
        c.set_source_rgba(*lit[:3], 0.7)
        c.rectangle(-30 + (i % 2) * 40, -480 + (i // 2) * 120, 18, 40)
        c.fill()
    c.restore()


class LondresNoche(Escena):
    """Londres 1908: cielo nocturno que brilla (nubes noctilucentes) sobre el Támesis."""
    agua = None
    luz = (0.6, 0.8, 1.0, 0.45, "soft")

    def __init__(self):
        rnd = random.Random(1908)
        s, c = new_layer()
        vgrad(c, 0, 1500, [(0, hx("070B22")), (0.55, hx("1A2A5A")), (1, hx("3A4A7A"))])
        def nlc(cc):
            r2 = random.Random(6)
            for i in range(26):
                y = 500 + i * 26 + r2.uniform(-10, 10)
                cc.set_source_rgba(0.7, 0.9, 1.0, r2.uniform(0.15, 0.4))
                cc.set_line_width(r2.uniform(6, 22))
                cc.move_to(-50, y)
                for x in range(0, BW + 100, 100):
                    cc.line_to(x, y + 30 * math.sin(x * 0.006 + i * 0.7))
                cc.stroke()
        paint_blur(c, nlc, 9)
        for i in range(150):
            c.set_source_rgba(1, 1, 1, rnd.uniform(0.2, 0.7))
            c.arc(rnd.uniform(0, BW), rnd.uniform(0, 480), rnd.uniform(0.6, 1.6), 0, 6.3)
            c.fill()
        # Parlamento + Big Ben
        col = hx("0B0E1C")
        c.set_source_rgba(*col)
        c.rectangle(0, 1290, 1000, 170)
        c.fill()
        for i in range(20):
            x = i * 50
            c.rectangle(x + 10, 1250, 14, 50)
            c.fill()
            c.set_source_rgba(1, 0.8, 0.45, 0.7)
            c.rectangle(x + 25, 1340, 10, 22)
            c.fill()
            c.set_source_rgba(*col)
        big_ben(c, 1080, 1460, 1.05, col, hx("FFE7A8"))
        # Támesis con reflejos
        vgrad(c, 1460, BH, [(0, hx("2A3A6A")), (1, hx("070A18"))])
        for i in range(60):
            y = rnd.uniform(1470, 2000)
            x = rnd.uniform(0, BW)
            c.set_source_rgba(0.8, 0.9, 1, rnd.uniform(0.08, 0.3))
            c.rectangle(x, y, rnd.uniform(30, 160), 3)
            c.fill()
        self.bg = s
        self.part = Particulas(40, 5, "polvo")

    def dyn(self, c, t, lt, k):
        glow(c, 700, 700, 800, hx("8FD0FF"), 0.18 + 0.06 * math.sin(t * 1.5))

    def fg(self, c, t, lt, k):
        # baranda de piedra del puente de Westminster
        y = 1500
        c.set_source_rgba(*hx("1A1C26"))
        c.rectangle(0, y, W, 60)
        c.fill()
        for i in range(12):
            x = i * 95 + 10
            c.set_source_rgba(*hx("22242F"))
            R_ = 22
            c.move_to(x, y + 60)
            c.curve_to(x - 8, y + 120, x + 50, y + 120, x + 42, y + 60)
            c.line_to(x + 42, y + 220)
            c.line_to(x, y + 220)
            c.close_path()
            c.fill()
        c.rectangle(0, y + 200, W, H - y - 200)
        c.set_source_rgba(*hx("12131A"))
        c.fill()
        c.set_source_rgba(0.6, 0.8, 1, 0.35)
        c.rectangle(0, y, W, 4)
        c.fill()
        # farola victoriana
        x = 960
        c.set_source_rgba(*hx("0A0A10"))
        c.rectangle(x - 6, 900, 12, 620)
        c.fill()
        glow(c, x, 880, 160, hx("FFD08A"), 0.8)
        c.set_source_rgba(1, 0.88, 0.6, 1)
        c.arc(x, 880, 18, 0, 6.3)
        c.fill()


def onion(c, x, y, r, h, c1, c2, stripes=True):
    c.save()
    c.translate(x, y)
    c.move_to(-r * 0.75, 0)
    c.curve_to(-r * 1.25, -h * 0.35, -r * 0.6, -h * 0.75, 0, -h)
    c.curve_to(r * 0.6, -h * 0.75, r * 1.25, -h * 0.35, r * 0.75, 0)
    c.close_path()
    c.clip_preserve()
    c.set_source_rgba(*c1)
    c.fill()
    if stripes:
        c.set_source_rgba(*c2)
        for i in range(-6, 7, 2):
            c.move_to(i * r * 0.18, 0)
            c.curve_to(i * r * 0.3, -h * 0.4, i * r * 0.1, -h * 0.8, 0, -h)
            c.line_to(0, -h)
            c.curve_to((i + 1) * r * 0.1, -h * 0.8, (i + 1) * r * 0.3, -h * 0.4, (i + 1) * r * 0.18, 0)
            c.fill()
    c.reset_clip()
    c.set_source_rgba(1, 0.85, 0.4, 1)
    c.rectangle(-2, -h - 40, 4, 40)
    c.fill()
    c.rectangle(-12, -h - 30, 24, 4)
    c.fill()
    c.restore()


class MoscuNieve(Escena):
    """Plaza Roja nevando: cúpulas de San Basilio iluminadas, cielo rojizo."""
    luz = (1.0, 0.6, 0.5, 0.35, "soft")

    def __init__(self):
        rnd = random.Random(1917)
        s, c = new_layer()
        vgrad(c, 0, 1500, [(0, hx("0A0A20")), (0.6, hx("3A1E3A")), (1, hx("8A3A3A"))])
        # catedral de San Basilio
        base = 1420
        c.set_source_rgba(*hx("5A1A1A"))
        c.rectangle(250, base - 300, 900, 300)
        c.fill()
        for (x, top, r, h, c1, c2) in (
            (400, base - 300, 70, 190, hx("2E8B57"), hx("F2E8C8")),
            (560, base - 420, 85, 230, hx("C8323A"), hx("FFFFFF")),
            (700, base - 620, 70, 200, hx("D4A73A"), hx("8A5A1A")),
            (840, base - 420, 85, 230, hx("2A5AC8"), hx("FFFFFF")),
            (1000, base - 300, 70, 190, hx("C8323A"), hx("2E8B57"))):
            c.set_source_rgba(*hx("7A2A22"))
            c.rectangle(x - r * 0.7, top, r * 1.4, base - top)
            c.fill()
            for k in range(3):
                c.set_source_rgba(1, 0.85, 0.5, 0.75)
                c.rectangle(x - 10, top + 40 + k * 70, 20, 36)
                c.fill()
            onion(c, x, top, r, h, c1, c2)
        glow(c, 700, base - 300, 700, hx("FFB070"), 0.25)
        # muralla del Kremlin
        c.set_source_rgba(*hx("3A0E10"))
        c.rectangle(0, base - 90, 250, 90)
        c.rectangle(1150, base - 90, 300, 90)
        c.fill()
        for i in range(30):
            c.rectangle(i * 50, base - 120, 26, 34)
            c.fill()
        vgrad(c, base, BH, [(0, hx("D8D0D8")), (1, hx("8A8098"))])
        self.bg = s
        self.snow_back = Particulas(90, 31, "nieve")
        self.snow_front = Particulas(40, 32, "nieve")

    def dyn(self, c, t, lt, k):
        self.snow_back.draw(c, t, BW, BH, 0.6, wind=0.4)

    def fg(self, c, t, lt, k):
        c.move_to(-20, H)
        c.curve_to(150, 1540, 380, 1600, 540, 1640)
        c.curve_to(700, 1590, 860, 1520, 1100, 1580)
        c.line_to(1100, H)
        c.close_path()
        c.set_source_rgba(*hx("E8E2EC"))
        c.fill()
        c.save()
        c.scale(1, 1)
        self.snow_front.draw(c, t, strength=1.0, wind=0.4)
        c.restore()


class Chelyabinsk(Escena):
    """Chelyabinsk 2013: ciudad nevada al amanecer y una estela blanca que cruza el cielo."""
    luz = (1.0, 0.8, 0.7, 0.35, "soft")

    def __init__(self):
        rnd = random.Random(2013)
        s, c = new_layer()
        vgrad(c, 0, 1500, [(0, hx("3A5A8A")), (0.6, hx("C8A8C0")), (1, hx("FFD8B8"))])
        glow(c, 300, 1250, 500, hx("FFE0C0"), 0.8)
        # bloques de departamentos soviéticos
        for i in range(14):
            x = i * 105 + rnd.uniform(-10, 10)
            h = rnd.uniform(250, 520)
            col = mix(hx("5A5A70"), hx("8A8498"), rnd.random())
            c.set_source_rgba(*col)
            c.rectangle(x, 1450 - h, 95, h)
            c.fill()
            for yy in range(int(1450 - h + 20), 1440, 34):
                for xx in range(int(x + 10), int(x + 90), 22):
                    if rnd.random() < 0.35:
                        c.set_source_rgba(1, 0.85, 0.55, 0.85)
                    else:
                        c.set_source_rgba(0.2, 0.2, 0.3, 0.6)
                    c.rectangle(xx, yy, 12, 18)
                    c.fill()
            if rnd.random() < 0.4:
                def smoke(cc, x=x, top=1450 - h):
                    for k in range(10):
                        cc.set_source_rgba(0.95, 0.93, 0.95, 0.25)
                        cc.arc(x + 40 + k * 12, top - 30 - k * 35, 20 + k * 6, 0, 6.3)
                        cc.fill()
                paint_blur(c, smoke, 10)
        vgrad(c, 1450, BH, [(0, hx("E8E4EE")), (1, hx("A8A0B8"))])
        self.bg = s
        self.snow = Particulas(50, 41, "nieve")

    def dyn(self, c, t, lt, k):
        p = clamp(lt / 3.5)
        x0, y0 = 1400, 150
        x1, y1 = lerp(1400, 120, p), lerp(150, 980, p)
        g = cairo.LinearGradient(x0, y0, x1, y1)
        g.add_color_stop_rgba(0, 1, 1, 1, 0.15)
        g.add_color_stop_rgba(1, 1, 0.98, 0.95, 0.9)
        c.set_source(g)
        c.set_line_width(26)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        c.move_to(x0, y0)
        c.line_to(x1, y1)
        c.stroke()
        glow(c, x1, y1, 260, hx("FFF8E0"), 1.0)
        glow(c, x1, y1, 60, hx("FFFFFF"), 1.0)

    def fg(self, c, t, lt, k):
        self.snow.draw(c, t, strength=0.7)
        c.move_to(-20, H)
        c.curve_to(200, 1560, 420, 1600, 560, 1630)
        c.curve_to(740, 1580, 900, 1540, 1100, 1590)
        c.line_to(1100, H)
        c.close_path()
        c.set_source_rgba(*hx("EEEAF2"))
        c.fill()


ESCENAS = {
    "taiga_amanecer": TaigaAmanecer, "rio_taiga": RioTaiga, "cielo_meteoro": CieloMeteoro,
    "explosion": Explosion, "calor": Calor, "bosque_aereo": BosqueAereo, "bosque_caido": BosqueCaido,
    "expedicion_1927": Expedicion1927, "pantano": Pantano, "londres_noche": LondresNoche,
    "moscu_nieve": MoscuNieve, "chelyabinsk": Chelyabinsk,
}
_CACHE = {}


def escena(nombre):
    if nombre not in _CACHE:
        _CACHE[nombre] = ESCENAS[nombre]()
    return _CACHE[nombre]


# ---------------------------------------------------------------- cámara y transiciones
def camara(cam, k):
    """cam: {z0,z1,x0,x1,y0,y1,r0,r1}; k: progreso 0..1 del plano."""
    e = smooth(k)
    g = lambda a, b, d: lerp(cam.get(a, d), cam.get(b, cam.get(a, d)), e)  # noqa: E731
    return g("z0", "z1", 1.0), g("x0", "x1", 0.0), g("y0", "y1", 0.0), g("r0", "r1", 0.0)


def aplicar_camara(c, z, x, y, r, shake=(0, 0)):
    c.translate(W / 2 + shake[0], H / 2 + shake[1])
    c.scale(z, z)
    c.rotate(r)
    c.translate(-BW / 2 - x, -BH / 2 - y)


def transicion(c, tipo, lt):
    """Se dibuja ENCIMA del plano nuevo durante sus primeros instantes."""
    if tipo == "flash" and lt < 0.35:
        c.set_source_rgba(1, 0.97, 0.9, 1 - lt / 0.35)
        c.paint()
    elif tipo == "luz" and lt < 0.6:
        a = 1 - lt / 0.6
        g = cairo.LinearGradient(0, 0, W, H)
        g.add_color_stop_rgba(0, 1, 0.6, 0.2, 0.9 * a)
        g.add_color_stop_rgba(0.5, 1, 0.9, 0.6, 0.6 * a)
        g.add_color_stop_rgba(1, 1, 0.3, 0.4, 0.0)
        c.set_source(g)
        c.paint()
    elif tipo == "negro" and lt < 0.45:
        c.set_source_rgba(0, 0, 0, 1 - lt / 0.45)
        c.paint()
    elif tipo == "barrido" and lt < 0.22:
        a = 1 - lt / 0.22
        r = random.Random(int(lt * 100))
        for i in range(60):
            y = r.uniform(0, H)
            c.set_source_rgba(1, 1, 1, 0.25 * a)
            c.rectangle(0, y, W, r.uniform(2, 30))
            c.fill()
        c.set_source_rgba(0.05, 0.05, 0.08, 0.55 * a)
        c.paint()


def desplazamiento_transicion(tipo, lt):
    """Desplazamiento/zoom del plano entrante (barrido y zoom)."""
    if tipo == "barrido" and lt < 0.22:
        return (W * 0.6 * (1 - ease_out(lt / 0.22)) ** 2, 0, 1.0)
    if tipo == "zoom" and lt < 0.35:
        return (0, 0, 1 + 0.35 * (1 - ease_out(lt / 0.35)))
    return (0, 0, 1.0)


def sepia_overlay(c, t):
    """Aspecto de película de 1927: tono sepia, parpadeo, rayas y vaivén."""
    c.save()
    c.set_operator(cairo.OPERATOR_HSL_COLOR)
    c.set_source_rgba(0.62, 0.48, 0.3, 1)
    c.paint()
    c.restore()
    fl = 0.06 * (0.5 + 0.5 * math.sin(t * 37) * math.sin(t * 13))
    c.set_source_rgba(0, 0, 0, fl)
    c.paint()
    r = random.Random(int(t * 24))
    for i in range(r.randint(1, 4)):
        x = r.uniform(0, W)
        c.set_source_rgba(0.1, 0.08, 0.05, r.uniform(0.2, 0.5))
        c.set_line_width(r.uniform(1, 3))
        c.move_to(x, 0)
        c.line_to(x + r.uniform(-10, 10), H)
        c.stroke()
    for i in range(r.randint(3, 10)):
        c.set_source_rgba(0.05, 0.04, 0.03, 0.6)
        c.arc(r.uniform(0, W), r.uniform(0, H), r.uniform(1, 4), 0, 6.3)
        c.fill()
