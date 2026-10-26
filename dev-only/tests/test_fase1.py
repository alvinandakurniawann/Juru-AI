"""Test Fase 1. Stdlib saja. Jalankan: py test_fase1.py (dari folder ini)."""
import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "..", "usb-drive"))
sys.path.insert(0, ROOT)
from agent import core
from tools import permissions

PASS = []


def check(name, cond):
    PASS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


# 1. Permission
check("high butuh konfirmasi",
      permissions.needs_confirm("delete_file", {}, False) is True)
check("high lolos setelah konfirmasi",
      permissions.needs_confirm("delete_file", {}, True) is False)
check("open_app itu LOW", permissions.classify("open_app", {}) == "LOW")

# 2. Heuristic planner
check("rencana notepad+ketik 2 langkah",
      len(core.heuristic_plan("Buka Notepad dan ketik Halo Dunia")) == 2)
check("rencana screenshot 1 langkah",
      core.heuristic_plan("Ambil screenshot")[0]["tool"] == "screenshot")

# 3. Perintah tak dikenal tanpa key: panduan, tanpa eksekusi
out = core.handle("lakukan sesuatu yang aneh xyz", api_key="")
check("tak dikenal memberi panduan", "belum paham" in out["reply"])

# 4. Tool tak dikenal ditolak
try:
    core.run_step("teleport", {})
    check("tool asing ditolak", False)
except ValueError:
    check("tool asing ditolak", True)

# 5. Server live
port = "8799"
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
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())

    for _ in range(30):
        try:
            h = call("/api/health")
            if h.get("ok") is True:
                break
            h = None
        except OSError:
            h = None
            time.sleep(0.5)
    check("health ok", h is not None)
    c = call("/api/chat", {"message": "halo test xyz"})
    check("chat menjawab", "reply" in c and "steps" in c)
    a = call("/api/act", {"action": "delete_file", "path": "C:/x"})
    check("HIGH tanpa confirm ditahan", a.get("needs_confirm") is True)
    g = call("/api/history")
    check("history terbaca", "items" in g)
finally:
    srv.terminate()

bad = [n for n, ok in PASS if not ok]
print("---\n%d/%d lolos" % (len(PASS) - len(bad), len(PASS)))
sys.exit(1 if bad else 0)
