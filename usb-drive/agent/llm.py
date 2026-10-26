"""Klien DeepSeek (OpenAI-compatible) dengan urllib stdlib. Tanpa pip install."""
import base64
import json
import os
import urllib.request

API_URL = "https://api.deepseek.com/chat/completions"


def _cfg():
    try:
        try:
            from _paths import resource as _res
            cfg_p = _res("config", "agent.json")
        except ImportError:
            here = os.path.dirname(os.path.abspath(__file__))
            cfg_p = os.path.join(here, "..", "config", "agent.json")
        with open(cfg_p, encoding="utf-8") as f:
            return json.loads(f.read() or "{}")
    except (OSError, ValueError):
        return {}


CFG = _cfg()
# Peran model ala koma ModelRole: utama untuk rencana, safeguard (murah/cepat)
# untuk cek visual sekunder. Tanpa config = keduanya model default.
# config/agent.json opsional: {"models": {"main": "...", "safeguard": "..."}}
MODEL = CFG.get("model", "deepseek-flash")
MODEL_MAIN = CFG.get("models", {}).get("main", MODEL) if isinstance(CFG.get("models"), dict) else MODEL
MODEL_SAFE = CFG.get("models", {}).get("safeguard", MODEL_MAIN) if isinstance(CFG.get("models"), dict) else MODEL_MAIN
TOOLS = ("open_app, type_text, click, open_url, open_browser, screenshot, "
         "read_file, create_file, create_docx, create_pdf, create_pptx, "
         "open_file, create_xlsx, list_dir, "
         "make_dir, rename_file, move_file, delete_file, run_shell, hotkey, wait, "
         "start_search, focus_window, open_browser {url, browser chrome|edge|firefox, guest true/false}, "
         "youtube_play {query} putar hasil pertama YouTube, "
         "youtube_oldest {query} buka video PALING LAMA dari channel YouTube, "
         "web_fetch, web_search")
SYSTEM = ("Kamu perencana aksi untuk agen desktop Windows. Jawab HANYA JSON: "
          '{"steps": [{"tool": "<salah satu: ' + TOOLS + '>", '
          '"args": {}, "risk": "LOW|MEDIUM|HIGH", '
          '"target": "elemen UI yang dituju, misal: Blank Document", '
          '"reason": "alasan 8 kata", '
          '"expect": "harapan visual maks 12 kata (HANYA untuk aksi GUI: '
          'open_app/click/type/hotkey/focus/browser; kosongkan untuk operasi '
          'file/web/shell)", '
          '"fallback": "strategi cadangan, misal: tekan Ctrl+N"}]}. '
          "Wajib isi expect untuk open_app, click, type_text, open_browser. "
          "expect = kondisi yang HARUS terlihat SELESAI langkah itu saja, "
          "bukan tujuan akhir tugas. "
          "Aturan args (nama field wajib persis): open_app {app: notepad|calc|word}; "
          "JANGAN pakai open_app untuk browser (chrome/edge/firefox): pakai open_browser. "
          "open_browser {url, browser chrome|edge/firefox opsional, guest true untuk mode tamu} / open_url {url}; type_text {text}; "
          "click {x, y angka}; hotkey {keys, misal ^n untuk Ctrl+N}; "
          "focus_window {title, misal Word}; start_search {query} untuk cari "
          "app/file lewat pencarian Start Windows; "
          "screenshot {}; read_file {path}; create_docx {path, text} untuk dokumen Word; "
          "create_pdf {path, text, title opsional} laporan PDF; "
          "create_pptx {path, text (slide dipisah '# Judul')} presentasi; "
          "open_file {path} membuka dengan aplikasi default; create_xlsx {path, rows teks}; "
          "create_docx {path, text, size angka opsional, bold true/false}: "
          "tafsirkan dulu instruksi format (capslock jadi huruf besar, "
          "font 12 jadi size 12) baru tulis text final; "
          "list_dir {path}; make_dir {path}; rename_file {src, dst}; "
          "create_file {path, content} path di folder data; "
          "move_file {src, dst}; delete_file {path} risk HIGH; "
          "create_xlsx {path, rows}: rows WAJIB data nyata baris-per-baris "
          "(kolom pisah ; ). Bila user minta tabel NxM isi random/acak, "
          "tulis SENDIRI grid acak sebesar itu (angka 1-100), jangan kosong; "
          "run_shell {cmd}; web_fetch {url}; web_search {query}; "
          "youtube_oldest {query nama channel} untuk 'video paling lama/terlama': "
          "JANGAN pakai youtube_play/click koordinat untuk kasus ini. "
          "research {query}. Jangan pakai nama field lain. "
          "Jika user minta kirim pesan, akhiri dengan hotkey {ENTER} setelah "
          "teks terketik; tanpa kata kirim, JANGAN tekan Enter. "
          "Untuk situs dikenal, utamakan navigasi URL langsung daripada klik "
          "koordinat buta: video channel YouTube terlama = "
          "https://www.youtube.com/@HANDLE/videos?view=0&sort=da&flow=grid; "
          "hasil pencarian YouTube = https://www.youtube.com/results?search_query=KATA. "
          "Maksimal 8 langkah. Jangan sertakan teks lain.")


def _post(body, api_key, timeout):
    req = urllib.request.Request(API_URL, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + api_key})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            payload = json.loads(res.read().decode("utf-8"))
        return payload["choices"][0]["message"]["content"]
    except Exception as e:
        raise RuntimeError("LLM tidak terjangkau: %s" % e)


def _extract_json(text):
    """Ambil objek JSON pertama dari teks (tahan fence markdown)."""
    if "```" in text:
        parts = text.split("```")
        text = max(parts, key=len)
        text = text[text.find("{"):text.rfind("}") + 1] if "{" in text else text
    else:
        text = text[text.find("{"):text.rfind("}") + 1] if "{" in text else text
    try:
        data = json.loads(text)
        steps = data["steps"] if isinstance(data, dict) else data
        if isinstance(steps, dict):
            steps = [steps]
        return steps
    except (ValueError, KeyError, TypeError):
        raise RuntimeError("respon LLM bukan JSON rencana: %s" % text[:120])


def plan(message, api_key, model=None, timeout=60, context=""):
    model = model or MODEL_MAIN
    last = "kosong"
    sys = SYSTEM + ("\nKondisi komputer:\n" + context if context else "") + (
        "\nPilih hanya aplikasi yang terinstall. Jika aplikasi ideal tak ada, "
        "pakai alternatif yang ada dan tulis di langkah pertama.")
    for _ in range(3):
        text = _post({"model": model,
                      "messages": [{"role": "system", "content": sys},
                                   {"role": "user", "content": message}],
                      "temperature": 0.2,
                      "max_tokens": 1500,
                      "response_format": {"type": "json_object"}}, api_key, timeout)
        try:
            return _extract_json(text)
        except RuntimeError as e:
            last = str(e)
    raise RuntimeError(last)


def ask(text_prompt, api_key, model=None, timeout=60, max_tokens=800):
    """Tanya jawab bebas (ringkas, riset). Return string."""
    model = model or MODEL_MAIN
    return _post({"model": model,
                  "messages": [{"role": "user", "content": text_prompt}],
                  "temperature": 0.3,
                  "max_tokens": max_tokens}, api_key, timeout)


def see(image_path, question, api_key, model=None, timeout=90):
    """Vision: kirim screenshot, terima deskripsi. Hemat via detail low."""
    model = model or MODEL_SAFE
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    text = _post({"model": model,
                  "messages": [{"role": "user", "content": [
                      {"type": "text", "text": "(Gambar bisa gabungan beberapa monitor "
                       "yang disambung. Perhatikan seluruh gambar.) " + question},
                      {"type": "image_url", "image_url": {
                          "url": "data:image/png;base64," + b64, "detail": "low"}}]}],
                  "temperature": 0.2,
                  "max_tokens": 500}, api_key, timeout)
    return text


NEXT_SYSTEM = ("Kamu pengendali PC Windows yang memutuskan SATU langkah berikutnya. "
               "Jawab HANYA JSON: {\"tool\": \"<nama>\", \"args\": {...}} "
               "atau {\"done\": true, \"reply\": \"ringkasan hasil untuk user\"}. "
               "Tool (nama field args wajib persis): "
               "open_app {app: notepad|calc|word|excel|powerpoint|discord|whatsapp|telegram|spotify}; "
               "open_browser {url} / open_url {url}; type_text {text}; click {x, y angka}; "
               "hotkey {keys, misal ^n}; focus_window {title}; start_search {query}; "
               "screenshot {}; read_file {path}; list_dir {path}; make_dir {path}; "
               "create_file {path, content}; create_docx {path, text} dokumen Word; "
               "create_pdf {path, text, title opsional} laporan PDF; "
               "create_xlsx {path, rows teks (kolom pisah ;)}; "
               "create_pptx {path, text (slide dipisah '# Judul')} presentasi; "
               "open_file {path}; rename_file {src, dst}; move_file {src, dst}; "
               "delete_file {path}; run_shell {cmd}; wait {seconds}; "
               "web_fetch {url}; web_search {query}; youtube_play {query}; "
               "youtube_oldest {query nama channel}; research {query}. "
               "Aturan: JANGAN open_app untuk browser (pakai open_browser). "
               "Untuk 'video paling lama' pakai youtube_oldest. "
               "Untuk tabel NxM acak di create_xlsx, tulis SENDIRI grid acak sebesar itu. "
               "Untuk soal kuis/laporan: research dulu bila perlu fakta, lalu tulis file "
               "(create_docx/create_pdf), akhiri done. Bila tugas selesai jawab done. "
               "Maksimal 1 aksi per jawaban, tanpa teks lain.")


def next_step(task, history, api_key, model=None, timeout=60, context=""):
    """Putuskan SATU langkah berikutnya ala koma advance_turn.

    history: list 'tool -> hasil' yang sudah jalan.
    Return {'tool':..., 'args':...} atau {'done': True, 'reply':...}.
    """
    model = model or MODEL_MAIN
    hist = "\n".join(history[-6:]) if history else "(belum ada langkah)"
    user = ("Tugas: %s\nSudah dikerjakan:\n%s%s\nKeputusan berikutnya?"
            % (task, hist,
               ("\nKondisi komputer:\n" + context if context else "")))
    last = "kosong"
    for _ in range(3):
        text = _post({"model": model,
                      "messages": [{"role": "system", "content": NEXT_SYSTEM},
                                   {"role": "user", "content": user}],
                      "temperature": 0.2,
                      "max_tokens": 800,
                      "response_format": {"type": "json_object"}}, api_key, timeout)
        try:
            frag = text[text.find("{"):text.rfind("}") + 1] if "{" in text else text
            data = json.loads(frag)
            if isinstance(data, dict) and data.get("steps"):
                first = data["steps"][0] if isinstance(data["steps"], list) else data["steps"]
                data = first if isinstance(first, dict) else {}
            if not isinstance(data, dict):
                raise ValueError("bukan objek")
            if data.get("done"):
                return {"done": True,
                        "reply": str(data.get("reply", "Selesai."))[:500]}
            if data.get("tool"):
                args = data.get("args", {})
                return {"tool": str(data["tool"]).strip(),
                        "args": args if isinstance(args, dict) else {}}
            last = "tanpa tool/done: %s" % text[:120]
        except (ValueError, KeyError, TypeError) as e:
            last = str(e)
    raise RuntimeError(last)
