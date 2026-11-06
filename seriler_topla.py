"""Sesli Yayınlar sekmesindeki serileri dinimizislam.com'dan toplar; books.json ve books.js'e ekler.

Kitaplara dokunmaz, yalnızca serileri yeniler. linkleri_topla.ps1 ve kapak_ve_sure.py'den sonra çalıştırın.
Yeni seri eklemek için SERIES listesine sayfa numarasını (Aid), sekme adını ve kapak satırlarını yazın.
"""
import html, json, os, re, struct, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageFont
import kapak_ve_sure as k

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGE = "https://dinimizislam.com/detay.asp?Aid={}"
TEFSIR = 4443  # sure sure ayrı sayfalara bölünmüş seri
#   Aid    sekme adı               seri adı                                      kapak satırları                    renk       tek dosyanın adı
SERIES = [
    (TEFSIR, "Kur'an-ı Kerim Tefsiri", "Kur'an-ı Kerim Tefsiri (Prof. Dr. Orhan Karmış)", ["KUR'AN-I KERİM", "TEFSİRİ"],     "#1f4e5f", None),
    (13611, "Evliyalar",           "Evliyalar Serisi",            ["EVLİYALAR", "SERİSİ"],              "#14532d", None),
    (13610, "Eshâb-ı Kirâm",       "Eshâb-ı Kirâm Serisi",        ["ESHÂB-I KİRÂM", "SERİSİ"],          "#7a2e2a", None),
    (13609, "Çocuklar İçin",       "Çocuk Serisi",                ["ÇOCUK", "SERİSİ"],                  "#1d5f8a", None),
    (13624, "Tarih",               "Tarih Serisi",                ["TARİH", "SERİSİ"],                  "#6b4a1f", None),
    (13623, "Sevgili Peygamberim", "Sevgili Peygamberim Serisi",  ["SEVGİLİ", "PEYGAMBERİM", "SERİSİ"], "#0f5c48", None),
    (13613, "İlahiler",            "İlahiler",                    ["İLAHİLER"],                         "#4a2d6b", None),
    (13622, "Sesli Şiirler",       "Sesli Şiirler",               ["SESLİ", "ŞİİRLER"],                 "#8a3b5a", None),
    (13618, "Mehter Marşları",     "Mehter Marşları",             ["MEHTER", "MARŞLARI"],               "#8a2f1f", None),
    (13619, "Câliyet-ül Ekdâr",    "Câliyet-ül Ekdâr",            ["CÂLİYET-ÜL", "EKDÂR"],              "#3f5a2a", "Câliyet-ül Ekdâr"),
]
GOLD = "#e2b857"
FONT = r"C:\Windows\Fonts\georgiab.ttf"
clean = lambda s: re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", s))).strip()


def make_cover(path, lines, color):
    """Kitap görselleriyle aynı oranda, sade bir cilt."""
    W, H = 1050, 1280
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([40, 30, W - 40, H - 30], 26, fill=color)
    d.rectangle([40, 56, 150, H - 56], fill="#00000044")
    d.rounded_rectangle([190, 90, W - 100, H - 90], 14, outline=GOLD, width=7)
    d.rounded_rectangle([214, 114, W - 124, H - 114], 8, outline=GOLD, width=2)
    cx = (190 + W - 100) / 2
    y = H / 2 - (len(lines) - 1) * 62
    for line in lines:
        size = 92
        while d.textlength(line, font=ImageFont.truetype(FONT, size)) > 620:
            size -= 2
        d.text((cx, y), line, font=ImageFont.truetype(FONT, size), fill=GOLD, anchor="mm")
        y += 124
    img.thumbnail((420, 520), Image.LANCZOS)
    img.save(os.path.join(ROOT, path), "WEBP", quality=88, method=6)
    return k.tint_of(img)


def page(aid):
    return urllib.request.urlopen(urllib.request.Request(PAGE.format(aid), headers=k.UA), timeout=40).read().decode("utf-8", "replace")


def rows_of(c):
    """Sayfadaki MP3 bağlantıları. Çift tırnaklı adreste tek tırnak (Kur'an.mp3), sonda ek (0340.mp3?v1.5) olabilir."""
    out = []
    for dq, sq, text in re.findall(r"""(?is)<a[^>]+href=(?:"([^"]+\.mp3)(?:\?[^"]*)?"|'([^']+\.mp3)(?:\?[^']*)?')[^>]*>(.*?)</a>""", c):
        url = urllib.parse.quote(html.unescape(dq or sq).strip(), safe=":/")  # Türkçe karakterli dosya adları
        out.append((url, clean(text)))
    return out


def tracks_of(aid, single_name):
    out, seen = [], set()
    for url, name in rows_of(page(aid)):
        if url not in seen:
            seen.add(url)
            out.append({"name": single_name or name, "url": url})
    return out


def tefsir_tracks():
    """114 sure; bazı surelerin âyetleri alt sayfalarda (bir sonraki surenin numarasına kadar)."""
    c = page(TEFSIR)
    sur = []
    for a, x in re.findall(r"""(?is)<a[^>]+href=["']([^"']*(?:Aid|id)=\d+[^"']*)["'][^>]*>(.*?)</a>""", c):
        t, n = clean(x), int(re.search(r"(?i)(?:Aid|id)=(\d+)", a).group(1))
        # Sure sayfaları ve sondaki hatim duası sayfası; menü bağlantıları bu aralığın dışında
        if TEFSIR + 2 <= n <= 4640 and n not in [s[0] for s in sur]:
            sur.append((n, re.sub(r"(?i)\s+tefsiri$", "", t)))
    assert sum(1 for _, t in sur if t.lower().endswith("suresi")) == 114, len(sur)
    ids = [(i, name) for pos, (n, name) in enumerate(sur) for i in range(n, sur[pos + 1][0] if pos + 1 < len(sur) else n + 1)]
    with ThreadPoolExecutor(4) as pool:
        pages = list(pool.map(lambda x: rows_of(page(x[0])), [(TEFSIR + 1, "")] + ids))
    out, seen = [], set()
    for (i, name), rows in zip([(TEFSIR + 1, "Giriş")] + ids, pages):
        for url, label in rows:
            if url not in seen:
                seen.add(url)
                out.append({"name": f"{name}, {label}" if label else name, "group": name, "url": url})
    return out


def kbps_of(url):
    """Bit hızı: yalnızca dosyanın başı okunur (etiket uzunsa etiketten sonrası)."""
    def part(a, b):
        r = urllib.request.Request(url, headers={**k.UA, "Range": f"bytes={a}-{b}"})
        return urllib.request.urlopen(r, timeout=40).read()
    data, base = part(0, 16383), 0
    if data[:3] == b"ID3":
        s = data[6:10]
        base = 10 + ((s[0] << 21) | (s[1] << 14) | (s[2] << 7) | s[3])
        if base + 8 > len(data):
            data = part(base, base + 8191)
        else:
            data = data[base:]
    for pos in range(len(data) - 4):
        if data[pos] == 0xFF and (data[pos + 1] & 0xE0) == 0xE0:
            h = struct.unpack(">I", data[pos:pos + 4])[0]
            n = (k.BITRATES if (h >> 19) & 3 == 3 else k.BITRATES_V2)[(h >> 12) & 15]
            if n:
                return n
    return 48


known = {}  # önceki çalıştırmada ölçülen süreler: url -> saniye


def with_duration(t):
    """Süre: dosya boyutu / bit hızı. Daha önce ölçüldüyse tekrar istenmez; açılmayan dosyanın süresi 0 kalır."""
    t["dur"] = known.get(t["url"], 0)
    for _ in range(3 if not t["dur"] else 0):
        try:
            size = k.size_of(t["url"])
            if not size:
                continue
            t["dur"] = round(size * 8 / (kbps_of(t["url"]) * 1000))
            break
        except Exception:
            pass
    return t


def main():
    p = os.path.join(ROOT, "books.json")
    old = json.load(open(p, encoding="utf-8"))
    known.update({t["url"]: t["dur"] for b in old if b.get("section") == "seri" for t in b["tracks"] if t.get("dur")})
    books = [b for b in old if b.get("section") != "seri"]
    all_urls = {}
    with ThreadPoolExecutor(6) as pool:
        for aid, tab, title, lines, color, single in SERIES:
            tracks = tefsir_tracks() if aid == TEFSIR else tracks_of(aid, single)
            tracks = list(pool.map(with_duration, tracks))
            dead = [t["name"] for t in tracks if not t["dur"]]  # kaynakta açılmayan dosyalar listeye alınmaz
            if dead:
                print("  elendi:", ascii(dead))
            tracks = [t for t in tracks if t["dur"]]
            cover = f"covers/seri-{aid}.webp"
            tint = make_cover(cover, lines, color)
            # Dosya klasörü serilere özel olmayabilir (Mehter, Tarih klasöründe): seri kimliği ayrı tutulur
            books.append({"title": title, "name": title, "key": f"seri-{aid}", "section": "seri", "tab": tab, "source": PAGE.format(aid), "cover": cover, "tint": tint, "tracks": tracks})
            for t in tracks:
                all_urls.setdefault(t["url"], []).append(aid)
            print(f"{ascii(tab)}: {len(tracks)} parca, {sum(t['dur'] for t in tracks) / 3600:.1f} sa, suresiz {sum(1 for t in tracks if not t['dur'])}", flush=True)
    dup = {u: a for u, a in all_urls.items() if len(a) > 1}
    print("birden cok seride:", len(dup), ascii(list(dup.items())[:5]))
    js = json.dumps(books, ensure_ascii=False, indent=1)
    open(p, "w", encoding="utf-8").write(js)
    open(os.path.join(ROOT, "books.js"), "w", encoding="utf-8").write(f"window.BOOKS = {js};")
    print("toplam:", len(books), "kayit,", sum(len(b["tracks"]) for b in books), "bolum", round(os.path.getsize(os.path.join(ROOT, "books.js")) / 1024), "KB")


if __name__ == "__main__":
    main()
