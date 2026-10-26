"""Web research stdlib: ambil halaman, cari via DuckDuckGo, riset + ringkas."""
import re
import time
import urllib.parse
import urllib.request

TIMEOUT = 25
MAX_HTML = 600_000
MAX_TEXT = 8000

# shortcut: pola untuk handle/channel YouTube di HTML hasil pencarian.
_CHANNEL_PATTERNS = (
    r'"channelId":"([A-Za-z0-9_-]{24})"',
    r'/(@[A-Za-z0-9_.-]+)/videos',
    r'"browseId":"(UC[A-Za-z0-9_-]{22})"',
)


def fetch(url):
    """Ambil halaman, kembalikan teks bersih. Hanya http/https."""
    u = (url or "").strip()
    if not (u.startswith("http://") or u.startswith("https://")):
        raise ValueError("URL harus http/https")
    req = urllib.request.Request(u, headers={"User-Agent": "JURU/1"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
        raw = res.read(MAX_HTML).decode("utf-8", errors="replace")
    text = re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>", " ", raw)
    text = re.sub(r"(?s)<!--.*?-->", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        raise RuntimeError("halaman kosong atau tak terbaca")
    return text[:MAX_TEXT]


def _ddg(html, pattern):
    out = []
    for m in re.finditer(pattern, html):
        link, title, snippet = m.group(1), m.group(2), m.group(3)
        if link.startswith("//duckduckgo.com/l/?uddg="):
            link = urllib.parse.unquote(link.split("uddg=", 1)[1].split("&", 1)[0])
        clean = lambda s: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()
        if link.startswith("http"):
            out.append({"title": clean(title), "url": link, "snippet": clean(snippet)})
    return out


def _wiki(query, n, timeout=12):
    u = ("https://id.wikipedia.org/w/api.php?action=opensearch&search=" +
         urllib.parse.quote(query) + "&limit=%d&format=json" % n)
    req = urllib.request.Request(u, headers={"User-Agent": "JURU/1"})
    import json
    with urllib.request.urlopen(req, timeout=timeout) as res:
        _, titles, _, links = json.loads(res.read().decode("utf-8"))
    return [{"title": t, "url": l, "snippet": "Artikel Wikipedia: " + t}
            for t, l in zip(titles, links)]


def search(query, n=5):
    """Cari web tanpa API key. Backend lapis: DDG html, DDG lite, Wikipedia."""
    q = (query or "").strip()
    if not q:
        raise ValueError("query kosong")
    errs = []
    for name, url, pat in (
            ("ddg", "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(q),
             r'(?s)<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?<a[^>]+class="result__snippet"[^>]*>(.*?)</a>'),
            ("lite", "https://lite.duckduckgo.com/lite/?q=" + urllib.parse.quote(q),
             r'(?s)<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>')):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "JURU/1"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
                html = res.read(MAX_HTML).decode("utf-8", errors="replace")
            if name == "lite":
                links = re.findall(pat, html)
                hits = [{"title": re.sub(r"<[^>]+>", "", t).strip(), "url": l,
                         "snippet": ""} for l, t in links
                        if l.startswith("http") and "duckduckgo" not in l][:n]
            else:
                hits = _ddg(html, pat)[:n]
            if hits:
                return hits
        except OSError as e:
            errs.append("%s: %s" % (name, e))
    try:
        words = q.split()
        for i in range(len(words), 0, -1):
            hits = _wiki(" ".join(words[:i]), n)
            if hits:
                return hits
    except OSError as e:
        errs.append("wiki: %s" % e)
    raise RuntimeError("pencarian tak terjangkau dari jaringan ini (%s)" % "; ".join(errs))


def youtube_play(query):
    """Cari di YouTube, buka hasil pertama. Return URL. Tanpa klik buta."""
    import time
    from tools import actions
    q = (query or "").strip()
    if not q:
        raise ValueError("query kosong")
    url = ("https://www.youtube.com/results?search_query=" +
           urllib.parse.quote(q))
    uas = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
           "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
           "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Edg/126.0 Safari/537.36")
    seen = []
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": uas[attempt % len(uas)]})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
                html = res.read(4 * 1024 * 1024).decode("utf-8", errors="replace")
            for v in re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', html):
                if v not in seen:
                    seen.append(v)
                if len(seen) >= 3:
                    break
            if seen:
                break
        except OSError:
            pass
        time.sleep(2)
    if not seen:
        raise RuntimeError("YouTube tak memberi hasil (coba lagi nanti): %s" % q)
    watch = "https://www.youtube.com/watch?v=" + seen[0]
    actions.open_url(watch)
    try:
        actions.focus("YouTube")
    except OSError:
        pass
    return watch


def _clean_channel_query(q):
    """Ambil nama channel dari kalimat bebas. Jaga casing asli secukupnya."""
    s = (q or "").strip()
    low = s.lower()
    for cut in ("tonton video paling lama", "tonton video terlama",
                "video paling lama", "video paling lamanya", "video terlama",
                "tonton videonya", "tonton video", "tonton",
                "buka channel", "buka kanal", "buka",
                "di youtube", "youtube", "channel", "kanal",
                "lalu", "kemudian", "terus", "habis itu", "dan",
                "chrome", "browser"):
        low = low.replace(cut, " ")
    # potong sisa kata kerja umum di depan
    low = re.sub(r"\s+", " ", low).strip(" ,.-")
    return low.strip()


def _find_channel_base(channel_name):
    """Cari base URL channel YouTube. Return (base_url, sumber)."""
    q = (channel_name or "").strip()
    if not q:
        raise ValueError("nama channel kosong")
    # 1) Coba tebak handle langsung: raditya dika -> @radityadika
    guess = "@" + re.sub(r"[^a-z0-9]", "", q.lower())
    if len(guess) > 2:
        direct = "https://www.youtube.com/" + guess + "/videos?view=0&sort=da&flow=grid"
        try:
            req = urllib.request.Request(direct, headers={"User-Agent": "JURU/1"})
            with urllib.request.urlopen(req, timeout=12) as res:
                html = res.read(2 * 1024 * 1024).decode("utf-8", errors="replace")
            if '"videoId":"' in html or "videoId" in html:
                return "https://www.youtube.com/" + guess, "tebak-handle"
        except OSError:
            pass
    # 2) Cari via web.search (DDG -> Wikipedia fallback sudah ada)
    try:
        hits = search("youtube channel " + q, 5)
    except (RuntimeError, OSError):
        hits = []
    for h in hits:
        u = h.get("url", "")
        if "youtube.com/@" in u:
            base = u.split("/videos")[0].split("/featured")[0].split("?")[0]
            return base, "pencarian"
        if "youtube.com/channel/" in u or "youtube.com/c/" in u:
            base = u.split("/videos")[0].split("?")[0]
            return base, "pencarian"
    # 3) Scrap halaman search YouTube untuk /@handle pertama
    try:
        surl = ("https://www.youtube.com/results?search_query=" +
                urllib.parse.quote(q + " channel"))
        req = urllib.request.Request(surl, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
            html = res.read(4 * 1024 * 1024).decode("utf-8", errors="replace")
        m = re.search(r'/(@[A-Za-z0-9_.-]+)', html)
        if m:
            return "https://www.youtube.com/" + m.group(1), "scrap-search"
    except OSError:
        pass
    # 4) Fallback: halaman search biasa (user pilih manual, tidak gagal)
    return ("https://www.youtube.com/results?search_query=" +
            urllib.parse.quote(q)), "fallback-search"


def youtube_oldest(channel_query):
    """Buka halaman video TERLAMA channel di browser nyata (jujur, anti-hoax).

    Kenapa tidak parse HTML mentah: halaman /videos?sort=da di-sort oleh JS
    setelah load. Fetch urllib tanpa JS selalu dapat urutan TERBARU, sehingga
    regex videoId pertama = video terbaru (bug kemarin: D-xShRWhiY4).
    Solusi benar: buka oldest_page di browser (JS jalan, sort benar),
    video pertama di halaman itu = paling lama. Return provenance lengkap
    agar log tunjukkan sumber, bukan link tiba-tiba.
    """
    from tools import actions
    name = _clean_channel_query(channel_query)
    if not name:
        raise ValueError("nama channel kosong")
    base, src = _find_channel_base(name)
    # Jika channel tak ketemu, buka hasil pencarian (jujur, jangan ngarang ID).
    if "/results?search_query=" in base:
        actions.open_browser(base)
        return ("kanal tak pasti untuk '%s' (sumber: %s).\n"
                "Dibuka hasil pencarian, pilih channel manual:\n%s"
                % (name, src, base))
    oldest_page = base.rstrip("/") + "/videos?view=0&sort=da&flow=grid"
    actions.open_browser(oldest_page)
    return ("kanal: %s (sumber: %s, kueri: '%s').\n"
            "Halaman terlama dibuka:\n%s\n"
            "Video pertama di halaman itu = paling lama. "
            "Klik/putar video pertama untuk menonton."
            % (base, src, name, oldest_page))


def research(query, api_key, ask_fn, n=3):
    """Cari, baca n hasil teratas, ringkas dengan sumber. ask_fn = llm.ask."""
    hits = search(query, n + 2)
    if not hits:
        return "Tidak ada hasil untuk: %s" % query
    docs, sources = [], []
    for h in hits:
        try:
            docs.append("SUMBER: %s\n%s" % (h["url"], fetch(h["url"])[:2500]))
            sources.append(h["url"])
        except (ValueError, RuntimeError, OSError):
            continue
        if len(docs) >= n:
            break
    if not docs:
        return "Hasil ada tapi isinya tak bisa dibaca: %s" % query
    summary = ask_fn("Ringkas dalam Bahasa Indonesia (maks 150 kata) dari:\n\n" +
                     "\n\n".join(docs), api_key)
    return summary + "\n\nSumber:\n" + "\n".join("- " + s for s in sources)
