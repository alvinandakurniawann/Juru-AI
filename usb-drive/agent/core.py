"""Agent loop: UNDERSTAND -> PLAN -> RISK CHECK -> EXECUTE -> OBSERVE -> VERIFY."""
import os
import re
import time
from . import llm
from . import memory as project_memory
from tools import actions, capabilities, environment, files, permissions, shell, web

MAX_RETRY = 2
# ala koma: batas loop agen agar perintah spesifik tak infinite-loop.
MAX_AGENT_STEPS = 8
MAX_REPLAN = 1
STATUS = ["Memahami perintah...", "Membuat rencana...", "Menjalankan tindakan...",
          "Mengamati hasil...", "Memverifikasi...", "Selesai."]
API_KEY = ""
_EMIT = None

# Registry ala koma Tool::parameters: nama -> (args wajib, risk default).
# Dipakai _validate_plan untuk tolak halusinasi LLM sebelum eksekusi.
# Sumber kebenaran: tools/manifest.py (satu tempat, cegah drift nama tool).
try:
    from tools.manifest import TOOL_DEFS as _TOOL_DEFS
    TOOL_SCHEMAS = {n: (m["args"], m["risk"]) for n, m in _TOOL_DEFS.items()}
except ImportError:
    TOOL_SCHEMAS = {
    "open_app": (("app",), "LOW"),
    "open_browser": ((), "LOW"),
    "open_url": (("url",), "LOW"),
    "open_file": (("path",), "LOW"),
    "type_text": (("text",), "MEDIUM"),
    "click": (("x", "y"), "MEDIUM"),
    "hotkey": (("keys",), "LOW"),
    "focus_window": (("title",), "LOW"),
    "start_search": (("query",), "LOW"),
    "wait": ((), "LOW"),
    "screenshot": ((), "LOW"),
    "read_file": (("path",), "LOW"),
    "create_file": (("path",), "MEDIUM"),
    "create_docx": (("path", "text"), "MEDIUM"),
    "create_xlsx": (("path", "rows"), "MEDIUM"),
    "list_dir": ((), "LOW"),
    "make_dir": (("path",), "LOW"),
    "rename_file": (("src", "dst"), "MEDIUM"),
    "move_file": (("src", "dst"), "MEDIUM"),
    "delete_file": (("path",), "HIGH"),
    "run_shell": (("cmd",), "HIGH"),
    "web_fetch": (("url",), "LOW"),
    "web_search": (("query",), "LOW"),
    "youtube_play": (("query",), "LOW"),
    "youtube_oldest": (("query",), "LOW"),
    "research": (("query",), "MEDIUM"),
}

GUI_TOOLS = {"open_app", "click", "type_text", "hotkey", "focus_window",
             "open_url", "open_browser", "start_search"}

FOCUS_TOOLS = {"click", "type_text", "hotkey", "focus_window"}

RUNNERS = {
    "open_app": lambda a: actions.open_app(a.get("app", ""), emit=_EMIT),
    "type_text": lambda a: actions.type_text(a.get("text", "")),
    "click": lambda a: actions.click(a.get("x"), a.get("y")),
    "open_url": lambda a: actions.open_url(a.get("url", "")),
    "open_browser": lambda a: actions.open_browser(a.get("url", "https://www.bing.com/"),
                                                  a.get("browser", ""), a.get("guest", False)),
    "screenshot": lambda a: "tersimpan: " + actions.screenshot(),
    "read_file": lambda a: files.read_file(a.get("path", ""))[:500],
    "create_file": lambda a: files.create_file(a.get("path", ""), a.get("content", "")),
    "move_file": lambda a: files.move_file(a.get("src", ""), a.get("dst", "")),
    "delete_file": lambda a: files.delete_file(a.get("path", "")),
    "create_docx": lambda a: files.create_docx(a.get("path", ""), a.get("text", ""),
                                               a.get("size"), a.get("bold", False)),
    "create_xlsx": lambda a: files.create_xlsx(a.get("path", ""), a.get("rows", "")),
    "create_pdf": lambda a: files.create_pdf(a.get("path", ""), a.get("text", ""),
                                             a.get("title", "")),
    "create_pptx": lambda a: files.create_pptx(a.get("path", ""), a.get("text", "")),
    "list_dir": lambda a: files.list_dir(a.get("path", "")),
    "make_dir": lambda a: files.make_dir(a.get("path", "")),
    "rename_file": lambda a: files.rename_file(a.get("src", ""), a.get("dst", "")),    "open_file": lambda a: actions.open_file(a.get("path", "")),
    "run_shell": lambda a: shell.run(a.get("cmd", "")),
    "hotkey": lambda a: actions.hotkey(a.get("keys", "")),
    "start_search": lambda a: actions.start_search(a.get("query", "")),
    "wait": lambda a: actions.wait(a.get("seconds", 2)),
    "focus_window": lambda a: _focus(a),
    "web_fetch": lambda a: web.fetch(a.get("url", ""))[:800],
    "web_search": lambda a: _fmt_search(web.search(a.get("query", ""))),
    "youtube_play": lambda a: web.youtube_play(a.get("query", "")),
    "youtube_oldest": lambda a: web.youtube_oldest(a.get("query", "")),
    "research": lambda a: web.research(a.get("query", ""), API_KEY, llm.ask),
}


def _fmt_search(hits):
    if not hits:
        return "tidak ada hasil"
    return "\n".join("- %s | %s" % (h["title"][:80], h["url"]) for h in hits)[:1500]


def _focus(a):
    if not actions.focus(a.get("title", "")):
        raise RuntimeError("jendela '%s' tak ditemukan" % a.get("title", ""))
    return "fokus ok"


def heuristic_plan(message):
    """Perencana lokal tanpa API. Menangani perintah demo."""
    m = (message or "").lower()
    urls = re.findall(r"https?://\S+", message or "")
    # 0) Kasus spesifik ala koma: navigasi URL langsung, bukan klik buta.
    #    "buka chrome + channel raditya dika + video paling lama" -> 1 tool.
    yt = _detect_youtube_oldest(message)
    if yt:
        channel = web._clean_channel_query(yt) or yt
        return [{"tool": "youtube_oldest", "args": {"query": channel},
                 "risk": "LOW", "target": "video paling lama",
                 "reason": "buka video terlama channel langsung",
                 "expect": "",
                 "fallback": "buka halaman videos sort=da manual"}]
    brow = _detect_browser_open(message)
    if brow and not _app_in(m) and "youtube" not in m:
        url, b = brow if isinstance(brow, tuple) else (brow, "")
        if url == "__default__":
            return [{"tool": "open_browser",
                     "args": ({"browser": b} if b else {}),
                     "risk": "LOW"}]
        args = {"url": url}
        if isinstance(b, str) and b:
            args["browser"] = b
        return [{"tool": "open_browser", "args": args, "risk": "LOW"}]
    if urls and any(k in m for k in ("baca", "ringkas", "rangkum", "fetch")):
        return [{"tool": "web_fetch", "args": {"url": urls[0]}, "risk": "LOW"}]
    if "hapus" in m or "delete" in m:
        return []
    if "taskbar" in m or "menu start" in m or "start menu" in m or \
            "di laptop" in m or "di komputer" in m or "aplikasi apa" in m:
        q = _app_in(m)
        if not q:
            q = _after_keyword(message)
            for cut in ("di laptop", "di komputer", "di taskbar", "taskbar",
                        "menu start", "start menu", "aplikasi apa saja",
                        "aplikasi apa", "buka", "bukakan", "tolong"):
                q = q.replace(cut, "").strip()
        if not q:
            return []
        return [{"tool": "start_search", "args": {"query": q},
                 "risk": "LOW"},
                {"tool": "wait", "args": {"seconds": 2}, "risk": "LOW"},
                {"tool": "hotkey", "args": {"keys": "{ENTER}"}, "risk": "LOW"}]
    if "screenshot" in m:
        return [{"tool": "screenshot", "args": {}, "risk": "LOW"}]
    if any(k in m for k in ("play ", "putar", "mainkan", "setel", "sttel",
                             "tonton", "tontonlah")) and \
            not any(k in m for k in (".mp4", ".mkv", ".mp3", "folder", "file ",
                                     "paling lama", "terlama", "oldest")):
        q = m
        for cut in ("play", "putar", "mainkan", "setel", "sttel", "di youtube",
                    "youtube", "lagu", "lagunya", "video", "videonya", "tolong",
                    "salah satu", "coba", "dong"):
            q = q.replace(cut, " ").strip()
        q = " ".join(q.split())
        if q:
            return [{"tool": "youtube_play", "args": {"query": q}, "risk": "LOW"}]
    if "notepad" in m:
        steps = [{"tool": "open_app", "args": {"app": "notepad"}, "risk": "LOW"}]
        if "ketik" in m or "type" in m or "halo" in m or "hello" in m:
            steps.append({"tool": "type_text",
                          "args": {"text": _after_keyword(message)}, "risk": "MEDIUM"})
        return steps
    if "word" in m or "dokumen" in m or "pengolah kata" in m:
        if any(k in m for k in ("capslock", "kapital", "huruf besar",
                                "huruf kecil", "font", "ukuran", "size",
                                "bold", "tebal", "miring", "italic",
                                "warna", "color", "underline", "garis bawah")):
            return []
        if "ketik" in m or "type" in m or "tulis" in m or "halo" in m or "hello" in m:
            return [{"tool": "create_docx",
                     "args": {"path": "Dokumen.docx",
                              "text": _after_keyword(message)}, "risk": "MEDIUM"},
                    {"tool": "open_file", "args": {"path": "Dokumen.docx"},
                     "risk": "LOW"}]
        return [{"tool": "open_app", "args": {"app": "word"}, "risk": "LOW"},
                {"tool": "focus_window", "args": {"title": "Word"}, "risk": "LOW"},
                {"tool": "hotkey", "args": {"keys": "^n"}, "risk": "LOW"}]
    if (("spreadsheet" in m or "tabel" in m or "laporan" in m or "excel" in m)
            and any(k in m for k in ("buat", "bikin", "isi", "data"))):
        rows = _tabel_rows(message) or _after_keyword(message)
        return [{"tool": "create_xlsx",
                 "args": {"path": "Laporan.xlsx", "rows": rows},
                 "risk": "MEDIUM"},
                {"tool": "open_file", "args": {"path": "Laporan.xlsx"},
                 "risk": "LOW"}]
    if "browser" in m or (("cari" in m or "search" in m) and not _app_in(m)):
        if any(k in m for k in ("chrome", "edge", "firefox", "guest", "mode tamu",
                                "youtube", "video", "channel")):
            return []
        if any(k in m for k in (" lalu ", " kemudian ", " terus ", " habis itu ",
                                " dan buka", " dan ketik", " dan cari")):
            return []
        q = _after_keyword(message) or "AI agent"
        return [{"tool": "open_browser",
                 "args": {"url": "https://www.bing.com/search?q=" + q.replace(" ", "+")},
                 "risk": "LOW"}]
    app = _app_in(m)
    if app:
        if ("cari" in m or "search" in m) and app == "discord":
            found = _cari_dan_ketik(message)
            if found:
                who, text = found
                steps = [{"tool": "open_app", "args": {"app": app}, "risk": "LOW"},
                         {"tool": "focus_window", "args": {"title": app}, "risk": "LOW"},
                         {"tool": "hotkey", "args": {"keys": "^k"}, "risk": "LOW"},
                         {"tool": "type_text", "args": {"text": who}, "risk": "MEDIUM"},
                         {"tool": "hotkey", "args": {"keys": "{ENTER}"}, "risk": "LOW"},
                         {"tool": "wait", "args": {"seconds": 2}, "risk": "LOW"},
                         {"tool": "type_text", "args": {"text": text}, "risk": "MEDIUM"}]
                if "kirim" in m and "jangan kirim" not in m:
                    steps.append({"tool": "hotkey", "args": {"keys": "{ENTER}"},
                                  "risk": "MEDIUM"})
                return steps
            return []
        if "cari" in m or "search" in m:
            return []
        steps = [{"tool": "open_app", "args": {"app": app}, "risk": "LOW"},
                 {"tool": "focus_window", "args": {"title": app}, "risk": "LOW"}]
        if "ketik" in m or "type" in m or "tulis" in m:
            steps.append({"tool": "type_text",
                          "args": {"text": _after_keyword(message)}, "risk": "MEDIUM"})
            if "kirim" in m and "jangan kirim" not in m:
                steps.append({"tool": "hotkey", "args": {"keys": "{ENTER}"},
                              "risk": "MEDIUM"})
        return steps
    if "kalkulator" in m or "calc" in m:
        return [{"tool": "open_app", "args": {"app": "calc"}, "risk": "LOW"}]
    return []


APP_ALIAS = {"discord": "discord", "excel": "excel", "powerpoint": "powerpoint",
             "power point": "powerpoint", "ppt": "powerpoint",
             "whatsapp": "whatsapp",
             "telegram": "telegram", "spotify": "spotify",
             "valorant": "valorant", "valo": "valorant"}


def _cari_dan_ketik(message):
    """Pola 'cari X dan/lalu ketik Y' -> (X, Y). None jika tak cocok."""
    import re
    m = (message or "").lower()
    pat = re.search(r"(?:cari|search)\s+(.+?)\s+(?:dan|lalu|,)\s+(?:ketik|type|tulis)\s+(.+)", m)
    if not pat:
        return None
    who, text = pat.group(1).strip(), pat.group(2).strip().strip("\"'")
    if not who or not text:
        return None
    return who, text


def _app_in(m):
    for word, app in APP_ALIAS.items():
        if word in m:
            return app
    return ""


def _looks_research(message):
    m = (message or "").lower()
    return any(k in m for k in ("teliti", "riset", "research", "ringkas",
                                "rangkum", "berita", "apa itu", "siapa",
                                "kapan", "bagaimana"))


def _tabel_rows(message):
    """Bangun teks rows untuk create_xlsx dari perintah tabel.

    'tabel 5x5 isi random' -> grid 5x5 angka acak 1-100.
    'tabel 5x5' tanpa data -> grid bernomor sesuai ukuran (bukan default 2 baris).
    Return '' bila tak ada pola tabel (jalur lama).
    """
    import random
    m = (message or "").lower()
    if not any(k in m for k in ("tabel", "spreadsheet", "excel", "laporan")):
        return ""
    d = re.search(r"(\d{1,2})\s*[x\u00d7]\s*(\d{1,2})", m)
    nrow, ncol = (int(d.group(1)), int(d.group(2))) if d else (5, 5)
    nrow, ncol = min(20, max(1, nrow)), min(10, max(1, ncol))
    if any(k in m for k in ("random", "acak", "rand", "contoh", "dummy")):
        grid = [[str(random.randint(1, 100)) for _ in range(ncol)]
                for _ in range(nrow)]
    else:
        after = _after_keyword(message)
        if after and any(sep in after for sep in (";", ",", "\n")):
            return after
        head = [chr(65 + c) for c in range(ncol)]
        grid = [head] + [[str(r * ncol + c + 1) for c in range(ncol)]
                        for r in range(nrow - 1)]
    return "\n".join(";".join(row) for row in grid)


def _after_keyword(message):
    # Jaga casing asli (perbaikan bug lower): deteksi pakai lower,
    # potong pakai string asli agar "Halo Dunia" tak jadi "halo dunia".
    low = (message or "").lower()
    for kw in ("ketik", "type", "tulis", "cari", "search"):
        if kw in low:
            idx = low.find(kw) + len(kw)
            return message[idx:].strip().strip("\"'") or "Halo Dunia"
    if "halo" in low or "hello" in low:
        # kembalikan kalimat asli bila ada, bukan template mentah
        return message.strip() or "Halo Dunia"
    return ""


def _detect_youtube_oldest(message):
    """Return channel query bila user minta video paling lama/terlama."""
    m = (message or "").lower()
    if not any(k in m for k in ("paling lama", "paling lamanya", "terlama",
                                "oldest", "pertama diupload", "video pertama")):
        return ""
    if not any(k in m for k in ("youtube", "channel", "kanal", "video",
                                "tonton", "putar", "play", "buka")):
        return ""
    # buang kata perintah, sisakan nama channel
    q = " ".join((message or "").split())
    return q


def _detect_browser_open(message):
    """Return url/browser bila user eksplisit minta buka browser/chrome."""
    m = (message or "").lower()
    if "chrome" in m or "browser" in m or "edge" in m or "firefox" in m:
        urls = re.findall(r"https?://\S+", message or "")
        if urls:
            return urls[0].rstrip(".,)")
        # tanpa URL: biarkan open_browser default (bukan open_app chrome)
        b = ""
        for cand in ("chrome", "edge", "firefox"):
            if cand in m:
                b = cand
                break
        return ("__default__", b)
    return ""


def _validate_plan(steps):
    """Validasi ala koma execute_tool: tolak tool/args halusinasi.

    - buang langkah tool tak dikenal (bukan silent-run)
    - perbaiki open_app chrome/edge/firefox -> open_browser
    - potong ke MAX_AGENT_STEPS
    Return (valid_steps, dibuang).
    """
    valid, dropped = [], 0
    for s in steps or []:
        if not isinstance(s, dict):
            dropped += 1
            continue
        tool = (s.get("tool", "") or "").strip()
        args = s.get("args", {}) or {}
        if not isinstance(args, dict):
            dropped += 1
            continue
        # auto-repair khas: LLM suka open_app chrome
        if tool == "open_app" and (args.get("app", "") or "").lower() in (
                "chrome", "browser", "edge", "firefox"):
            tool = "open_browser"
            args = {"browser": args.get("app", "").lower()
                    if args.get("app", "").lower() != "browser" else ""}
            s = dict(s, tool=tool, args=args)
        if tool not in RUNNERS or tool not in TOOL_SCHEMAS:
            dropped += 1
            continue
        req, _risk = TOOL_SCHEMAS[tool]
        # click butuh angka; tolak koordinat buta non-angka
        if tool == "click":
            try:
                int(args.get("x", "")), int(args.get("y", ""))
            except (TypeError, ValueError):
                dropped += 1
                continue
        valid.append(s)
        if len(valid) >= MAX_AGENT_STEPS:
            break
    return valid, dropped


def run_step(tool, args):
    if tool not in RUNNERS:
        raise ValueError("tool '%s' belum didukung" % tool)
    return RUNNERS[tool](args or {})


def _outside_data(args):
    for v in (args or {}).values():
        if isinstance(v, str) and v and ("/" in v or "\\" in v or v.endswith(".txt")):
            try:
                _, inside = files.resolve(v)
                if not inside:
                    return True
            except ValueError:
                pass
    return False


def _verify(tool, args, result):
    """Verifikasi ringan per langkah. False = gagal, picu retry."""
    try:
        if tool == "open_app":
            key = (args.get("app", "") or "").lower()
            exe = actions.ALLOW_APPS.get(key, key + ".exe")
            # beri waktu start (ala koma: verifikasi pasca-aksi, bukan instan)
            for _ in range(4):
                if actions.is_running(os.path.basename(exe)):
                    return True
                time.sleep(1.0)
            return actions.is_running(os.path.basename(exe))
        if tool in ("open_browser", "open_url", "youtube_play", "youtube_oldest"):
            # sukses = URL/halaman terbuka tanpa exception; browser fallback
            # sudah ditangani di actions.open_browser. Jangan verifikasi
            # via vision agar tak infinite-loop pada halaman JS-berat.
            # youtube_oldest sengaja buka halaman sort=da (bukan tebak ID),
            # jadi terima hasil provenance "dibuka".
            txt = str(result or "").lower()
            return bool("terbuka" in txt or "dibuka" in txt
                        or txt.strip().startswith("http"))
        if tool == "screenshot":
            return os.path.exists(result.rsplit("tersimpan: ", 1)[-1].strip())
        if tool in ("create_file", "move_file", "create_docx", "create_xlsx",
                      "create_pdf", "create_pptx"):
            p = args.get("path", "") or args.get("dst", "")
            return os.path.exists(files.resolve(p)[0])
        if tool == "delete_file":
            return not os.path.exists(files.resolve(args.get("path", ""))[0])
        return True
    except (ValueError, FileNotFoundError, KeyError, IndexError):
        return False


def _parse_verdict(text):
    """Ambil YA/TIDAK dari jawaban bebas. None jika tak jelas."""
    import re
    t = (text or "").upper()
    ya = bool(re.search(r"\bYA\b", t)) or bool(re.search(r"\bYES\b", t))
    tidak = bool(re.search(r"\bTIDAK\b", t)) or bool(re.search(r"\bNO\b", t))
    if ya and not tidak:
        return True
    if tidak and not ya:
        return False
    return None


def _verify_visual(expect, prior_err):
    """Screenshot lalu tanya vision. Return (ok, confident, msg, shot).
    confident True = TIDAK yang meyakinkan -> gagal. False = tak jelas -> lanjut."""
    try:
        for attempt in range(2):
            shot = actions.screenshot()
            if attempt:
                actions.refocus_last()
            verdict = llm.see(shot, "Apakah terlihat: %s? Jawab hanya satu kata: YA atau TIDAK."
                              % expect, API_KEY)
            hit = _parse_verdict(verdict)
            if hit is True:
                return True, True, "", shot
            if hit is False and attempt == 1:
                return False, True, "layar tak sesuai harapan (%s)" % expect, shot
        return False, False, "pengecekan tak meyakinkan (%s)" % expect, shot
    except Exception as e:
        return False, False, "cek visual gagal: %s" % e, ""


def _replan(message, steps_log, failed_i, tool, err, plan_steps=None):
    """Susun maksimal 3 langkah lanjutan dari kondisi layar saat ini."""
    try:
        fb = ""
        if plan_steps:
            fb = (plan_steps[failed_i].get("fallback", "") or "")
        shot = actions.screenshot()
        seen = llm.see(shot, "Deskripsikan kondisi layar saat ini dalam 2 kalimat.", API_KEY)
        prompt = ("Tugas awal: %s\nSudah dikerjakan:\n%s\nLangkah %d (%s) gagal: %s\n"
                  "Strategi cadangan: %s\n"
                  "Kondisi layar: %s\nSusun LANJUTAN maksimal 3 langkah dari kondisi ini "
                  "untuk menyelesaikan tugas awal." % (
                      message, "\n".join(steps_log[-6:]), failed_i + 1, tool, err, fb, seen))
        cont = llm.plan(prompt, API_KEY, context=capabilities.describe())
        return cont[:3] if isinstance(cont, list) else []
    except (RuntimeError, OSError):
        return []


def _observe(question):
    """Screenshot + deskripsi singkat. '' jika gagal/offline."""
    if not API_KEY:
        return ""
    try:
        return llm.see(actions.screenshot(), question, API_KEY)
    except (RuntimeError, OSError):
        return ""


def _precheck(s):
    """Cek kesiapan sebelum eksekusi. Hanya aksi sensitif fokus.
    (siap, observasi). Skip jika offline/tanpa target."""
    if s.get("tool") not in FOCUS_TOOLS:
        return True, ""
    need = s.get("expect") or s.get("target")
    if not API_KEY or not need:
        return True, ""
    try:
        shot = actions.screenshot()
        t = llm.see(shot, "Kondisi layar dalam 1 kalimat. Lalu jawab: siap untuk %s %s? YA atau TIDAK."
                     % (s.get("tool", ""), need), API_KEY)
        obs = t.split("YA")[0].split("TIDAK")[0].strip()[:150] or t[:150]
        return _parse_verdict(t) is not False, obs
    except (RuntimeError, OSError):
        return True, ""


def _suggest_next(tool, err):
    e = (err or "").lower()
    if "winerror 5" in e or "access is denied" in e or "permission denied" in e:
        return ("akses tulis ditolak Windows. Jalankan JURU dari flashdisk "
                "(bukan Dokumen/OneDrive yang dilindungi), cek Controlled "
                "Folder Access/antivirus, lalu coba lagi.")
    if tool in ("youtube_oldest", "youtube_play", "open_browser", "open_url"):
        if "tak terinstall" in e or "tak memberi hasil" in e:
            return "coba browser default atau buka halaman channel manual."
        return "halaman channel terlama sudah dibuka di browser, pilih video pertama."
    if tool == "open_app":
        return "coba via Start search atau install dulu aplikasinya."
    return "coba sederhanakan perintah atau tekan Coba lagi."


_FILE_ARTIFACT_TOOLS = ("create_file", "create_docx", "create_xlsx",
                        "create_pdf", "create_pptx",
                        "screenshot", "move_file", "rename_file")


def _artifact_for(tool, args, result):
    """Bangun artifact unduhan untuk balasan chatbot. None bila bukan file."""
    if tool not in _FILE_ARTIFACT_TOOLS:
        return None
    try:
        if tool == "screenshot":
            name = (result or "").rsplit("tersimpan: ", 1)[-1].strip()
            name = os.path.basename(name)
            if not name.lower().endswith(".png"):
                return None
            return {"kind": "image", "name": name,
                    "url": "/api/shot?name=" + name, "label": "Screenshot"}
        p = args.get("path", "") or args.get("dst", "")
        if not p:
            return None
        abs_p, _inside = files.resolve(p)
        name = os.path.basename(abs_p)
        if not name:
            return None
        kind = "file"
        if name.lower().endswith(".png"):
            kind = "image"
        return {"kind": kind, "name": name,
                "url": "/api/file?name=" + name, "label": name}
    except (ValueError, OSError):
        return None


def _react_context():
    """Konteks tiap ronde putusan: kapabilitas + memory proyek."""
    ctx = capabilities.describe()
    mem = project_memory.load_project_memory()
    if mem:
        ctx += "\n" + mem
    return ctx


def handle_react(message, api_key=None, confirmed_step=None, resume=None,
                 emit=None):
    """Loop per-langkah ala koma advance_turn: model putuskan 1 aksi ->
    approval gate -> eksekusi -> observasi masuk konteks -> model putuskan
    lagi, hingga done atau MAX_AGENT_STEPS. Dipakai saat ada API key;
    jalur heuristik/offline tetap untuk mode tanpa key."""
    global API_KEY, _EMIT
    API_KEY = api_key or ""
    steps_log, artifacts, hist = [], [], []

    def log_step(s):
        steps_log.append(s)
        if emit:
            try:
                emit(s)
            except Exception:
                pass

    _EMIT = log_step
    log_step(STATUS[0])
    queue = []
    if resume and resume.get("react"):
        hist = list(resume.get("history", []))
        if resume.get("action") and confirmed_step == resume.get("index"):
            queue.append(resume["action"])
        log_step(STATUS[1] + " (lanjutan reaktif)")
    else:
        log_step(STATUS[1] + " (reaktif)")
        seen0 = _observe("Deskripsikan kondisi layar saat ini dalam 2 kalimat.")
        if seen0:
            hist.append("kondisi awal layar: " + seen0[:200])
    i = 0
    last_fail = None
    while i < MAX_AGENT_STEPS:
        if queue:
            act = queue.pop(0)
            dec = {"tool": act.get("tool", ""),
                   "args": act.get("args", {})}
        else:
            try:
                dec = llm.next_step(message, hist, API_KEY,
                                    context=_react_context())
            except RuntimeError as e:
                log_step("Rencana gagal: %s" % str(e)[:150])
                direct = (llm.ask(message, API_KEY) or "").strip()
                if not direct:
                    return {"reply": ("Model tidak menjawab (respon kosong). "
                                       "Ini gangguan sesaat, tekan Coba lagi."),
                            "steps": steps_log, "needs_confirm": False,
                            "pending": None, "artifacts": artifacts,
                            "retry": True, "original": message}
                return {"reply": direct, "steps": steps_log + [STATUS[5]],
                        "needs_confirm": False, "pending": None,
                        "artifacts": artifacts}
        if dec.get("done"):
            steps_log += [STATUS[3], STATUS[4], STATUS[5]]
            reply = dec.get("reply", "Selesai.")
            if hist and "langkah" not in reply.lower():
                reply = "%s (%d langkah.)" % (reply.rstrip(), len(hist))
            return {"reply": reply, "steps": steps_log,
                    "needs_confirm": False, "pending": None,
                    "artifacts": artifacts}
        tool, args = dec.get("tool", ""), dec.get("args", {})
        valid, _dropped = _validate_plan(
            [{"tool": tool, "args": args if isinstance(args, dict) else {}}])
        if not valid:
            hist.append("%s -> DITOLAK validasi (tool tak dikenal)" % (tool or "?"))
            log_step("Validasi: '%s' ditolak, minta putusan ulang."
                     % (tool or "?"))
            i += 1
            continue
        tool, args = valid[0]["tool"], valid[0]["args"]
        if permissions.needs_confirm(tool, args, False):
            return {"reply": ("Langkah '%s' butuh persetujuanmu (risiko HIGH)."
                              % tool),
                    "steps": steps_log + [STATUS[2] + " menunggu konfirmasi"],
                    "needs_confirm": True, "artifacts": artifacts,
                    "pending": {"react": True, "message": message,
                                "history": hist,
                                "action": {"tool": tool, "args": args},
                                "index": len(hist)}}
        ok, err, result = False, "", ""
        for _ in range(MAX_RETRY + 1):
            try:
                result = run_step(tool, args)
                ok = _verify(tool, args, result)
                err = "verifikasi gagal" if not ok else ""
                if ok:
                    break
            except Exception as e:
                err = str(e)
        if not ok:
            hist.append("%s -> GAGAL: %s" % (tool, err[:200]))
            log_step("%s -> gagal: %s" % (tool, err[:150]))
            # ala koma: gagal beruntun pada aksi IDENTIK = kondisi lingkungan
            # (izin folder, belum login), bukan salah strategi. Berhenti di
            # kegagalan ke-2 agar tak bakar 8 langkah sia-sia seperti kemarin.
            sig = (tool, repr(sorted((args or {}).items())))
            if sig == last_fail:
                steps_log += [STATUS[3], STATUS[4], STATUS[5]]
                return {"reply": ("Langkah '%s' gagal 2x beruntun: %s. "
                                  "Berhenti agar tak mengulang sia-sia. Saran: %s"
                                  % (tool, err[:200],
                                     _suggest_next(tool, err))),
                        "steps": steps_log, "needs_confirm": False,
                        "pending": None, "artifacts": artifacts,
                        "retry": True, "original": message}
            last_fail = sig
            i += 1
            continue
        last_fail = None
        art = _artifact_for(tool, args, result)
        if art and all(a.get("name") != art["name"] for a in artifacts):
            artifacts.append(art)
        line = "%s -> %s" % (tool, str(result).strip()[:300])
        hist.append(line)
        log_step(line)
        i += 1
    steps_log += [STATUS[3], STATUS[4], STATUS[5]]
    return {"reply": ("Berhenti setelah %d langkah (batas). "
                      "Tugas mungkin belum selesai; sederhanakan perintah "
                      "atau kirim kelanjutannya." % MAX_AGENT_STEPS),
            "steps": steps_log, "needs_confirm": False, "pending": None,
            "artifacts": artifacts, "retry": True, "original": message}


def handle(message, api_key=None, confirmed_step=None, resume=None, emit=None):
    """Jalankan perintah atau lanjutkan rencana. pending = {steps, index}.
    emit(line) dipanggil tiap baris status untuk progress live."""
    global API_KEY, _EMIT
    API_KEY = api_key or ""
    steps_log = []
    artifacts = []

    def log_step(s):
        steps_log.append(s)
        if emit:
            try:
                emit(s)
            except Exception:
                pass

    _EMIT = log_step

    log_step(STATUS[0])
    # ala koma: mode normal tanpa langkah perencanaan terpisah — bila ada key,
    # model putuskan per langkah (handle_react). Tanpa key = heuristik/offline.
    if resume and isinstance(resume, dict) and resume.get("react"):
        return handle_react(resume.get("message", message), api_key,
                            confirmed_step, resume, emit)
    if api_key and not resume:
        return handle_react(message, api_key, confirmed_step, None, emit)
    if resume:
        plan_steps, start = resume["steps"], resume["index"]
        log_step(STATUS[1] + " (lanjutan)")
    else:
        plan_steps = heuristic_plan(message)
        if not plan_steps and api_key:
            log_step(STATUS[1] + " (cloud)")
            seen0 = _observe("Deskripsikan kondisi layar saat ini dalam 2 kalimat.")
            ctx = capabilities.describe()
            mem = project_memory.load_project_memory()
            if mem:
                ctx += "\n" + mem
            if seen0:
                ctx += "\nKondisi awal layar: " + seen0
                log_step("Lihat: " + seen0[:150])
            try:
                plan_steps = llm.plan(message, api_key, context=ctx)
            except RuntimeError as e:
                log_step("Rencana gagal: %s" % str(e)[:150])
                if _looks_research(message):
                    summary = web.research(message, api_key, llm.ask)
                    log_step("research -> ringkasan + sumber")
                    return {"reply": summary,
                            "steps": steps_log + [STATUS[5]],
                            "needs_confirm": False, "pending": None, "artifacts": []}
                direct = (llm.ask(message, api_key) or "").strip()
                if not direct:
                    return {"reply": ("Model tidak menjawab (respon kosong). "
                                       "Ini gangguan sesaat, tekan Coba lagi."),
                            "steps": steps_log,
                            "needs_confirm": False, "pending": None, "artifacts": [],
                            "retry": True, "original": message}
                return {"reply": direct,
                        "steps": steps_log + [STATUS[5]],
                        "needs_confirm": False, "pending": None, "artifacts": []}
        elif plan_steps:
            log_step(STATUS[1] + " (lokal)")
        # ala koma process_tools: validasi + potong ke batas agen
        plan_steps, dropped = _validate_plan(plan_steps)
        if dropped:
            log_step("Validasi: %d langkah tak dikenal dibuang." % dropped)
        start = 0
    if not plan_steps:
        return {"reply": ("Aku belum paham perintah itu di mode offline. "
                           "Isi DEEPSEEK_API_KEY untuk perintah bebas, atau coba: "
                           "Buka Notepad, Screenshot, Buka browser."),
                "steps": steps_log, "needs_confirm": False, "pending": None, "artifacts": []}
    i = start
    replan_count = 0
    # batas keras ala koma MAX_AGENT_STEPS: rencana boleh tumbuh via replan,
    # tapi eksekusi tak pernah lewat batas ini.
    while i < len(plan_steps) and (i - start) < MAX_AGENT_STEPS:
        s = plan_steps[i]
        tool, args = s.get("tool", ""), s.get("args", {})
        risk = permissions.classify(tool, args)
        confirmed = confirmed_step == i
        if permissions.needs_confirm(tool, args, confirmed):
            return {"reply": "Langkah %d '%s' menghapus dan butuh persetujuanmu." % (i + 1, tool),
                    "steps": steps_log + [STATUS[2] + " menunggu konfirmasi"],
                    "needs_confirm": True, "artifacts": artifacts,
                    "pending": {"steps": plan_steps, "index": i}}
        ok, err, soft = False, "", ""
        ready, obs = _precheck(s)
        if obs:
            log_step("Lihat: " + obs)
        if not ready:
            time.sleep(4)
            ready2, obs2 = _precheck(s)
            if obs2:
                steps_log.append("Lihat: " + obs2)
            if not ready2:
                steps_log.append("Pra-cek ragu, lanjut eksekusi (verifikasi akhir menentukan).")
        for _ in range(MAX_RETRY + 1):
            try:
                result = run_step(tool, args)
                ok = _verify(tool, args, result)
                err = "verifikasi gagal" if not ok else ""
                if ok and s.get("expect") and API_KEY and tool in GUI_TOOLS:
                    ok, conf, verr, shot = _verify_visual(s["expect"], err)
                    if ok:
                        result += " | cek layar: %s" % os.path.basename(shot)
                    elif not conf:
                        ok = True
                        soft = ("jalan, tapi belum pasti (%s)"
                                % verr[:120])
                        result += " | %s" % soft
                        if shot:
                            result += " | cek layar: %s" % os.path.basename(shot)
                        break
                    else:
                        err = verr
                        if shot:
                            err += " | cek layar: %s" % os.path.basename(shot)
                if ok:
                    break
            except Exception as e:
                err = str(e)
        if not ok:
            # ala koma: replan mengganti langkah gagal, bukan menduplikasi.
            # Maksimal MAX_REPLAN kali agar tak infinite-loop di step yang sama.
            if api_key and not resume and replan_count < MAX_REPLAN:
                cont, dropped2 = _validate_plan(
                    _replan(message, steps_log, i, tool, err, plan_steps))
                if cont:
                    plan_steps[i:i + 1] = cont
                    replan_count += 1
                    log_step(STATUS[1] + " (rencana lanjutan, ganti langkah %d)"
                             % (i + 1))
                    if dropped2:
                        log_step("Validasi lanjutan: %d dibuang." % dropped2)
                    err = ""
                    continue
            return {"reply": ("Langkah %d '%s' gagal: %s. "
                              "Saran: %s" % (i + 1, tool, err,
                              _suggest_next(tool, err))),
                    "steps": steps_log + [STATUS[2], STATUS[3], "Verifikasi gagal."],
                    "needs_confirm": False, "pending": None, "artifacts": artifacts,
                    "retry": True, "original": message}
        art = _artifact_for(tool, args, result)
        if art and all(a.get("name") != art["name"] for a in artifacts):
            artifacts.append(art)
        log_step("%s -> %s%s" % (tool, str(result).strip(),
                                           " | bidik: %s" % s["target"]
                                           if s.get("target") else ""))
        i += 1
    steps_log += [STATUS[3], STATUS[4], STATUS[5]]
    warn = [s for s in steps_log
            if "belum sesuai harapan" in s or "belum pasti" in s]
    done = (len(plan_steps) - start) - len(warn)
    used_youtube_oldest = any(s.get("tool") == "youtube_oldest"
                              for s in plan_steps[start:])
    if warn and done <= 0:
        reply = ("Berjalan %d langkah, tapi tak satu pun terverifikasi visual. "
                 "Kemungkinan gagal (misal klik mendarat di layar yang salah). "
                 "Cek gambar di log." % (len(plan_steps) - start))
    else:
        reply = "Selesai. %d langkah berjalan." % (len(plan_steps) - start)
        if warn:
            reply += " Catatan: %d langkah belum terverifikasi visual, cek gambar di log." % len(warn)
        if used_youtube_oldest:
            reply += (" Halaman video terlama sudah dibuka di browser "
                      "(sort=da); putar video pertama di halaman itu.")
    return {"reply": reply, "steps": steps_log,
            "needs_confirm": False, "pending": None, "artifacts": artifacts}
