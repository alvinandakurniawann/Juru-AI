"""Backend: HTTP server stdlib + scheduler. Sajikan frontend + API."""
import datetime
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from agent import core
from tools import actions, environment, permissions

try:
    from _paths import resource as _res, writable as _wr, exe_dir as _exe
    ROOT = _exe()
    FRONTEND = _res("frontend", "index.html")
    FRONT_ASSETS = _res("frontend")
    HISTORY_FILE = _wr("data", "history.jsonl")
    TASKS_FILE = _wr("data", "tasks.json")
    CONVO_FILE = _wr("data", "conversations.json")
    LOG_FILE = _wr("data", "agent.log")
except ImportError:
    ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    HISTORY_FILE = os.path.join(ROOT, "data", "history.jsonl")
    TASKS_FILE = os.path.join(ROOT, "data", "tasks.json")
    CONVO_FILE = os.path.join(ROOT, "data", "conversations.json")
    LOG_FILE = os.path.join(ROOT, "data", "agent.log")
HISTORY = []
TASKS = []
PROGRESS = {"active": False, "steps": []}
EVENT_SEQ = [0]
SUBS = []
CONVOS = []


def emit_progress(s):
    PROGRESS["steps"].append(s)
    EVENT_SEQ[0] += 1
    for q in list(SUBS):
        q.append((EVENT_SEQ[0], s))


LOG_FILE = LOG_FILE if "LOG_FILE" in dir() else os.path.join(ROOT, "data", "agent.log")


def log(*parts):
    line = "[INFO] " + " ".join(str(p) for p in parts)
    print(line, flush=True)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + line + "\n")
    except OSError:
        pass


def load_env():
    try:
        from _paths import resource as _res2
        cands = [_res2("config", ".env"), _res2(".env")]
    except ImportError:
        cands = (os.path.join(ROOT, "config", ".env"),
                 os.path.join(ROOT, ".env"))
    for name in cands:
        if not os.path.exists(name):
            continue
        with open(name, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def history_add(action, result):
    entry = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "action": action,
             "result": result[:120]}
    HISTORY.append(entry)
    del HISTORY[:-50]
    try:
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def history_load():
    try:
        with open(HISTORY_FILE, encoding="utf-8") as f:
            for line in f:
                try:
                    HISTORY.append(json.loads(line))
                except ValueError:
                    pass
        del HISTORY[:-50]
    except OSError:
        pass


def tasks_load():
    try:
        with open(TASKS_FILE, encoding="utf-8") as f:
            TASKS.extend(json.loads(f.read() or "[]"))
    except (OSError, ValueError):
        pass


def convos_load():
    try:
        with open(CONVO_FILE, encoding="utf-8") as f:
            CONVOS.extend(json.loads(f.read() or "[]"))
    except (OSError, ValueError):
        pass


def convos_save():
    try:
        os.makedirs(os.path.dirname(CONVO_FILE), exist_ok=True)
        with open(CONVO_FILE, "w", encoding="utf-8") as f:
            f.write(json.dumps(CONVOS, ensure_ascii=False))
    except OSError:
        pass


def convo_get(cid):
    for c in CONVOS:
        if c.get("id") == cid:
            return c
    return None


def tasks_save():
    try:
        os.makedirs(os.path.dirname(TASKS_FILE), exist_ok=True)
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            f.write(json.dumps(TASKS, ensure_ascii=False))
    except OSError:
        pass


def _due(t, now):
    if not t.get("enabled"):
        return False
    if t.get("kind") == "every":
        try:
            gap = max(1, int(t.get("every", 60))) * 60
        except (TypeError, ValueError):
            return False
        last = t.get("last_run", 0)
        return now - last >= gap
    if t.get("kind") == "once" and not t.get("done"):
        try:
            at = datetime.datetime.fromisoformat(t["at"]).timestamp()
        except (KeyError, ValueError):
            return False
        return now >= at
    return False


def _run_task(t):
    log("Scheduled run:", t["id"], t["message"][:60])
    try:
        out = core.handle(t["message"], os.environ.get("DEEPSEEK_API_KEY", ""))
        if out.get("needs_confirm"):
            history_add("jadwal-" + t["id"], "dilewati, butuh konfirmasi user")
            t["fails"] = 0
        elif out.get("retry"):
            # shortcut: tugas gagal beruntun (misal belum login/API mati)
            # jangan diulang terus. Mati otomatis setelah 3x, user hidupkan manual.
            fails = int(t.get("fails", 0) or 0) + 1
            t["fails"] = fails
            history_add("jadwal-" + t["id"],
                        "gagal (%d/3): %s" % (fails, out.get("reply", "")[:100]))
            if fails >= 3:
                t["enabled"] = False
                history_add("jadwal-" + t["id"],
                            "dimatikan otomatis setelah 3 gagal beruntun. "
                            "Cek login/API lalu nyalakan lagi di panel Jadwal.")
                log("Task dimatikan otomatis:", t["id"])
        else:
            t["fails"] = 0
            history_add("jadwal-" + t["id"], out.get("reply", "")[:120])
    except Exception as e:
        fails = int(t.get("fails", 0) or 0) + 1
        t["fails"] = fails
        history_add("jadwal-" + t["id"], "gagal: %s" % e)
        if fails >= 3:
            t["enabled"] = False
            history_add("jadwal-" + t["id"], "dimatikan otomatis setelah 3 gagal beruntun.")
    t["last_run"] = time.time()
    t["runs"] = t.get("runs", 0) + 1
    if t.get("kind") == "once":
        t["done"] = True
    tasks_save()


def scheduler_loop():
    # ala koma MAX_SUBAGENTS=5: tugas terjadwal jalan paralel di thread,
    # bukan antre sekuensial. Satu tugas macet tak blokir yang lain.
    import concurrent.futures as _fut
    pool = _fut.ThreadPoolExecutor(max_workers=5, thread_name_prefix="juru-task")
    while True:
        time.sleep(20)
        try:
            now = time.time()
            for t in TASKS:
                if _due(t, now):
                    pool.submit(_run_task, t)
        except Exception as e:
            log("Scheduler error:", e)


class Handler(BaseHTTPRequestHandler):
    server_version = "JURU/1"

    def _json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        try:
            return json.loads(self.rfile.read(
                int(self.headers.get("Content-Length", 0) or 0)).decode("utf-8") or "{}")
        except (ValueError, KeyError):
            return {}

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            try:
                fp = FRONTEND
            except NameError:
                fp = os.path.join(ROOT, "frontend", "index.html")
            return self._file(fp, "text/html")
        if path == "/api/health":
            key = os.environ.get("DEEPSEEK_API_KEY", "")
            return self._json({"ok": True, "bridge": "on",
                               "llm": "deepseek-flash" if key else "belum dikonfigurasi"})
        if path == "/api/history":
            return self._json({"items": HISTORY})
        if path == "/api/tasks":
            return self._json({"items": TASKS})
        if path == "/api/convos":
            return self._json({"items": [
                {"id": c["id"], "title": c.get("title", ""),
                 "updated": c.get("updated", ""),
                 "n": len(c.get("messages", []))} for c in CONVOS]})
        if path == "/api/convo":
            q = urlparse(self.path).query
            cid = ""
            for kv in q.split("&"):
                if kv.startswith("id="):
                    cid = kv[3:]
            c = convo_get(cid)
            if c is None:
                return self._json({"error": "tidak ada"})
            return self._json(c)
        if path == "/api/progress":
            return self._json(PROGRESS)
        if path == "/api/ui":
            # Pengaturan jendela Desktop (selalu-depan + opacity).
            # Mode browser ikut tersimpan, diterapkan saat Desktop jalan.
            try:
                from tools import window as _win
                return self._json(_win.load())
            except ImportError:
                return self._json({"always_on_top": False, "opacity": 100})
        if path == "/api/events":
            return self._events()
        if path == "/api/shot":
            import re
            name = ""
            for kv in urlparse(self.path).query.split("&"):
                if kv.startswith("name="):
                    name = kv[5:]
            if re.fullmatch(r"shot-\d{8}-\d{6}\.png", name or ""):
                try:
                    sp = _wr("data", name)
                except NameError:
                    sp = os.path.join(ROOT, "data", name)
                return self._file(sp, "image/png")
            return self._json({"error": "tidak dikenal"}, 404)
        if path == "/api/file":
            import re
            from urllib.parse import unquote
            name = ""
            for kv in urlparse(self.path).query.split("&"):
                if kv.startswith("name="):
                    name = unquote(kv[5:])
            # shortcut: nama file sederhana dari folder data (anti path traversal)
            if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _.\-]{0,120}", name or "") and ".." not in name:
                try:
                    fp = _wr("data", name)
                except NameError:
                    fp = os.path.join(ROOT, "data", name)
                ctype = "application/octet-stream"
                if name.lower().endswith(".png"):
                    ctype = "image/png"
                elif name.lower().endswith(".txt") or name.lower().endswith(".md"):
                    ctype = "text/plain"
                return self._file(fp, ctype)
            return self._json({"error": "tidak dikenal"}, 404)
        if path == "/assets/AIbackground.jpg":
            try:
                ap = _res("frontend", "assets", "AIbackground.jpg")
            except NameError:
                ap = os.path.join(ROOT, "frontend", "assets", "AIbackground.jpg")
            return self._file(ap, "image/jpeg")
        self._json({"error": "tidak dikenal"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/chat":
            b = self._body()
            msg = b.get("message", "")
            log("User command received:", msg[:80])
            cid = b.get("convo_id") or ""
            c = convo_get(cid) if cid else None
            if c is None and msg and not b.get("resume"):
                c = {"id": "c%d" % int(time.time() * 1000),
                     "title": msg[:40], "created": time.strftime("%Y-%m-%d %H:%M"),
                     "updated": "", "messages": []}
                CONVOS.append(c)
                convos_save()
            PROGRESS["active"] = True
            PROGRESS["steps"] = []
            try:
                out = core.handle(msg,
                                  os.environ.get("DEEPSEEK_API_KEY", ""),
                                  b.get("confirmed_step"),
                                  b.get("resume"),
                                  emit=emit_progress)
                for s in out.get("steps", []):
                    if " -> " in s:
                        history_add(s.split(" -> ", 1)[0], s.split(" -> ", 1)[1])
            except Exception as e:
                out = {"reply": "Gagal: %s" % e, "steps": [], "needs_confirm": False}
            PROGRESS["active"] = False
            if c is not None:
                if msg and not b.get("resume"):
                    c["messages"].append({"who": "Kamu", "text": msg})
                c["messages"].append({"who": "Agen", "text": out.get("reply", ""),
                                      "steps": out.get("steps", []),
                                      "artifacts": out.get("artifacts", [])})
                c["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
                convos_save()
                out["convo_id"] = c["id"]
            log("Task completed:", out["reply"][:80])
            return self._json(out)
        if path == "/api/act":
            b = self._body()
            tool, args = b.get("action", ""), {k: v for k, v in b.items()
                                               if k not in ("action", "confirm")}
            if permissions.needs_confirm(tool, args, b.get("confirm")):
                return self._json({"needs_confirm": True,
                                   "message": "Hapus butuh konfirmasi."})
            try:
                result = core.run_step(tool, args)
                history_add(tool, result)
                log("Action executed:", tool, "->", result[:80])
                return self._json({"message": "OK: " + result})
            except Exception as e:
                return self._json({"message": "Gagal: %s" % e})
        if path == "/api/tasks":
            b = self._body()
            act = b.get("action", "")
            if act == "create":
                msg = (b.get("message", "") or "").strip()
                if not msg:
                    return self._json({"error": "perintah kosong"})
                t = {"id": "t%d" % int(time.time()), "message": msg,
                     "kind": "every" if b.get("kind") == "every" else "once",
                     "enabled": True, "runs": 0, "last_run": time.time()}
                if t["kind"] == "every":
                    try:
                        t["every"] = max(1, int(b.get("every", 60)))
                    except (TypeError, ValueError):
                        return self._json({"error": "menit tidak valid"})
                else:
                    try:
                        datetime.datetime.fromisoformat(b.get("at", ""))
                        t["at"] = b["at"]
                    except ValueError:
                        return self._json({"error": "waktu tidak valid"})
                TASKS.append(t)
                tasks_save()
                log("Task created:", t["id"])
                return self._json({"id": t["id"]})
            if act in ("toggle", "delete"):
                for i, t in enumerate(TASKS):
                    if t.get("id") == b.get("id"):
                        if act == "toggle":
                            t["enabled"] = not t.get("enabled")
                        else:
                            TASKS.pop(i)
                        tasks_save()
                        return self._json({"ok": True})
                return self._json({"error": "jadwal tidak ada"})
            return self._json({"error": "aksi tidak dikenal"})
        if path == "/api/ui":
            b = self._body()
            try:
                from tools import window as _win
                s = _win.save(b)
                top_ok, op_ok, s = _win.apply(s)  # langsung terasa bila Desktop jalan
                s["applied_topmost"] = bool(top_ok)
                s["applied_opacity"] = bool(op_ok)
                return self._json(s)
            except ImportError:
                return self._json({"error": "kontrol jendela tak tersedia"})
        if path == "/api/convos":
            b = self._body()
            act, cid = b.get("action", ""), b.get("id", "")
            c = convo_get(cid)
            if c is None:
                return self._json({"error": "percakapan tidak ada"})
            if act == "rename":
                t = (b.get("title", "") or "").strip()[:60]
                if not t:
                    return self._json({"error": "judul kosong"})
                c["title"] = t
            elif act == "delete":
                CONVOS.remove(c)
            else:
                return self._json({"error": "aksi tidak dikenal"})
            convos_save()
            return self._json({"ok": True})
        self._json({"error": "tidak dikenal"}, 404)

    def _events(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        q = []
        SUBS.append(q)
        try:
            self.wfile.write(b"retry: 3000\n\n")
            self.wfile.flush()
            idle = 0
            while True:
                time.sleep(1)
                while q:
                    i, s = q.pop(0)
                    line = "id: %d\ndata: %s\n\n" % (
                        i, json.dumps(s, ensure_ascii=False))
                    self.wfile.write(line.encode("utf-8"))
                    self.wfile.flush()
                    idle = 0
                idle += 1
                if idle >= 15:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    idle = 0
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            if q in SUBS:
                SUBS.remove(q)

    def _file(self, path, ctype):
        try:
            with open(path, "rb") as f:
                data = f.read()
        except OSError:
            return self._json({"error": "tidak dikenal"}, 404)
        self.send_response(200)
        ct = ctype if ctype.startswith("image/") else ctype + "; charset=utf-8"
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass

    def handle_error(self, request, client_address):
        # Putus SSE/poll tengah jalan reaktif itu normal; jangan cetak traceback.
        import sys as _sys
        exc = _sys.exc_info()[1]
        if isinstance(exc, (ConnectionAbortedError, ConnectionResetError,
                            BrokenPipeError)):
            return
        super().handle_error(request, client_address)


if __name__ == "__main__":
    load_env()
    history_load()
    tasks_load()
    convos_load()
    env = environment.scan()
    log("Environment:", len(env.get("applications", [])), "aplikasi terdeteksi")
    threading.Thread(target=scheduler_loop, daemon=True).start()
    port = int(os.environ.get("PORT", "8787"))
    host = os.environ.get("HOST", "127.0.0.1")
    log("Agent started on port", port,
        "python", "%d-bit" % (8 * __import__("struct").calcsize("P")))
    if host == "0.0.0.0":
        log("LAN terbuka. Buka dari HP (satu WiFi) via salah satu:")
        try:
            import socket
            seen = set()
            for info in socket.getaddrinfo(socket.gethostname(), None):
                ip = (info[4][0] if isinstance(info[4], tuple) else "")
                if ip and not ip.startswith("127.") and ":" not in ip and ip not in seen:
                    seen.add(ip)
                    log("  http://%s:%d/" % (ip, port))
        except OSError:
            pass
        log("Hanya untuk WiFi tepercaya. Matikan (HOST=127.0.0.1) jika ragu.")
    try:
        ThreadingHTTPServer((host, port), Handler).serve_forever()
    except OSError as e:
        log("Port %d tidak bisa dipakai (%s). Tutup jendela backend lain lalu coba lagi."
            % (port, e))
        raise SystemExit(1)
