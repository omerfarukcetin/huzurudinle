"""Sesli Kitap Rafı logosu: açık kitap + kitabın üstünde konuşma ses dalgası (5 çubuk).

Aynı geometriden hem SVG (logo.svg, favicon) hem PNG uygulama simgeleri (icons/) üretir.
Renkleri ya da ölçüleri değiştirmek için aşağıdaki sabitleri düzenleyip tekrar çalıştırın.
"""
import os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.abspath(__file__))
BG, PAGE, WAVE = "#0f5c48", "#f6efe0", "#e2b857"
S = 512                      # tasarım ızgarası
WAVE_Y = 176                 # ses dalgasının orta çizgisi
BAR_W, BAR_GAP = 24, 38      # çubuk kalınlığı, çubuk merkezleri arası
BAR_H = (40, 84, 128, 84, 40)  # çubuk boyları (ortadaki en uzun)

# Sayfalar: sırtta aşağı doğru kavisli üst ve alt kenar (ikinci dereceden Bezier)
LEFT = dict(spine_x=249, outer_x=96, top=(288, 250), bottom=(376, 344), ctrl_x=180)


def page_path(p, mirror=False):
    f = (lambda x: S - x) if mirror else (lambda x: x)
    sx, ox, cx = f(p["spine_x"]), f(p["outer_x"]), f(p["ctrl_x"])
    (ts, to), (bs, bo) = p["top"], p["bottom"]
    return f"M{sx} {ts} Q{cx} {to} {ox} {to} L{ox} {bo} Q{cx} {bo} {sx} {bs} Z"


def page_poly(p, mirror=False, n=40):
    f = (lambda x: S - x) if mirror else (lambda x: x)
    sx, ox, cx = f(p["spine_x"]), f(p["outer_x"]), f(p["ctrl_x"])
    (ts, to), (bs, bo) = p["top"], p["bottom"]
    q = lambda a, c, b, t: (1 - t) ** 2 * a + 2 * (1 - t) * t * c + t * t * b
    top = [(q(sx, cx, ox, i / n), q(ts, to, to, i / n)) for i in range(n + 1)]
    bot = [(q(ox, cx, sx, i / n), q(bo, bo, bs, i / n)) for i in range(n + 1)]
    return top + bot


def bars():
    """(x, y, w, h) — orta çizgiye göre simetrik dikey çubuklar."""
    n = len(BAR_H)
    return [(S / 2 + (i - (n - 1) / 2) * BAR_GAP - BAR_W / 2, WAVE_Y - h / 2, BAR_W, h) for i, h in enumerate(BAR_H)]


def svg(rounded=True):
    rects = "".join(f'<rect x="{x:g}" y="{y:g}" width="{w}" height="{h}" rx="{w / 2:g}"/>' for x, y, w, h in bars())
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}">'
            f'<rect width="{S}" height="{S}" rx="{112 if rounded else 0}" fill="{BG}"/>'
            f'<path d="{page_path(LEFT)}" fill="{PAGE}"/><path d="{page_path(LEFT, True)}" fill="{PAGE}"/>'
            f'<g fill="{WAVE}">{rects}</g></svg>')


def png(size, rounded=True, scale=1.0):
    """scale < 1: içeriği küçült (maskable simgede güvenli alan için)."""
    k = 4 * size / S  # 4 kat büyük çiz, sonra küçült (yumuşak kenarlar)
    W = 4 * size
    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if rounded:
        d.rounded_rectangle([0, 0, W - 1, W - 1], radius=112 * k, fill=BG)
    else:
        d.rectangle([0, 0, W, W], fill=BG)
    t = lambda x, y: ((x - S / 2) * scale * k + W / 2, (y - S / 2) * scale * k + W / 2)
    for mirror in (False, True):
        d.polygon([t(x, y) for x, y in page_poly(LEFT, mirror)], fill=PAGE)
    for x, y, w, h in bars():
        x0, y0 = t(x, y)
        x1, y1 = t(x + w, y + h)
        d.rounded_rectangle([x0, y0, x1, y1], radius=(x1 - x0) / 2, fill=WAVE)
    return img.resize((size, size), Image.LANCZOS)


def main():
    os.makedirs(os.path.join(ROOT, "icons"), exist_ok=True)
    open(os.path.join(ROOT, "logo.svg"), "w", encoding="utf-8").write(svg())
    png(192).save(os.path.join(ROOT, "icons", "icon-192.png"))
    png(512).save(os.path.join(ROOT, "icons", "icon-512.png"))
    # Android "maskable": kenara kadar zemin, içerik %80 güvenli alanda
    png(512, rounded=False, scale=0.82).save(os.path.join(ROOT, "icons", "maskable-512.png"))
    # iPhone ana ekran simgesi: köşeleri iOS kendisi yuvarlar
    png(180, rounded=False, scale=0.9).convert("RGB").save(os.path.join(ROOT, "icons", "apple-touch-icon.png"))
    png(32).save(os.path.join(ROOT, "icons", "favicon-32.png"))
    print("logo.svg ve icons/ klasörü oluşturuldu.")


if __name__ == "__main__":
    main()
