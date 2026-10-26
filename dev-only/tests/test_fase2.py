"""Test Fase 2. Stdlib saja. Jalankan: py test_fase2.py (dari folder ini)."""
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
from tools import actions, files, permissions

PASS = []


def check(name, cond):
    PASS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


# 1. File ops di dalam data/
check("create+read data", files.create_file("uji/a.txt", "halo") and
      files.read_file("uji/a.txt") == "halo")
check("move data", files.move_file("uji/a.txt", "uji/b.txt") and
      files.read_file("uji/b.txt") == "halo")
check("delete butuh HIGH", permissions.classify("delete_file", {}) == "HIGH")
files.delete_file("uji/b.txt")
check("delete jalan", not os.path.exists(os.path.join(ROOT, "data", "uji", "b.txt")))

# 2. Kebijakan user: hanya hapus yang ditahan
check("shell MEDIUM jalan otomatis",
      permissions.classify("run_shell", {"cmd": "echo x"}) == "MEDIUM" and
      permissions.needs_confirm("run_shell", {"cmd": "echo x"}, False) is False)
check("kata berbahaya tetap HIGH",
      permissions.needs_confirm("run_shell", {"cmd": "format C:"}, False) is True)

# 3. Path luar data/ + validasi klik virtual desktop
check("path luar HIGH", core._outside_data({"path": "C:/Windows/x.txt"}) is True)
check("path dalam ok", core._outside_data({"path": "catatan.txt"}) is False)
try:
    actions.click(999999, 999999)
    check("klik luar semua layar ditolak", False)
except ValueError as e:
    check("klik luar semua layar ditolak", "semua layar" in str(e))

# 4. Resume multi-step: hapus di tengah ditahan
plan = [{"tool": "screenshot", "args": {}, "risk": "LOW"},
        {"tool": "delete_file", "args": {"path": "uji-tahan.txt"}, "risk": "HIGH"}]
out = core.handle("", resume={"steps": plan, "index": 1},
                  confirmed_step=None)
check("hapus tengah ditahan", out["needs_confirm"] is True and
      out["pending"]["index"] == 1)
files.create_file("uji-tahan.txt", "x")
out2 = core.handle("", resume=out["pending"], confirmed_step=1)
check("resume lanjut + selesai", "Selesai" in out2["reply"])

# 5. Server: file create via act + history permanen
port = "8791"
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

    h = None
    for _ in range(30):
        try:
            h = call("/api/history")
            break
        except OSError:
            time.sleep(0.5)
    check("history terbaca", h is not None and "items" in h)
    a = call("/api/act", {"action": "create_file", "path": "uji2.txt",
                          "content": "fase2", "confirm": True})
    check("create via api", "OK" in a.get("message", ""))
    r = call("/api/act", {"action": "read_file", "path": "uji2.txt",
                          "confirm": True})
    check("read via api", "fase2" in r.get("message", ""))
    s = call("/api/act", {"action": "run_shell", "cmd": "echo halo-fase2"})
    check("shell tanpa confirm jalan", "halo-fase2" in s.get("message", ""))
    s2 = call("/api/act", {"action": "delete_file", "path": "uji2.txt"})
    check("hapus tanpa confirm ditahan", s2.get("needs_confirm") is True)
    d = call("/api/act", {"action": "delete_file", "path": "uji2.txt",
                          "confirm": True})
    check("delete via api", "OK" in d.get("message", ""))
    hist = os.path.join(ROOT, "data", "history.jsonl")
    check("history tersimpan di file", os.path.exists(hist))
finally:
    srv.terminate()

# bersih
import shutil
p = os.path.join(ROOT, "data", "uji")
if os.path.isdir(p):
    shutil.rmtree(p)

bad = [n for n, ok in PASS if not ok]
print("---\n%d/%d lolos" % (len(PASS) - len(bad), len(PASS)))
sys.exit(1 if bad else 0)
