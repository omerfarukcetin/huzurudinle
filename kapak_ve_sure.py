"""books.json'a kapak resmi ve tahmini sure ekler, books.js'i yeniden yazar.

Kapaklar hakikatkitabevi.net'ten (B###.png) indirilip kucultulmus WebP olarak covers/ klasorune kaydedilir.
Sure: her MP3'un boyutu (HEAD) / ilk MP3'un bit hizi. linkleri_topla.ps1'den sonra calistirin.
"""
import io, json, os, re, struct, urllib.request
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0"}
LIST_URL = "https://www.hakikatkitabevi.net/?listBook=tr"
COVER_URL = "https://www.hakikatkitabevi.net/images/books/B{code}.png"

BITRATES = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]  # MPEG-1 Layer III
BITRATES_V2 = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0]   # MPEG-2/2.5 Layer III


def get(url, headers=None, method="GET"):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})}, method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.headers, (r.read() if method == "GET" else b"")


def norm(s):
    s = s.casefold().replace("i̇", "i")
    return re.sub(r"[^a-z0-9]", "", s.translate(str.maketrans("âîûçğıöşü", "aiucgiosu")))


def bitrate_kbps(url):
    _, data = get(url, {"Range": "bytes=0-131071"})
    pos = 0
    if data[:3] == b"ID3":  # ID3v2 etiketini atla
        size = data[6:10]
        pos = 10 + ((size[0] << 21) | (size[1] << 14) | (size[2] << 7) | size[3])
    while pos + 4 <= len(data):
        if data[pos] == 0xFF and (data[pos + 1] & 0xE0) == 0xE0:
            h = struct.unpack(">I", data[pos:pos + 4])[0]
            version = (h >> 19) & 3
            idx = (h >> 12) & 15
            kbps = (BITRATES if version == 3 else BITRATES_V2)[idx]
            if kbps:
                return kbps
        pos += 1
    return 48


def tint_of(img):
    """Kapagin opak piksellerinin ortalama rengi (kart arka plani icin)."""
    small = img.resize((32, 40))
    px = [p for p in small.getdata() if p[3] > 200]
    if not px:
        return "#888888"
    r, g, b = (sum(p[i] for p in px) // len(px) for i in range(3))
    return f"#{r:02x}{g:02x}{b:02x}"


def size_of(url):
    try:
        headers, _ = get(url, method="HEAD")
        return int(headers.get("Content-Length", 0))
    except Exception:
        return 0


def main():
    books = json.load(open(os.path.join(ROOT, "books.json"), encoding="utf-8"))

    # Kapak kodlarini kitap adlarindan eslestir
    _, html = get(LIST_URL)
    found = re.findall(r'bookCode=(\d+)" title="([^"]+)"', html.decode("utf-8", "replace"))
    codes = {norm(t): c for c, t in found}
    names = {c: t.replace("`", "’") for c, t in found}  # dogru Turkce yazilisli kitap adlari
    os.makedirs(os.path.join(ROOT, "covers"), exist_ok=True)

    with ThreadPoolExecutor(16) as pool:
        for b in books:
            key = norm(b["title"])
            code = next((c for t, c in codes.items() if key.startswith(t) or t.startswith(key)), None)
            if code:
                _, png = get(COVER_URL.format(code=code))
                img = Image.open(io.BytesIO(png)).convert("RGBA")
                img.thumbnail((420, 520))
                name = f"covers/{code}.webp"
                img.save(os.path.join(ROOT, name), "WEBP", quality=82, method=6)
                b["cover"] = name
                b["tint"] = tint_of(img)
                b["name"] = names[code]
            else:
                print("  kapak bulunamadi:", b["title"])

            kbps = bitrate_kbps(b["tracks"][0]["url"])
            sizes = list(pool.map(size_of, [t["url"] for t in b["tracks"]]))
            for t, s in zip(b["tracks"], sizes):
                t["dur"] = round(s * 8 / (kbps * 1000)) if s else 0
            total = sum(t["dur"] for t in b["tracks"])
            print(f"{b['title'][:40]:<42} kapak={code}  {kbps}kbps  ~{total / 3600:.1f} sa")

    js = json.dumps(books, ensure_ascii=False, indent=1)
    open(os.path.join(ROOT, "books.json"), "w", encoding="utf-8").write(js)
    open(os.path.join(ROOT, "books.js"), "w", encoding="utf-8").write(f"window.BOOKS = {js};")
    print("books.json ve books.js guncellendi.")


if __name__ == "__main__":
    main()
