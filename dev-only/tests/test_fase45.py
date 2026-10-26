"""Test Fase 4+5. Stdlib saja. Jalankan: py test_fase45.py (dari folder ini)."""
import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "..", "usb-drive"))
sys.path.insert(0, ROOT)

PASS = []


def check(name, cond):
    PASS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


# Fase 4: HTML memuat voice wiring + fallback
html = open(os.path.join(ROOT, "frontend", "index.html"), encoding="utf-8").read()
check("voice: SpeechRecognition + id-ID", "SpeechRecognition" in html and "id-ID" in html)
check("voice: fallback nonaktif + pesan", "btnVoice" in html and "tidak mendukung" in html)
check("voice: tombol aktif default", 'id="btnVoice">Suara<' in html)

# Fase 5: unit scheduler tanpa server
sys.path.insert(0, os.path.join(ROOT, "backend"))
import server
t = {"id": "x", "message": "halo test xyz", "kind": "every", "every": 1,
     "enabled": True, "runs": 0, "last_run": 0}
check("due saat lewat interval", server._due(t, time.time()) is True)
t2 = dict(t, enabled=False)
check("nonaktif tidak due", server._due(t2, time.time()) is False)
server.TASKS.append(t)
server._run_task(t)
check("jadwal jalan + tercatat",
      t["runs"] == 1 and any(h["action"] == "jadwal-x" for h in server.HISTORY))
server.TASKS.clear()

# Fase 5: API live
port = "8794"
env = dict(os.environ, PORT=port)
srv = subprocess.Popen([sys.executable, os.path.join(ROOT, "backend", "server.py")],
                       env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
try:
    def call(path, data=None):
        if data is None:
            req = urllib.request.Request("http://127.0.0.1:%s%s" % (port, path))
        else:
            req = urllib.request.Request("http://127.0.0.1:%s%s" % (port, path),
                                         data=json.dumps(data).encode(),
                                         headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())

    for _ in range(30):
        try:
            call("/api/tasks")
            break
        except OSError:
            time.sleep(0.5)
    g = call("/api/tasks")
    check("tasks terbaca", "items" in g)
    c = call("/api/tasks", {"action": "create", "message": "halo test xyz",
                            "kind": "every", "every": 60})
    check("task dibuat", "id" in c)
    tid = c.get("id", "?")
    tg = call("/api/tasks", {"action": "toggle", "id": tid})
    check("toggle ok", tg.get("ok") is True)
    dl = call("/api/tasks", {"action": "delete", "id": tid})
    check("delete ok", dl.get("ok") is True)
    bad = call("/api/tasks", {"action": "create", "message": "   ", "kind": "once"})
    check("perintah kosong ditolak", "error" in bad)
finally:
    srv.terminate()
    p = os.path.join(ROOT, "data", "tasks.json")
    if os.path.exists(p):
        os.remove(p)

bad = [n for n, ok in PASS if not ok]
print("---\n%d/%d lolos" % (len(PASS) - len(bad), len(PASS)))
sys.exit(1 if bad else 0)
